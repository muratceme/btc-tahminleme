"""Geleceğe bakış / sahte isabet testi (ağ gerektirmez, ~1 dk).

Saf rastgele fiyatta gerçek bir örüntü yoktur. Sistem burada model satırı, derin tarama kuralı ya da
güçlü (n>=40, %75+) bir kural bulursa, hesaplamada bir sızıntı var demektir. 25 örnekte %72 gibi tek tük
zayıf kural, binlerce aday denendiği için şans eseri çıkabilir (bkz. sahte keşif testi); 2'ye kadar izin verilir.
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
        # Sabit bitiş zamanı: test deterministik olsun (zaman kaydıkça seans/gün özellikleri değişir ve binlerce aday
        # arasından şans eseri %70'i geçen tek bir kural çıkabilir; bu sızıntı değil, çoklu karşılaştırmadır)
        z = pd.date_range(end=pd.Timestamp("2026-01-01 00:00", tz="UTC"), periods=n, freq="15min")
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
    # Gerçek bir sızıntı (ör. gün sonu hedefinin son mumda bilinmesi) onlarca güçlü kural ve model satırı üretir.
    # Binlerce aday arasından 20-30 örnekte %70'i şans eseri geçen tek tük kural ise çoklu karşılaştırmadır; buna izin verilir.
    tum = r1 + r2
    guclu = [r for r in tum if r.test[0] >= 40 and r.tutarlilik >= 0.75]
    assert not m, "SIZINTI: rastgele veride model güven eşiğini geçti"
    assert not d, "SIZINTI: rastgele veride derin tarama kuralı bulundu"
    assert len(tum) <= 2 and not guclu, f"SIZINTI: rastgele veride {len(tum)} kural, {len(guclu)} tanesi güçlü"
    print(f"OK - sızıntı yok ({len(tum)} zayıf kural şans payı içinde)")


def test_sizinti_yok():
    main()


if __name__ == "__main__":
    main()
