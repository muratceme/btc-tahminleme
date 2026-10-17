"""Gün sonu risk modelleri ve tutarlılık ölçümü.

İki tür risk üretilir:
  * YÖN RİSKİ  : Şu an LONG açarsam gün sonunda zararda olma ihtimali (%).
                 Tutarlılık = modelin bu güven eşiğindeyken TEST döneminde
                 doğru bilme oranı.
  * DÜŞÜŞ RİSKİ: Gün sonuna kadar fiyatın şu anki seviyeden en fazla yüzde kaç
                 aşağı sarkabileceği. Tutarlılık = bu sınırın TEST döneminde
                 aşılmama oranı (ör. %90 -> 10 günden 9'unda sınır tutmuş).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .features import gun_sonuna_kalan_saat

try:
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    SKLEARN = True
except ImportError:  # pragma: no cover
    SKLEARN = False

SAYISAL = ["rsi", "rsi_7", "stoch_k", "stoch_d", "srsi_k", "bb_pct", "bb_genislik", "adx", "cci",
           "mfi", "willr", "atr_pct", "obv_egim", "supertrend", "vwap_sapma", "roc_4", "roc_16",
           "hacim_z", "alis_orani", "gunluk_yuksek_uzak", "gunluk_dusuk_uzak", "getiri_1"]


def ozellik_matrisi(o: pd.DataFrame) -> pd.DataFrame:
    c = o["close"]
    X = o[SAYISAL].astype(float).copy()
    X["macd_hist_n"] = o["macd_hist"] / c * 1000
    X["macd_n"] = o["macd"] / c * 1000
    for n in (9, 21, 50, 200):
        X[f"ema{n}_uzak"] = (c / o[f"ema{n}"] - 1) * 100
    X["di_fark"] = o["pdi"] - o["mdi"]
    X["ichi_uzak"] = (c / o["ichi_ust"] - 1) * 100
    X["gun_sonuna_kalan_saat"] = gun_sonuna_kalan_saat(o)
    X["saat_utc"] = o["time"].dt.hour
    X["haftanin_gunu"] = o["time"].dt.dayofweek
    for k in [x for x in o.columns if x.startswith("ctx_")]:
        X[k] = o[k].astype(float)
    return X.replace([np.inf, -np.inf], np.nan)


def _modeller():
    if not SKLEARN:
        return {}
    # (model üretici, NaN doldurulmalı mı)
    return {
        "GradientBoost": (lambda: HistGradientBoostingClassifier(
            max_iter=200, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=200,
            l2_regularization=1.0, random_state=42), False),
        "Lojistik": (lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500)), True),
    }


def _yuru_ileri(model_fn, doldur: bool, X: np.ndarray, y: np.ndarray, kat: int = 5):
    """Walk-forward: her katta sadece geçmişle eğit, sonraki dilimi tahmin et."""
    n = len(y)
    sinirlar = np.linspace(int(n * 0.4), n, kat + 1).astype(int)
    p = np.full(n, np.nan)
    for a, b in zip(sinirlar[:-1], sinirlar[1:]):
        m = model_fn()
        Xtr, Xte = (np.nan_to_num(X[:a]), np.nan_to_num(X[a:b])) if doldur else (X[:a], X[a:b])
        m.fit(Xtr, y[:a])
        p[a:b] = m.predict_proba(Xte)[:, 1]
    return p, sinirlar


def _sec(m: np.ndarray, gun) -> np.ndarray:
    """Sinyal indeksleri. Gün sonu hedefinde her günün yalnızca ilk sinyali (bağımsız örnek)."""
    idx = np.nonzero(m)[0]
    if gun is None or len(idx) == 0:
        return idx
    _, ilk = np.unique(gun[idx], return_index=True)
    return idx[np.sort(ilk)]


def _esik_bul(p, y, gun, hedef_oran, min_n):
    """Seçim dilimi üzerinde, hedef isabet oranına ulaşan en küçük güven marjını bulur."""
    for d in np.arange(0.02, 0.40, 0.01):
        idx = _sec(np.abs(p - 0.5) >= d, gun)
        if len(idx) < min_n:
            return None
        if ((p[idx] > 0.5).astype(int) == y[idx]).mean() >= hedef_oran:
            return round(float(d), 2)
    return None


def yon_modelleri(o: pd.DataFrame, hedef: pd.DataFrame, hedef_adi: str = "gun_sonu_yukari") -> list[dict]:
    """Her model ve her tutarlılık seviyesi için (eşik, test isabeti, şu anki risk) üretir."""
    if not SKLEARN:
        return []
    X_df = ozellik_matrisi(o)
    y_s = hedef[hedef_adi]
    gecerli = y_s.notna().to_numpy()
    X = X_df.to_numpy()[gecerli]
    y = y_s.to_numpy()[gecerli].astype(int)
    yerel = o["time"] + pd.Timedelta(hours=config.GUN_SONU_UTC_OFFSET_SAAT)
    gun = yerel.dt.floor("D").to_numpy()[gecerli] if hedef_adi.startswith("gun") else None
    min_n = config.MIN_DESTEK_TEST * 3 if gun is None else 30   # gün sonu: 30 farklı gün

    satirlar = []
    for ad, (fn, doldur) in _modeller().items():
        p, sinirlar = _yuru_ileri(fn, doldur, X, y)
        sec = slice(sinirlar[0], sinirlar[-2])      # eşik seçimi: ilk 4 kat
        tst = slice(sinirlar[-2], sinirlar[-1])     # tutarlılık ölçümü: son kat (hiç dokunulmamış)
        genel_dogruluk = float(((p[tst] > 0.5).astype(int) == y[tst]).mean())

        tam = fn()
        tam.fit(np.nan_to_num(X) if doldur else X, y)
        x_son = X_df.to_numpy()[-1:]
        p_simdi = float(tam.predict_proba(np.nan_to_num(x_son) if doldur else x_son)[0, 1])

        satirlar.append({  # eşiksiz ham tahmin: her zaman üretilir, tutarlılığı düşük olabilir
            "tur": "HAM", "model": f"{ad} ({hedef_adi})", "hedef": hedef_adi,
            "p_yukari_simdi": round(p_simdi, 4), "long_risk_yuzde": round(100 * (1 - p_simdi), 1),
            "modelin_genel_dogrulugu": round(genel_dogruluk, 4),
        })
        for hedef_oran in config.TUTARLILIK_SEVIYELERI:
            d = _esik_bul(p[sec], y[sec], None if gun is None else gun[sec], hedef_oran, min_n)
            if d is None:
                continue
            pt, yt = p[tst], y[tst]
            idx = _sec(np.abs(pt - 0.5) >= d, None if gun is None else gun[tst])
            n = len(idx)
            if n < config.MIN_DESTEK_TEST:
                continue
            isabet = float(((pt[idx] > 0.5).astype(int) == yt[idx]).mean())
            if isabet < config.MIN_TUTARLILIK:
                continue
            satirlar.append({
                "tur": "YON", "model": f"{ad} ({hedef_adi})", "hedef": hedef_adi,
                "hedeflenen_seviye": hedef_oran, "tutarlilik": round(isabet, 4),
                "test_n": n, "kapsama_yuzde": round(100 * n / (len(np.unique(gun[tst])) if gun is not None else tst.stop - tst.start), 2),
                "guven_marji": d, "p_yukari_simdi": round(p_simdi, 4),
                "sinyal_var": bool(abs(p_simdi - 0.5) >= d),
                "long_risk_yuzde": round(100 * (1 - p_simdi), 1),
                "short_risk_yuzde": round(100 * p_simdi, 1),
                "modelin_genel_dogrulugu": round(genel_dogruluk, 4),
            })
    return satirlar


def dusus_riski(o: pd.DataFrame, hedef: pd.DataFrame) -> list[dict]:
    """Volatilite rejimine ve kalan saate göre 'gün sonuna kadar max düşüş' sınırları.

    Sınırlar eğitim döneminden (ilk %70) öğrenilir, tutarlılık son %30'da ölçülür.
    """
    dd = hedef["gun_ici_max_dusus"]
    kalan = gun_sonuna_kalan_saat(o)
    vol_rejim = pd.qcut(o["atr_pct"].rank(method="first"), 3, labels=["dusuk", "orta", "yuksek"])
    kalan_kova = pd.cut(kalan, [0, 4, 8, 12, 16, 20, 24.01], labels=False)
    df = pd.DataFrame({"dd": dd, "vol": vol_rejim, "kalan": kalan_kova}).dropna()
    n = len(df)
    if n < 500:
        return []
    s = int(n * 0.7)
    egt, tst = df.iloc[:s], df.iloc[s:]
    simdi_vol = vol_rejim.iloc[-1]
    simdi_kalan = kalan_kova.iloc[-1]
    satirlar = []
    for seviye in config.TUTARLILIK_SEVIYELERI:
        q = 1 - seviye
        esikler = egt.groupby(["vol", "kalan"], observed=True)["dd"].quantile(q)
        t_esik = tst.set_index(["vol", "kalan"]).index.map(lambda k: esikler.get(k, np.nan))
        t_esik = np.asarray(t_esik, dtype=float)
        ok = ~np.isnan(t_esik)
        tutma = float((tst["dd"].to_numpy()[ok] >= t_esik[ok]).mean())
        simdi = esikler.get((simdi_vol, simdi_kalan), np.nan)
        if np.isnan(simdi) or tutma < config.MIN_TUTARLILIK:
            continue
        satirlar.append({
            "tur": "DUSUS", "model": "Volatilite-rejimi dusus siniri",
            "hedeflenen_seviye": seviye, "tutarlilik": round(tutma, 4), "test_n": int(ok.sum()),
            "max_dusus_yuzde": round(float(simdi), 2),
            "aciklama": f"%{int(seviye*100)} ihtimalle gün sonuna kadar fiyat %{abs(simdi):.2f}'den fazla düşmez",
            "vol_rejim": str(simdi_vol),
        })
    return satirlar
