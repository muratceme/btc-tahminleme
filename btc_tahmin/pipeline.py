"""Tüm parçaları birleştirir: veri -> koşullar -> kurallar + modeller -> risk tablosu."""
from __future__ import annotations

import json
import string
from datetime import datetime, timezone

import pandas as pd

from . import bildirim, config, fable, gunluk, market, miner, models, performans, sinyal
from .features import gun_sonuna_kalan_saat, ince_kosullar, veri_seti_hazirla


def _gun_serisi(o: pd.DataFrame) -> pd.Series:
    return (o["time"] + pd.Timedelta(hours=config.GUN_SONU_UTC_OFFSET_SAAT)).dt.floor("D")


def _kural_onbellek(sembol, aralik):
    return config.CIKTI_DIR / f"kurallar_{sembol}_{aralik}.json"


KURAL_SURUM = 5   # önbellek biçimi değişince eski önbellek yok sayılır


def kurallari_getir(sembol, aralik, o, K, KT, hedef, hizli: bool) -> dict[str, list[dict]]:
    """K: standart koşullar, KT: K + ince eşikli koşullar (derin tarama için)."""
    dosya = _kural_onbellek(sembol, aralik)
    if hizli and dosya.exists():
        kayit = json.loads(dosya.read_text(encoding="utf-8"))
        yas = datetime.now(timezone.utc) - datetime.fromisoformat(kayit["zaman"])
        if (kayit.get("surum") == KURAL_SURUM and kayit.get("min_tutarlilik", 0.70) == config.MIN_TUTARLILIK
                and yas.total_seconds() < 24 * 3600):
            son = KT.iloc[-1]
            for liste in kayit["kurallar"].values():
                for r in liste:
                    r["aktif_su_an"] = bool(all(son.get(k, False) for k in r["kosullar"]))
            return kayit["kurallar"]
    gun = _gun_serisi(o)
    kurallar = {
        "sonraki_mum": [r.sozluk() for r in miner.kurallari_ara(K, hedef["sonraki_yesil"], "sonraki_mum")],
        "gun_sonu": [r.sozluk() for r in miner.kurallari_ara(K, hedef["gun_sonu_yukari"], "gun_sonu", gun=gun)],
        "derin": derin_tarama(KT, hedef),
    }
    # Komisyon sonrası test döneminde zarar ettiren kurallar elenir; kalanlara net kazanç bilgisi eklenir
    kurallar = {k: performans.performans_ekle_ve_ele(v, o, KT, hedef) for k, v in kurallar.items()}
    config.CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    dosya.write_text(json.dumps({"zaman": datetime.now(timezone.utc).isoformat(), "surum": KURAL_SURUM,
                                 "min_tutarlilik": config.MIN_TUTARLILIK, "kurallar": kurallar},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    pd.DataFrame(kurallar["sonraki_mum"] + kurallar["gun_sonu"] + kurallar["derin"]).to_csv(
        config.CIKTI_DIR / f"kurallar_{sembol}_{aralik}.csv", index=False)
    return kurallar


def derin_tarama(KT: pd.DataFrame, hedef: pd.DataFrame) -> list[dict]:
    """3-7 koşullu, ince eşikli kombinasyonlar; sadece TEST döneminde %85+ tutanlar."""
    sonuc = []
    for kolon, blok, yonler in config.DERIN_HEDEFLER:
        bulunan = miner.kurallari_ara(
            KT, hedef[kolon], kolon, max_kosul=config.DERIN_MAX_KOSUL, beam=config.DERIN_BEAM,
            min_destek=config.DERIN_ESIKLER[0], min_tutarlilik=config.DERIN_MIN_TUTARLILIK, blok=blok,
            yonler=yonler, min_kosul=config.DERIN_MIN_KOSUL, esikler=config.DERIN_ESIKLER)
        sonuc.extend(r.sozluk() for r in bulunan)
    sonuc.sort(key=lambda r: (-miner.wilson_alt(r["tutarlilik"] * r["test_n"], r["test_n"]), -r["test_n"]))
    return sonuc


def grafik_verisi_yaz(sembol: str, aralik: str, o: pd.DataFrame, KT: pd.DataFrame, hedef: pd.DataFrame,
                      kurallar: dict[str, list[dict]]):
    """Grafik sayfası için mumlar + her kuralın geçmişteki tüm oluşumları (cikti/veri/<sembol>_<aralik>.js).

    JS dosyası olarak yazılır ki tarayıcı dosyayı doğrudan (file://) açsa bile yüklenebilsin."""
    from .aciklama import hedef_metni, kosul_bilgisi
    # pandas sürümüne göre iç çözünürlük ns ya da µs olabilir; saniyeyi farktan hesapla
    zaman = ((o["time"] - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)).to_numpy()
    def yuv(x):
        return float(f"{x:.6g}")
    mumlar = [[int(t), yuv(a), yuv(b), yuv(c), yuv(d)] for t, a, b, c, d in
              zip(zaman, o["open"], o["high"], o["low"], o["close"])]
    detay = {}
    # Sadece panoda gösterilen kurallar: her listeden en iyi 20 + şu an aktif olanlar
    tum = [r for liste in kurallar.values() for i, r in enumerate(liste) if i < 20 or r["aktif_su_an"]]
    cv = o["close"].to_numpy()
    for r in tum:
        if r["id"] in detay:
            continue
        ol = performans.olusumlar(r, o, KT, hedef)
        if ol is None:
            continue
        # [zaman, dönem(0 eğitim,1 doğrulama,2 test,3 şimdi), isabet, giriş, çıkış, fiyat değişimi %, net işlem sonucu %]
        olusum = [[int(zaman[i]), int(b), int(h), yuv(cv[i]), yuv(cv[j]), round(float((cv[j] / cv[i] - 1) * 100), 3),
                   round(float(n), 3)]
                  for i, j, b, h, n in zip(ol["idx"], ol["cikis_idx"], ol["bolum"], ol["isabet"], ol["net"])]
        if ol["aktif"]:   # şu an aktif: sonucu henüz belli değil
            olusum.append([int(zaman[-1]), 3, -1, yuv(cv[-1]), None, None, None])
        yon = 1 if r["yon"].startswith("YESIL") else 0
        _, metin = hedef_metni(r["hedef"], yon, aralik)
        detay[r["id"]] = {
            "kosullar": [kosul_bilgisi(k) | {"ham": k} for k in r["kosullar"]],
            "hedef": metin, "yukselis": ol["yukselis"], "blok": ol["blok"],
            "tutarlilik": r["tutarlilik"], "test_n": r["test_n"], "egitim_oran": r["egitim_oran"],
            "dogrulama_oran": r["dogrulama_oran"], "taban_oran": r["taban_oran"], "p_deger": r["p_deger"],
            "kaldirac_lift": r["kaldirac_lift"], "maliyet": performans.islem_maliyeti(), "olusumlar": olusum,
        }
    veri = {"sembol": sembol, "aralik": aralik, "mumlar": mumlar, "kurallar": detay,
            "olusturma": datetime.now(timezone.utc).isoformat()}
    hedef_dir = config.CIKTI_DIR / "veri"
    hedef_dir.mkdir(parents=True, exist_ok=True)
    anahtar = f"{sembol}_{aralik}"
    (hedef_dir / f"{anahtar}.js").write_text(
        f"window.KR=window.KR||{{}};window.KR[{json.dumps(anahtar)}]=" + json.dumps(veri, ensure_ascii=False, separators=(",", ":")) + ";",
        encoding="utf-8")


def risk_tablosu(yon_satirlari, kurallar_gs, dusus_satirlari, kirim) -> dict:
    satirlar = []
    for r in yon_satirlari:
        if r["tur"] != "YON" or r["hedef"] != "gun_sonu_yukari":
            continue
        satirlar.append({
            "kaynak": r["model"], "tur": "Yön (gün sonu)", "tutarlilik": r["tutarlilik"], "test_n": r["test_n"],
            "sinyal_var": r["sinyal_var"], "long_risk": r["long_risk_yuzde"], "short_risk": r["short_risk_yuzde"],
            "detay": f"güven marjı ±{r['guven_marji']:.2f}, test günlerinin %{r['kapsama_yuzde']}'inde sinyal verdi",
        })
    for k in kurallar_gs:
        if not k["aktif_su_an"]:
            continue
        p_yukari = k["tutarlilik"] if k["yon"].startswith("YESIL") else 1 - k["tutarlilik"]
        satirlar.append({
            "kaynak": "Kombinasyon: " + " + ".join(k["kosullar"]), "tur": "Yön (gün sonu)", "kosullar": k["kosullar"],
            "tutarlilik": k["tutarlilik"], "test_n": k["test_n"], "sinyal_var": True,
            "long_risk": round(100 * (1 - p_yukari), 1), "short_risk": round(100 * p_yukari, 1),
            "detay": f"testte {k['test_bagimsiz_gun']} farklı gün, lift x{k['kaldirac_lift']}",
        })
    for d in dusus_satirlari:
        satirlar.append({
            "kaynak": d["model"], "tur": "Max düşüş (gün sonuna kadar)", "tutarlilik": d["tutarlilik"],
            "test_n": d["test_n"], "sinyal_var": True, "max_dusus": d["max_dusus_yuzde"], "detay": d["aciklama"],
        })
    satirlar = [s for s in satirlar if s["tutarlilik"] >= config.MIN_TUTARLILIK]
    satirlar.sort(key=lambda s: (-s["tutarlilik"], -s["test_n"]))
    harfler = list(string.ascii_uppercase) + [a + b for a in string.ascii_uppercase for b in string.ascii_uppercase]
    for h, s in zip(harfler, satirlar):
        s["etiket"] = f"Risk-{h}"

    # Özet: sinyal veren yön satırlarının tutarlılık ağırlıklı ortalaması
    aktif = [s for s in satirlar if s["tur"].startswith("Yön") and s["sinyal_var"]]
    ozet = {"long_risk": None, "short_risk": None, "dayanak_sayisi": len(aktif)}
    w = [sinyal.agirlik(s["tutarlilik"], s["test_n"]) for s in aktif]
    if aktif and sum(w) > 0:
        lr = sum(wi * s["long_risk"] for wi, s in zip(w, aktif)) / sum(w)
        ozet.update(long_risk=round(lr, 1), short_risk=round(100 - lr, 1),
                    en_tutarli=max(s["tutarlilik"] for s in aktif))
    ham = [r for r in yon_satirlari if r["tur"] == "HAM" and r["hedef"] == "gun_sonu_yukari"]
    if ham:
        ozet["ham_model_long_risk"] = round(sum(r["long_risk_yuzde"] for r in ham) / len(ham), 1)
        ozet["ham_model_dogrulugu"] = round(sum(r["modelin_genel_dogrulugu"] for r in ham) / len(ham), 4)
        ozet["teshis"] = [{"model": r["model"].split(" (")[0], "genel": r["modelin_genel_dogrulugu"], **r["teshis"]}
                          for r in ham if r.get("teshis")]
    dusus = [s for s in satirlar if s["tur"].startswith("Max")]
    if dusus:
        ozet["max_dusus"] = {f"%{int(round(s['tutarlilik'] * 100))}": s["max_dusus"] for s in dusus}
    temel = ozet["long_risk"]   # tutarlı sinyal yoksa kırımlı risk de hesaplanmaz (düşük güvenli sayı sunulmaz)
    if temel is not None:
        # Puan kırımı ayrı gösterilir: risk + kırım * (100 - risk) / 100
        ozet["kirimli_long_risk"] = round(min(99.0, temel + kirim["toplam_kirim"] * (100 - temel) / 100), 1)
    return {"satirlar": satirlar, "ozet": ozet}


def pozisyon_onerisi(fiyat: float, oz: dict, kirim: dict) -> dict:
    """Kasa ve işlem başı riske göre pozisyon büyüklüğü, stop ve hedef (yalnızca hesap makinesi; tavsiye değil).

    Stop, gün içi en kötü hareket sınırının en güvenli seviyesinden (%90 ise %90) alınır. Risk tutarı genel
    piyasa puanıyla küçültülür (puan %80 ise risk de %80'ine iner). Hedef: 1,5 kat risk (1:1,5)."""
    lr = oz.get("long_risk")
    if lr is None or 40 <= lr <= 60:
        return {"durum": "yok", "neden": "Tutarlı ve net bir gün sonu yön sinyali yok (long riski %40-60 arasında ya da hesaplanamadı)."}
    long = lr < 40
    sinirlar = oz.get("max_dusus") if long else oz.get("max_yukselis")
    if not sinirlar:
        return {"durum": "yok", "neden": "Stop seviyesi için gün içi hareket sınırı hesaplanamadı."}
    seviye, sinir = max(sinirlar.items(), key=lambda kv: int(kv[0].strip("%")))
    stop_yuzde = abs(float(sinir)) * 1.1 + 0.05          # sınırın biraz ötesi: gürültüyle stop olmasın
    puan_carpani = max(0.0, kirim["genel_puan"] / 100)
    risk_usd = config.KASA_USD * config.ISLEM_BASI_RISK_YUZDE / 100 * puan_carpani
    pozisyon = risk_usd / (stop_yuzde / 100)
    sinirli = pozisyon > config.KASA_USD * config.MAX_KALDIRAC
    pozisyon = min(pozisyon, config.KASA_USD * config.MAX_KALDIRAC)
    hedef_yuzde = stop_yuzde * 1.5
    yon = 1 if long else -1
    return {
        "durum": "var", "yon": "LONG" if long else "SHORT", "giris": fiyat,
        "stop": round(fiyat * (1 - yon * stop_yuzde / 100), 6), "stop_yuzde": round(stop_yuzde, 2),
        "hedef": round(fiyat * (1 + yon * hedef_yuzde / 100), 6), "hedef_yuzde": round(hedef_yuzde, 2),
        "pozisyon_usd": round(pozisyon, 2), "kaldirac": round(pozisyon / config.KASA_USD, 2),
        "risk_usd": round(risk_usd if not sinirli else pozisyon * stop_yuzde / 100, 2),
        "kasa_usd": config.KASA_USD, "islem_basi_risk_yuzde": config.ISLEM_BASI_RISK_YUZDE,
        "puan_carpani": round(puan_carpani, 2), "stop_dayanagi": f"{seviye} güvenle gün içi en kötü hareket {sinir}%",
        "kaldirac_siniri_uygulandi": sinirli,
    }


def _degisim_24s(o: pd.DataFrame):
    once = o[o["time"] <= o["time"].iloc[-1] - pd.Timedelta(hours=24)]
    if once.empty:
        return None
    return round(float(o["close"].iloc[-1] / once["close"].iloc[-1] - 1) * 100, 2)


def veri_boslugu(m: pd.DataFrame, aralik: str) -> dict:
    """Mum serisindeki eksikler: Binance bakım/kesinti anlarında mum gelmez, indikatörler sessizce bozulur."""
    sure = pd.Timedelta(aralik.replace("m", "min"))
    fark = m["time"].diff().iloc[1:]
    bosluk = fark[fark > sure]
    eksik = int(((bosluk / sure) - 1).sum()) if len(bosluk) else 0
    son7 = m["time"].iloc[-1] - pd.Timedelta(days=7)
    yakin = bosluk[m["time"].iloc[1:].loc[bosluk.index] >= son7] if len(bosluk) else bosluk
    return {"eksik_mum": eksik, "bosluk_sayisi": int(len(bosluk)), "eksik_yuzde": round(100 * eksik / max(1, len(m) + eksik), 3),
            "son7_gun_bosluk": int(len(yakin)),
            "son_bosluk": m["time"].iloc[1:].loc[bosluk.index[-1]].isoformat() if len(bosluk) else None}


def sahte_kesif_oku(sembol: str, aralik: str) -> dict | None:
    """'python -m btc_tahmin sahte' çıktısı varsa okur (kaç kuralın şans eseri olabileceği)."""
    f = config.CIKTI_DIR / f"sahte_{sembol}_{aralik}.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def coin_analizi(sembol: str, aralik: str, mumlar: dict, kirim: dict, hizli: bool, emekli: set | None = None) -> dict:
    o, K, hedef = veri_seti_hazirla(mumlar, ana=sembol)
    KT = pd.concat([K, ince_kosullar(o)], axis=1)
    kurallar = kurallari_getir(sembol, aralik, o, K, KT, hedef, hizli)
    # Canlı karnede kötü giden kurallar işaretlenir ve "şu an aktif" listelerinden çıkarılır
    for liste in kurallar.values():
        for r in liste:
            r["emekli"] = r["id"] in (emekli or set())
            if r["emekli"]:
                r["aktif_su_an"] = False
    grafik_verisi_yaz(sembol, aralik, o, KT, hedef, kurallar)
    simulasyon = {ad: performans.kasa_simulasyonu(kurallar[ad], o, KT, hedef) for ad in ("derin", "sonraki_mum")}
    yon = models.yon_modelleri(o, hedef, "gun_sonu_yukari") + models.yon_modelleri(o, hedef, "sonraki_yesil")
    dusus = models.dusus_riski(o, hedef)
    tablo = risk_tablosu(yon, kurallar["gun_sonu"], dusus, kirim)
    tablo["ozet"]["max_yukselis"] = models.yukselis_siniri(o, hedef)

    son = o.iloc[-1]
    aktif_kosullar = [k for k, v in K.iloc[-1].items() if v]
    sonraki_aktif = [r for r in kurallar["sonraki_mum"] if r["aktif_su_an"]]
    sonraki_ml = [r for r in yon if r["tur"] == "YON" and r["hedef"] == "sonraki_yesil"]
    sonuc = {
        "sembol": sembol, "aralik": aralik,
        "son_mum_zamani": son["time"].isoformat(), "fiyat": float(son["close"]),
        "degisim_24s": _degisim_24s(o),
        "veri_mum_sayisi": int(len(o)),
        "gun_sonuna_kalan_saat": round(float(gun_sonuna_kalan_saat(o).iloc[-1]), 2),
        "son_fiyatlar": [round(float(x), 6) for x in o["close"].iloc[-96:]],
        "veri_baslangic": o["time"].iloc[0].isoformat(),
        "teknik_ozet": {
            "RSI": round(float(son["rsi"]), 1), "ADX": round(float(son["adx"]), 1),
            "MACD_hist": round(float(son["macd_hist"]), 4), "Supertrend": "boğa" if son["supertrend"] > 0 else "ayı",
            "BB_%": round(float(son["bb_pct"]), 2), "ATR_%": round(float(son["atr_pct"]), 3),
            "EMA200_ustunde": bool(son["close"] > son["ema200"]), "VWAP_sapma_%": round(float(son["vwap_sapma"]), 3),
        },
        "aktif_kosullar": aktif_kosullar,
        "risk": tablo,
        "sonraki_mum": {
            "aktif_kurallar": sonraki_aktif[:25],
            "ml": sonraki_ml,
        },
        "derin": {"aktif": [r for r in kurallar["derin"] if r["aktif_su_an"]][:30]},
        "kural_kutuphanesi": {k: v[:60] for k, v in kurallar.items()},
        "simulasyon": simulasyon,
        "pozisyon": pozisyon_onerisi(float(o["close"].iloc[-1]), tablo["ozet"], kirim),
        "yon": sinyal.hesapla(o, KT, kurallar, yon, aralik),
        "cizelge": sinyal.zaman_cizelgesi(o, KT, kurallar, yon, aralik),
        "fable": fable.hesapla(o),
        "tarama": (lambda t: {**t, "sayfa": fable.tarama_sayfa_verisi(o, t, fable.rejim_serisi(o))})(fable.tarama(o)),
        "cizelge_mumlar": [[int((t - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)), float(a), float(b), float(c_), float(d)]
                           for t, a, b, c_, d in zip(o["time"].iloc[-config.CIZELGE_MUM - 40:], o["open"].iloc[-config.CIZELGE_MUM - 40:],
                                                     o["high"].iloc[-config.CIZELGE_MUM - 40:], o["low"].iloc[-config.CIZELGE_MUM - 40:],
                                                     o["close"].iloc[-config.CIZELGE_MUM - 40:])],
        "aktif_tum": [{k: r[k] for k in ("id", "hedef", "yon", "tutarlilik", "kosullar")}
                      for liste in kurallar.values() for r in liste if r["aktif_su_an"]],
        "kural_sayisi": {k: len(v) for k, v in kurallar.items()},
        "net_zararli_sayisi": {k: sum(1 for r in v if r.get("net_zararli")) for k, v in kurallar.items()},
        "veri_boslugu": veri_boslugu(mumlar[sembol], aralik),
        "sahte_kesif": sahte_kesif_oku(sembol, aralik),
    }
    from . import umut
    sonuc["umut"] = umut.calis(mumlar, sembol, o, sonuc["tarama"]) if aralik in ("5m", "10m", "15m", "30m") else None
    return sonuc


def _ilerleme(i: int, toplam: int, sembol: str) -> None:
    """Terminale ve (canlı moddaysa) 'hazırlanıyor' sayfasına ilerleme yazar."""
    from . import sunucu
    mesaj = f"{sembol} analiz ediliyor ({i + 1}/{toplam}) ..."
    print(f"  · {mesaj}", flush=True)
    sunucu.DURUM = mesaj


def calistir(aralik: str = config.VARSAYILAN_ARALIK, semboller=None, hizli: bool = False,
             guncelle: bool = True, mumlar: dict | None = None, baglam: dict | None = None) -> dict:
    from . import data
    semboller = semboller or config.SEMBOLLER
    mumlar_verildi = mumlar is not None
    if mumlar is None:
        from . import sunucu
        sunucu.DURUM = "Binance'ten mumlar indiriliyor ve piyasa verileri toplanıyor ..."
        mumlar = {s: data.mumlari_getir(s, aralik, guncelle=guncelle) for s in config.SEMBOLLER}
    if baglam is None:
        baglam = market.baglam_topla(config.SEMBOLLER)
    if (baglam.get("makro") or {}).get("veriler") and config.ANA_SEMBOL in mumlar:
        from . import ekveri
        baglam["makro"]["btc_korelasyon"] = ekveri.btc_korelasyonu(baglam["makro"], mumlar[config.ANA_SEMBOL])
        for v in baglam["makro"]["veriler"].values():
            v.pop("seri", None)    # rapor dosyasını şişirmesin
    canli = mumlar_verildi is False     # testlerde (dışarıdan mum verilince) gerçek günlüğe yazılmaz
    olaylar = market.olaylari_oku()
    kirim = market.puan_kirimlari(baglam, olaylar, config.ANA_SEMBOL)
    gun = gunluk.sonuclandir(gunluk.oku(), mumlar) if canli else gunluk.oku().iloc[0:0]
    rapor = {
        "olusturma": datetime.now(timezone.utc).isoformat(),
        "aralik": aralik, "genel_puan": kirim, "baglam": baglam,
        "coinler": {s: _ilerleme(i, len(semboller), s) or coin_analizi(s, aralik, mumlar, kirim, hizli, gunluk.emekliler(gun))
                    for i, s in enumerate(semboller)},
        "uyari": ("Bu sistem istatistiksel bir karar destek aracıdır, yatırım tavsiyesi değildir. "
                  "Tutarlılık oranları geçmiş TEST dönemine aittir; piyasa rejimi değişirse düşebilir."),
    }
    gun, yeni = gunluk.kaydet(gun, rapor)
    if canli:
        gunluk.yaz(gun)
        rapor["bildirim"] = bildirim.yeni_sinyaller(yeni)
    rapor["karne"] = gunluk.karne(gun)
    from . import saglik
    rapor["saglik"] = saglik.kontrol(rapor)
    config.CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    (config.CIKTI_DIR / "rapor.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1, default=str),
                                                  encoding="utf-8")
    return rapor
