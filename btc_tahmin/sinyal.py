"""Yön sinyali (LONG / SHORT / BEKLE) ve geriye dönük kontrol.

İki ayrı ufukta sinyal üretilir; farklı vadeler aynı oya karıştırılmaz:
  * KISA VADE : sonraki mum, 2-8 mum sonra, seri mumlar hedefli kurallar + "sonraki mum" modeli
  * GÜN SONU  : gün sonu hedefli kurallar + gün sonu modeli

Her kaynağın ağırlığı, tutarlılığının Wilson ALT SINIRI − 0,5'tir. Böylece 20 örnekli %85'lik bir
kural, 200 örnekli %85'lik kuraldan daha az söz hakkı alır (az örnek = daha geniş hata payı).

Geriye dönük kontrol (kısa vade): 15/30/45/60 dakika önceki mumda sistem hangi sinyali veriyordu ve o an
long ya da short açılsaydı şu anki fiyatla (komisyon dahil) sonuç ne olurdu?
"""
from __future__ import annotations

import pandas as pd

from . import config
from .aciklama import hedef_metni, kosul_bilgisi
from .miner import wilson_alt

KARARSIZLIK_ESIGI = 0.2   # iki taraf oyları birbirine bu kadar yakınsa BEKLE
UFUKLAR = {"kisa": "Kısa vade (sonraki mumlar)", "gun_sonu": "Gün sonu"}


def _dakika(aralik: str) -> int:
    return int(aralik[:-1]) * (60 if aralik.endswith("h") else 1)


def ufuk(hedef: str) -> str:
    return "gun_sonu" if hedef.startswith("gun") else "kisa"


def agirlik(tutarlilik: float, n: int) -> float:
    """Oy ağırlığı: tutarlılığın Wilson alt sınırı − 0,5 (negatifse 0)."""
    return max(0.0, wilson_alt(tutarlilik * n, n) - 0.5) if n else 0.0


def oylar(i: int, KT: pd.DataFrame, kurallar: dict[str, list[dict]], yon_satirlari: list[dict],
          aralik: str, geri: int, ufuk_adi: str = "kisa") -> list[dict]:
    """i. mumda aktif olan kaynakların oyları. geri: son mumdan kaç mum geride (ML geçmiş tahmini için)."""
    satir = KT.iloc[i]
    out = []
    for liste in kurallar.values():
        for r in liste:
            if ufuk(r["hedef"]) != ufuk_adi or r.get("emekli") or not all(satir.get(k, False) for k in r["kosullar"]):
                continue
            yon = 1 if r["yon"].startswith("YESIL") else 0
            yukselis, metin = hedef_metni(r["hedef"], yon, aralik)
            out.append({"yon": "LONG" if yukselis else "SHORT", "agirlik": agirlik(r["tutarlilik"], r["test_n"]),
                        "tutarlilik": r["tutarlilik"], "n": r["test_n"], "kaynak": "kural",
                        "aciklama": metin + " · " + " + ".join(kosul_bilgisi(k)["etiket"] for k in r["kosullar"])})
    # Yapay zekâ modelleri: o mumdaki tahmin, bir tutarlılık seviyesinin güven eşiğini geçiyorsa oy verir
    ham = {(r["model"]): r for r in yon_satirlari if r["tur"] == "HAM"}
    en_iyi: dict[str, dict] = {}
    for r in yon_satirlari:
        if r["tur"] != "YON" or r["model"] not in ham or ufuk(r["hedef"]) != ufuk_adi:
            continue
        pg = ham[r["model"]].get("p_gecmis") or []
        if geri >= len(pg):
            continue
        p = pg[-1 - geri]
        if abs(p - 0.5) >= r["guven_marji"] and (r["model"] not in en_iyi or r["tutarlilik"] > en_iyi[r["model"]]["tutarlilik"]):
            yukari = p > 0.5
            ufuk_metni = "gün sonu" if ufuk_adi == "gun_sonu" else f"sonraki {aralik} mum"
            en_iyi[r["model"]] = {"yon": "LONG" if yukari else "SHORT", "agirlik": agirlik(r["tutarlilik"], r["test_n"]),
                                  "tutarlilik": r["tutarlilik"], "n": r["test_n"], "kaynak": "model",
                                  "aciklama": f"{r['model'].split(' (')[0]} modeli · {ufuk_metni} {'YUKARI' if yukari else 'AŞAĞI'} "
                                              f"(olasılık %{max(p, 1 - p) * 100:.0f})"}
    out.extend(en_iyi.values())
    return out


