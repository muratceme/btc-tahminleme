"""Kuralların para olarak performansı: komisyon sonrası net kazanç, kâr faktörü, yaşlanma, kasa simülasyonu.

"Tutarlılık" bir kuralın yönü ne sıklıkla doğru bildiğini söyler. Ama doğru bilip çok az
kazandıran bir kural, komisyon düşülünce zarar ettirebilir. Bu modül bunu ölçer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, miner
from .aciklama import hedef_metni


def islem_maliyeti() -> float:
    """Giriş + çıkış toplam maliyeti (% olarak): komisyon + kayma."""
    return float(config.ISLEM_MALIYETI_YUZDE[config.ISLEM_TURU])


def _gun(o: pd.DataFrame) -> pd.Series:
    return (o["time"] + pd.Timedelta(hours=config.GUN_SONU_UTC_OFFSET_SAAT)).dt.floor("D")


def hedef_tanimi(hedef_adi: str, o: pd.DataFrame, hedef: pd.DataFrame):
    """(hedef serisi, bağımsızlık bloğu, gün serisi ya da None, çıkış indeksi dizisi)"""
    n_bar = len(o)
    idx = np.arange(n_bar)
    if hedef_adi in ("sonraki_mum", "sonraki_yesil"):
        return hedef["sonraki_yesil"], 1, None, np.minimum(idx + 1, n_bar - 1)
    if hedef_adi == "gun_sonu":
        g = _gun(o)
        son = pd.Series(idx).groupby(g.to_numpy()).transform("max").to_numpy()
        return hedef["gun_sonu_yukari"], 1, g, son
    n = int(hedef_adi.split("_")[1])
    return hedef[hedef_adi], n, None, np.minimum(idx + n, n_bar - 1)


def olusumlar(r: dict, o: pd.DataFrame, KT: pd.DataFrame, hedef: pd.DataFrame) -> dict | None:
    """Kuralın tüm geçmişteki bağımsız oluşumları ve her birinin işlem sonucu."""
    if not all(k in KT.columns for k in r["kosullar"]):
        return None
    y, blok, gun, cikis_idx = hedef_tanimi(r["hedef"], o, hedef)
    yon = 1 if r["yon"].startswith("YESIL") else 0
    yukselis, _ = hedef_metni(r["hedef"], yon)
    maske = KT[list(r["kosullar"])].all(axis=1).to_numpy()
    gecerli = y.notna().to_numpy()
    V = np.nonzero(gecerli)[0]
    s1 = int(len(V) * config.EGITIM_ORANI)
    s2 = int(len(V) * (config.EGITIM_ORANI + config.DOGRULAMA_ORANI))
    idx = miner.ayristir(np.nonzero(maske & gecerli)[0], None if gun is None else gun.to_numpy(), blok)
    c = o["close"].to_numpy()
    cik = cikis_idx[idx]
    brut = (c[cik] / c[idx] - 1) * 100 * (1 if yukselis else -1)   # işlem yönüne göre % getiri
    sira = np.searchsorted(V, idx)
    return {
        "idx": idx, "cikis_idx": cik, "bolum": np.where(sira < s1, 0, np.where(sira < s2, 1, 2)),
        "isabet": (y.to_numpy()[idx] == yon).astype(int), "brut": brut, "net": brut - islem_maliyeti(),
        "yukselis": yukselis, "blok": blok, "aktif": bool(maske[-1]),
    }


def istatistik(ol: dict, bolum: int | None = None) -> dict:
    m = np.ones(len(ol["idx"]), bool) if bolum is None else ol["bolum"] == bolum
    net = ol["net"][m]
    if len(net) == 0:
        return {"islem": 0}
    kazanc, kayip = net[net > 0], net[net <= 0]
    return {
        "islem": int(len(net)),
        "isabet": round(float(ol["isabet"][m].mean()), 4),
        "net_kazanma_orani": round(float((net > 0).mean()), 4),
        "ort_net": round(float(net.mean()), 4),
        "ort_kazanc": round(float(kazanc.mean()), 4) if len(kazanc) else 0.0,
        "ort_kayip": round(float(kayip.mean()), 4) if len(kayip) else 0.0,
        "kar_faktoru": round(float(kazanc.sum() / -kayip.sum()), 2) if len(kayip) and kayip.sum() < 0 else None,
        "toplam_net": round(float(net.sum()), 3),
    }


def kural_performansi(r: dict, o, KT, hedef) -> dict | None:
    ol = olusumlar(r, o, KT, hedef)
    if ol is None:
        return None
    son = ol["isabet"][-config.YASLANMA_PENCERE:]
    son_oran = float(son.mean()) if len(son) else None
    return {
        "maliyet_yuzde": islem_maliyeti(),
        "test": istatistik(ol, 2), "tum": istatistik(ol),
        "son_oran": round(son_oran, 4) if son_oran is not None else None, "son_n": int(len(son)),
        # Son oluşumlardaki isabet, test tutarlılığının belirgin altına düştüyse kural zayıflıyor olabilir
        "yaslaniyor": bool(son_oran is not None and len(son) >= 10 and son_oran < r["tutarlilik"] - config.YASLANMA_FARK),
    }


def performans_ekle_ve_ele(kurallar: list[dict], o, KT, hedef) -> list[dict]:
    """Her kurala performans ekler; komisyon sonrası test döneminde zarar ettirenleri eler."""
    kalan = []
    for r in kurallar:
        p = kural_performansi(r, o, KT, hedef)
        if p is None:
            continue
        r["performans"] = p
        if config.NET_ZARARLI_KURALLARI_ELE and p["test"].get("ort_net", 0) <= 0:
            continue
        kalan.append(r)
    return kalan


def kasa_simulasyonu(kurallar: list[dict], o, KT, hedef, baslangic: float | None = None) -> dict | None:
    """Test döneminde, listedeki kuralların sinyallerine (komisyonla) uyulsaydı kasa ne olurdu?

    Aynı anda tek pozisyon: açık işlem varken gelen sinyal atlanır. Kaldıraç yok, kasanın
    config.SIM_ISLEM_ORANI kadarı her işleme girer. Kurallar test dönemi de dahil seçildiği için
    sonuç iyimserdir; gerçek performans için canlı karneye bak."""
    baslangic = baslangic or config.SIM_BASLANGIC_KASA
    islemler = []
    for r in kurallar:
        ol = olusumlar(r, o, KT, hedef)
        if ol is None:
            continue
        m = ol["bolum"] == 2
        for i, j, net in zip(ol["idx"][m], ol["cikis_idx"][m], ol["net"][m]):
            islemler.append((int(i), int(j), float(net), r["id"]))
    if not islemler:
        return None
    islemler.sort()
    zaman = ((o["time"] - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)).to_numpy()
    kasa, tepe, max_dd, acik_bitis = baslangic, baslangic, 0.0, -1
    egri = [[int(zaman[islemler[0][0]]), round(kasa, 2)]]
    yapilan, kazanan = 0, 0
    for i, j, net, _ in islemler:
        if i <= acik_bitis:
            continue
        kasa *= 1 + config.SIM_ISLEM_ORANI * net / 100
        acik_bitis = j
        yapilan += 1
        kazanan += net > 0
        tepe = max(tepe, kasa)
        max_dd = min(max_dd, (kasa / tepe - 1) * 100)
        egri.append([int(zaman[j]), round(kasa, 2)])
    bas_i, son_i = islemler[0][0], max(j for _, j, _, _ in islemler)
    al_tut = (o["close"].iloc[son_i] / o["close"].iloc[bas_i] - 1) * 100
    if len(egri) > 400:   # pano için seyrelt
        adim = len(egri) / 400
        egri = [egri[int(k * adim)] for k in range(400)] + [egri[-1]]
    return {
        "baslangic_kasa": baslangic, "son_kasa": round(kasa, 2), "getiri_yuzde": round((kasa / baslangic - 1) * 100, 2),
        "islem": yapilan, "kazanma_orani": round(kazanan / yapilan, 4) if yapilan else None,
        "max_dusus_yuzde": round(max_dd, 2), "al_tut_yuzde": round(float(al_tut), 2),
        "bas_zaman": int(zaman[bas_i]), "son_zaman": int(zaman[son_i]), "maliyet_yuzde": islem_maliyeti(),
        "kural_sayisi": len({k for *_, k in islemler}), "egri": egri,
    }
