"""Kullanım:
    python -m btc_tahmin rapor            # veriyi güncelle, analiz et, rapor üret (15m)
    python -m btc_tahmin rapor --aralik 10m
    python -m btc_tahmin rapor --hizli    # 24 saatten yeni kural önbelleğini kullan (madenciliği atla)
    python -m btc_tahmin izle --dakika 15 # her N dakikada bir raporu yenile
    python -m btc_tahmin canli            # izle + http://localhost:8000 (telefondan da açılır)
    python -m btc_tahmin ozet             # son raporu (rapor.json) terminalde tekrar göster
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
    alt.add_parser("ozet")
    args = p.parse_args(argv)

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
        from . import sunucu
        try:
            sunucu.baslat(args.port)
        except OSError:
            print(f"HATA: {args.port} portu kullanımda. Başka port dene: --port 8080", file=sys.stderr)
            return
        adres = f"http://localhost:{args.port}"
        ip = sunucu.yerel_ip()
        print("=" * 60)
        print(f"  PANO BU BİLGİSAYARDA :  {adres}")
        if ip:
            print(f"  TELEFONDAN (aynı Wi-Fi): http://{ip}:{args.port}")
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
