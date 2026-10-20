"""Birim testleri (ağ gerektirmez, saniyeler içinde biter):  python -m pytest -q"""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from btc_tahmin import config, ekveri, gunluk, miner, performans, saglik, sinyal
from btc_tahmin.aciklama import hedef_metni, kosul_bilgisi


# ------------------------------------------------------------------ miner
def test_wilson_alt_az_ornek_daha_dusuk():
    assert miner.wilson_alt(17, 20) < miner.wilson_alt(170, 200) < 0.85
    assert miner.wilson_alt(0, 0) == 0.0


def test_binom_p_sinirlar():
    assert miner.binom_p(0, 0, 0.5) == 1.0
    assert miner.binom_p(90, 100, 0.5) < 1e-6
    assert 0.4 < miner.binom_p(50, 100, 0.5) < 0.6


def test_aile_ince_kosul_ayni_aile():
    assert miner.aile("RSI~:35..40") == miner.aile("RSI:30-45") == "RSI"


def test_ayristir_gun_ve_blok():
    idx = np.array([0, 1, 2, 10, 11, 30])
    gun = np.array([0] * 5 + [1] * 10 + [2] * 20)
    assert miner.ayristir(idx, gun=gun).tolist() == [0, 10, 30]
    assert miner.ayristir(idx, blok=3).tolist() == [0, 10, 30]
    assert miner.ayristir(np.array([], dtype=int), blok=3).tolist() == []


def test_kural_id_sira_bagimsiz():
    assert miner.kural_id("h", 1, ["A:x", "B:y"]) == miner.kural_id("h", 1, ["B:y", "A:x"])


# ------------------------------------------------------------------ sinyal
def test_agirlik_wilson():
    assert sinyal.agirlik(0.85, 0) == 0.0
    assert 0 < sinyal.agirlik(0.85, 20) < sinyal.agirlik(0.85, 200) < 0.35
    assert sinyal.agirlik(0.55, 20) == 0.0    # alt sınır %50'nin altında: söz hakkı yok


def test_ufuk():
    assert sinyal.ufuk("gun_sonu") == "gun_sonu"
    for h in ("sonraki_mum", "sonraki_yesil", "ileri_3", "seri_2_kirmizi"):
        assert sinyal.ufuk(h) == "kisa"


def test_karar_bekle_ve_yon():
    assert sinyal.karar([])["sinyal"] == "BEKLE"
    oy = lambda yon, w: {"yon": yon, "agirlik": w, "tutarlilik": 0.5 + w, "n": 50, "aciklama": "x"}
    assert sinyal.karar([oy("LONG", 0.3), oy("SHORT", 0.28)])["sinyal"] == "BEKLE"
    k = sinyal.karar([oy("LONG", 0.3), oy("SHORT", 0.1)])
    assert k["sinyal"] == "LONG" and k["long_oy"] == 1 and k["short_oy"] == 1 and k["guc"] == 0.5
    assert sinyal.karar([oy("LONG", 0.0)])["sinyal"] == "BEKLE"


def _kt(**kosullar):
    return pd.DataFrame({k: [v] for k, v in kosullar.items()})


def test_oylar_ufuk_ayrimi_ve_emekli():
    KT = _kt(**{"A:x": True, "B:y": True})
    kurallar = {"sonraki_mum": [{"hedef": "sonraki_mum", "yon": "YESIL/YUKARI", "tutarlilik": 0.8, "test_n": 50, "kosullar": ["A:x"]}],
                "gun_sonu": [{"hedef": "gun_sonu", "yon": "KIRMIZI/ASAGI", "tutarlilik": 0.8, "test_n": 50, "kosullar": ["B:y"]},
                             {"hedef": "gun_sonu", "yon": "KIRMIZI/ASAGI", "tutarlilik": 0.9, "test_n": 50, "kosullar": ["B:y"], "emekli": True}]}
    kisa = sinyal.oylar(0, KT, kurallar, [], "15m", 0, "kisa")
    gs = sinyal.oylar(0, KT, kurallar, [], "15m", 0, "gun_sonu")
    assert [o["yon"] for o in kisa] == ["LONG"]
    assert [o["yon"] for o in gs] == ["SHORT"]


