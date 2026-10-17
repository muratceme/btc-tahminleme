"""Tüm parçaları birleştirir: veri -> koşullar -> kurallar + modeller -> risk tablosu."""
from __future__ import annotations

import json
import string
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config, market, miner, models
from .features import gun_sonuna_kalan_saat, ince_kosullar, veri_seti_hazirla


def _gun_serisi(o: pd.DataFrame) -> pd.Series:
    return (o["time"] + pd.Timedelta(hours=config.GUN_SONU_UTC_OFFSET_SAAT)).dt.floor("D")


def _kural_onbellek(sembol, aralik):
    return config.CIKTI_DIR / f"kurallar_{sembol}_{aralik}.json"


KURAL_SURUM = 2   # önbellek biçimi değişince eski önbellek yok sayılır


def kurallari_getir(sembol, aralik, o, K, KT, hedef, hizli: bool) -> dict[str, list[dict]]:
    """K: standart koşullar, KT: K + ince eşikli koşullar (derin tarama için)."""
    dosya = _kural_onbellek(sembol, aralik)
    if hizli and dosya.exists():
        kayit = json.loads(dosya.read_text(encoding="utf-8"))
        yas = datetime.now(timezone.utc) - datetime.fromisoformat(kayit["zaman"])
        if kayit.get("surum") == KURAL_SURUM and yas.total_seconds() < 24 * 3600:
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
    config.CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    dosya.write_text(json.dumps({"zaman": datetime.now(timezone.utc).isoformat(), "surum": KURAL_SURUM,
                                 "kurallar": kurallar}, ensure_ascii=False, indent=1), encoding="utf-8")
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


