"""Geleceğe bakış / sahte isabet testi (ağ gerektirmez, ~1 dk).

Saf rastgele fiyatta gerçek bir örüntü yoktur. Sistem burada %70+ tutarlılıkta
tek bir yön kuralı veya model satırı bulursa, hesaplamada bir sızıntı var demektir.
    python -m tests.sizinti_test
"""
import numpy as np
import pandas as pd

import time

from btc_tahmin import config, features, miner, models, pipeline


def rastgele_yuruyus(gun=540):
    mum = {}
    for i, (s, b) in enumerate(zip(config.SEMBOLLER, [60000, 3000, 0.6])):
        rng = np.random.default_rng(200 + i)
        n = gun * 96
        z = pd.date_range(end=pd.Timestamp.now(tz="UTC").floor("15min") - pd.Timedelta("15min"), periods=n, freq="15min")
        c = b * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
        o = np.r_[c[0], c[:-1]]
        h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, .001, n)))
        lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, .001, n)))
        v = rng.lognormal(3, .5, n)
        mum[s] = pd.DataFrame(dict(time=z, open=o, high=h, low=lo, close=c, volume=v, quote_volume=v * c,
                                   trades=100, taker_buy_base=v * .5))
    return mum


def main():
    o, K, hd = features.veri_seti_hazirla(rastgele_yuruyus())
    kalan = features.gun_sonuna_kalan_saat(o)
    assert hd["gun_sonu_yukari"][kalan < config.GUN_SONU_MIN_KALAN_SAAT].isna().all(), "gün sonu hedefi son saatte tanımlı olmamalı"
    gun = (o["time"] + pd.Timedelta(hours=config.GUN_SONU_UTC_OFFSET_SAAT)).dt.floor("D")
    r1 = miner.kurallari_ara(K, hd["sonraki_yesil"], "s")
    r2 = miner.kurallari_ara(K, hd["gun_sonu_yukari"], "g", gun=gun)
    m = [r for h in ("gun_sonu_yukari", "sonraki_yesil") for r in models.yon_modelleri(o, hd, h) if r["tur"] == "YON"]
    t0 = time.time()
    KT = pd.concat([K, features.ince_kosullar(o)], axis=1)
    d = pipeline.derin_tarama(KT, hd)
    print(f"rastgele veride bulunan: sonraki mum kuralı {len(r1)}, gün sonu kuralı {len(r2)}, model satırı {len(m)}, "
          f"derin tarama kuralı {len(d)} (derin tarama {time.time() - t0:.0f} sn, {KT.shape[1]} koşul)")
    for r in d[:5]:
        print("  ", r["hedef"], r["tutarlilik"], r["test_n"], r["kosullar"])
    assert not r1 and not r2 and not m and not d, "SIZINTI: rastgele veride tutarlı sinyal bulundu"
    print("OK - sızıntı yok")


if __name__ == "__main__":
    main()
