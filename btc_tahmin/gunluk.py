"""Canlı karne: panoda çıkan her sinyali kaydeder, süresi dolunca gerçek fiyatla sonuçlandırır.

Geçmiş testteki tutarlılık iyimser olabilir (kurallar o verilerle seçildi). Canlı karne ise
sistemin, sinyali verdiği anda bilmediği gelecekte ne yaptığını ölçer. En dürüst ölçüt budur.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from . import config
from .aciklama import hedef_metni, kosul_bilgisi

KOLONLAR = ["kayit_zamani", "sembol", "aralik", "tur", "kural_id", "hedef", "yon_yukari", "tutarlilik", "aciklama",
            "sinyal_zamani", "giris", "cikis_zamani", "durum", "cikis", "brut_yuzde", "net_yuzde"]


def _dosya():
    return config.VERI_DIR / "sinyal_gunlugu.csv"


def oku() -> pd.DataFrame:
    f = _dosya()
    if not f.exists():
        return pd.DataFrame(columns=KOLONLAR)
    df = pd.read_csv(f, dtype={"kural_id": str})
    for k in ("sinyal_zamani", "cikis_zamani"):
        df[k] = pd.to_datetime(df[k], utc=True, format="ISO8601")
    return df


def yaz(df: pd.DataFrame):
    config.VERI_DIR.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for k in ("sinyal_zamani", "cikis_zamani"):
        out[k] = out[k].map(lambda t: t.isoformat())
    out.to_csv(_dosya(), index=False)


def _cikis_zamani(hedef: str, t: pd.Timestamp, sure: pd.Timedelta) -> pd.Timestamp:
    """Sinyal mumunun açılış zamanı t; dönen değer, sonucu belirleyen son mumun açılış zamanı."""
    if hedef in ("sonraki_mum", "sonraki_yesil"):
        return t + sure
    if hedef in ("gun_sonu", "gun_sonu_ozet"):
        ofs = pd.Timedelta(hours=config.GUN_SONU_UTC_OFFSET_SAAT)
        gun_bitis = (t + sure + ofs).floor("D") + pd.Timedelta(days=1) - ofs
        if (t + sure + ofs).floor("D") == t + sure + ofs:   # mum tam gece yarısı kapanıyor
            gun_bitis -= pd.Timedelta(days=1)
        return gun_bitis - sure
    return t + sure * int(hedef.split("_")[1])


def sonuclandir(df: pd.DataFrame, mumlar: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Süresi dolan bekleyen sinyalleri gerçek mumlarla sonuçlandırır."""
    if df.empty:
        return df
    maliyet = config.ISLEM_MALIYETI_YUZDE[config.ISLEM_TURU]
    for i in df.index[df["durum"] == "bekliyor"]:
        r = df.loc[i]
        m = mumlar.get(r["sembol"])
        if m is None or m.empty or m["time"].iloc[-1] < r["cikis_zamani"]:
            continue
        mi = m.set_index("time")
        sure = pd.Timedelta(r["aralik"].replace("m", "min"))
        araliktaki = mi.loc[r["sinyal_zamani"] + sure: r["cikis_zamani"]]
        if araliktaki.empty or r["cikis_zamani"] not in mi.index:
            df.loc[i, "durum"] = "veri_yok"
            continue
        cikis = float(mi.loc[r["cikis_zamani"], "close"])
        yukari = bool(r["yon_yukari"])
        h = str(r["hedef"])
        if h in ("sonraki_mum", "sonraki_yesil"):
            mum = araliktaki.iloc[0]
            tuttu = (mum["close"] > mum["open"]) == yukari
        elif h.startswith("seri_"):
            yesil = araliktaki["close"] > araliktaki["open"]
            kirmizi = araliktaki["close"] < araliktaki["open"]
            tuttu = bool(yesil.all()) if yukari else bool(kirmizi.all())
        else:
            tuttu = (cikis > r["giris"]) == yukari
        brut = (cikis / r["giris"] - 1) * 100 * (1 if yukari else -1)
        df.loc[i, ["durum", "cikis", "brut_yuzde", "net_yuzde"]] = ["tuttu" if tuttu else "tutmadi", cikis,
                                                                     round(brut, 4), round(brut - maliyet, 4)]
    return df


def emekliler(df: pd.DataFrame) -> set[str]:
    """Canlıda yeterince sinyal verip isabeti düşük kalan kurallar."""
    if df.empty:
        return set()
    biten = df[df["durum"].isin(["tuttu", "tutmadi"]) & (df["tur"] == "kural")]
    g = biten.groupby("kural_id")["durum"].agg(lambda s: ((s == "tuttu").sum(), len(s)))
    return {k for k, (t, n) in g.items() if n >= config.KARNE_MIN_SINYAL and t / n < config.KARNE_EMEKLI_ORAN}