def test_oylar_model_esik():
    KT = _kt(**{"A:x": False})
    yon = [{"tur": "HAM", "model": "GB (sonraki_yesil)", "hedef": "sonraki_yesil", "p_gecmis": [0.5, 0.9]},
           {"tur": "YON", "model": "GB (sonraki_yesil)", "hedef": "sonraki_yesil", "tutarlilik": 0.8, "test_n": 40, "guven_marji": 0.2}]
    assert [o["yon"] for o in sinyal.oylar(0, KT, {}, yon, "15m", 0, "kisa")] == ["LONG"]
    assert sinyal.oylar(0, KT, {}, yon, "15m", 1, "kisa") == []      # bir mum önce p=0.5: eşik altı
    assert sinyal.oylar(0, KT, {}, yon, "15m", 0, "gun_sonu") == []  # farklı ufuk


# ------------------------------------------------------------------ gunluk
def test_cikis_zamani():
    t = pd.Timestamp("2026-01-10 12:00", tz="UTC")
    sure = pd.Timedelta("15min")
    assert gunluk._cikis_zamani("sonraki_mum", t, sure) == t + sure
    assert gunluk._cikis_zamani("ileri_4", t, sure) == t + 4 * sure
    # TSİ gün sonu 23:59 = 20:45 UTC açılışlı son mum
    assert gunluk._cikis_zamani("gun_sonu", t, sure) == pd.Timestamp("2026-01-10 20:45", tz="UTC")
    # 20:45 UTC mumu (TSİ 23:45-24:00) günün son mumu: çıkış kendisi
    assert gunluk._cikis_zamani("gun_sonu", pd.Timestamp("2026-01-10 20:45", tz="UTC"), sure) == pd.Timestamp("2026-01-10 20:45", tz="UTC")


def test_tur_adi():
    assert gunluk._tur_adi("ileri_3") == "3 mum sonra"
    assert gunluk._tur_adi("seri_2_yesil").startswith("Sonraki 2 mum")


# ------------------------------------------------------------------ performans
def test_istatistik_ve_funding():
    ol = {"idx": np.arange(4), "bolum": np.array([0, 2, 2, 2]), "isabet": np.array([1, 1, 0, 1]),
          "net": np.array([0.5, 0.3, -0.2, 0.1])}
    t = performans.istatistik(ol, 2)
    assert t["islem"] == 3 and t["net_kazanma_orani"] == pytest.approx(2 / 3, abs=1e-3) and t["kar_faktoru"] == 2.0
    assert performans.istatistik(ol, 1) == {"islem": 0}
    f = performans.funding_maliyeti(np.array([0.25, 7.9, 8.0, 24.0]))
    beklenen = np.array([0, 0, 1, 3]) * config.FUNDING_8S_YUZDE
    assert np.allclose(f, beklenen)


# ------------------------------------------------------------------ ekveri ayrıştırıcılar
def test_takvim_ayristir():
    liste = [{"country": "USD", "impact": "High", "title": "CPI", "date": "2026-02-11T08:30:00-05:00", "forecast": "3%", "previous": "2.9%"},
             {"country": "EUR", "impact": "High", "title": "x", "date": "2026-02-11T08:30:00-05:00"},
             {"country": "USD", "impact": "Low", "title": "y", "date": "2026-02-11T08:30:00-05:00"},
             {"country": "USD", "impact": "Medium", "title": "z", "date": "bozuk"}]
    out = ekveri.takvim_ayristir(liste)
    assert len(out) == 1 and out[0]["tarih"] == "2026-02-11T13:30:00Z" and out[0]["etki"] == "yuksek"


