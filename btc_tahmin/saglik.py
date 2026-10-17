"""Veri sağlığı: raporda her metriğin geldi mi, boş mu (ve bu normal mi), hatalı mı olduğunu söyler.

Durumlar:
  "ok"     -> veri geldi
  "normal" -> boş ama beklenen bir durum (ör. şu an tutarlı sinyal yok)
  "hata"   -> gelmesi gerekirdi ama gelmedi; sebep ve çözüm yazılır
"""
from __future__ import annotations

import pandas as pd

from . import config


def _satir(grup, metrik, durum, aciklama=""):
    return {"grup": grup, "metrik": metrik, "durum": durum, "aciklama": aciklama}


def _sebep(hata: str) -> str:
    h = (hata or "").lower()
    if "429" in h or "hız sınırı" in h:
        return "Kaynak hız sınırına takıldı. Bir sonraki güncellemede genelde düzelir."
    if "403" in h or "451" in h or "engellendi" in h:
        return "Kaynak erişimi engelledi (bölge/ağ). VPN veya farklı ağ gerekebilir."
    if "timed out" in h or "timeout" in h or "connection" in h or "resolve" in h:
        return "İnternet bağlantısı veya kaynak sunucusu yanıt vermedi."
    return hata[:160] if hata else "Bilinmeyen hata."


