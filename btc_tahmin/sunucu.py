"""Yerel web sunucusu: panoyu http://localhost:8000 adresinde yayınlar.

Aynı Wi-Fi'daki telefon da http://<bilgisayar-ip>:8000 adresinden açabilir.
"""
from __future__ import annotations

import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from . import config

HAZIRLANIYOR = """<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="15">
<title>Hazırlanıyor</title><style>body{margin:0;background:#07090d;color:#d7dde6;font:16px ui-monospace,monospace;
display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;padding:16px}
b{color:#fbbf24}</style></head><body><div><b>◆ KRİPTO RİSK TERMİNALİ</b><p>İlk analiz hazırlanıyor...</p>
<p style="color:#7c8a9c;font-size:13px">İlk çalıştırmada veri indirildiği için birkaç dakika sürebilir.<br>
Bu sayfa 15 saniyede bir kendini yeniler.</p></div></body></html>"""


class _Isleyici(SimpleHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path in ("/", "/index.html"):
            self.path = "/rapor.html"
        if self.path.split("?")[0] == "/rapor.html" and not (config.CIKTI_DIR / "rapor.html").exists():
            veri = HAZIRLANIYOR.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(veri)))
            self.end_headers()
            self.wfile.write(veri)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):  # terminali erişim kayıtlarıyla doldurma
        pass


def yerel_ip() -> str | None:
    """Bilgisayarın ev ağındaki IP adresi (telefondan bağlanmak için)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # paket gönderilmez, sadece arayüz seçilir
            return s.getsockname()[0]
    except OSError:
        return None


def baslat(port: int = 8000) -> ThreadingHTTPServer:
    config.CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    sunucu = ThreadingHTTPServer(("0.0.0.0", port), partial(_Isleyici, directory=str(config.CIKTI_DIR)))
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    return sunucu
