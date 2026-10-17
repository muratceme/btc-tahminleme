"""Kullanım:
    python -m btc_tahmin rapor            # veriyi güncelle, analiz et, rapor üret (15m)
    python -m btc_tahmin rapor --aralik 10m
    python -m btc_tahmin rapor --hizli    # 24 saatten yeni kural önbelleğini kullan (madenciliği atla)
    python -m btc_tahmin izle --dakika 15 # her N dakikada bir raporu yenile
    python -m btc_tahmin canli            # izle + http://localhost:8000 (telefondan da açılır)
    python -m btc_tahmin ozet             # son raporu (rapor.json) terminalde tekrar göster
    python -m btc_tahmin kontrol          # her metrik geldi mi? (son rapora göre)
    python -m btc_tahmin telegram         # telefona bildirim kurulumu (adım adım)
    python -m btc_tahmin karne            # canlı karne: sistemin gerçek sinyal performansı
    python -m btc_tahmin kontrol --kaynaklar  # dış kaynakları (dominans, F&G, vadeli, haber) şimdi tekrar dene
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import webbrowser
from datetime import datetime

from . import config, pipeline, report


def _rapor(args, yenile_sn=None):
    t0 = time.time()
    print(f"[{datetime.now():%H:%M:%S}] Veri güncelleniyor ve analiz ediliyor ({args.aralik}) ...", flush=True)
    semboller = [s.upper() if s.upper().endswith("USDT") else s.upper() + "USDT" for s in args.coin] if args.coin else None
    r = pipeline.calistir(aralik=args.aralik, semboller=semboller, hizli=args.hizli)
    yol = report.kaydet(r, yenile_sn)
    print(report.terminal(r))
    print(f"(süre {time.time() - t0:.0f} sn)")
    return yol


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if os.name == "nt":
        os.system("")  # Windows konsolunda renk kodlarını etkinleştir
    p = argparse.ArgumentParser(prog="btc_tahmin", description="BTC/ETH/XRP gün sonu risk raporu")
    alt = p.add_subparsers(dest="komut", required=True)
    for ad in ("rapor", "izle", "canli"):
        a = alt.add_parser(ad)
        a.add_argument("--aralik", default=config.VARSAYILAN_ARALIK, choices=config.ARALIKLAR)
        a.add_argument("--hizli", action="store_true", help="kural önbelleğini kullan")
        a.add_argument("--coin", nargs="*", help="ör. --coin BTC ETH (varsayılan: hepsi)")
        a.add_argument("--ac", action="store_true", help="raporu tarayıcıda aç")
        if ad in ("izle", "canli"):
            a.add_argument("--dakika", type=int, default=15)
        if ad == "canli":
            a.add_argument("--port", type=int, default=8000)
            a.add_argument("--sifre", help="panoyu şifrele (kullanıcı adı: kripto)")
            a.add_argument("--tunel", action="store_true",
                           help="cloudflared ile her yerden erişilebilen https adresi aç (şifre otomatik konur)")
    alt.add_parser("ozet")
    alt.add_parser("telegram")
    alt.add_parser("karne")
    k = alt.add_parser("kontrol")
    k.add_argument("--kaynaklar", action="store_true", help="dış veri kaynaklarını şimdi tekrar dene")
    args = p.parse_args(argv)
    print(f"Kripto Risk Terminali · sürüm {config.SURUM}", flush=True)

    if args.komut == "telegram":
        from . import bildirim
        bildirim.kurulum()
        return
    if args.komut == "karne":
        from . import gunluk
        print(report.karne_metni(gunluk.karne(gunluk.oku())))
        return
    if args.komut == "kontrol":
        from . import market, saglik
        try:
            r = report.json_oku()
        except FileNotFoundError:
            print("Henüz rapor yok. Önce: python -m btc_tahmin rapor")
            return
        if args.kaynaklar:
            print("Dış kaynaklar tekrar deneniyor (dominans, korku/açgözlülük, vadeli, haberler) ...", flush=True)
            r["baglam"] = market.baglam_topla(config.SEMBOLLER)
        print(report.saglik_tablosu(saglik.kontrol(r)))
        return
    if args.komut == "ozet":
        print(report.terminal(report.json_oku()))
        return
    if args.komut == "rapor":
        yol = _rapor(args)
        if args.ac:
            webbrowser.open(yol.as_uri())
        return
    adres = None
    if args.komut == "canli":
        import secrets

        from . import sunucu
        if args.tunel and not args.sifre:
            args.sifre = secrets.token_urlsafe(6)
        sunucu.SIFRE = args.sifre
        sunucu.HAZIR = False
        try:
            sunucu.baslat(args.port)
        except OSError:
            print(f"""
HATA: {args.port} portu başka bir program tarafından kullanılıyor.
Büyük ihtimalle programın ESKİ bir kopyası hâlâ açık ve eski sayfayı göstermeye devam ediyor.
Çözüm: Açık olan TÜM siyah pencereleri kapat (ya da Görev Yöneticisi'nde 'Python' işlemlerini sonlandır),
sonra calistir.bat'ı tekrar çalıştır. Bundan sonraki sürümler eski kopyayı kendisi kapatır.
""", file=sys.stderr)
            return
        adres = f"http://localhost:{args.port}"
        ip = sunucu.yerel_ip()
        print("=" * 60)
        print(f"  PANO BU BİLGİSAYARDA :  {adres}")
        if ip:
            print(f"  TELEFONDAN (aynı Wi-Fi): http://{ip}:{args.port}")
        if args.tunel:
            dis, mesaj = sunucu.tunel(args.port)
            print(f"  HER YERDEN (mobil veri dahil): {dis}" if dis else f"  TÜNEL: {mesaj}")
            if dis:
                print(f"  {mesaj}")
        if args.sifre:
            print(f"  GİRİŞ: kullanıcı adı 'kripto' · şifre '{args.sifre}'")
        print("  Bu pencereyi KAPATMA. Kapatırsan güncelleme durur.")
        print("=" * 60, flush=True)
        if args.ac:
            webbrowser.open(adres)
    # izle: ilk tur tam madencilik, sonrakiler önbellekle (günde bir kez yeniden madencilik)
    ilk = True
    while True:
        try:
            yol = _rapor(args, yenile_sn=60)
            if adres:
                from . import sunucu
                sunucu.HAZIR = True
                print(f"Pano güncellendi: {adres}")
            elif ilk and args.ac:
                webbrowser.open(yol.as_uri())
            ilk = False
            args.hizli = True
        except Exception as e:  # noqa: BLE001
            print(f"HATA: {e} — bir sonraki turda tekrar denenecek", file=sys.stderr)
        # bir sonraki mum kapanışından 20 sn sonra çalış
        simdi = time.time()
        periyot = args.dakika * 60
        bekle = periyot - (simdi % periyot) + 20
        print(f"Sonraki güncelleme {bekle/60:.1f} dk sonra. Durdurmak için Ctrl+C.")
        time.sleep(bekle)


if __name__ == "__main__":
    main()
