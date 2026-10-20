"""Ek piyasa verileri: makro (Nasdaq, S&P, DXY, altın, ABD 10Y), otomatik ekonomik takvim,
opsiyon (put/call, max pain), ETF akışları, likidasyon tahmini.

Her fonksiyon iki parçalı: ağdan ham veriyi çeken kısım ve ağdan bağımsız ayrıştırıcı (test edilebilir).
Hepsi modellere GİRMEZ; bağlam ve genel puan kırımı için kullanılır.
"""
from __future__ import annotations

import html as _html
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

from . import config

TARAYICI = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0 Safari/537.36", "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}


def _get(url, params=None, json_mu=True):
    son = None
    for i in range(3):
        try:
            r = requests.get(url, params=params, headers=TARAYICI, timeout=config.HTTP_TIMEOUT)
            if r.status_code == 429 and i < 2:
                import time
                time.sleep(3 * (i + 1))
                continue
            if r.status_code in (401, 403, 451):
                raise RuntimeError(f"erişim engellendi ({r.status_code})")
            r.raise_for_status()
            return r.json() if json_mu else r.text
        except requests.RequestException as e:
            son = e
    raise RuntimeError(str(son))


# ------------------------------------------------------------------ makro
MAKRO = {   # ad: (Yahoo sembolü, açıklama)
    "Nasdaq 100 vadeli": ("NQ=F", "Teknoloji hisseleri. BTC çoğu gün bununla aynı yönde hareket eder."),
    "S&P 500 vadeli": ("ES=F", "ABD borsası genel risk iştahı."),
    "Dolar endeksi (DXY)": ("DX-Y.NYB", "Dolar güçlenince kripto genelde baskılanır (ters ilişki)."),
    "Altın": ("GC=F", "Güvenli liman talebi."),
    "ABD 10Y faiz": ("^TNX", "Faiz yükselişi riskli varlıklar için olumsuz."),
}


def yahoo_ayristir(veri: dict) -> pd.Series:
    """Yahoo chart API yanıtından saatlik kapanış serisi (UTC)."""
    r = veri["chart"]["result"][0]
    t = pd.to_datetime(r["timestamp"], unit="s", utc=True)
    c = r["indicators"]["quote"][0]["close"]
    return pd.Series(c, index=t, dtype=float).dropna()


def makro() -> dict:
    sonuc, hatalar = {}, {}
    for ad, (sembol, ne) in MAKRO.items():
        try:
            veri = None
            for host in ("query1", "query2"):
                try:
                    veri = _get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{sembol}",
                                {"interval": "1h", "range": "10d"})
                    break
                except RuntimeError:
                    if host == "query2":
                        raise
            s = yahoo_ayristir(veri)
            once = s[s.index <= s.index[-1] - pd.Timedelta(hours=24)]
            sonuc[ad] = {"sembol": sembol, "deger": round(float(s.iloc[-1]), 4), "aciklama": ne,
                         "degisim_24s": round(float(s.iloc[-1] / once.iloc[-1] - 1) * 100, 2) if len(once) else None,
                         "zaman": s.index[-1].isoformat(),
                         "seri": [[int(i.timestamp()), float(v)] for i, v in s.items()]}
        except Exception as e:  # noqa: BLE001
            hatalar[ad] = str(e)[:160]
    if not sonuc:
        raise RuntimeError("Makro veri alınamadı: " + "; ".join(f"{k}: {v}" for k, v in hatalar.items()))
    return {"veriler": sonuc, "hatalar": hatalar}


def btc_korelasyonu(makro_veri: dict, btc: pd.DataFrame) -> dict:
    """Son ~10 günde BTC saatlik getirileri ile makro göstergelerin saatlik getirileri arası korelasyon."""
    b = btc.set_index("time")["close"].resample("1h").last().pct_change()
    out = {}
    for ad, v in (makro_veri or {}).get("veriler", {}).items():
        s = pd.Series({pd.Timestamp(t, unit="s", tz="UTC"): x for t, x in v.get("seri", [])}).pct_change()
        ortak = pd.concat([b, s], axis=1, join="inner").dropna()
        if len(ortak) >= 30:
            out[ad] = round(float(ortak.corr().iloc[0, 1]), 2)
    return out


# ------------------------------------------------------------------ ekonomik takvim
def takvim_ayristir(liste: list[dict], ulkeler=("USD",)) -> list[dict]:
    out = []
    for e in liste:
        if e.get("country") not in ulkeler or e.get("impact") not in ("High", "Medium"):
            continue
        try:
            t = datetime.fromisoformat(e["date"]).astimezone(timezone.utc)
        except (KeyError, ValueError):
            continue
        out.append({"tarih": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "ad": f"{e.get('country')} {e.get('title', '')}".strip(),
                    "etki": "yuksek" if e["impact"] == "High" else "orta",
                    "beklenti": e.get("forecast") or None, "onceki": e.get("previous") or None, "kaynak": "otomatik"})
    return out


def ekonomik_takvim() -> list[dict]:
    olaylar, hata = [], None
    for hafta in ("thisweek", "nextweek"):
        try:
            olaylar += takvim_ayristir(_get(f"https://nfs.faireconomy.media/ff_calendar_{hafta}.json"))
        except Exception as e:  # noqa: BLE001
            hata = e
    if not olaylar and hata:
        raise RuntimeError(str(hata))
    return olaylar