def _hedef_tanimi(hedef_adi: str, o: pd.DataFrame, hedef: pd.DataFrame):
    """(hedef serisi, bağımsızlık bloğu, gün serisi ya da None, çıkış fiyatı serisi)"""
    c = o["close"]
    if hedef_adi in ("sonraki_mum", "sonraki_yesil"):
        return hedef["sonraki_yesil"], 1, None, c.shift(-1)
    if hedef_adi == "gun_sonu":
        return hedef["gun_sonu_yukari"], 1, _gun_serisi(o), hedef["gun_sonu_fiyat"]
    n = int(hedef_adi.split("_")[1])
    return hedef[hedef_adi], n, None, c.shift(-n)


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
    for r in tum:
        if r["id"] in detay or not all(k in KT.columns for k in r["kosullar"]):
            continue
        y, blok, gun, cikis = _hedef_tanimi(r["hedef"], o, hedef)
        yon = 1 if r["yon"].startswith("YESIL") else 0
        maske = KT[r["kosullar"]].all(axis=1).to_numpy()
        gecerli = y.notna().to_numpy()
        V = np.nonzero(gecerli)[0]
        s1 = int(len(V) * config.EGITIM_ORANI)
        s2 = int(len(V) * (config.EGITIM_ORANI + config.DOGRULAMA_ORANI))
        idx = miner.ayristir(np.nonzero(maske & gecerli)[0], None if gun is None else gun.to_numpy(), blok)
        olusum = []
        yv, cv, ck = y.to_numpy(), o["close"].to_numpy(), cikis.to_numpy()
        for i in idx:
            sira = np.searchsorted(V, i)
            bolum = 0 if sira < s1 else (1 if sira < s2 else 2)
            olusum.append([int(zaman[i]), bolum, int(yv[i] == yon), yuv(cv[i]), yuv(ck[i]),
                           round(float((ck[i] / cv[i] - 1) * 100), 3)])
        if maske[-1]:   # şu an aktif: sonucu henüz belli değil
            olusum.append([int(zaman[-1]), 3, -1, yuv(cv[-1]), None, None])
        yukselis, metin = hedef_metni(r["hedef"], yon, aralik)
        detay[r["id"]] = {
            "kosullar": [kosul_bilgisi(k) | {"ham": k} for k in r["kosullar"]],
            "hedef": metin, "yukselis": yukselis, "blok": blok,
            "tutarlilik": r["tutarlilik"], "test_n": r["test_n"], "egitim_oran": r["egitim_oran"],
            "dogrulama_oran": r["dogrulama_oran"], "taban_oran": r["taban_oran"], "p_deger": r["p_deger"],
            "kaldirac_lift": r["kaldirac_lift"], "olusumlar": olusum,
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
    if aktif:
        w = [(s["tutarlilik"] - 0.5) for s in aktif]
        lr = sum(wi * s["long_risk"] for wi, s in zip(w, aktif)) / sum(w)
        ozet.update(long_risk=round(lr, 1), short_risk=round(100 - lr, 1),
                    en_tutarli=max(s["tutarlilik"] for s in aktif))
    ham = [r for r in yon_satirlari if r["tur"] == "HAM" and r["hedef"] == "gun_sonu_yukari"]
    if ham:
        ozet["ham_model_long_risk"] = round(sum(r["long_risk_yuzde"] for r in ham) / len(ham), 1)
        ozet["ham_model_dogrulugu"] = round(sum(r["modelin_genel_dogrulugu"] for r in ham) / len(ham), 4)
    dusus = [s for s in satirlar if s["tur"].startswith("Max")]
    if dusus:
        ozet["max_dusus"] = {f"%{int(round(s['tutarlilik'] * 100))}": s["max_dusus"] for s in dusus}
    temel = ozet["long_risk"]   # tutarlı sinyal yoksa kırımlı risk de hesaplanmaz (düşük güvenli sayı sunulmaz)
    if temel is not None:
        # Puan kırımı ayrı gösterilir: risk + kırım * (100 - risk) / 100
        ozet["kirimli_long_risk"] = round(min(99.0, temel + kirim["toplam_kirim"] * (100 - temel) / 100), 1)
    return {"satirlar": satirlar, "ozet": ozet}


def _degisim_24s(o: pd.DataFrame):
    once = o[o["time"] <= o["time"].iloc[-1] - pd.Timedelta(hours=24)]
    if once.empty:
        return None
    return round(float(o["close"].iloc[-1] / once["close"].iloc[-1] - 1) * 100, 2)


def coin_analizi(sembol: str, aralik: str, mumlar: dict, kirim: dict, hizli: bool) -> dict:
    o, K, hedef = veri_seti_hazirla(mumlar, ana=sembol)
    KT = pd.concat([K, ince_kosullar(o)], axis=1)
    kurallar = kurallari_getir(sembol, aralik, o, K, KT, hedef, hizli)
    grafik_verisi_yaz(sembol, aralik, o, KT, hedef, kurallar)
    yon = models.yon_modelleri(o, hedef, "gun_sonu_yukari") + models.yon_modelleri(o, hedef, "sonraki_yesil")
    dusus = models.dusus_riski(o, hedef)
    tablo = risk_tablosu(yon, kurallar["gun_sonu"], dusus, kirim)

    son = o.iloc[-1]
    aktif_kosullar = [k for k, v in K.iloc[-1].items() if v]
    sonraki_aktif = [r for r in kurallar["sonraki_mum"] if r["aktif_su_an"]]
    sonraki_ml = [r for r in yon if r["tur"] == "YON" and r["hedef"] == "sonraki_yesil"]
    return {
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
        "kural_sayisi": {k: len(v) for k, v in kurallar.items()},
    }


def calistir(aralik: str = config.VARSAYILAN_ARALIK, semboller=None, hizli: bool = False,
             guncelle: bool = True, mumlar: dict | None = None, baglam: dict | None = None) -> dict:
    from . import data
    semboller = semboller or config.SEMBOLLER
    if mumlar is None:
        mumlar = {s: data.mumlari_getir(s, aralik, guncelle=guncelle) for s in config.SEMBOLLER}
    if baglam is None:
        baglam = market.baglam_topla(config.SEMBOLLER)
    olaylar = market.olaylari_oku()
    kirim = market.puan_kirimlari(baglam, olaylar, config.ANA_SEMBOL)
    rapor = {
        "olusturma": datetime.now(timezone.utc).isoformat(),
        "aralik": aralik, "genel_puan": kirim, "baglam": baglam,
        "coinler": {s: coin_analizi(s, aralik, mumlar, kirim, hizli) for s in semboller},
        "uyari": ("Bu sistem istatistiksel bir karar destek aracıdır, yatırım tavsiyesi değildir. "
                  "Tutarlılık oranları geçmiş TEST dönemine aittir; piyasa rejimi değişirse düşebilir."),
    }
    from . import saglik
    rapor["saglik"] = saglik.kontrol(rapor)
    config.CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    (config.CIKTI_DIR / "rapor.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1, default=str),
                                                  encoding="utf-8")
    return rapor
