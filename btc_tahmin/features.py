"""İndikatör değerlerini okunabilir 'durum' koşullarına çevirir ve hedefleri üretir.

Her koşul bir bool sütundur, adı "aile:durum" biçimindedir (ör. "RSI:30-45").
Aynı aileden iki koşul aynı kombinasyonda kullanılmaz.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .indicators import ema, hepsini_hesapla, rsi, supertrend
from .patterns import formasyonlar


def _bant(s: pd.Series, aile: str, sinirlar: list[float], etiketler: list[str]) -> dict:
    kat = pd.cut(s, [-np.inf] + sinirlar + [np.inf], labels=etiketler)
    return {f"{aile}:{e}": (kat == e) for e in etiketler}


def kosullar(o: pd.DataFrame) -> pd.DataFrame:
    c = o["close"]
    k: dict[str, pd.Series] = {}
    k.update(_bant(o["rsi"], "RSI", [30, 45, 55, 70], ["<30", "30-45", "45-55", "55-70", ">70"]))
    rsi_yon = o["rsi"].diff(2)
    k["RSI_YON:yukari"] = rsi_yon > 0
    k["RSI_YON:asagi"] = rsi_yon <= 0
    k.update(_bant(o["stoch_k"], "STOCH", [20, 80], ["<20", "20-80", ">80"]))
    k["STOCH_KESISIM:yukari"] = (o["stoch_k"] > o["stoch_d"]) & (o["stoch_k"].shift() <= o["stoch_d"].shift())
    k["STOCH_KESISIM:asagi"] = (o["stoch_k"] < o["stoch_d"]) & (o["stoch_k"].shift() >= o["stoch_d"].shift())
    k.update(_bant(o["srsi_k"], "STOCHRSI", [20, 80], ["<20", "20-80", ">80"]))
    h = o["macd_hist"]
    k["MACD_HIST:pozitif_artan"] = (h > 0) & (h > h.shift())
    k["MACD_HIST:pozitif_azalan"] = (h > 0) & (h <= h.shift())
    k["MACD_HIST:negatif_artan"] = (h <= 0) & (h > h.shift())
    k["MACD_HIST:negatif_azalan"] = (h <= 0) & (h <= h.shift())
    k["MACD_KESISIM:yukari"] = (o["macd"] > o["macd_sig"]) & (o["macd"].shift() <= o["macd_sig"].shift())
    k["MACD_KESISIM:asagi"] = (o["macd"] < o["macd_sig"]) & (o["macd"].shift() >= o["macd_sig"].shift())
    k["MACD_SIFIR:ustunde"] = o["macd"] > 0
    k["MACD_SIFIR:altinda"] = o["macd"] <= 0
    k["EMA9_21:boga"] = o["ema9"] > o["ema21"]
    k["EMA9_21:ayi"] = o["ema9"] <= o["ema21"]
    k["EMA21_50:boga"] = o["ema21"] > o["ema50"]
    k["EMA21_50:ayi"] = o["ema21"] <= o["ema50"]
    k["FIYAT_EMA200:ustunde"] = c > o["ema200"]
    k["FIYAT_EMA200:altinda"] = c <= o["ema200"]
    k["EMA_DIZILIM:tam_boga"] = (o["ema9"] > o["ema21"]) & (o["ema21"] > o["ema50"]) & (o["ema50"] > o["ema200"])
    k["EMA_DIZILIM:tam_ayi"] = (o["ema9"] < o["ema21"]) & (o["ema21"] < o["ema50"]) & (o["ema50"] < o["ema200"])
    k.update(_bant(o["bb_pct"], "BOLLINGER", [0, 0.2, 0.8, 1], ["alt_bant_disi", "alt_bolge", "orta", "ust_bolge", "ust_bant_disi"]))
    k["BB_SIKISMA:var"] = o["bb_sikisma"].astype(bool)
    k.update(_bant(o["adx"], "ADX", [20, 30], ["zayif_trend<20", "20-30", "guclu_trend>30"]))
    k["DI:boga"] = o["pdi"] > o["mdi"]
    k["DI:ayi"] = o["pdi"] <= o["mdi"]
    k.update(_bant(o["cci"], "CCI", [-100, 100], ["<-100", "-100..100", ">100"]))
    k.update(_bant(o["mfi"], "MFI", [20, 80], ["<20", "20-80", ">80"]))
    k.update(_bant(o["willr"], "WILLIAMS_R", [-80, -20], ["<-80", "-80..-20", ">-20"]))
    k["SUPERTREND:boga"] = o["supertrend"] > 0
    k["SUPERTREND:ayi"] = o["supertrend"] < 0
    k["ICHIMOKU:bulut_ustu"] = c > o["ichi_ust"]
    k["ICHIMOKU:bulut_alti"] = c < o["ichi_alt"]
    k["ICHIMOKU:bulut_ici"] = (c <= o["ichi_ust"]) & (c >= o["ichi_alt"])
    k["TK:boga"] = o["tenkan"] > o["kijun"]
    k["TK:ayi"] = o["tenkan"] <= o["kijun"]
    k["VWAP:ustunde"] = o["vwap_sapma"] > 0
    k["VWAP:altinda"] = o["vwap_sapma"] <= 0
    k.update(_bant(o["hacim_z"], "HACIM", [-0.5, 1, 2.5], ["dusuk", "normal", "yuksek", "asiri"]))
    k.update(_bant(o["alis_orani"], "ALICI_BASKISI", [0.45, 0.55], ["satici", "dengeli", "alici"]))
    k["OBV:artan"] = o["obv_egim"] > 0
    k["OBV:azalan"] = o["obv_egim"] <= 0
    k.update(_bant(o["atr_pct"].rank(pct=True), "VOLATILITE", [0.33, 0.66], ["dusuk", "orta", "yuksek"]))
    k.update(_bant(o["roc_16"], "MOMENTUM_4S", [-1.5, -0.4, 0.4, 1.5], ["sert_dusus", "dusus", "yatay", "yukselis", "sert_yukselis"]))
    k["KELTNER:ust_disi"] = c > o["keltner_ust"]
    k["KELTNER:alt_disi"] = c < o["keltner_alt"]
    k["SON_MUM:yesil"] = c > o["open"]
    k["SON_MUM:kirmizi"] = c <= o["open"]
    for ad, s in formasyonlar(o).items():
        k[f"FORMASYON_{ad.upper()}:var"] = s

    # Seans / saat (UTC). Asya 00-08, Avrupa 08-13, ABD 13-21, gece 21-24
    saat = o["time"].dt.hour
    seans = pd.cut(saat, [-1, 7, 12, 20, 24], labels=["asya", "avrupa", "abd", "gec_abd"])
    for e in ["asya", "avrupa", "abd", "gec_abd"]:
        k[f"SEANS:{e}"] = seans == e
    k["HAFTA_SONU:evet"] = o["time"].dt.dayofweek >= 5

    # Üst zaman dilimi ve diğer coinler (varsa)
    for kol in [x for x in o.columns if x.startswith("ctx_")]:
        k[kol.replace("ctx_", "").upper().replace("__", ":", 1)] = o[kol].astype(bool)

    df = pd.DataFrame(k).fillna(False).astype(bool)
    return df


def _ince_bant(s: pd.Series, aile: str, sinirlar: list[float]) -> dict:
    """Sayısal değeri dar aralıklara böler: RSI~:35-40 gibi."""
    def f(x):
        return f"{x:g}"
    etiketler = [f"<{f(sinirlar[0])}"] + [f"{f(a)}..{f(b)}" for a, b in zip(sinirlar[:-1], sinirlar[1:])] + [f">{f(sinirlar[-1])}"]
    kat = pd.cut(s, [-np.inf] + sinirlar + [np.inf], labels=etiketler)
    return {f"{aile}~:{e}": (kat == e) for e in etiketler}


INCE_BANTLAR = {
    # aile: (sütun hesaplayıcı, sınırlar)
    "RSI": (lambda o: o["rsi"], list(range(20, 81, 5))),
    "STOCH": (lambda o: o["stoch_k"], list(range(10, 91, 10))),
    "STOCHRSI": (lambda o: o["srsi_k"], list(range(10, 91, 10))),
    "MFI": (lambda o: o["mfi"], list(range(10, 91, 10))),
    "CCI": (lambda o: o["cci"], list(range(-200, 201, 50))),
    "WILLIAMS_R": (lambda o: o["willr"], list(range(-90, -9, 10))),
    "ADX": (lambda o: o["adx"], list(range(10, 51, 5))),
    "BOLLINGER": (lambda o: o["bb_pct"], [-0.2, 0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.2]),
    "MACD_GUC": (lambda o: o["macd_hist"] / o["atr"], [-1, -0.5, -0.2, 0, 0.2, 0.5, 1]),
    "EMA21_UZAKLIK": (lambda o: (o["close"] / o["ema21"] - 1) * 100, [-2, -1, -0.5, -0.2, 0, 0.2, 0.5, 1, 2]),
    "VWAP": (lambda o: o["vwap_sapma"], [-1, -0.5, -0.25, 0, 0.25, 0.5, 1]),
    "MOMENTUM_4S": (lambda o: o["roc_16"], [-3, -2, -1, -0.5, 0, 0.5, 1, 2, 3]),
    "HACIM": (lambda o: o["hacim_z"], [-1, -0.5, 0, 0.5, 1, 2, 3]),
    "ALICI_BASKISI": (lambda o: o["alis_orani"], [0.4, 0.45, 0.5, 0.55, 0.6]),
}


def ince_kosullar(o: pd.DataFrame) -> pd.DataFrame:
    """Derin tarama için ince eşikli koşullar ("RSI 35-40 arası", "CCI -150..-100 arası" ...)."""
    k: dict[str, pd.Series] = {}
    for aile, (fn, sinirlar) in INCE_BANTLAR.items():
        k.update(_ince_bant(fn(o), aile, sinirlar))
    return pd.DataFrame(k).fillna(False).astype(bool)


def ust_zaman_dilimi(df: pd.DataFrame, kural: str, etiket: str) -> pd.DataFrame:
    """1s / 4s trendini hesaplar ve geleceğe bakmadan 15m'ye taşır."""
    g = df.set_index("time").resample(kural, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    u = pd.DataFrame(index=g.index)
    ug = g.reset_index()
    u[f"ctx_{etiket}_trend__boga"] = (ema(g["close"], 21) > ema(g["close"], 50)).to_numpy()
    u[f"ctx_{etiket}_trend__ayi"] = ~u[f"ctx_{etiket}_trend__boga"]
    r = rsi(g["close"], 14)
    u[f"ctx_{etiket}_rsi__asiri_satim"] = (r < 35).to_numpy()
    u[f"ctx_{etiket}_rsi__asiri_alim"] = (r > 65).to_numpy()
    u[f"ctx_{etiket}_supertrend__boga"] = (supertrend(ug).to_numpy() > 0)
    # Üst periyot mumu kapandığı andan itibaren bilgi kullanılabilir.
    # 15m mumunun açılış zamanına göre hizalanır -> geleceğe bakış yok.
    u.index = u.index + pd.Timedelta(kural)
    hizali = u.reindex(df["time"], method="ffill")
    return hizali.reset_index(drop=True).fillna(False).astype(bool)


def baska_coin(ana: pd.DataFrame, diger: pd.DataFrame, etiket: str) -> pd.DataFrame:
    d = diger.set_index("time")["close"].reindex(ana["time"]).ffill()
    a = ana.set_index("time")["close"]
    d_ret = d.pct_change(4)
    a_ret = a.pct_change(4)
    rd = rsi(d, 14)
    out = pd.DataFrame(index=range(len(ana)))
    out[f"ctx_{etiket}_1s__yukari"] = (d_ret > 0.002).to_numpy()
    out[f"ctx_{etiket}_1s__asagi"] = (d_ret < -0.002).to_numpy()
    out[f"ctx_{etiket}_guc__btcden_guclu"] = (d_ret > a_ret).to_numpy()
    out[f"ctx_{etiket}_rsi__gt60"] = (rd > 60).to_numpy()
    out[f"ctx_{etiket}_rsi__lt40"] = (rd < 40).to_numpy()
    # ETH/BTC oranı yükseliyorsa altcoin iştahı
    oran = d / a
    out[f"ctx_{etiket}_btc_parite__yukselis"] = (oran > ema(oran, 50)).to_numpy()
    return out.fillna(False)


def gun_sonu_kapanis(df: pd.DataFrame) -> pd.Series:
    """Her mum için, Türkiye saatine göre o günün son kapanış fiyatı."""
    yerel = df["time"] + pd.Timedelta(hours=config.GUN_SONU_UTC_OFFSET_SAAT)
    gun = yerel.dt.floor("D")
    son = df.groupby(gun)["close"].transform("last")
    # Gün henüz bitmediyse (son gün) hedef bilinmiyor
    son_gun = gun == gun.iloc[-1]
    return son.where(~son_gun)


def mum_suresi(df: pd.DataFrame) -> pd.Timedelta:
    return df["time"].diff().median() if len(df) > 1 else pd.Timedelta("15min")


def gun_sonuna_kalan_saat(df: pd.DataFrame) -> pd.Series:
    """Mum kapandıktan (karar anından) sonra TSİ gün sonuna kalan saat."""
    kapanis = df["time"] + mum_suresi(df) + pd.Timedelta(hours=config.GUN_SONU_UTC_OFFSET_SAAT)
    gece = kapanis.dt.floor("D")
    kalan = (gece + pd.Timedelta(days=1) - kapanis).dt.total_seconds() / 3600
    return kalan.where(kalan < 24, 0.0)   # tam gece yarısı kapanan mum: gün bitti


def veri_seti_hazirla(mumlar: dict[str, pd.DataFrame], ana: str = config.ANA_SEMBOL):
    """Ana coin için tüm indikatörleri, bağlam koşullarını ve hedefleri hazırlar."""
    df = mumlar[ana].copy().reset_index(drop=True)
    parcalar = [df]
    parcalar.append(ust_zaman_dilimi(df, "1h", "1s"))
    parcalar.append(ust_zaman_dilimi(df, "4h", "4s"))
    for sembol, d in mumlar.items():
        if sembol != ana and d is not None and not d.empty:
            parcalar.append(baska_coin(df, d, sembol.replace("USDT", "")))
    birlesik = pd.concat(parcalar, axis=1)
    o = hepsini_hesapla(birlesik)
    k = kosullar(o)

    hedef = pd.DataFrame(index=o.index)
    sonraki = o["close"].shift(-1) - o["open"].shift(-1)
    hedef["sonraki_yesil"] = (sonraki > 0).astype(float).where(sonraki.notna())
    gs = gun_sonu_kapanis(o)
    # Gün sonuna çok az kalmışsa hedef anlamsız: günün son mumunda "gün sonu" o mumun kendi
    # kapanışıdır ve hedef her zaman "yükselmedi" çıkar. Model bunu ezberleyip sahte isabet üretir.
    gs = gs.where(gun_sonuna_kalan_saat(o) >= config.GUN_SONU_MIN_KALAN_SAAT)
    hedef["gun_sonu_yukari"] = (gs > o["close"]).astype(float).where(gs.notna())
    hedef["gun_sonu_getiri"] = (gs / o["close"] - 1) * 100
    # Gün sonuna kadar en kötü düşüş (long için) %
    yerel = o["time"] + pd.Timedelta(hours=config.GUN_SONU_UTC_OFFSET_SAAT)
    gun = yerel.dt.floor("D")
    ters_min = o["low"][::-1].groupby(gun[::-1]).cummin()[::-1]
    sonraki_min = ters_min.groupby(gun).shift(-1)
    hedef["gun_ici_max_dusus"] = ((sonraki_min / o["close"] - 1) * 100).where(gs.notna())
    # Gün sonuna kadar en yüksek yükseliş (short için en kötü durum) %
    ters_max = o["high"][::-1].groupby(gun[::-1]).cummax()[::-1]
    sonraki_max = ters_max.groupby(gun).shift(-1)
    hedef["gun_ici_max_yukselis"] = ((sonraki_max / o["close"] - 1) * 100).where(gs.notna())

    # Çok mumlu hedefler (derin tarama): N mum sonra fiyat, sonraki N mumun hepsi aynı renk
    c = o["close"]
    for n in config.ILERI_MUMLAR:
        ileri = c.shift(-n)
        hedef[f"ileri_{n}"] = (ileri > c).astype(float).where(ileri.notna())
        hedef[f"ileri_{n}_fiyat"] = ileri
    yesil = (o["close"] > o["open"]).astype(float)
    kirmizi = (o["close"] < o["open"]).astype(float)
    for n in config.SERI_MUMLAR:
        gy = sum(yesil.shift(-i) for i in range(1, n + 1))
        gk = sum(kirmizi.shift(-i) for i in range(1, n + 1))
        hedef[f"seri_{n}_yesil"] = (gy == n).astype(float).where(gy.notna())
        hedef[f"seri_{n}_kirmizi"] = (gk == n).astype(float).where(gk.notna())
    hedef["gun_sonu_fiyat"] = gs

    # ısınma dönemi (EMA200 vb.) dışarı
    gecerli = o.index >= 250
    return o[gecerli].reset_index(drop=True), k[gecerli].reset_index(drop=True), hedef[gecerli].reset_index(drop=True)