# ------------------------------------------------------------------ opsiyon (Deribit)
_AY = {a: i + 1 for i, a in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}


def _vade(s: str) -> datetime | None:
    m = re.match(r"(\d{1,2})([A-Z]{3})(\d{2})$", s)
    if not m:
        return None
    return datetime(2000 + int(m.group(3)), _AY[m.group(2)], int(m.group(1)), 8, tzinfo=timezone.utc)


def opsiyon_ayristir(liste: list[dict], simdi: datetime | None = None) -> dict:
    """Deribit kitap özetinden put/call oranı ve en yakın büyük vadenin max pain seviyesi."""
    simdi = simdi or datetime.now(timezone.utc)
    satir = []
    for x in liste:
        p = x.get("instrument_name", "").split("-")
        if len(p) != 4:
            continue
        v = _vade(p[1])
        if v is None or v < simdi:
            continue
        satir.append({"vade": v, "strike": float(p[2]), "tip": p[3], "oi": float(x.get("open_interest") or 0),
                      "fiyat": float(x.get("underlying_price") or 0)})
    if not satir:
        raise RuntimeError("opsiyon verisi boş")
    df = pd.DataFrame(satir)
    put = df.loc[df["tip"] == "P", "oi"].sum()
    call = df.loc[df["tip"] == "C", "oi"].sum()
    # "Büyük" vade: toplam açık pozisyonun en az %5'ini taşıyan en yakın vade
    vadeler = df.groupby("vade")["oi"].sum().sort_index()
    buyuk = vadeler[vadeler >= vadeler.sum() * 0.05]
    vade = buyuk.index[0] if len(buyuk) else vadeler.index[0]
    d = df[df["vade"] == vade]
    strikes = np.sort(d["strike"].unique())
    c = d[d["tip"] == "C"]
    pt = d[d["tip"] == "P"]
    aci = [float((c["oi"] * np.maximum(0, k - c["strike"])).sum() + (pt["oi"] * np.maximum(0, pt["strike"] - k)).sum())
           for k in strikes]
    return {"put_call_orani": round(float(put / call), 3) if call else None,
            "vade": vade.isoformat(), "vade_saat_kaldi": round((vade - simdi).total_seconds() / 3600, 1),
            "vade_oi_payi": round(float(vadeler[vade] / vadeler.sum()), 3),
            "max_pain": float(strikes[int(np.argmin(aci))]), "spot": round(float(d["fiyat"].iloc[0]), 2)}


def opsiyon(para: str) -> dict:
    v = _get("https://www.deribit.com/api/v2/public/get_book_summary_by_currency", {"currency": para, "kind": "option"})
    return opsiyon_ayristir(v["result"])


# ------------------------------------------------------------------ ETF akışları (Farside, deneysel)
def _hucre(h: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", h)).replace("\xa0", " ").strip()


def etf_ayristir(sayfa: str, gun: int = 7) -> list[dict]:
    """Farside tablo sayfasından günlük toplam net akış (milyon $). Negatifler parantezli yazılır."""
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", sayfa, flags=re.S | re.I):
        hucreler = [_hucre(h) for h in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S | re.I)]
        if len(hucreler) < 3 or not re.match(r"^\d{1,2} [A-Za-z]{3} \d{4}$", hucreler[0]):
            continue
        toplam = hucreler[-1].replace(",", "")
        if toplam in ("", "-"):
            continue
        neg = toplam.startswith("(") and toplam.endswith(")")
        try:
            deger = float(toplam.strip("()")) * (-1 if neg else 1)
        except ValueError:
            continue
        out.append({"tarih": datetime.strptime(hucreler[0], "%d %b %Y").strftime("%Y-%m-%d"), "net_milyon_usd": deger})
    return out[-gun:]


def etf_akislari() -> dict:
    sonuc, hatalar = {}, {}
    for ad, url in (("BTC", "https://farside.co.uk/bitcoin-etf-flow-all-data/"),
                    ("ETH", "https://farside.co.uk/ethereum-etf-flow-all-data/")):
        try:
            gunler = etf_ayristir(_get(url, json_mu=False))
            if not gunler:
                raise RuntimeError("tablo okunamadı (site yapısı değişmiş ya da bot koruması)")
            sonuc[ad] = {"gunler": gunler, "son": gunler[-1], "toplam_5g": round(sum(g["net_milyon_usd"] for g in gunler[-5:]), 1)}
        except Exception as e:  # noqa: BLE001
            hatalar[ad] = str(e)[:160]
    if not sonuc:
        raise RuntimeError("; ".join(f"{k}: {v}" for k, v in hatalar.items()))
    return {"veriler": sonuc, "hatalar": hatalar}


# ------------------------------------------------------------------ likidasyon tahmini
def likidasyon_tahmini(oi_1s: float | None, fiyat_1s: float | None) -> str | None:
    """Açık pozisyon 1 saatte sertçe düşerken fiyat da sert hareket ettiyse büyük olasılıkla
    zorunlu kapanışlar (likidasyon) yaşanmıştır. Ücretsiz likidasyon verisi olmadığı için tahmindir."""
    if oi_1s is None or fiyat_1s is None or oi_1s > -2.5:
        return None
    if fiyat_1s <= -1.2:
        return "Olası LONG likidasyon dalgası (OI ve fiyat birlikte sert düştü)"
    if fiyat_1s >= 1.2:
        return "Olası SHORT sıkışması (OI düşerken fiyat sert yükseldi)"
    return None