def karar(o: list[dict]) -> dict:
    lw = sum(x["agirlik"] for x in o if x["yon"] == "LONG")
    sw = sum(x["agirlik"] for x in o if x["yon"] == "SHORT")
    toplam = lw + sw
    if not o or toplam <= 0:
        neden = "Aktif tutarlı kural/model yok." if not o else "Aktif kaynaklar var ama örnek sayıları az; güvenli ağırlıkları sıfır."
        return {"sinyal": "BEKLE", "guc": 0.0, "long_oy": 0, "short_oy": 0, "neden": neden}
    guc = abs(lw - sw) / toplam
    sinyal = "BEKLE" if guc < KARARSIZLIK_ESIGI else ("LONG" if lw > sw else "SHORT")
    secili = sorted(o, key=lambda x: -x["agirlik"])
    return {
        "sinyal": sinyal, "guc": round(guc, 3),
        "long_oy": sum(1 for x in o if x["yon"] == "LONG"), "short_oy": sum(1 for x in o if x["yon"] == "SHORT"),
        "en_tutarli": round(max(x["tutarlilik"] for x in o), 4),
        "dayanak": [f"{'▲' if x['yon'] == 'LONG' else '▼'} %{x['tutarlilik'] * 100:.0f} (n={x['n']}, güvenli %{(x['agirlik'] + 0.5) * 100:.0f}) {x['aciklama']}"
                    for x in secili[:5]],
        "neden": "Long ve short oyları birbirine çok yakın (kararsız)." if sinyal == "BEKLE" else "",
    }


def hesapla(o: pd.DataFrame, KT: pd.DataFrame, kurallar: dict, yon_satirlari: list[dict], aralik: str) -> dict:
    dk = _dakika(aralik)
    maliyet = config.ISLEM_MALIYETI_YUZDE[config.ISLEM_TURU]
    n = len(o)
    simdi_fiyat = float(o["close"].iloc[-1])
    simdi = karar(oylar(n - 1, KT, kurallar, yon_satirlari, aralik, 0, "kisa"))
    gun_sonu = karar(oylar(n - 1, KT, kurallar, yon_satirlari, aralik, 0, "gun_sonu"))
    satirlar = []
    for dakika in config.GERIYE_DAKIKALAR:
        geri = dakika // dk
        if geri < 1 or dakika % dk or geri >= min(n, config.GERIYE_MAX_MUM + 1):
            continue
        i = n - 1 - geri
        k = karar(oylar(i, KT, kurallar, yon_satirlari, aralik, geri, "kisa"))
        giris = float(o["close"].iloc[i])
        hareket = (simdi_fiyat / giris - 1) * 100
        long_net, short_net = hareket - maliyet, -hareket - maliyet
        sonuc = {"LONG": long_net, "SHORT": short_net}.get(k["sinyal"])
        satirlar.append({
            "dakika": dakika, "zaman": o["time"].iloc[i].isoformat(), "giris": giris, "simdi": simdi_fiyat,
            "hareket_yuzde": round(hareket, 3), "long_net": round(long_net, 3), "short_net": round(short_net, 3),
            "sinyal": k["sinyal"], "guc": k["guc"], "long_oy": k["long_oy"], "short_oy": k["short_oy"],
            "dayanak": k.get("dayanak", [])[:3],
            "sinyale_gore_net": None if sonuc is None else round(sonuc, 3),
            "sinyal_dogru": None if sonuc is None else bool((hareket > 0) == (k["sinyal"] == "LONG") and hareket != 0),
        })
    return {"simdi": simdi, "gun_sonu": gun_sonu, "geriye": satirlar, "maliyet_yuzde": maliyet, "ufuklar": UFUKLAR}