def test_opsiyon_ayristir_max_pain():
    simdi = datetime(2026, 3, 1, tzinfo=timezone.utc)
    def enst(vade, strike, tip, oi):
        return {"instrument_name": f"BTC-{vade}-{strike}-{tip}", "open_interest": oi, "underlying_price": 70000}
    liste = [enst("27MAR26", 60000, "C", 100), enst("27MAR26", 80000, "P", 100), enst("27MAR26", 70000, "C", 10),
             enst("27MAR26", 70000, "P", 10), enst("27FEB26", 50000, "C", 999)]   # geçmiş vade atlanır
    o = ekveri.opsiyon_ayristir(liste, simdi)
    assert o["max_pain"] == 70000.0 and o["put_call_orani"] == 1.0 and o["vade"].startswith("2026-03-27")
    with pytest.raises(RuntimeError):
        ekveri.opsiyon_ayristir([], simdi)


def test_etf_ayristir():
    sayfa = ("<table><tr><th>Date</th><th>IBIT</th><th>Total</th></tr>"
             "<tr><td>01 Oct 2025</td><td>10.0</td><td>(123.4)</td></tr>"
             "<tr><td>02 Oct 2025</td><td>10.0</td><td>1,050.0</td></tr>"
             "<tr><td>Total</td><td>-</td><td>900</td></tr></table>")
    out = ekveri.etf_ayristir(sayfa)
    assert [g["net_milyon_usd"] for g in out] == [-123.4, 1050.0]
    assert out[0]["tarih"] == "2025-10-01"


def test_likidasyon_tahmini():
    assert ekveri.likidasyon_tahmini(-3.0, -1.5).startswith("Olası LONG")
    assert ekveri.likidasyon_tahmini(-3.0, 1.5).startswith("Olası SHORT")
    assert ekveri.likidasyon_tahmini(-1.0, -1.5) is None and ekveri.likidasyon_tahmini(None, 1) is None


# ------------------------------------------------------------------ aciklama
def test_hedef_metni_yon():
    assert hedef_metni("sonraki_mum", 1, "15m")[0] is True
    assert hedef_metni("seri_2_kirmizi", 1, "15m")[0] is False
    assert hedef_metni("gun_sonu", 0, "15m")[0] is False


def test_kosul_bilgisi_bilinmeyen_kosul_patlamaz():
    b = kosul_bilgisi("YENI_AILE:durum")
    assert b["etiket"] and "grup" in b


# ------------------------------------------------------------------ saglik
def test_saglik_bos_rapor():
    satirlar = saglik.kontrol({"baglam": {}, "coinler": {}, "karne": {}, "genel_puan": {}})
    assert any(x["durum"] == "hata" for x in satirlar)
    assert set(saglik.ozet(satirlar)) == {"ok", "normal", "hata"}


# ------------------------------------------------------------------ fable stratejileri
def test_fable_islemler_cakismaz_ve_cikis_sinirli():
    from btc_tahmin import fable
    from btc_tahmin.features import veri_seti_hazirla
    from tests.sentetik_test import sahte_mumlar
    o, _, _ = veri_seti_hazirla({"BTCUSDT": sahte_mumlar(n=6000, tohum=3)}, ana="BTCUSDT")
    for st in fable.STRATEJILER:
        isl = fable.islemler(o, st)
        for a, b in zip(isl, isl[1:]):
            assert b["i"] > a["j"], st["id"]                       # tek pozisyon: giriş bir öncekinin çıkışından sonra
        assert all(x["j"] - x["i"] <= x["maks_mum"] for x in isl), st["id"]
        cz = fable.cizelge(o, isl, mum=50)
        assert len(cz) == 51 and all(r["sinyal"] in ("LONG", "SHORT", "BEKLE") for r in cz)
    r = fable.hesapla(o)
    assert set(r) == {s["id"] for s in fable.STRATEJILER}


