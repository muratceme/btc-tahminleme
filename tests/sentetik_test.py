"""Ağ olmadan uçtan uca çalışma testi (sentetik fiyat verisi ile).

Sonuçların anlamı yoktur; sadece kodun hatasız çalıştığını doğrular.
    python -m tests.sentetik_test
"""
import time

import numpy as np
import pandas as pd

from btc_tahmin import config, pipeline, report


def sahte_mumlar(n=20000, tohum=0, baslangic=30000.0):
    rng = np.random.default_rng(tohum)
    zaman = pd.date_range(end=pd.Timestamp.now(tz="UTC").floor("15min") - pd.Timedelta("15min"),
                          periods=n, freq="15min")
    r = rng.standard_t(4, n) * 0.002 + 0.00002
    # biraz rejim/oto-korelasyon ekle
    r = pd.Series(r).ewm(span=3).mean().to_numpy()
    c = baslangic * np.exp(np.cumsum(r))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.001, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.001, n)))
    v = rng.lognormal(3, 0.5, n)
    return pd.DataFrame({"time": zaman, "open": o, "high": h, "low": l, "close": c, "volume": v,
                         "quote_volume": v * c, "trades": rng.integers(100, 1000, n),
                         "taker_buy_base": v * rng.uniform(0.3, 0.7, n)})


def main():
    t0 = time.time()
    mumlar = {s: sahte_mumlar(tohum=i, baslangic=b) for i, (s, b) in
              enumerate(zip(config.SEMBOLLER, [60000, 3000, 0.6]))}
    baglam = {"hatalar": {"not": "sentetik test - dış veri yok"}, "dominans": None,
              "korku_acgozluluk": {"deger": 25, "sinif": "Fear", "dun": 30, "hafta_once": 40},
              "haberler": {"adet": 0, "onemli": []}, "vadeli": {}}
    r = pipeline.calistir(mumlar=mumlar, baglam=baglam, semboller=["BTCUSDT"])
    report.kaydet(r)
    print(report.terminal(r))
    c = r["coinler"]["BTCUSDT"]
    assert all(s["tutarlilik"] >= config.MIN_TUTARLILIK for s in c["risk"]["satirlar"])
    print(f"OK ({time.time() - t0:.0f} sn)")


if __name__ == "__main__":
    main()
