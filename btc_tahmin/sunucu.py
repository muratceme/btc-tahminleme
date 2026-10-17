"""Yerel web sunucusu: panoyu http://localhost:8000 adresinde yayınlar.

Aynı Wi-Fi'daki telefon da http://<bilgisayar-ip>:8000 adresinden açabilir.
"""
from __future__ import annotations

import base64
import hmac
import json
import os
import secrets
import re
import shutil
import socket
import subprocess
import threading
import time
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


SIFRE: str | None = None     # ayarlanırsa pano kullanıcı adı "kripto" + bu şifreyle korunur
KULLANICI = "kripto"
_KAPAT_ANAHTARI = secrets.token_urlsafe(16)   # yeni açılan programın eskisini kapatabilmesi için


def _kilit_dosyasi():
    return config.VERI_DIR / "sunucu.json"


class _Isleyici(SimpleHTTPRequestHandler):
    def _yetkili(self) -> bool:
        if not SIFRE:
            return True
        b = self.headers.get("Authorization", "")
        if not b.startswith("Basic "):
            return False
        try:
            k, _, p = base64.b64decode(b[6:]).decode("utf-8").partition(":")
        except ValueError:
            return False
        return hmac.compare_digest(k, KULLANICI) and hmac.compare_digest(p, SIFRE)

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/__kapat") and self.client_address[0] in ("127.0.0.1", "::1"):
            # Yeni açılan program eskisini kapatıyor (anahtar yalnızca bu bilgisayardaki dosyada)
            if self.path == f"/__kapat?anahtar={_KAPAT_ANAHTARI}":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"kapaniyor")
                print("\nYeni bir pencerede program yeniden başlatıldı; bu pencere kapanıyor.", flush=True)
                threading.Timer(0.5, lambda: os._exit(0)).start()
            else:
                self.send_response(403)
                self.end_headers()
            return
        if not self._yetkili():
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Kripto Risk Terminali"')
            self.end_headers()
            return
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


class _Sunucu(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # Tarayıcı sayfa yenilenirken bağlantıyı erken kapatabilir; bu bir hata değil
        import sys
        if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
            return
        super().handle_error(request, client_address)


def _eskiyi_kapat(port: int) -> bool:
    """Aynı portta çalışan eski kopyamızı kapatmayı dener."""
    import urllib.request
    try:
        bilgi = json.loads(_kilit_dosyasi().read_text(encoding="utf-8"))
        if int(bilgi.get("port", -1)) != port:
            return False
        urllib.request.urlopen(f"http://127.0.0.1:{port}/__kapat?anahtar={bilgi['anahtar']}", timeout=3).read()
        return True
    except Exception:  # noqa: BLE001
        return False


def baslat(port: int = 8000) -> ThreadingHTTPServer:
    """Sunucuyu başlatır. Port doluysa ve doluluk eski bir kopyamızdan geliyorsa onu kapatıp yerine geçer."""
    config.CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    try:
        sunucu = _Sunucu(("0.0.0.0", port), partial(_Isleyici, directory=str(config.CIKTI_DIR)))
    except OSError:
        if not _eskiyi_kapat(port):
            raise
        print("Eski açık kopya kapatıldı, yerine geçiliyor ...", flush=True)
        for _ in range(20):
            time.sleep(0.5)
            try:
                sunucu = _Sunucu(("0.0.0.0", port), partial(_Isleyici, directory=str(config.CIKTI_DIR)))
                break
            except OSError:
                continue
        else:
            raise
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    config.VERI_DIR.mkdir(parents=True, exist_ok=True)
    _kilit_dosyasi().write_text(json.dumps({"port": port, "anahtar": _KAPAT_ANAHTARI, "pid": os.getpid(),
                                            "surum": config.SURUM}), encoding="utf-8")
    return sunucu


def tunel(port: int, bekle_sn: int = 40) -> tuple[str | None, str]:
    """cloudflared ile ücretsiz geçici bir https adresi açar (bilgisayar açık kaldıkça her yerden erişim).

    Dönen: (adres ya da None, açıklama)."""
    exe = shutil.which("cloudflared")
    if not exe:
        return None, ("cloudflared kurulu değil. Windows: 'winget install --id Cloudflare.cloudflared' · "
                      "macOS: 'brew install cloudflared' · sonra komutu tekrar çalıştır.")
    p = subprocess.Popen([exe, "tunnel", "--no-autoupdate", "--url", f"http://localhost:{port}"],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    bulunan: list[str] = []

    def oku():
        for satir in p.stdout:   # type: ignore[union-attr]
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", satir)
            if m and not bulunan:
                bulunan.append(m.group(0))
    threading.Thread(target=oku, daemon=True).start()
    for _ in range(bekle_sn * 2):
        if bulunan or p.poll() is not None:
            break
        time.sleep(0.5)
    if bulunan:
        return bulunan[0], "Tünel açık. Bu pencere açık kaldıkça adres çalışır; her açılışta adres değişir."
    return None, "Tünel açılamadı (cloudflared çıktısında adres bulunamadı)."
