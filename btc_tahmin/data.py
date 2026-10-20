"""Binance'ten mum verisi indirme + yerel önbellek."""
from __future__ import annotations

import time

import pandas as pd
import requests

from . import config

KOLONLAR = ["open_time", "open", "high", "low", "close", "volume", "close_time",
            "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]


def _get(path: str, params: dict) -> list:
    son_hata = None
    for taban in config.BINANCE_SPOT:
        for deneme in range(3):
            try:
                r = requests.get(taban + path, params=params, timeout=config.HTTP_TIMEOUT)
                if r.status_code == 429:
                    time.sleep(5 * (deneme + 1))
                    continue
                r.raise_for_status()
                return r.json()
            except requests.RequestException as e:  # bir sonraki tabanı/denemeyi dene
                son_hata = e
                time.sleep(1 + deneme)
    raise RuntimeError(f"Binance verisi alınamadı: {son_hata}")


def _indir(sembol: str, aralik: str, baslangic_ms: int) -> pd.DataFrame:
    satirlar = []
    simdi_ms = int(time.time() * 1000)
    while baslangic_ms < simdi_ms:
        parca = _get("/api/v3/klines", {"symbol": sembol, "interval": aralik,
                                        "startTime": baslangic_ms, "limit": 1000})
        if not parca:
            break
        satirlar.extend(parca)
        baslangic_ms = parca[-1][0] + 1
        if len(parca) < 1000:
            break
        time.sleep(0.15)
    df = pd.DataFrame(satirlar, columns=KOLONLAR)
    if df.empty:
        return df
    for k in ["open", "high", "low", "close", "volume", "quote_volume", "taker_buy_base"]:
        df[k] = df[k].astype(float)
    df["trades"] = df["trades"].astype(int)
    df["time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    return df[["time", "open", "high", "low", "close", "volume", "quote_volume",
               "trades", "taker_buy_base"]]


FUNDING_HATA: dict[str, str] = {}


def funding_gecmisi(sembol: str, gun: int = config.GECMIS_GUN, guncelle: bool = True) -> pd.DataFrame:
    """Binance vadeli funding oranı geçmişi (8 saatte bir). Önbellek: veri/<sembol>_funding.csv. Hata olursa boş döner."""
    config.VERI_DIR.mkdir(parents=True, exist_ok=True)
    dosya = config.VERI_DIR / f"{sembol}_funding.csv"
    eski = pd.DataFrame(columns=["time", "funding"])
    if dosya.exists():
        eski = pd.read_csv(dosya)
        eski["time"] = pd.to_datetime(eski["time"], utc=True)
    bas = int((time.time() - gun * 86400) * 1000)
    if not eski.empty:
        bas = max(bas, int(eski["time"].iloc[-1].timestamp() * 1000) + 1)
    if guncelle:
        satirlar = []
        try:
            while True:
                r = requests.get(config.BINANCE_FUTURES + "/fapi/v1/fundingRate",
                                 params={"symbol": sembol, "startTime": bas, "limit": 1000}, timeout=config.HTTP_TIMEOUT)
                r.raise_for_status()
                parca = r.json()
                if not parca:
                    break
                satirlar += [(int(x["fundingTime"]), float(x["fundingRate"])) for x in parca]
                bas = int(parca[-1]["fundingTime"]) + 1
                if len(parca) < 1000:
                    break
            FUNDING_HATA.pop(sembol, None)
        except (requests.RequestException, ValueError, KeyError) as e:
            FUNDING_HATA[sembol] = str(e)[:120]
        if satirlar:
            yeni = pd.DataFrame(satirlar, columns=["ms", "funding"])
            yeni["time"] = pd.to_datetime(yeni["ms"], unit="ms", utc=True).dt.floor("5min")   # funding saati mum açılışına hizalanır
            eski = pd.concat([eski, yeni[["time", "funding"]]]).drop_duplicates("time").sort_values("time")
            eski.to_csv(dosya, index=False)
    return eski.reset_index(drop=True)


def funding_ekle(df: pd.DataFrame, sembol: str, guncelle: bool = True) -> pd.DataFrame:
    """Mum tablosuna 'funding' sütunu ekler: funding ödeme anına denk gelen mumda oran (ondalık), diğerlerinde 0."""
    if config.ISLEM_TURU != "vadeli" or df.empty:
        return df
    f = funding_gecmisi(sembol, guncelle=guncelle)
    if f.empty:
        return df
    sure = df["time"].diff().median() if len(df) > 1 else pd.Timedelta("15min")
    hizali = f.copy()
    hizali["time"] = hizali["time"].dt.floor(sure)
    seri = hizali.groupby("time")["funding"].sum()
    df = df.copy()
    df["funding"] = df["time"].map(seri).fillna(0.0)
    return df


def mumlari_getir(sembol: str, aralik: str = "15m", gun: int = config.GECMIS_GUN,
                  guncelle: bool = True) -> pd.DataFrame:
    """Önbellekten okur, eksik kısmı indirir. 10m için 5m indirip birleştirir."""
    if aralik == "10m":
        return _yeniden_ornekle(mumlari_getir(sembol, "5m", gun, guncelle), "10min")

    config.VERI_DIR.mkdir(parents=True, exist_ok=True)
    # v2: önbelleğe yalnızca kapanmış mumlar yazılır (v1 yarım mumları da kaydediyordu)
    dosya = config.VERI_DIR / f"{sembol}_{aralik}_v2.csv"
    eski = pd.DataFrame()
    baslangic_ms = int((time.time() - gun * 86400) * 1000)
    if dosya.exists():
        eski = pd.read_csv(dosya, parse_dates=["time"])
        eski["time"] = pd.to_datetime(eski["time"], utc=True)
        if not eski.empty:
            baslangic_ms = max(baslangic_ms, int(eski["time"].iloc[-1].timestamp() * 1000) + 1)
    if guncelle:
        yeni = _indir(sembol, aralik, baslangic_ms)
        df = pd.concat([eski, yeni]) if not eski.empty and not yeni.empty else (yeni if eski.empty else eski)
    else:
        df = eski
    df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    sinir = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=gun)
    df = _kapanmamis_mumu_at(df[df["time"] >= sinir].reset_index(drop=True), aralik)
    df.to_csv(dosya, index=False)
    return funding_ekle(df, sembol, guncelle)


def _kapanmamis_mumu_at(df: pd.DataFrame, aralik: str) -> pd.DataFrame:
    """Son mum henüz kapanmadıysa analizden çıkar (yanıltıcı sinyal vermesin)."""
    if df.empty:
        return df
    sure = pd.Timedelta(aralik.replace("m", "min"))
    if df["time"].iloc[-1] + sure > pd.Timestamp.now(tz="UTC"):
        return df.iloc[:-1].reset_index(drop=True)
    return df


def _yeniden_ornekle(df: pd.DataFrame, kural: str) -> pd.DataFrame:
    g = df.set_index("time").resample(kural, label="left", closed="left")
    out = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
        "close": g["close"].last(), "volume": g["volume"].sum(),
        "quote_volume": g["quote_volume"].sum(), "trades": g["trades"].sum(),
        "taker_buy_base": g["taker_buy_base"].sum(),
        **({"funding": g["funding"].sum()} if "funding" in df.columns else {}),
    }).dropna().reset_index()
    # 5m'lik parçaların hepsi gelmediyse son 10m mumu yarımdır
    sayim = g["close"].count().reset_index(drop=True)
    if len(sayim) and sayim.iloc[-1] < 2:
        out = out.iloc[:-1]
    return out.reset_index(drop=True)
