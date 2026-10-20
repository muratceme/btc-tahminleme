"""Mum tahmini: şu andan itibaren N mum sonrası için beklenen kapanış ve son 1 gündeki tahmin-gerçek karşılaştırması.

Modeller: her ufuk (1, 2, 4, 8 mum) için ayrı bir Gradient Boosting regresyonu; girdi, yön modellerinin kullandığı
indikatör matrisidir; çıktı o ufuktaki yüzde getiridir. Son CIZELGE_MUM mum eğitime GİRMEZ; böylece "son 1 gün" tablosu
modelin görmediği veride ölçülür. Hata bandı, son 1 gündeki hataların %80'lik dilimidir. Günde bir eğitilir (pickle).

Dürüst not: kısa vadeli fiyat tahmini büyük ölçüde gürültüdür; sayfa yön isabetini ve hatayı yanında gösterir.
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

from . import config
from .models import SKLEARN, ozellik_matrisi

UFUKLAR = [1, 2, 4, 8]
TAHMIN_SURUM = 1


def _dosya(anahtar: str):
    return config.CIKTI_DIR / f"tahmin_{anahtar}.pkl"


def _egit(o: pd.DataFrame) -> dict:
    from sklearn.ensemble import HistGradientBoostingRegressor
    X_df = ozellik_matrisi(o)
    X = X_df.to_numpy()
    c = o["close"].to_numpy()
    kes = len(o) - config.CIZELGE_MUM - 1
    modeller = {}
    for h in UFUKLAR:
        y = (np.roll(c, -h) / c - 1) * 100
        son = kes - h                       # hedefi bilinen ve son güne taşmayan satırlar
        m = HistGradientBoostingRegressor(max_iter=150, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=200,
                                          l2_regularization=1.0, random_state=42)
        m.fit(X[:son], y[:son])
        modeller[h] = m
    return {"surum": TAHMIN_SURUM, "zaman": pd.Timestamp.now(tz="UTC").isoformat(), "kolonlar": list(X_df.columns), "modeller": modeller}


def _yukle_veya_egit(o: pd.DataFrame, anahtar: str | None, hizli: bool) -> dict:
    dosya = _dosya(anahtar) if anahtar else None
    if dosya and hizli and dosya.exists():
        try:
            with open(dosya, "rb") as f:
                e = pickle.load(f)
            if e.get("surum") == TAHMIN_SURUM and (pd.Timestamp.now(tz="UTC") - pd.Timestamp(e["zaman"])).total_seconds() < 24 * 3600:
                return e
        except Exception:  # noqa: BLE001
            pass
    e = _egit(o)
    if dosya:
        config.CIKTI_DIR.mkdir(parents=True, exist_ok=True)
        with open(dosya, "wb") as f:
            pickle.dump(e, f)
    return e


def hesapla(o: pd.DataFrame, anahtar: str | None = None, hizli: bool = False) -> dict | None:
    if not SKLEARN:
        return None
    e = _yukle_veya_egit(o, anahtar, hizli)
    X = ozellik_matrisi(o).reindex(columns=e["kolonlar"]).to_numpy()
    n = len(o)
    bas = n - config.CIZELGE_MUM          # son 1 gün + şimdi
    c = o["close"].to_numpy()
    zaman = ((o["time"] - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)).to_numpy()
    sure = int(o["time"].diff().median().total_seconds())
    tah = {h: e["modeller"][h].predict(X[bas:]) for h in UFUKLAR}   # (CIZELGE_MUM,) her ufuk için yüzde getiri

    # Son 1 gün: her mum için 1 mum sonrası tahmini kapanış vs gerçek
    gecmis, hatalar = [], {h: [] for h in UFUKLAR}
    for k, i in enumerate(range(bas, n)):
        satir = {"zaman": int(zaman[i]), "kapanis": float(c[i]), "tahmin_1": float(c[i] * (1 + tah[1][k] / 100)),
                 "tahmin_yuzde_1": round(float(tah[1][k]), 4)}
        if i + 1 < n:
            gercek = float(c[i + 1])
            satir.update({"gercek_1": gercek, "gercek_yuzde_1": round(float((gercek / c[i] - 1) * 100), 4),
                          "yon_dogru": bool((tah[1][k] > 0) == (gercek > c[i])) if gercek != c[i] else None,
                          "hata_yuzde": round(float(abs(tah[1][k] - (gercek / c[i] - 1) * 100)), 4)})
        gecmis.append(satir)
        for h in UFUKLAR:
            if i + h < n:
                hatalar[h].append(abs(float(tah[h][k]) - float((c[i + h] / c[i] - 1) * 100)))
    band = {h: (float(np.quantile(v, 0.8)) if v else None) for h, v in hatalar.items()}
    yon = [x["yon_dogru"] for x in gecmis if x.get("yon_dogru") is not None]
    mae = [x["hata_yuzde"] for x in gecmis if "hata_yuzde" in x]
    sapma_ort = float(np.mean(np.abs([x["gercek_yuzde_1"] for x in gecmis if "gercek_yuzde_1" in x]))) if mae else None

    # Şu andan itibaren: ufuklar arası doğrusal ara değerle 1..8 mum yolu
    simdi_c = float(c[-1])
    t0 = int(zaman[-1])
    noktalar = {h: float(tah[h][-1]) for h in UFUKLAR}
    yol = []
    for m in range(1, max(UFUKLAR) + 1):
        if m in noktalar:
            y = noktalar[m]
        else:
            alt = max(h for h in UFUKLAR if h < m)
            ust = min(h for h in UFUKLAR if h > m)
            y = noktalar[alt] + (noktalar[ust] - noktalar[alt]) * (m - alt) / (ust - alt)
        b = band.get(m) if m in band else None
        if b is None:   # ara ufuk: komşu bantların ara değeri
            alt = max(h for h in UFUKLAR if h < m); ust = min(h for h in UFUKLAR if h > m)
            if band.get(alt) is not None and band.get(ust) is not None:
                b = band[alt] + (band[ust] - band[alt]) * (m - alt) / (ust - alt)
        yol.append({"mum": m, "zaman": t0 + m * sure, "tahmin_yuzde": round(y, 4), "tahmin": round(simdi_c * (1 + y / 100), 6),
                    "band_yuzde": None if b is None else round(b, 4),
                    "alt": None if b is None else round(simdi_c * (1 + (y - b) / 100), 6),
                    "ust": None if b is None else round(simdi_c * (1 + (y + b) / 100), 6)})
    return {
        "egitim_zamani": e["zaman"], "mum_suresi_sn": sure, "simdi": {"zaman": t0, "kapanis": simdi_c},
        "gecmis": gecmis, "yol": yol,
        "ozet": {"yon_isabeti": round(float(np.mean(yon)), 4) if yon else None, "n": len(yon),
                 "ort_hata_yuzde": round(float(np.mean(mae)), 4) if mae else None,
                 "ort_gercek_hareket_yuzde": round(sapma_ort, 4) if sapma_ort is not None else None,
                 "band_yuzde": {str(h): (round(v, 4) if v is not None else None) for h, v in band.items()}},
    }
