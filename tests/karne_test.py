"""Canlı karne testi (ağ gerektirmez): sinyal kaydı, sonuçlandırma ve tekrar kayıt engeli.
    python -m tests.karne_test
"""
import tempfile
from pathlib import Path


from btc_tahmin import config, gunluk
from tests.sentetik_test import sahte_mumlar


def rapor(m, aktif):
    son = m.iloc[-1]
    return {"coinler": {"BTCUSDT": {"aralik": "15m", "son_mum_zamani": son["time"].isoformat(), "fiyat": float(son["close"]),
                                    "aktif_tum": aktif, "risk": {"ozet": {"long_risk": 30.0, "en_tutarli": 0.8}}}}}


def main():
    config.VERI_DIR = Path(tempfile.mkdtemp())
    tum = sahte_mumlar(n=400)
    simdi = tum.iloc[:300]
    kurallar = [
        {"id": "a", "hedef": "ileri_3", "yon": "YESIL/YUKARI", "tutarlilik": 0.9, "kosullar": ["RSI:<30"]},
        {"id": "b", "hedef": "sonraki_yesil", "yon": "KIRMIZI/ASAGI", "tutarlilik": 0.86, "kosullar": []},
        {"id": "c", "hedef": "seri_2_kirmizi", "yon": "YESIL/YUKARI", "tutarlilik": 0.88, "kosullar": []},
    ]
    df, yeni = gunluk.kaydet(gunluk.oku(), rapor(simdi, kurallar))
    assert len(yeni) == 4, len(yeni)   # 3 kural + gün sonu özeti
    # Aynı mumda tekrar çalışınca yeni kayıt olmamalı
    df, yeni2 = gunluk.kaydet(df, rapor(simdi, kurallar))
    assert not yeni2
    # Bir mum sonra: 'a' (3 mumluk) hâlâ açık -> tekrar kaydedilmez; 'b' (1 mumluk) sonuçlanmadan da kapanmış sayılır
    df, yeni3 = gunluk.kaydet(df, rapor(tum.iloc[:301], kurallar))
    assert "a" not in {s["kural_id"] for s in yeni3}            # 3 mumluk işlem hâlâ açık
    assert "b" in {s["kural_id"] for s in yeni3}                # 1 mumluk işlem bitti, yeni sinyal alınır
    gunluk.yaz(df)
    df = gunluk.sonuclandir(gunluk.oku(), {"BTCUSDT": tum})
    t = simdi.iloc[-1]
    a = df[(df["kural_id"] == "a")].iloc[0]
    beklenen = tum.iloc[302]["close"] > t["close"]
    assert a["durum"] == ("tuttu" if beklenen else "tutmadi"), (a["durum"], beklenen)
    b = df[(df["kural_id"] == "b")].sort_values("sinyal_zamani").iloc[0]
    sonraki = tum.iloc[300]
    assert b["durum"] == ("tuttu" if not sonraki["close"] > sonraki["open"] else "tutmadi")
    c = df[(df["kural_id"] == "c")].iloc[0]
    iki = tum.iloc[300:302]
    assert c["durum"] == ("tuttu" if (iki["close"] < iki["open"]).all() else "tutmadi")
    net = (tum.iloc[302]["close"] / t["close"] - 1) * 100 - config.ISLEM_MALIYETI_YUZDE[config.ISLEM_TURU]
    assert abs(a["net_yuzde"] - round(net, 4)) < 1e-6
    k = gunluk.karne(df)
    print({x: k[x] for x in ("toplam", "bekleyen")}, k["genel"])
    print("OK - karne doğru")


def test_karne():
    main()


if __name__ == "__main__":
    main()
