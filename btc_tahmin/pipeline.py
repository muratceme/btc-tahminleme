"""Tüm parçaları birleştirir: veri -> koşullar -> kurallar + modeller -> risk tablosu."""
from __future__ import annotations

import json
import string
from datetime import datetime, timezone

import pandas as pd

from . import config, market, miner, models
from .features import gun_sonuna_kalan_saat, veri_seti_hazirla


def _gun_serisi(o: pd.DataFrame) -> pd.Series:
    return (o["time"] + pd.Timedelta(hours=config.GUN_SONU_UTC_OFFSET_SAAT)).dt.floor("D")


def _kural_onbellek(sembol, aralik):
    return config.CIKTI_DIR / f"kurallar_{sembol}_{aralik}.json"


def kurallari_getir(sembol, aralik, o, K, hedef, hizli: bool) -> dict[str, list[dict]]:
    dosya = _kural_onbellek(sembol, aralik)
    if hizli and dosya.exists():
        kayit = json.loads(dosya.read_text(encoding="utf-8"))
        yas = datetime.now(timezone.utc) - datetime.fromisoformat(kayit["zaman"])
        if yas.total_seconds() < 24 * 3600:
            son = K.iloc[-1]
            for liste in kayit["kurallar"].values():
                for r in liste:
                    r["aktif_su_an"] = bool(all(son.get(k, False) for k in r["kosullar"]))
            return kayit["kurallar"]
    gun = _gun_serisi(o)
    kurallar = {
        "sonraki_mum": [r.sozluk() for r in miner.kurallari_ara(K, hedef["sonraki_yesil"], "sonraki_mum")],
        "gun_sonu": [r.sozluk() for r in miner.kurallari_ara(K, hedef["gun_sonu_yukari"], "gun_sonu", gun=gun)],
    }
    config.CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    dosya.write_text(json.dumps({"zaman": datetime.now(timezone.utc).isoformat(), "kurallar": kurallar},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    pd.DataFrame(kurallar["sonraki_mum"] + kurallar["gun_sonu"]).to_csv(
        config.CIKTI_DIR / f"kurallar_{sembol}_{aralik}.csv", index=False)
    return kurallar


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
    kurallar = kurallari_getir(sembol, aralik, o, K, hedef, hizli)
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
    config.CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    (config.CIKTI_DIR / "rapor.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=1, default=str),
                                                  encoding="utf-8")
    return rapor