def test_tarama_sadece_uc_donemde_arti():
    from btc_tahmin import fable
    from btc_tahmin.features import veri_seti_hazirla
    from tests.sentetik_test import sahte_mumlar
    o, _, _ = veri_seti_hazirla({"BTCUSDT": sahte_mumlar(n=8000, tohum=5)}, ana="BTCUSDT")
    t = fable.tarama(o)
    assert t["denenen"] > 300 and t["gecen"]["test"] <= t["gecen"]["dogrulama"] <= t["gecen"]["egitim"]
    for s in t["secilen"]:
        assert all(s["donemler"][d]["toplam_net"] > 0 for d in ("egitim", "dogrulama", "test"))
    sayfa = fable.tarama_sayfa_verisi(o, t)
    assert set(sayfa) == {s["id"] for s in t["secilen"]}


def test_umut_dilimler_ve_oran():
    from btc_tahmin import fable, umut
    from btc_tahmin.features import veri_seti_hazirla
    from tests.sentetik_test import sahte_mumlar
    mumlar = {"BTCUSDT": sahte_mumlar(n=12000, tohum=7)}
    o, _, _ = veri_seti_hazirla(mumlar, ana="BTCUSDT")
    u = umut.calis(mumlar, "BTCUSDT", o, fable.tarama(o))
    assert [z["aralik"] for z in u["ozetler"]] == ["15m", "1h", "4h"]
    assert u["ozetler"][0]["hareket_bolu_maliyet"] < u["ozetler"][1]["hareket_bolu_maliyet"] < u["ozetler"][2]["hareket_bolu_maliyet"]
    assert set(u["dilimler"]) == {"1h", "4h"} and all(d["rejim_simdi"] in ("trend", "yatay") for d in u["dilimler"].values())


def test_anlik_topla_bos_ve_dolu():
    from btc_tahmin import anlik
    cz = [{"zaman": "2026-01-10T12:00:00+00:00", "fiyat": 100.0, "sinyal": "LONG", "cikis_mum": 8, "maks_mum": 8, "pozisyonda": False,
           "cikis": {"durum": "acik", "net": 0.2}}]
    f = {"ad": "x", "istatistik": {"tum": {"islem": 5, "toplam_net": 1.0, "kar_faktoru": 1.5}}, "cizelge": cz, "kurallar": ["a"]}
    rapor = {"olusturma": "2026-01-10T12:15:00+00:00", "coinler": {"BTCUSDT": {
        "aralik": "15m", "son_mum_zamani": "2026-01-10T12:00:00+00:00", "fiyat": 100.0,
        "yon": {"simdi": {"sinyal": "LONG", "guc": 0.5, "long_oy": 2, "short_oy": 0, "en_tutarli": 0.8, "cikis_mum": 3}, "gun_sonu": {"sinyal": "BEKLE", "egilim": {"yon": "SHORT", "olasilik": 0.6, "model_dogrulugu": 0.52}}},
        "aktif_tum": [], "fable": {"s1": f}}}}
    a = anlik.topla(rapor)
    assert [r["kaynak"] for r in a["sinyaller"]] == ["Fable sinyalleri", "Sinyaller"]
    assert a["sinyaller"][1]["cikis"]["mum"] == 3 and a["sinyaller"][1]["cikis"]["saat"] == "16:00"   # 12:00 UTC + 4 mum x 15 dk = 13:00 UTC = 16:00 TSİ
    assert a["sinyaller"][0]["link"] == "fable.html?strat=s1#BTCUSDT" and len(a["egilimler"]) == 1
    bos = anlik.topla({"olusturma": "x", "coinler": {}})
    assert bos["sinyaller"] == [] and bos["acik_pozisyonlar"] == []