def kontrol(rapor: dict) -> list[dict]:
    s: list[dict] = []
    b = rapor.get("baglam") or {}
    hatalar = b.get("hatalar") or {}

    # --- Mum verisi (her şeyin temeli)
    for sembol, c in (rapor.get("coinler") or {}).items():
        son = pd.Timestamp(c["son_mum_zamani"])
        sure = pd.Timedelta(c["aralik"].replace("m", "min"))
        gecikme = pd.Timestamp.now(tz="UTC") - (son + sure)
        if gecikme > sure * 3:
            s.append(_satir("Mum verisi", f"{sembol} mumları", "hata",
                            f"Son kapanan mum {gecikme.total_seconds() / 60:.0f} dk önce. Veri güncellenemiyor olabilir (Binance bağlantısı)."))
        else:
            s.append(_satir("Mum verisi", f"{sembol} mumları", "ok", f"{c['veri_mum_sayisi']:,} mum, son mum {c['son_mum_zamani'][11:16]} UTC"))

    # --- Dominans
    d = b.get("dominans")
    if not d:
        s.append(_satir("Dominans", "Anlık dominanslar (BTC/ETH/XRP/USDT/USDC)", "hata", _sebep(hatalar.get("dominans", ""))))
    else:
        s.append(_satir("Dominans", "Anlık dominanslar (BTC/ETH/XRP/USDT/USDC)", "ok",
                        f"BTC.D %{d['anlik']['btc']:.2f}, USDT.D %{d['anlik']['usdt']:.2f}"))
        dg = d.get("degisim") or {}
        eksik24 = [k for k in ("btc", "eth", "xrp", "usdt", "usdc") if "24s" not in dg.get(k, {})]
        eksik7 = [k for k in ("btc", "eth", "xrp", "usdt", "usdc") if "7g" not in dg.get(k, {})]
        if eksik24:
            s.append(_satir("Dominans", "24 saatlik dominans değişimi", "hata",
                            f"Eksik: {', '.join(x.upper() for x in eksik24)}. " + _sebep(d.get("trend_hatasi", ""))))
        else:
            s.append(_satir("Dominans", "24 saatlik dominans değişimi", "ok", d.get("degisim_kaynagi_24s", "")))
        if eksik7:
            s.append(_satir("Dominans", "7 günlük dominans değişimi", "hata",
                            f"Eksik: {', '.join(x.upper() for x in eksik7)}. " + _sebep(d.get("trend_hatasi", ""))))
        else:
            s.append(_satir("Dominans", "7 günlük dominans değişimi", "ok", "5 coin payından tahmini"))

    # --- Duygu
    fg = b.get("korku_acgozluluk")
    s.append(_satir("Duygu", "Korku / Açgözlülük endeksi", "ok" if fg else "hata",
                    f"{fg['deger']} ({fg['sinif']})" if fg else _sebep(hatalar.get("korku_acgozluluk", ""))))

    # --- Vadeli
    alanlar = {"funding_yuzde": "Funding", "oi_degisim_24s_yuzde": "Açık pozisyon (OI)",
               "long_short_orani": "Long/Short oranı", "taker_alis_satis": "Taker alış/satış"}
    for sembol in config.SEMBOLLER:
        v = (b.get("vadeli") or {}).get(sembol)
        if not v:
            s.append(_satir("Vadeli piyasa", f"{sembol} vadeli verileri", "hata", _sebep(hatalar.get(f"vadeli_{sembol}", ""))))
            continue
        eksik = [ad for k, ad in alanlar.items() if v.get(k) is None]
        if eksik:
            ilk = next(iter((v.get("hatalar") or {}).values()), "")
            s.append(_satir("Vadeli piyasa", f"{sembol} vadeli verileri", "hata", f"Eksik: {', '.join(eksik)}. " + _sebep(ilk)))
        else:
            s.append(_satir("Vadeli piyasa", f"{sembol} vadeli verileri", "ok",
                            f"funding %{v['funding_yuzde']}, OI {v['oi_degisim_24s_yuzde']:+}%"))

    # --- Haberler
    hb = b.get("haberler")
    if not hb:
        s.append(_satir("Haberler", "Haber akışı", "hata", _sebep(hatalar.get("haberler", ""))))
    else:
        kd = hb.get("kaynak_durumu") or {}
        bozuk = [k for k, v in kd.items() if str(v).startswith("HATA")]
        if hb.get("adet", 0) == 0:
            s.append(_satir("Haberler", "Haber akışı", "hata",
                            "Hiçbir kaynaktan başlık gelmedi. " + ("; ".join(f"{k}: {kd[k]}" for k in bozuk) or "")))
        else:
            s.append(_satir("Haberler", "Haber akışı", "ok",
                            f"{hb['adet']} başlık · {len(kd) - len(bozuk)}/{len(kd)} kaynak çalışıyor"
                            + (f" (çalışmayan: {', '.join(bozuk)})" if bozuk else "")))

    # --- Makro, takvim, ETF, opsiyon
    mk = b.get("makro")
    if not mk:
        s.append(_satir("Makro ve kurumsal", "Nasdaq / S&P / DXY / altın / 10Y faiz", "hata", _sebep(hatalar.get("makro", ""))))
    else:
        eksik = list((mk.get("hatalar") or {}).keys())
        s.append(_satir("Makro ve kurumsal", "Nasdaq / S&P / DXY / altın / 10Y faiz", "hata" if eksik else "ok",
                        (f"Eksik: {', '.join(eksik)}. " + _sebep(next(iter(mk['hatalar'].values())))) if eksik
                        else f"{len(mk.get('veriler', {}))} gösterge · BTC korelasyonu {'hesaplandı' if mk.get('btc_korelasyon') else 'yok'}"))
    to = b.get("takvim_oto")
    s.append(_satir("Makro ve kurumsal", "Otomatik ekonomik takvim", "ok" if to else ("normal" if to == [] else "hata"),
                    f"{len(to)} ABD olayı (bu ve gelecek hafta)" if to else
                    ("Bu hafta yüksek/orta etkili ABD olayı yok." if to == [] else
                     _sebep(hatalar.get("takvim_oto", "")) + " Elle girilen takvim (ayarlar/olaylar.json) yine çalışır.")))
    etf = b.get("etf")
    s.append(_satir("Makro ve kurumsal", "ETF akışları (deneysel)", "ok" if etf else "hata",
                    ", ".join(f"{k} son gün {v['son']['net_milyon_usd']:+,.0f} M$" for k, v in etf["veriler"].items()) if etf else
                    _sebep(hatalar.get("etf", "")) + " Farside sitesi bot koruması kullanıyor olabilir; bu veri isteğe bağlıdır."))
    for para in ("BTC", "ETH"):
        op = (b.get("opsiyon") or {}).get(para)
        s.append(_satir("Makro ve kurumsal", f"{para} opsiyon (put/call, max pain)", "ok" if op else "hata",
                        f"put/call {op['put_call_orani']}, max pain {op['max_pain']:,.0f}" if op else _sebep(hatalar.get(f"opsiyon_{para}", ""))))

    # --- Canlı karne ve bildirim
    k = rapor.get("karne") or {}
    s.append(_satir("Canlı karne", "Sinyal günlüğü", "ok" if k.get("toplam") else "normal",
                    f"{k['toplam']} sinyal kayıtlı, {k.get('bekleyen', 0)} sonuç bekliyor" if k.get("toplam") else
                    "Henüz kayıt yok. Canlı modda çalıştıkça dolar."))
    bd = rapor.get("bildirim") or {}
    s.append(_satir("Canlı karne", "Telegram bildirimi", "hata" if str(bd.get("durum", "")).startswith("hata") else
                    ("ok" if bd.get("durum") == "ok" else "normal"),
                    bd.get("durum", "") if str(bd.get("durum", "")).startswith("hata") else
                    (f"açık · bu turda {bd.get('gonderilen', 0)} mesaj" if bd.get("durum") == "ok" else
                     "Kapalı. Kurmak için: python -m btc_tahmin telegram")))

    # --- Olaylar ve puan
    gp = rapor.get("genel_puan") or {}
    s.append(_satir("Olaylar", "Genel piyasa puanı", "ok", f"%{gp.get('genel_puan')} ({len(gp.get('kalemler', []))} kırım kalemi)"))
    s.append(_satir("Olaylar", "Yaklaşan olaylar (48 saat)", "ok" if gp.get("yaklasan_olaylar") else "normal",
                    f"{len(gp.get('yaklasan_olaylar', []))} olay" if gp.get("yaklasan_olaylar") else
                    "48 saat içinde takvimde olay yok. Yeni olayları ayarlar/olaylar.json'a ekleyebilirsin."))

    # --- Coin bazında analiz çıktıları
    for sembol, c in (rapor.get("coinler") or {}).items():
        g = f"{sembol.replace('USDT', '')} analizi"
        oz = c["risk"]["ozet"]
        s.append(_satir(g, "Yapay zekâ ham tahmini", "ok" if oz.get("ham_model_long_risk") is not None else "hata",
                        (f"long riski %{oz['ham_model_long_risk']}, genel isabeti %{round((oz.get('ham_model_dogrulugu') or 0) * 100)} "
                         "(eşiksiz, karar için değil)") if oz.get("ham_model_long_risk") is not None
                        else "scikit-learn kurulu değil: pip install -r requirements.txt"))
        if oz.get("long_risk") is not None:
            s.append(_satir(g, "Gün sonu long riski", "ok", f"%{oz['long_risk']} ({oz['dayanak_sayisi']} tutarlı sinyal)"))
        else:
            kalan = c.get("gun_sonuna_kalan_saat")
            neden = (f"Gün sonuna {kalan * 60:.0f} dk kaldı; gün sonu tahmini yapılmaz." if kalan is not None and kalan < config.GUN_SONU_MIN_KALAN_SAAT
                     else "Hiçbir model/kombinasyon şu an %70+ güvende değil. Sistem emin olmadığında susar.")
            s.append(_satir(g, "Gün sonu long riski", "normal", neden))
            s.append(_satir(g, "Kırım dahil long riski", "normal", "Long riski olmadığı için hesaplanmaz."))
        md = oz.get("max_dusus")
        s.append(_satir(g, "Max düşüş sınırları", "ok" if md else "hata",
                        ", ".join(f"{k}: {v}%" for k, v in md.items()) if md else "Yeterli geçmiş veri yok (en az birkaç hafta gerekir)."))
        ks = c.get("kural_sayisi", {})
        s.append(_satir(g, "Kural kütüphanesi (sonraki mum)", "ok" if ks.get("sonraki_mum") else "normal",
                        f"{ks.get('sonraki_mum', 0)} kural" if ks.get("sonraki_mum") else "Test döneminde %70+ tutan kural bulunamadı."))
        s.append(_satir(g, "Kural kütüphanesi (gün sonu)", "ok" if ks.get("gun_sonu") else "normal",
                        f"{ks.get('gun_sonu', 0)} kural" if ks.get("gun_sonu") else
                        "Gün sonu yönü için %70+ tutan kombinasyon yok. Bu sık görülür: gün sonu yönü zor tahmin edilir."))
        s.append(_satir(g, "Derin tarama kütüphanesi (%85+)", "ok" if ks.get("derin") else "normal",
                        f"{ks.get('derin', 0)} kural" if ks.get("derin") else "%85+ tutan 3-7 koşullu kombinasyon bulunamadı."))
        sim = (c.get("simulasyon") or {}).get("derin")
        s.append(_satir(g, "Kasa simülasyonu (derin kurallar)", "ok" if sim else "normal",
                        f"{sim['baslangic_kasa']:,.0f}$ → {sim['son_kasa']:,.0f}$ ({sim['islem']} işlem)" if sim else
                        "Test döneminde derin kural işlemi yok."))
        pz = c.get("pozisyon") or {}
        s.append(_satir(g, "Pozisyon hesaplayıcı", "ok" if pz.get("durum") == "var" else "normal",
                        f"{pz['yon']} · {pz['pozisyon_usd']:,.0f}$ · stop {pz['stop_yuzde']}%" if pz.get("durum") == "var"
                        else pz.get("neden", "")))
        sm = ((c.get("yon") or {}).get("simdi") or {})
        s.append(_satir(g, "Yön sinyali (LONG/SHORT)", "ok" if sm.get("sinyal") in ("LONG", "SHORT") else "normal",
                        f"{sm.get('sinyal')} · güç %{sm.get('guc', 0) * 100:.0f}" if sm.get("sinyal") in ("LONG", "SHORT")
                        else (sm.get("neden") or "Aktif tutarlı kaynak yok.")))
        aktif = len(c["sonraki_mum"]["aktif_kurallar"])
        s.append(_satir(g, "Şu an aktif sonraki mum kuralı", "ok" if aktif else "normal",
                        f"{aktif} kural" if aktif else "Son mumda tutarlı kombinasyon oluşmadı (sık olur)."))
        da = len((c.get("derin") or {}).get("aktif", []))
        s.append(_satir(g, "Şu an aktif derin kural", "ok" if da else "normal",
                        f"{da} kural" if da else "Derin kurallar nadir oluşur; şu an yok."))
    return s


def ozet(satirlar: list[dict]) -> dict:
    return {d: sum(1 for x in satirlar if x["durum"] == d) for d in ("ok", "normal", "hata")}

