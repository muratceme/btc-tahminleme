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


def _teshis(p, y, gun, min_n) -> dict:
    """'Neden sinyal yok?' sorusu için: eşik seçimi döneminde, sinyalin geçmesi gereken kapıyla aynı
    koşulda (en az min_n bağımsız örnek) herhangi bir güven eşiğinde ulaşılabilen en yüksek isabet."""
    en_iyi, kapsama = 0.0, None
    toplam = len(np.unique(gun)) if gun is not None else len(p)
    for d in np.arange(0.0, 0.40, 0.01):
        idx = _sec(np.abs(p - 0.5) >= d, gun)
        if len(idx) < min_n:
            break
        isabet = float(((p[idx] > 0.5).astype(int) == y[idx]).mean())
        if isabet > en_iyi:
            en_iyi, kapsama = isabet, round(100 * len(idx) / max(1, toplam), 1)
    return {"en_iyi_isabet": round(en_iyi, 4), "kapsama_yuzde": kapsama, "esik": config.MIN_TUTARLILIK}


MODEL_SURUM = 1


def _model_dosyasi(anahtar: str, hedef_adi: str):
    return config.CIKTI_DIR / f"model_{anahtar}_{hedef_adi}.pkl"


def _egit(o: pd.DataFrame, hedef: pd.DataFrame, hedef_adi: str) -> dict:
    """Pahalı kısım: walk-forward + eşik seçimi + tam model eğitimi. Sonuç günde bir hesaplanıp saklanır."""
    X_df = ozellik_matrisi(o)
    y_s = hedef[hedef_adi]
    gecerli = y_s.notna().to_numpy()
    X = X_df.to_numpy()[gecerli]
    y = y_s.to_numpy()[gecerli].astype(int)
    yerel = o["time"] + pd.Timedelta(hours=config.GUN_SONU_UTC_OFFSET_SAAT)
    gun = yerel.dt.floor("D").to_numpy()[gecerli] if hedef_adi.startswith("gun") else None
    min_n = config.MIN_DESTEK_TEST * 3 if gun is None else 30   # gün sonu: 30 farklı gün
    modeller = {}
    for ad, (fn, doldur) in _modeller().items():
        p, sinirlar = _yuru_ileri(fn, doldur, X, y)
        sec = slice(sinirlar[0], sinirlar[-2])      # eşik seçimi: ilk 4 kat
        tst = slice(sinirlar[-2], sinirlar[-1])     # tutarlılık ölçümü: son kat (hiç dokunulmamış)
        genel_dogruluk = float(((p[tst] > 0.5).astype(int) == y[tst]).mean())
        # Son CIZELGE_MUM+1 mum eğitime girmez: geriye dönük kontrolde model, sonucunu bildiği mumu tahmin etmesin
        kes = max(sinirlar[0], len(y) - config.CIZELGE_MUM - 1)
        tam = fn()
        tam.fit(np.nan_to_num(X[:kes]) if doldur else X[:kes], y[:kes])
        seviyeler = []
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
            seviyeler.append({"hedeflenen_seviye": hedef_oran, "tutarlilik": round(isabet, 4), "test_n": n,
                              "kapsama_yuzde": round(100 * n / (len(np.unique(gun[tst])) if gun is not None else tst.stop - tst.start), 2),
                              "guven_marji": d})
        modeller[ad] = {"tam": tam, "doldur": doldur, "genel_dogruluk": round(genel_dogruluk, 4),
                        "teshis": _teshis(p[sec], y[sec], None if gun is None else gun[sec], min_n), "seviyeler": seviyeler}
    return {"surum": MODEL_SURUM, "zaman": pd.Timestamp.now(tz="UTC").isoformat(), "hedef": hedef_adi,
            "kolonlar": list(X_df.columns), "modeller": modeller}


def _satirlar(egitim: dict, o: pd.DataFrame) -> list[dict]:
    """Ucuz kısım: saklanan modellerle son mumların tahmini; her turda çalışır."""
    hedef_adi = egitim["hedef"]
    X_df = ozellik_matrisi(o).reindex(columns=egitim["kolonlar"])
    x_gecmis = X_df.to_numpy()[-config.CIZELGE_MUM - 1:]
    satirlar = []
    for ad, m in egitim["modeller"].items():
        xg = np.nan_to_num(x_gecmis) if m["doldur"] else x_gecmis
        p_gecmis = m["tam"].predict_proba(xg)[:, 1].round(4).tolist()
        p_simdi = float(p_gecmis[-1])
        satirlar.append({  # eşiksiz ham tahmin: her zaman üretilir, tutarlılığı düşük olabilir
            "tur": "HAM", "model": f"{ad} ({hedef_adi})", "hedef": hedef_adi,
            "p_yukari_simdi": round(p_simdi, 4), "long_risk_yuzde": round(100 * (1 - p_simdi), 1),
            "modelin_genel_dogrulugu": m["genel_dogruluk"], "p_gecmis": p_gecmis, "teshis": m["teshis"],
            "egitim_zamani": egitim["zaman"],
        })
        for sv in m["seviyeler"]:
            satirlar.append({
                "tur": "YON", "model": f"{ad} ({hedef_adi})", "hedef": hedef_adi, **sv,
                "p_yukari_simdi": round(p_simdi, 4), "sinyal_var": bool(abs(p_simdi - 0.5) >= sv["guven_marji"]),
                "long_risk_yuzde": round(100 * (1 - p_simdi), 1), "short_risk_yuzde": round(100 * p_simdi, 1),
                "modelin_genel_dogrulugu": m["genel_dogruluk"],
            })
    return satirlar


