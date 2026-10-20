"""Mum formasyonları ve basit grafik formasyonları. Her biri bool sütun döner."""
from __future__ import annotations

import numpy as np
import pandas as pd


def formasyonlar(df: pd.DataFrame) -> pd.DataFrame:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    govde = (c - o).abs()
    aralik = (h - l).replace(0, np.nan)
    ust_fitil = h - np.maximum(o, c)
    alt_fitil = np.minimum(o, c) - l
    yesil = c > o
    kirmizi = c < o
    ort_govde = govde.rolling(20).mean()
    p1o, p1c, p1h, p1l = o.shift(), c.shift(), h.shift(), l.shift()
    p2o, p2c = o.shift(2), c.shift(2)
    yesil1, kirmizi1 = p1c > p1o, p1c < p1o
    trend_dusus = c.shift(1) < c.shift(6)
    trend_yukselis = c.shift(1) > c.shift(6)

    f = pd.DataFrame(index=df.index)
    f["doji"] = govde <= 0.1 * aralik
    f["cekic"] = (alt_fitil >= 2 * govde) & (ust_fitil <= 0.3 * govde + 0.1 * aralik) & trend_dusus
    f["ters_cekic"] = (ust_fitil >= 2 * govde) & (alt_fitil <= 0.3 * govde + 0.1 * aralik) & trend_dusus
    f["kayan_yildiz"] = (ust_fitil >= 2 * govde) & (alt_fitil <= 0.3 * govde + 0.1 * aralik) & trend_yukselis
    f["asili_adam"] = (alt_fitil >= 2 * govde) & (ust_fitil <= 0.3 * govde + 0.1 * aralik) & trend_yukselis
    f["yutan_boga"] = yesil & kirmizi1 & (c >= p1o) & (o <= p1c)
    f["yutan_ayi"] = kirmizi & yesil1 & (c <= p1o) & (o >= p1c)
    f["harami_boga"] = yesil & kirmizi1 & (c < p1o) & (o > p1c)
    f["harami_ayi"] = kirmizi & yesil1 & (c > p1o) & (o < p1c)
    f["sabah_yildizi"] = (p2c < p2o) & ((p1c - p1o).abs() < 0.3 * ort_govde) & yesil & (c > (p2o + p2c) / 2)
    f["aksam_yildizi"] = (p2c > p2o) & ((p1c - p1o).abs() < 0.3 * ort_govde) & kirmizi & (c < (p2o + p2c) / 2)
    uc_yesil = yesil & yesil1 & (p2c > p2o) & (c > p1c) & (p1c > p2c)
    uc_kirmizi = kirmizi & kirmizi1 & (p2c < p2o) & (c < p1c) & (p1c < p2c)
    f["uc_beyaz_asker"] = uc_yesil & (govde > ort_govde)
    f["uc_kara_karga"] = uc_kirmizi & (govde > ort_govde)
    f["marubozu_boga"] = yesil & (govde >= 0.9 * aralik) & (govde > 1.5 * ort_govde)
    f["marubozu_ayi"] = kirmizi & (govde >= 0.9 * aralik) & (govde > 1.5 * ort_govde)
    f["ic_mum"] = (h < p1h) & (l > p1l)
    f["dis_mum"] = (h > p1h) & (l < p1l)
    f["pin_bar_boga"] = (alt_fitil >= 0.66 * aralik)
    f["pin_bar_ayi"] = (ust_fitil >= 0.66 * aralik)
    f["cimbiz_dip"] = ((l - p1l).abs() <= 0.05 * aralik) & kirmizi1 & yesil
    f["cimbiz_tepe"] = ((h - p1h).abs() <= 0.05 * aralik) & yesil1 & kirmizi
    f["delici_hat"] = kirmizi1 & yesil & (o < p1l) & (c > (p1o + p1c) / 2) & (c < p1o)
    f["kara_bulut"] = yesil1 & kirmizi & (o > p1h) & (c < (p1o + p1c) / 2) & (c > p1o)
    f["buyuk_govde"] = govde > 2.5 * ort_govde
    f["ard_arda_3_yesil"] = yesil & yesil1 & (p2c > p2o)
    f["ard_arda_3_kirmizi"] = kirmizi & kirmizi1 & (p2c < p2o)

    # --- Grafik formasyonları (yaklaşık) ---
    hh20 = h.rolling(20).max().shift()
    ll20 = l.rolling(20).min().shift()
    f["kirilim_yukari_20"] = c > hh20
    f["kirilim_asagi_20"] = c < ll20
    pivot_l = l.rolling(5, center=True).min() == l
    pivot_h = h.rolling(5, center=True).max() == h
    # pivotlar 2 mum gecikmeyle bilinir -> geleceğe bakmamak için kaydır
    pl = l.where(pivot_l).shift(2).ffill()
    pl_onceki = l.where(pivot_l).shift(2).dropna().shift().reindex(df.index).ffill()
    ph = h.where(pivot_h).shift(2).ffill()
    ph_onceki = h.where(pivot_h).shift(2).dropna().shift().reindex(df.index).ffill()
    f["ikili_dip"] = ((pl - pl_onceki).abs() / pl < 0.003) & (c > pl)
    f["ikili_tepe"] = ((ph - ph_onceki).abs() / ph < 0.003) & (c < ph)
    f["yukselen_dipler"] = (pl > pl_onceki) & (ph > ph_onceki)
    f["alcalan_tepeler"] = (ph < ph_onceki) & (pl < pl_onceki)
    return f.fillna(False).astype(bool)
