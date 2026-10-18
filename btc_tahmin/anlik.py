"""Şimdi gir: tüm sayfalardaki kaynakların SON MUMDAKİ sinyallerini tek listede toplar.

Her satır: coin, kaynak (hangi sayfa), yön, çıkış (kaç mum sonra ≈ saat), grafik türü (mum süresi),
geçmiş performans özeti ve o kaynağın geçmişini gösteren sayfaya bağlantı. Açık pozisyonlar (sinyal önceki
mumlarda geldi, çıkış henüz gelmedi) ayrıca listelenir.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import config
from .aciklama import hedef_metni, kosul_bilgisi
from .sinyal import cikis_mumu

ARALIK_ADI = {"5m": "5 dakika", "10m": "10 dakika", "15m": "15 dakika", "30m": "30 dakika", "1h": "1 saat", "4h": "4 saat"}


def _dakika(aralik: str) -> int:
    return int(aralik[:-1]) * (60 if aralik.endswith("h") else 1)


def _tsi(iso: str, ek_dakika: int = 0) -> str:
    t = datetime.fromisoformat(iso) + timedelta(hours=config.GUN_SONU_UTC_OFFSET_SAAT, minutes=ek_dakika)
    return f"{t:%H:%M}"


def _cikis(zaman_iso: str, aralik: str, mum: int | None, en_gec: int | None = None) -> dict:
    """Sinyal mumunun açılışından itibaren: çıkış mumu kapanışı = (mum + 1) × süre sonra."""
    dk = _dakika(aralik)
    if mum is None:
        return {"mum": None, "metin": "çıkış kuralı koşula bağlı" + (f", en geç {en_gec} mum" if en_gec else ""),
                "saat": _tsi(zaman_iso, (en_gec + 1) * dk) if en_gec else None}
    return {"mum": mum, "metin": f"{mum} mum sonra" + (f" (en geç {en_gec})" if en_gec and en_gec != mum else ""),
            "saat": _tsi(zaman_iso, (mum + 1) * dk)}


def _strateji_satirlari(sembol: str, aralik: str, stratejiler: dict, kaynak: str, sayfa: str, ek_param: str = "") -> tuple[list, list]:
    sinyal, acik = [], []
    for sid, f in (stratejiler or {}).items():
        cz = f.get("cizelge") or []
        if not cz:
            continue
        son = cz[-1]
        st = f["istatistik"]["tum"]
        d = f.get("donemler")
        perf = (f"test {d['test']['toplam_net']:+.1f}% · KF {d['test']['kar_faktoru']}" if d else
                (f"tüm geçmiş {st['toplam_net']:+.1f}% · KF {st.get('kar_faktoru')} · {st['islem']} işlem" if st.get("islem") else "işlem yok"))
        link = f"{sayfa}?strat={sid}{ek_param}#{sembol}"
        ortak = {"sembol": sembol, "aralik": aralik, "grafik": ARALIK_ADI.get(aralik, aralik), "kaynak": kaynak, "ad": f["ad"],
                 "performans": perf, "link": link, "kurallar": f.get("kurallar", [])[:3]}
        if son["sinyal"] != "BEKLE":
            sinyal.append({**ortak, "yon": son["sinyal"], "zaman": son["zaman"], "fiyat": son["fiyat"],
                           "cikis": _cikis(son["zaman"], aralik, son.get("cikis_mum"), son.get("maks_mum"))})
        elif son.get("pozisyonda"):
            giris = next((r for r in reversed(cz) if r["sinyal"] != "BEKLE"), None)
            if giris and giris.get("cikis") and giris["cikis"]["durum"] == "acik":
                acik.append({**ortak, "yon": giris["sinyal"], "zaman": giris["zaman"], "fiyat": giris["fiyat"],
                             "simdi_net": giris["cikis"]["net"],
                             "cikis": _cikis(giris["zaman"], aralik, None, giris.get("maks_mum"))})
    return sinyal, acik


def topla(rapor: dict) -> dict:
    sinyaller, aciklar, egilimler = [], [], []
    for sembol, c in rapor["coinler"].items():
        aralik = c["aralik"]
        zaman = c["son_mum_zamani"]
        grafik = ARALIK_ADI.get(aralik, aralik)
        y = c.get("yon") or {}
        # 1) Yön oylaması (kısa vade / gün sonu) -> Sinyaller sayfası
        for anahtar, ad in (("simdi", "Yön oylaması · kısa vade"), ("gun_sonu", "Yön oylaması · gün sonu")):
            k = y.get(anahtar) or {}
            if k.get("sinyal") in ("LONG", "SHORT"):
                sinyaller.append({"sembol": sembol, "aralik": aralik, "grafik": grafik, "kaynak": "Sinyaller", "ad": ad,
                                  "yon": k["sinyal"], "zaman": zaman, "fiyat": c["fiyat"],
                                  "cikis": _cikis(zaman, aralik, k.get("cikis_mum"), k.get("en_gec_cikis_mum")),
                                  "performans": f"güç %{k.get('guc', 0) * 100:.0f} · {k.get('long_oy', 0)}L/{k.get('short_oy', 0)}S · en tutarlı kaynak %{(k.get('en_tutarli') or 0) * 100:.0f}",
                                  "link": f"sinyaller.html#{sembol}", "kurallar": k.get("dayanak", [])[:3]})
            elif (k.get("egilim") or {}).get("yon"):
                e = k["egilim"]
                egilimler.append({"sembol": sembol, "ad": ad, "yon": e["yon"], "olasilik": e["olasilik"], "model_dogrulugu": e["model_dogrulugu"],
                                  "link": f"sinyaller.html#{sembol}"})
        # 2) Şu an aktif kurallar -> Pano / grafik sayfası
        for r in c.get("aktif_tum", []):
            yon = 1 if r["yon"].startswith("YESIL") else 0
            yukselis, metin = hedef_metni(r["hedef"], yon, aralik)
            mum = cikis_mumu(r["hedef"], 1)
            if r["hedef"].startswith("gun"):
                kalan = c.get("gun_sonuna_kalan_saat") or 0
                mum = max(1, int(kalan * 60 / _dakika(aralik)))
            perf_r = next((x for liste in (c.get("kural_kutuphanesi") or {}).values() for x in liste if x["id"] == r["id"]), {})
            p = (perf_r.get("performans") or {}).get("test") or {}
            sinyaller.append({"sembol": sembol, "aralik": aralik, "grafik": grafik, "kaynak": "Pano · aktif kural", "ad": metin,
                              "yon": "LONG" if yukselis else "SHORT", "zaman": zaman, "fiyat": c["fiyat"],
                              "cikis": _cikis(zaman, aralik, mum),
                              "performans": f"tutarlılık %{r['tutarlilik'] * 100:.0f}" + (f" · test net {p['ort_net']:+.3f}%/işlem · {p['islem']} işlem" if p.get("islem") else ""),
                              "link": f"grafik.html?s={sembol}&k={r['id']}",
                              "kurallar": [kosul_bilgisi(k)["etiket"] for k in r["kosullar"]][:5]})
        # 3) Fable stratejileri, 4) tarama (15m), 5) uzun vade
        s_, a_ = _strateji_satirlari(sembol, aralik, c.get("fable"), "Fable sinyalleri", "fable.html"); sinyaller += s_; aciklar += a_
        s_, a_ = _strateji_satirlari(sembol, aralik, (c.get("tarama") or {}).get("sayfa"), "Strateji tarama", "tarama.html"); sinyaller += s_; aciklar += a_
        for tf, d in ((c.get("umut") or {}).get("dilimler") or {}).items():
            s_, a_ = _strateji_satirlari(sembol, tf, d.get("sayfa"), f"Uzun vade · {d['ad']}", "umut.html", f"&tf={tf}"); sinyaller += s_; aciklar += a_
        # 6) pozisyon hesaplayıcı (gün sonu)
        pz = c.get("pozisyon") or {}
        if pz.get("durum") == "var":
            sinyaller.append({"sembol": sembol, "aralik": aralik, "grafik": grafik, "kaynak": "Pano · pozisyon hesaplayıcı", "ad": "Gün sonu yön riski + stop/hedef",
                              "yon": pz["yon"], "zaman": zaman, "fiyat": c["fiyat"],
                              "cikis": {"mum": None, "metin": "gün sonu (TSİ 23:59) ya da stop/hedef", "saat": "23:59"},
                              "performans": f"stop {pz['stop_yuzde']}% · hedef {pz['hedef_yuzde']}% · {pz['pozisyon_usd']:,.0f}$ (x{pz['kaldirac']})",
                              "link": f"rapor.html#{sembol}", "kurallar": [pz.get("stop_dayanagi", "")]})
    sira = {"Uzun vade · 4 saat": 0, "Uzun vade · 1 saat": 1, "Strateji tarama": 2, "Fable sinyalleri": 3, "Sinyaller": 4, "Pano · pozisyon hesaplayıcı": 5, "Pano · aktif kural": 6}
    sinyaller.sort(key=lambda r: (r["sembol"], sira.get(r["kaynak"], 9)))
    return {"zaman": rapor["olusturma"], "sinyaller": sinyaller, "acik_pozisyonlar": aciklar, "egilimler": egilimler,
            "coin_son_mum": {s: {"zaman": c["son_mum_zamani"], "aralik": c["aralik"], "fiyat": c["fiyat"]} for s, c in rapor["coinler"].items()}}