def yon_modelleri(o: pd.DataFrame, hedef: pd.DataFrame, hedef_adi: str = "gun_sonu_yukari",
                  anahtar: str | None = None, hizli: bool = False) -> list[dict]:
    """Her model ve her tutarlılık seviyesi için (eşik, test isabeti, şu anki risk) üretir.

    anahtar verilirse (ör. "BTCUSDT_15m") eğitim günde bir yapılır ve cikti/model_*.pkl dosyasında saklanır;
    hizli=True ve dosya 24 saatten yeniyse yalnızca tahmin yapılır (tur süresi dakikalardan saniyelere iner)."""
    if not SKLEARN:
        return []
    egitim = None
    dosya = _model_dosyasi(anahtar, hedef_adi) if anahtar else None
    if dosya and hizli and dosya.exists():
        try:
            import pickle
            with open(dosya, "rb") as f:
                aday = pickle.load(f)
            yas = pd.Timestamp.now(tz="UTC") - pd.Timestamp(aday["zaman"])
            if aday.get("surum") == MODEL_SURUM and yas.total_seconds() < 24 * 3600 and aday.get("min_tutarlilik") == config.MIN_TUTARLILIK:
                egitim = aday
        except Exception:  # noqa: BLE001  bozuk dosya: yeniden eğit
            egitim = None
    if egitim is None:
        egitim = _egit(o, hedef, hedef_adi)
        egitim["min_tutarlilik"] = config.MIN_TUTARLILIK
        if dosya:
            import pickle
            config.CIKTI_DIR.mkdir(parents=True, exist_ok=True)
            with open(dosya, "wb") as f:
                pickle.dump(egitim, f)
    return _satirlar(egitim, o)


def _gun_ici_sinirlar(o: pd.DataFrame, seri: pd.Series, yukari: bool) -> list[tuple[float, float, int, float]]:
    """Volatilite rejimi ve güne kalan saate göre gün içi en kötü hareket sınırları.

    Sınırlar eğitim döneminden (ilk %70) öğrenilir, tutarlılık son %30'da ölçülür.
    Dönen: [(seviye, test tutma oranı, test n, şu anki sınır %), ...]"""
    kalan = gun_sonuna_kalan_saat(o)
    vol_rejim = pd.qcut(o["atr_pct"].rank(method="first"), 3, labels=["dusuk", "orta", "yuksek"])
    kalan_kova = pd.cut(kalan, [0, 4, 8, 12, 16, 20, 24.01], labels=False)
    df = pd.DataFrame({"dd": seri, "vol": vol_rejim, "kalan": kalan_kova}).dropna()
    n = len(df)
    if n < 500:
        return []
    s = int(n * 0.7)
    egt, tst = df.iloc[:s], df.iloc[s:]
    simdi_anahtar = (vol_rejim.iloc[-1], kalan_kova.iloc[-1])
    out = []
    for seviye in config.TUTARLILIK_SEVIYELERI:
        esikler = egt.groupby(["vol", "kalan"], observed=True)["dd"].quantile(seviye if yukari else 1 - seviye)
        t_esik = np.asarray(tst.set_index(["vol", "kalan"]).index.map(lambda k: esikler.get(k, np.nan)), dtype=float)
        ok = ~np.isnan(t_esik)
        d = tst["dd"].to_numpy()[ok]
        tutma = float((d <= t_esik[ok]).mean() if yukari else (d >= t_esik[ok]).mean())
        simdi = esikler.get(simdi_anahtar, np.nan)
        if not np.isnan(simdi) and tutma >= config.MIN_TUTARLILIK:
            out.append((seviye, tutma, int(ok.sum()), float(simdi)))
    return out


def dusus_riski(o: pd.DataFrame, hedef: pd.DataFrame) -> list[dict]:
    """'Gün sonuna kadar fiyat en fazla ne kadar düşer' sınırları (long için stop referansı)."""
    return [{
        "tur": "DUSUS", "model": "Volatilite-rejimi dusus siniri",
        "hedeflenen_seviye": sev, "tutarlilik": round(tut, 4), "test_n": n, "max_dusus_yuzde": round(v, 2),
        "aciklama": f"%{int(sev * 100)} ihtimalle gün sonuna kadar fiyat %{abs(v):.2f}'den fazla düşmez",
    } for sev, tut, n, v in _gun_ici_sinirlar(o, hedef["gun_ici_max_dusus"], yukari=False)]


def yukselis_siniri(o: pd.DataFrame, hedef: pd.DataFrame) -> dict:
    """'Gün sonuna kadar fiyat en fazla ne kadar yükselir' (short için stop referansı). {"%90": 1.7, ...}"""
    return {f"%{int(round(tut * 100))}": round(v, 2)
            for sev, tut, n, v in _gun_ici_sinirlar(o, hedef["gun_ici_max_yukselis"], yukari=True)}