def kaydet(df: pd.DataFrame, rapor: dict) -> tuple[pd.DataFrame, list[dict]]:
    """Rapordaki aktif sinyalleri günlüğe ekler. Yeni eklenenleri döndürür (bildirim için)."""
    yeni = []
    simdi = datetime.now(timezone.utc).isoformat()
    for sembol, c in rapor["coinler"].items():
        aralik = c["aralik"]
        sure = pd.Timedelta(aralik.replace("m", "min"))
        t = pd.Timestamp(c["son_mum_zamani"])
        adaylar = [("kural", r) for r in c.get("aktif_tum", [])]
        oz = c["risk"]["ozet"]
        if oz.get("long_risk") is not None:
            adaylar.append(("gun_sonu_ozet", {"id": "OZET", "hedef": "gun_sonu_ozet",
                                              "yon": "YESIL" if oz["long_risk"] < 50 else "KIRMIZI",
                                              "tutarlilik": oz.get("en_tutarli", 0), "kosullar": []}))
        for tur, r in adaylar:
            acik = df[(df["sembol"] == sembol) & (df["kural_id"] == r["id"]) & (df["aralik"] == aralik)
                      & ((df["sinyal_zamani"] == t) | ((df["durum"] == "bekliyor") & (df["cikis_zamani"] > t)))]
            if not acik.empty:     # aynı sinyal zaten kayıtlı ya da önceki işlemi hâlâ açık
                continue
            yukari = r["yon"].startswith("YESIL")
            if r["hedef"].startswith("seri_"):
                yukari = r["hedef"].endswith("yesil")
            hedef_ad = "gun_sonu" if r["hedef"] == "gun_sonu_ozet" else r["hedef"]
            _, metin = hedef_metni(hedef_ad, 1 if r["yon"].startswith("YESIL") else 0, aralik)
            if tur == "gun_sonu_ozet":
                metin = f"Gün sonu özeti: {'LONG lehine' if yukari else 'SHORT lehine'} (long riski %{oz['long_risk']})"
            satir = {
                "kayit_zamani": simdi, "sembol": sembol, "aralik": aralik, "tur": tur, "kural_id": r["id"],
                "hedef": r["hedef"], "yon_yukari": int(yukari), "tutarlilik": r["tutarlilik"],
                "aciklama": metin + (" · " + " + ".join(kosul_bilgisi(k)["etiket"] for k in r["kosullar"]) if r["kosullar"] else ""),
                "sinyal_zamani": t, "giris": c["fiyat"], "cikis_zamani": _cikis_zamani(r["hedef"], t, sure),
                "durum": "bekliyor", "cikis": None, "brut_yuzde": None, "net_yuzde": None,
            }
            yeni.append(satir)
    if yeni:
        df = pd.concat([df, pd.DataFrame(yeni)], ignore_index=True) if not df.empty else pd.DataFrame(yeni)
    return df, yeni


def karne(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"toplam": 0}
    biten = df[df["durum"].isin(["tuttu", "tutmadi"])]

    def ozet(d):
        if d.empty:
            return {"sinyal": 0}
        net = d["net_yuzde"].astype(float)
        return {"sinyal": int(len(d)), "isabet": round(float((d["durum"] == "tuttu").mean()), 4),
                "beklenen_isabet": round(float(d["tutarlilik"].astype(float).mean()), 4),
                "ort_net": round(float(net.mean()), 4), "toplam_net": round(float(net.sum()), 3),
                "net_kazanma_orani": round(float((net > 0).mean()), 4)}

    son7 = biten[biten["sinyal_zamani"] >= pd.Timestamp.now(tz="UTC") - timedelta(days=7)]
    turler = {}
    for ad, d in biten.groupby(biten["hedef"].map(_tur_adi)):
        turler[ad] = ozet(d)
    son = df.sort_values("sinyal_zamani", ascending=False).head(30)
    return {
        "toplam": int(len(df)), "bekleyen": int((df["durum"] == "bekliyor").sum()),
        "ilk_sinyal": df["sinyal_zamani"].min().isoformat(),
        "genel": ozet(biten), "son_7_gun": ozet(son7), "turler": turler,
        "emekli": sorted(emekliler(df)),
        "son_sinyaller": [
            {"zaman": r["sinyal_zamani"].isoformat(), "sembol": r["sembol"], "aciklama": r["aciklama"], "kural_id": str(r["kural_id"]),
             "hedef": str(r["hedef"]), "yon_yukari": int(r["yon_yukari"]), "aralik": str(r["aralik"]), "giris": float(r["giris"]),
             "cikis_zamani": r["cikis_zamani"].isoformat(), "tur": str(r["tur"]),
             "tutarlilik": r["tutarlilik"], "durum": r["durum"], "net": None if pd.isna(r["net_yuzde"]) else float(r["net_yuzde"])}
            for _, r in son.iterrows()],
    }


def _tur_adi(hedef: str) -> str:
    if hedef in ("sonraki_mum", "sonraki_yesil"):
        return "Sonraki mum"
    if hedef == "gun_sonu":
        return "Gün sonu kuralı"
    if hedef == "gun_sonu_ozet":
        return "Gün sonu özeti"
    if hedef.startswith("ileri_"):
        return f"{hedef.split('_')[1]} mum sonra"
    return f"Sonraki {hedef.split('_')[1]} mum aynı renk"
