"""Telegram bildirimi: yeni güçlü sinyal çıktığında telefona mesaj.

Kurulum: python -m btc_tahmin telegram  (adım adım sorar, ayarlar/kullanici.json'a kaydeder)
"""
from __future__ import annotations

import html
import json
import time

import pandas as pd
import requests

from . import config

API = "https://api.telegram.org/bot{token}/{metod}"
TSI = pd.Timedelta(hours=config.GUN_SONU_UTC_OFFSET_SAAT)


def ayarli() -> bool:
    return bool(config.TELEGRAM.get("token") and config.TELEGRAM.get("chat_id"))


def gonder(metin: str, token: str | None = None, chat_id: str | None = None) -> None:
    token = token or config.TELEGRAM["token"]
    chat_id = chat_id or config.TELEGRAM["chat_id"]
    r = requests.post(API.format(token=token, metod="sendMessage"), timeout=config.HTTP_TIMEOUT,
                      json={"chat_id": chat_id, "text": metin[:4000], "parse_mode": "HTML",
                            "disable_web_page_preview": True})
    if r.status_code != 200:
        raise RuntimeError(f"Telegram {r.status_code}: {r.text[:200]}")


def _mesaj(s: dict) -> str:
    sembol = s["sembol"].replace("USDT", "")
    ok = "▲" if s["yon_yukari"] else "▼"
    zaman = (pd.Timestamp(s["sinyal_zamani"]) + TSI).strftime("%H:%M")
    etiket = "komisyon sonrası artı oranı" if s.get("tur") == "strateji" else "tutarlılık"
    return (f"{ok} <b>{html.escape(sembol)}</b> · %{float(s['tutarlilik']) * 100:.0f} {etiket}\n"
            f"{html.escape(s['aciklama'])}\n"
            f"Giriş {s['giris']:,} · sinyal mumu {zaman} TSİ · sonuç {(pd.Timestamp(s['cikis_zamani']) + TSI).strftime('%H:%M')}")


def yeni_sinyaller(yeni: list[dict]) -> dict:
    """Günlüğe yeni eklenen sinyallerden eşiği geçenleri tek mesajda gönderir."""
    if not ayarli():
        return {"durum": "kapalı", "gonderilen": 0}
    esik = float(config.TELEGRAM.get("min_tutarlilik", 0.8))
    strat = bool(config.TELEGRAM.get("stratejiler", True))   # strateji girişleri (tarama/uzun vade) eşikten bağımsız gider
    secilen = [s for s in yeni if float(s["tutarlilik"] or 0) >= esik or (strat and s.get("tur") == "strateji")]
    if not secilen:
        return {"durum": "ok", "gonderilen": 0}
    secilen.sort(key=lambda s: -float(s["tutarlilik"]))
    metin = "◆ <b>KRİPTO RİSK TERMİNALİ</b> · yeni sinyal\n\n" + "\n\n".join(_mesaj(s) for s in secilen[:8])
    if len(secilen) > 8:
        metin += f"\n\n… ve {len(secilen) - 8} sinyal daha (panoya bak)"
    metin += "\n\n<i>Geçmiş isabet garanti değildir. Karar senin.</i>"
    try:
        gonder(metin)
        return {"durum": "ok", "gonderilen": len(secilen)}
    except Exception as e:  # noqa: BLE001
        return {"durum": f"hata: {e}", "gonderilen": 0}


def kurulum():
    """Etkileşimli kurulum: bot anahtarını alır, chat id'yi bulur, test mesajı gönderir."""
    print("""
TELEGRAM BİLDİRİMİ KURULUMU
1) Telegram'da @BotFather'ı aç, /newbot yaz, bota bir isim ver.
2) BotFather sana uzun bir anahtar (token) verecek. Onu kopyala.
""")
    token = input("Bot anahtarını (token) yapıştır ve Enter'a bas: ").strip()
    if not token:
        print("İptal edildi.")
        return
    r = requests.get(API.format(token=token, metod="getMe"), timeout=config.HTTP_TIMEOUT)
    if r.status_code != 200:
        print("Anahtar geçersiz görünüyor:", r.text[:200])
        return
    bot = r.json()["result"]["username"]
    print(f"\n3) Şimdi Telegram'da @{bot} botunu aç ve ona herhangi bir mesaj yaz (ör. 'merhaba').")
    print("   Mesajı bekliyorum (en fazla 2 dakika) ...")
    chat_id = None
    for _ in range(60):
        u = requests.get(API.format(token=token, metod="getUpdates"), timeout=config.HTTP_TIMEOUT).json()
        for g in reversed(u.get("result", [])):
            m = g.get("message") or g.get("channel_post")
            if m:
                chat_id = str(m["chat"]["id"])
                break
        if chat_id:
            break
        time.sleep(2)
    if not chat_id:
        print("Mesaj gelmedi. Bota mesaj yazdığından emin olup komutu tekrar çalıştır.")
        return
    gonder("✅ Kripto Risk Terminali bağlandı. Güçlü sinyallerde buraya mesaj gelecek.", token, chat_id)
    dosya = config.AYAR_DIR / "kullanici.json"
    ayar = json.loads(dosya.read_text(encoding="utf-8")) if dosya.exists() else \
        json.loads((config.AYAR_DIR / "kullanici.ornek.json").read_text(encoding="utf-8"))
    ayar.setdefault("telegram", {}).update({"token": token, "chat_id": chat_id})
    dosya.write_text(json.dumps(ayar, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTamam! Telefonuna test mesajı gitti. Ayar kaydedildi: {dosya}")
    print(f"Varsayılan olarak tutarlılığı %{float(ayar['telegram'].get('min_tutarlilik', 0.8)) * 100:.0f} ve üzeri sinyaller gönderilir.")
    print("Canlı modu yeniden başlat (calistir.bat) ki ayar devreye girsin.")
