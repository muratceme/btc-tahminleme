"""Fable sinyalleri: klasik, şeffaf, kuralları önceden yazılmış dört strateji.

Madencilikten farkı: bu kurallar veriden "bulunmadı", baştan yazıldı. Dolayısıyla seçim yanlılığı
(testte tutanı seçme) yoktur; bütün geçmişteki sonuç olduğu gibi gösterilir. Her strateji tek pozisyon
taşır: pozisyon açıkken yeni sinyal atlanır. Çıkış kuralı stratejinin parçasıdır (zamanla ya da koşulla).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, performans

_BOS = "sz-bos"


def _kesisim_yukari(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a > b) & (a.shift() <= b.shift())


def _trend(o: pd.DataFrame):
    """Trend takibi: EMA dizilimi + Supertrend + ADX. Giriş, dizilim yeni oluştuğunda; çıkış Supertrend dönünce."""
    boga = (o["ema9"] > o["ema21"]) & (o["ema21"] > o["ema50"]) & (o["supertrend"] > 0) & (o["adx"] > 20) & (o["vwap_sapma"] > 0)
    ayi = (o["ema9"] < o["ema21"]) & (o["ema21"] < o["ema50"]) & (o["supertrend"] < 0) & (o["adx"] > 20) & (o["vwap_sapma"] < 0)
    long_ = boga & ~boga.shift(fill_value=False)
    short = ayi & ~ayi.shift(fill_value=False)
    st = o["supertrend"].to_numpy()

    def cikis(i, yon):
        for j in range(i + 1, min(i + 24, len(o) - 1) + 1):
            if (yon == "LONG" and st[j] < 0) or (yon == "SHORT" and st[j] > 0):
                return j
        return i + 24 if i + 24 <= len(o) - 1 else None
    return long_, short, cikis, 24


def _donus(o: pd.DataFrame):
    """Ortalamaya dönüş: üst zaman dilimi trendi yönünde, aşırı satım/alımdan dönüş. Çıkış: BB orta banda dönünce ya da 8 mum."""
    ust = o["ctx_1s_trend__boga"].astype(bool) if "ctx_1s_trend__boga" in o else pd.Series(True, index=o.index)
    long_ = (o["rsi"] < 32) & (o["bb_pct"] < 0.05) & ust & (o["close"] > o["open"])          # dip + yeşil mum (dönüş teyidi)
    short = (o["rsi"] > 68) & (o["bb_pct"] > 0.95) & ~ust & (o["close"] < o["open"])
    bb = o["bb_pct"].to_numpy()

    def cikis(i, yon):
        for j in range(i + 1, min(i + 8, len(o) - 1) + 1):
            if (yon == "LONG" and bb[j] >= 0.5) or (yon == "SHORT" and bb[j] <= 0.5):
                return j
        return i + 8 if i + 8 <= len(o) - 1 else None
    return long_, short, cikis, 8


def _kirilim(o: pd.DataFrame):
    """Kırılım: Bollinger sıkışması sonrası hacimli Keltner kırılımı. Çıkış: 8 mum sonra."""
    sikisti = o["bb_sikisma"].astype(bool).rolling(6, min_periods=1).max().shift(fill_value=0).astype(bool)
    long_ = sikisti & (o["close"] > o["keltner_ust"]) & (o["close"].shift() <= o["keltner_ust"].shift()) & (o["hacim_z"] > 1)
    short = sikisti & (o["close"] < o["keltner_alt"]) & (o["close"].shift() >= o["keltner_alt"].shift()) & (o["hacim_z"] > 1)

    def cikis(i, yon):
        return i + 8 if i + 8 <= len(o) - 1 else None
    return long_, short, cikis, 8


def _momentum(o: pd.DataFrame):
    """Momentum: MACD kesişimi + 4 saatlik trend + alıcı baskısı + stokastik aynı yönde. Çıkış: MACD geri kesince ya da 12 mum."""
    ust4 = o["ctx_4s_trend__boga"].astype(bool) if "ctx_4s_trend__boga" in o else pd.Series(True, index=o.index)
    long_ = _kesisim_yukari(o["macd"], o["macd_sig"]) & ust4 & (o["alis_orani"] > 0.5) & (o["stoch_k"] > o["stoch_d"]) & (o["stoch_k"] < 80)
    short = _kesisim_yukari(o["macd_sig"], o["macd"]) & ~ust4 & (o["alis_orani"] < 0.5) & (o["stoch_k"] < o["stoch_d"]) & (o["stoch_k"] > 20)
    m, s = o["macd"].to_numpy(), o["macd_sig"].to_numpy()

    def cikis(i, yon):
        for j in range(i + 1, min(i + 12, len(o) - 1) + 1):
            if (yon == "LONG" and m[j] < s[j]) or (yon == "SHORT" and m[j] > s[j]):
                return j
        return i + 12 if i + 12 <= len(o) - 1 else None
    return long_, short, cikis, 12


STRATEJILER = [
    {"id": "trend", "ad": "Trend takibi", "uret": _trend, "renk": "#60a5fa",
     "ozet": "Trend yeni başladığında bin, Supertrend dönünce in.",
     "kurallar": ["LONG: EMA9 > EMA21 > EMA50 dizilimi yeni oluştu, Supertrend boğa, ADX > 20 (trend var), fiyat VWAP üstünde",
                  "SHORT: tam tersi dizilim yeni oluştu, Supertrend ayı, ADX > 20, fiyat VWAP altında",
                  "ÇIKIŞ: Supertrend yön değiştirince; en geç 24 mum (6 saat) sonra"]},
    {"id": "donus", "ad": "Ortalamaya dönüş", "uret": _donus, "renk": "#f472b6",
     "ozet": "Büyük trend yönünde, aşırı satım/alımdan dönen mumu yakala.",
     "kurallar": ["LONG: 1 saatlik trend yukarı, RSI < 32, fiyat Bollinger alt bandında (%B < 0,05) ve mum yeşil kapandı (dönüş teyidi)",
                  "SHORT: 1 saatlik trend aşağı, RSI > 68, fiyat üst bantta (%B > 0,95) ve mum kırmızı kapandı",
                  "ÇIKIŞ: fiyat Bollinger orta bandına dönünce; en geç 8 mum (2 saat) sonra"]},
    {"id": "kirilim", "ad": "Sıkışma kırılımı", "uret": _kirilim, "renk": "#fbbf24",
     "ozet": "Daralan bantlardan hacimle çıkan ilk mumu takip et.",
     "kurallar": ["Son 6 mumda Bollinger sıkışması vardı (bantlar Keltner içine girdi)",
                  "LONG: kapanış Keltner üst bandını yukarı kırdı ve hacim normalin 1 standart sapma üstünde",
                  "SHORT: kapanış Keltner alt bandını aşağı kırdı ve hacim yüksek",
                  "ÇIKIŞ: 8 mum (2 saat) sonra"]},
    {"id": "momentum", "ad": "Momentum teyitli", "uret": _momentum, "renk": "#34d399",
     "ozet": "MACD kesişimi, ama sadece büyük trend ve alıcılar aynı yöndeyse.",
     "kurallar": ["LONG: MACD sinyal çizgisini yukarı kesti, 4 saatlik trend yukarı, taker alış oranı > %50, Stokastik yukarı ve 80'in altında",
                  "SHORT: MACD aşağı kesti, 4 saatlik trend aşağı, alış oranı < %50, Stokastik aşağı ve 20'nin üstünde",
                  "ÇIKIŞ: MACD geri kesince; en geç 12 mum (3 saat) sonra"]},
]


def islemler(o: pd.DataFrame, strat: dict) -> list[dict]:
    """Stratejinin tüm geçmişteki işlemleri (tek pozisyon: açıkken gelen sinyal atlanır)."""
    long_, short, cikis, maks = strat["uret"](o)
    long_ = long_.fillna(False).to_numpy()
    short = short.fillna(False).to_numpy()
    c = o["close"].to_numpy()
    saat = performans.mum_saati(o)
    maliyet = performans.islem_maliyeti()
    out, acik = [], -1
    for i in np.nonzero(long_ | short)[0]:
        if i <= acik:
            continue
        yon = "LONG" if long_[i] else "SHORT"
        j = cikis(int(i), yon)
        if j is None:          # çıkış mumu henüz gelmedi: açık işlem, şimdiki fiyatla değerlendirilir
            jj, durum = len(o) - 1, "acik"
            acik = len(o)
        else:
            jj, durum = j, "kapandi"
            acik = j
        brut = (c[jj] / c[i] - 1) * 100 * (1 if yon == "LONG" else -1)
        net = brut - maliyet - float(performans.funding_maliyeti((jj - i) * saat))
        out.append({"i": int(i), "j": int(jj), "yon": yon, "durum": durum, "brut": round(float(brut), 3),
                    "net": round(float(net), 3), "dogru": bool(brut > 0), "maks_mum": maks})
    return out


def istatistik(isl: list[dict], o: pd.DataFrame, gun: int | None = None) -> dict:
    if gun is not None:
        sinir = o["time"].iloc[-1] - pd.Timedelta(days=gun)
        isl = [x for x in isl if o["time"].iloc[x["i"]] >= sinir]
    kap = [x for x in isl if x["durum"] == "kapandi"]
    if not kap:
        return {"islem": 0, "acik": len(isl) - len(kap)}
    net = np.array([x["net"] for x in kap])
    kaz, kay = net[net > 0], net[net <= 0]
    # kasa eğrisi: her işlemde kasanın tamamı, kaldıraçsız
    kasa = np.cumprod(1 + net / 100)
    tepe = np.maximum.accumulate(kasa)
    seri, en_kotu_seri = 0, 0
    for x in kap:
        seri = seri + 1 if x["net"] <= 0 else 0
        en_kotu_seri = max(en_kotu_seri, seri)
    return {"islem": len(kap), "acik": len(isl) - len(kap), "long": sum(1 for x in kap if x["yon"] == "LONG"),
            "isabet": round(float(np.mean([x["dogru"] for x in kap])), 4),
            "net_kazanma_orani": round(float((net > 0).mean()), 4), "ort_net": round(float(net.mean()), 4),
            "toplam_net": round(float(net.sum()), 3), "kasa_getiri": round(float((kasa[-1] - 1) * 100), 2),
            "kar_faktoru": round(float(kaz.sum() / -kay.sum()), 2) if len(kay) and kay.sum() < 0 else None,
            "max_dusus": round(float(((kasa / tepe) - 1).min() * 100), 2), "en_uzun_kayip_serisi": int(en_kotu_seri),
            "ort_sure_mum": round(float(np.mean([x["j"] - x["i"] for x in kap])), 1)}


def cizelge(o: pd.DataFrame, isl: list[dict], mum: int = config.CIZELGE_MUM) -> list[dict]:
    """Son `mum` mum için satır: sinyal / pozisyonda / bekle, çıkış ve sonuç (sinyaller sayfasıyla aynı biçim)."""
    n = len(o)
    bas = max(0, n - 1 - mum)
    girisler = {x["i"]: x for x in isl}
    pozisyonda = np.zeros(n, dtype=bool)
    for x in isl:
        pozisyonda[x["i"] + 1: x["j"] + 1] = True
    sure = o["time"].diff().median()
    out = []
    for i in range(bas, n):
        x = girisler.get(i)
        satir = {"zaman": o["time"].iloc[i].isoformat(), "fiyat": float(o["close"].iloc[i]), "pozisyonda": bool(pozisyonda[i])}
        if x:
            satir.update({"sinyal": x["yon"], "cikis_mum": x["j"] - x["i"] if x["durum"] == "kapandi" else None,
                          "maks_mum": x["maks_mum"],
                          "cikis": {"mum": x["j"] - x["i"], "zaman": o["time"].iloc[x["j"]].isoformat() if x["durum"] == "kapandi" else None,
                                    "beklenen_zaman": (o["time"].iloc[x["i"]] + sure * x["maks_mum"]).isoformat(),
                                    "fiyat": float(o["close"].iloc[x["j"]]), "durum": x["durum"], "net": x["net"], "dogru": x["dogru"]}})
        else:
            satir.update({"sinyal": "BEKLE", "cikis_mum": None, "cikis": None})
        out.append(satir)
    return out


def hesapla(o: pd.DataFrame) -> dict:
    """Tüm stratejiler için: istatistik (tüm geçmiş, son 90 ve 30 gün), son 24 saat çizelgesi, son işlemler."""
    sonuc = {}
    for st in STRATEJILER:
        isl = islemler(o, st)
        sonuc[st["id"]] = {
            "ad": st["ad"], "ozet": st["ozet"], "kurallar": st["kurallar"], "renk": st["renk"],
            "istatistik": {"tum": istatistik(isl, o), "son90": istatistik(isl, o, 90), "son30": istatistik(isl, o, 30)},
            "veri_gun": int((o["time"].iloc[-1] - o["time"].iloc[0]).days),
            "cizelge": cizelge(o, isl),
            "son_islemler": [{"zaman": o["time"].iloc[x["i"]].isoformat(), "cikis_zaman": o["time"].iloc[x["j"]].isoformat(),
                              "yon": x["yon"], "net": x["net"], "dogru": x["dogru"], "durum": x["durum"], "mum": x["j"] - x["i"]}
                             for x in isl[-15:]][::-1],
        }
    return sonuc