def test_son_saat_penceresi():
    from btc_tahmin import anlik
    def satir(z, sinyal="LONG"):
        return {"zaman": z, "fiyat": 100.0, "sinyal": sinyal, "cikis_mum": 2, "maks_mum": 2, "pozisyonda": False,
                "cikis": {"durum": "kapandi", "net": 0.3, "dogru": True, "zaman": z} if sinyal != "BEKLE" else None}
    f = {"ad": "x", "istatistik": {"tum": {"islem": 3, "toplam_net": 1.0, "kar_faktoru": 1.2}}, "kurallar": [],
         "cizelge": [satir("2026-01-10T10:00:00+00:00"), satir("2026-01-10T11:30:00+00:00"), satir("2026-01-10T12:00:00+00:00", "BEKLE")]}
    rapor = {"olusturma": "2026-01-10T12:10:00+00:00",
             "karne": {"son_sinyaller": [{"tur": "kural", "zaman": "2026-01-10T11:45:00+00:00", "sembol": "BTCUSDT", "aciklama": "sonraki 15m mum YEŞİL · RSI", "kural_id": "abc",
                                          "hedef": "sonraki_mum", "yon_yukari": 1, "aralik": "15m", "giris": 100.0, "cikis_zamani": "2026-01-10T12:00:00+00:00",
                                          "tutarlilik": 0.8, "durum": "bekliyor", "net": None}]},
             "coinler": {"BTCUSDT": {"aralik": "15m", "son_mum_zamani": "2026-01-10T12:00:00+00:00", "fiyat": 100.0, "cizelge": [], "fable": {"s1": f}}}}
    a = anlik.son_saat(rapor, 1.0)
    assert [r["kaynak"] for r in a["satirlar"]] == ["Pano · aktif kural", "Fable sinyalleri"]   # 10:00 pencere dışı, en yeni üstte
    assert a["acik"] == 1 and a["kapanan"] == 1 and a["satirlar"][0]["link"] == "grafik.html?s=BTCUSDT&k=abc"


def test_strateji_gunluge_kaydedilir_ve_karnede_gorunur():
    import tempfile
    from pathlib import Path as _P
    from btc_tahmin import config, gunluk
    from tests.sentetik_test import sahte_mumlar
    config.VERI_DIR = _P(tempfile.mkdtemp())
    m = sahte_mumlar(n=300)
    son = m.iloc[-1]
    giris_zamani = m["time"].iloc[-40]
    rapor = {"coinler": {"BTCUSDT": {"aralik": "15m", "son_mum_zamani": son["time"].isoformat(), "fiyat": float(son["close"]),
                                     "aktif_tum": [], "risk": {"ozet": {}},
                                     "strateji_sinyalleri": [{"id": "strateji:umut:trend_9_21:1h", "ad": "Trend EMA9/21", "kaynak": "umut", "tf": "1h", "sid": "trend_9_21",
                                                              "yon": "YESIL", "zaman": giris_zamani.isoformat(), "fiyat": 100.0, "maks_mum": 8, "tutarlilik": 0.6}]}}}
    df, yeni = gunluk.kaydet(gunluk.oku(), rapor)
    assert len(yeni) == 1 and yeni[0]["tur"] == "strateji" and yeni[0]["hedef"] == "ileri_35" and yeni[0]["giris"] == 100.0
    assert yeni[0]["cikis_zamani"] == giris_zamani + pd.Timedelta("15min") * 35      # 1h x 9 mum - 15 dk
    df2, yeni2 = gunluk.kaydet(df, rapor)
    assert not yeni2                                                                  # aynı giriş tekrar yazılmaz
    df3 = gunluk.sonuclandir(df2, {"BTCUSDT": m})
    assert df3["durum"].iloc[0] in ("tuttu", "tutmadi")
    k = gunluk.karne(df3)
    assert "strateji:umut:trend_9_21:1h" in k["stratejiler"] and k["stratejiler"]["strateji:umut:trend_9_21:1h"]["sinyal"] == 1
    assert "Stratejiler (Fable / tarama / uzun vade)" in k["turler"]
