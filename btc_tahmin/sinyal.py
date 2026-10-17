"""Yön sinyali (LONG / SHORT / BEKLE) ve geriye dönük kontrol.

Yön sinyali: o mumda aktif olan tüm tutarlı kaynakların oylaması. Her kural ve model,
tutarlılığı ölçüsünde oy verir (ağırlık = tutarlılık - 0,5; %85'lik bir kural %70'likten daha ağır basar).

Geriye dönük kontrol: 15/30/45/60 dakika önceki mumda sistem hangi sinyali veriyordu ve o an
long ya da short açılsaydı şu anki fiyatla (komisyon dahil) sonuç ne olurdu?
"""
from __future__ import annotations

import pandas as pd

from . import config
from .aciklama import hedef_metni, kosul_bilgisi

KARARSIZLIK_ESIGI = 0.2   # iki taraf oyları birbirine bu kadar yakınsa BEKLE


def _dakika(aralik: str) -> int:
    return int(aralik[:-1]) * (60 if aralik.endswith("h") else 1)


def oylar(i: int, KT: pd.DataFrame, kurallar: dict[str, list[dict]], yon_satirlari: list[dict],
          aralik: str, geri: int) -> list[dict]:
    """i. mumda aktif olan kaynakların oyları. geri: son mumdan kaç mum geride (ML geçmiş tahmini için)."""
    satir = KT.iloc[i]
    out = []
    for liste in kurallar.values():
        for r in liste:
            if r.get("emekli") or not all(satir.get(k, False) for k in r["kosullar"]):
                continue
            yon = 1 if r["yon"].startswith("YESIL") else 0
            yukselis, metin = hedef_metni(r["hedef"], yon, aralik)
            out.append({"yon": "LONG" if yukselis else "SHORT", "agirlik": max(0.0, r["tutarlilik"] - 0.5),
                        "tutarlilik": r["tutarlilik"], "kaynak": "kural",
                        "aciklama": metin + " · " + " + ".join(kosul_bilgisi(k)["etiket"] for k in r["kosullar"])})
    # Yapay zekâ modelleri: o mumdaki tahmin, bir tutarlılık seviyesinin güven eşiğini geçiyorsa oy verir
    ham = {(r["model"]): r for r in yon_satirlari if r["tur"] == "HAM"}
    en_iyi: dict[str, dict] = {}
    for r in yon_satirlari:
        if r["tur"] != "YON" or r["model"] not in ham:
            continue
        pg = ham[r["model"]].get("p_gecmis") or []
        if geri >= len(pg):
            continue
        p = pg[-1 - geri]
        if abs(p - 0.5) >= r["guven_marji"] and (r["model"] not in en_iyi or r["tutarlilik"] > en_iyi[r["model"]]["tutarlilik"]):
            yukari = p > 0.5
            ufuk = "gün sonu" if r["hedef"].startswith("gun") else f"sonraki {aralik} mum"
            en_iyi[r["model"]] = {"yon": "LONG" if yukari else "SHORT", "agirlik": r["tutarlilik"] - 0.5,
                                  "tutarlilik": r["tutarlilik"], "kaynak": "model",
                                  "aciklama": f"{r['model'].split(' (')[0]} modeli · {ufuk} {'YUKARI' if yukari else 'AŞAĞI'} "
                                              f"(olasılık %{max(p, 1 - p) * 100:.0f})"}
    out.extend(en_iyi.values())
    return out


def karar(o: list[dict]) -> dict:
    lw = sum(x["agirlik"] for x in o if x["yon"] == "LONG")
    sw = sum(x["agirlik"] for x in o if x["yon"] == "SHORT")
    toplam = lw + sw
    if not o or toplam <= 0:
        return {"sinyal": "BEKLE", "guc": 0.0, "long_oy": 0, "short_oy": 0, "neden": "Aktif tutarlı kural/model yok."}
    guc = abs(lw - sw) / toplam
    sinyal = "BEKLE" if guc < KARARSIZLIK_ESIGI else ("LONG" if lw > sw else "SHORT")
    secili = sorted(o, key=lambda x: -x["tutarlilik"])
    return {
        "sinyal": sinyal, "guc": round(guc, 3),
        "long_oy": sum(1 for x in o if x["yon"] == "LONG"), "short_oy": sum(1 for x in o if x["yon"] == "SHORT"),
        "en_tutarli": round(secili[0]["tutarlilik"], 4),
        "dayanak": [f"{'▲' if x['yon'] == 'LONG' else '▼'} %{x['tutarlilik'] * 100:.0f} {x['aciklama']}" for x in secili[:5]],
        "neden": "Long ve short oyları birbirine çok yakın (kararsız)." if sinyal == "BEKLE" else "",
    }


def hesapla(o: pd.DataFrame, KT: pd.DataFrame, kurallar: dict, yon_satirlari: list[dict], aralik: str) -> dict:
    dk = _dakika(aralik)
    maliyet = config.ISLEM_MALIYETI_YUZDE[config.ISLEM_TURU]
    n = len(o)
    simdi_fiyat = float(o["close"].iloc[-1])
    simdi = karar(oylar(n - 1, KT, kurallar, yon_satirlari, aralik, 0))
    satirlar = []
    for dakika in config.GERIYE_DAKIKALAR:
        geri = dakika // dk
        if geri < 1 or dakika % dk or geri >= min(n, config.GERIYE_MAX_MUM + 1):
            continue
        i = n - 1 - geri
        k = karar(oylar(i, KT, kurallar, yon_satirlari, aralik, geri))
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
    return {"simdi": simdi, "geriye": satirlar, "maliyet_yuzde": maliyet}
