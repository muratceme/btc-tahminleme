"""Piyasa bağlamı: dominanslar, korku/açgözlülük, vadeli piyasa verileri, haberler, olaylar.

Hepsi "hata verirse atla" mantığıyla çalışır; bir kaynak düşerse rapor yine üretilir.
"""
from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import pandas as pd
import requests

from . import config

BASLIK = {"User-Agent": "btc-tahminleme/1.0"}
# Bazı haber siteleri tanımadığı programları engelliyor; tarayıcı gibi görün
TARAYICI = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0 Safari/537.36", "Accept": "application/rss+xml, application/xml, text/xml, */*"}


def _json(url, params=None, deneme: int = 4):
    """GET + JSON. Hız sınırı (429) ve geçici sunucu hatalarında bekleyip tekrar dener."""
    for i in range(deneme):
        r = requests.get(url, params=params, timeout=config.HTTP_TIMEOUT, headers=BASLIK)
        if r.status_code in (429, 500, 502, 503, 504) and i < deneme - 1:
            bekle = float(r.headers.get("Retry-After") or 0) or (3 * 2 ** i)
            time.sleep(min(bekle, 30))
            continue
        if r.status_code == 429:
            raise RuntimeError("hız sınırı (429): kaynak çok fazla istek aldı, birkaç dakika sonra düzelir")
        if r.status_code in (403, 451):
            raise RuntimeError(f"erişim engellendi ({r.status_code}): kaynak bu bölgeden/ağdan erişime kapalı olabilir")
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------- dominanslar
DOM_COINLER = {"btc": "bitcoin", "eth": "ethereum", "xrp": "ripple", "usdt": "tether", "usdc": "usd-coin"}


def dominanslar() -> dict:
    """Anlık dominanslar (CoinGecko) + kendi kaydettiğimiz geçmişten trend."""
    g = _json(f"{config.COINGECKO}/global")["data"]
    yuzde = g["market_cap_percentage"]
    simdi = {k: round(float(yuzde.get(k, 0.0)), 3) for k in DOM_COINLER}
    simdi["stable_toplam"] = round(simdi["usdt"] + simdi["usdc"] + float(yuzde.get("dai", 0.0)), 3)
    simdi["others"] = round(100 - sum(float(v) for v in yuzde.values()), 3)
    toplam = float(g["total_market_cap"]["usd"])
    kayit = {"time": datetime.now(timezone.utc).isoformat(), "toplam_mcap": toplam, **simdi}

    config.VERI_DIR.mkdir(parents=True, exist_ok=True)
    dosya = config.VERI_DIR / "dominans_gecmisi.csv"
    gecmis = pd.read_csv(dosya) if dosya.exists() else pd.DataFrame()
    gecmis = pd.concat([gecmis, pd.DataFrame([kayit])], ignore_index=True)
    gecmis.to_csv(dosya, index=False)

    sonuc = {"anlik": simdi, "toplam_mcap_usd": toplam,
             "toplam_mcap_degisim_24s": round(float(g.get("market_cap_change_percentage_24h_usd", 0)), 2),
             "degisim": {}}
    # Geçmiş trend: CoinGecko market cap serilerinden (5 coin arası pay) -> 24s ve 7g değişim
    try:
        seriler = {}
        for k, cid in DOM_COINLER.items():
            time.sleep(2.5)   # ücretsiz CoinGecko dakikada ~10-30 istek kabul ediyor
            d = _json(f"{config.COINGECKO}/coins/{cid}/market_chart", {"vs_currency": "usd", "days": 8})
            s = pd.DataFrame(d["market_caps"], columns=["t", k])
            s["t"] = pd.to_datetime(s["t"], unit="ms").dt.floor("h")
            seriler[k] = s.groupby("t")[k].last()
        df = pd.DataFrame(seriler).dropna()
        # Toplam pazar değerinin geçmişi ücretsiz API'de yok; anlık oranla ölçekleyip
        # 5 coinin payındaki göreli değişimi gerçek dominansa uygula.
        oran = df.div(df.sum(axis=1), axis=0)
        for k in DOM_COINLER:
            o_simdi = oran[k].iloc[-1]
            for etiket, saat in (("24s", 24), ("7g", 168)):
                if len(oran) > saat:
                    o_once = oran[k].iloc[-1 - saat]
                    tahmini_once = simdi[k] * o_once / o_simdi
                    sonuc["degisim"].setdefault(k, {})[etiket] = round(simdi[k] - tahmini_once, 3)
    except Exception as e:  # noqa: BLE001
        sonuc["trend_hatasi"] = str(e)
    # Program düzenli çalıştırıldıysa kendi kayıtlarımız gerçek dominans geçmişini verir -> tahmini ez
    zaman = pd.to_datetime(gecmis["time"], utc=True, format="ISO8601")
    hedef_zaman = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=24)
    yakin = (zaman - hedef_zaman).abs()
    if len(gecmis) > 1 and yakin.min() <= pd.Timedelta(hours=2):
        once = gecmis.loc[yakin.idxmin()]
        for k in DOM_COINLER:
            sonuc["degisim"].setdefault(k, {})["24s"] = round(simdi[k] - float(once[k]), 3)
        sonuc["degisim_kaynagi_24s"] = "kendi kayıtları (gerçek)"
    else:
        sonuc["degisim_kaynagi_24s"] = "5 coin payından tahmini"
    sonuc["yorum"] = _dominans_yorumu(sonuc)
    return sonuc


def _dominans_yorumu(d: dict) -> list[str]:
    y = []
    dg = d.get("degisim", {})
    usdt = dg.get("usdt", {}).get("24s", 0) + dg.get("usdc", {}).get("24s", 0)
    btc = dg.get("btc", {}).get("24s", 0)
    tm = d.get("toplam_mcap_degisim_24s", 0)
    if usdt > 0.15:
        y.append("Stablecoin dominansı (USDT.D+USDC.D) yükseliyor -> piyasadan nakde kaçış, LONG riski artar.")
    elif usdt < -0.15:
        y.append("Stablecoin dominansı düşüyor -> nakit kriptoya giriyor, LONG lehine.")
    if btc > 0.2 and tm < 0:
        y.append("BTC.D yükselirken toplam piyasa düşüyor -> altcoinlerden BTC'ye kaçış (ETH/XRP için olumsuz).")
    elif btc > 0.2 and tm > 0:
        y.append("BTC.D ve toplam piyasa birlikte yükseliyor -> BTC liderliğinde ralli.")
    elif btc < -0.2 and tm > 0:
        y.append("BTC.D düşerken piyasa yükseliyor -> altcoin sezonu sinyali (ETH/XRP lehine).")
    for k in ("eth", "xrp"):
        v = dg.get(k, {}).get("24s", 0)
        if abs(v) > 0.05:
            y.append(f"{k.upper()}.D 24 saatte {v:+.2f} puan.")
    return y


# ---------------------------------------------------------------- duygu & vadeli
def korku_acgozluluk() -> dict:
    d = _json(config.FEAR_GREED)["data"]
    return {"deger": int(d[0]["value"]), "sinif": d[0]["value_classification"],
            "dun": int(d[1]["value"]), "hafta_once": int(d[7]["value"]) if len(d) > 7 else None}


def vadeli(sembol: str) -> dict:
    """Her alan ayrı denenir: biri gelmezse diğerleri yine gösterilir. Hatalar out["hatalar"]da."""
    out: dict = {"hatalar": {}}
    f = config.BINANCE_FUTURES

    def dene(ad, fn):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            out["hatalar"][ad] = str(e)[:200]

    def funding():
        p = _json(f"{f}/fapi/v1/premiumIndex", {"symbol": sembol})
        out["funding_yuzde"] = round(float(p["lastFundingRate"]) * 100, 4)

    def oi():
        d = _json(f"{f}/futures/data/openInterestHist", {"symbol": sembol, "period": "1h", "limit": 25})
        a, b = float(d[0]["sumOpenInterestValue"]), float(d[-1]["sumOpenInterestValue"])
        out["oi_usd"] = round(b)
        out["oi_degisim_24s_yuzde"] = round((b / a - 1) * 100, 2)

    def ls():
        d = _json(f"{f}/futures/data/globalLongShortAccountRatio", {"symbol": sembol, "period": "1h", "limit": 1})
        out["long_short_orani"] = round(float(d[-1]["longShortRatio"]), 3)

    def taker():
        d = _json(f"{f}/futures/data/takerlongshortRatio", {"symbol": sembol, "period": "1h", "limit": 4})
        out["taker_alis_satis"] = round(sum(float(x["buySellRatio"]) for x in d) / len(d), 3)

    for ad, fn in (("funding", funding), ("acik_pozisyon", oi), ("long_short", ls), ("taker", taker)):
        dene(ad, fn)
    if len(out["hatalar"]) == 4:
        raise RuntimeError("Binance Futures verisine ulaşılamadı: " + next(iter(out["hatalar"].values())))
    return out


# ---------------------------------------------------------------- haberler
OLUMSUZ = {
    "hack": 3, "exploit": 3, "war": 3, "attack": 2, "missile": 3, "strike": 2, "iran": 2, "israel": 1,
    "sanction": 2, "ban": 2, "crash": 3, "plunge": 2, "liquidat": 2, "lawsuit": 2, "sues": 2,
    "sec charges": 3, "tariff": 2, "recession": 2, "outflow": 2, "bankrupt": 3, "insolven": 3,
    "fraud": 2, "selloff": 2, "sell-off": 2, "dump": 1, "fear": 1, "hawkish": 2, "rate hike": 2,
    "delist": 2, "investigation": 1, "escalat": 2,
}
OLUMLU = {
    "approve": 2, "approval": 2, "inflow": 2, "rally": 2, "surge": 2, "record high": 3, "all-time high": 3,
    "adoption": 1, "rate cut": 2, "dovish": 2, "ceasefire": 3, "peace": 2, "partnership": 1,
    "etf": 1, "bullish": 1, "reserve": 1, "accumulat": 1, "upgrade": 1, "soar": 2, "jump": 1,
}
JEOPOLITIK = ["war", "iran", "israel", "missile", "strike", "escalat", "ceasefire", "military", "nuclear"]


def haberler(saat: int = 24) -> dict:
    sinir = datetime.now(timezone.utc) - timedelta(hours=saat)
    basliklar = []
    kaynak_durumu = {}
    atom = "{http://www.w3.org/2005/Atom}"
    for url in config.HABER_RSS:
        ad = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
        try:
            r = requests.get(url, timeout=config.HTTP_TIMEOUT, headers=TARAYICI)
            r.raise_for_status()
            kok = ET.fromstring(r.content)
            ogeler = list(kok.iter("item")) or list(kok.iter(f"{atom}entry"))
            adet = 0
            for it in ogeler:
                t = (it.findtext("title") or it.findtext(f"{atom}title") or "").strip()
                tarih = it.findtext("pubDate") or it.findtext(f"{atom}updated") or it.findtext(f"{atom}published")
                try:
                    dt = parsedate_to_datetime(tarih) if tarih and not tarih[:4].isdigit() else (
                        datetime.fromisoformat(tarih.replace("Z", "+00:00")) if tarih else None)
                except (TypeError, ValueError):
                    dt = None
                if not t or (dt and dt < sinir):
                    continue
                adet += 1
                basliklar.append({"baslik": t, "kaynak": ad, "zaman": dt.isoformat() if dt else None})
            kaynak_durumu[ad] = f"{adet} başlık"
        except Exception as e:  # noqa: BLE001
            kaynak_durumu[ad] = f"HATA: {str(e)[:120]}"
    # Aynı başlık birden çok kaynakta olabilir
    goruldu, tekil = set(), []
    for b in basliklar:
        anahtar = b["baslik"].lower()[:80]
        if anahtar not in goruldu:
            goruldu.add(anahtar)
            tekil.append(b)
    basliklar = tekil
    toplam, jeo = 0, 0
    for b in basliklar:
        k = b["baslik"].lower()
        skor = sum(v for w, v in OLUMLU.items() if w in k) - sum(v for w, v in OLUMSUZ.items() if w in k)
        b["skor"] = skor
        toplam += skor
        jeo += any(w in k for w in JEOPOLITIK)
    basliklar.sort(key=lambda b: abs(b["skor"]), reverse=True)
    return {"adet": len(basliklar), "toplam_skor": toplam,
            "ortalama_skor": round(toplam / len(basliklar), 3) if basliklar else 0,
            "jeopolitik_baslik_sayisi": jeo, "onemli": basliklar[:12], "kaynak_durumu": kaynak_durumu}


# ---------------------------------------------------------------- olaylar & puan kırımı
def olaylari_oku() -> dict:
    dosya = config.AYAR_DIR / "olaylar.json"
    if not dosya.exists():
        return {"genel_puan_kirimlari": [], "takvim": []}
    return json.loads(dosya.read_text(encoding="utf-8"))


def puan_kirimlari(baglam: dict, olaylar: dict, ana_sembol: str) -> dict:
    """Genel piyasa puanı (100 üzerinden). Modellerin içine girmez, ayrı gösterilir."""
    kalemler = []
    for k in olaylar.get("genel_puan_kirimlari", []):
        if k.get("aktif", True):
            kalemler.append({"ad": k["ad"], "kirim": float(k["kirim_yuzde"]), "kaynak": "manuel", "not": k.get("not", "")})

    simdi = datetime.now(timezone.utc)
    yaklasan = []
    for e in olaylar.get("takvim", []):
        try:
            t = datetime.fromisoformat(e["tarih"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        fark = (t - simdi).total_seconds() / 3600
        if -2 <= fark <= 48:
            yaklasan.append({**e, "saat_kaldi": round(fark, 1)})
            if fark <= 24:
                kirim = {"yuksek": 8, "orta": 4}.get(e.get("etki", "orta"), 2)
                kalemler.append({"ad": f"Yaklaşan olay: {e['ad']} ({fark:.0f} saat)", "kirim": kirim, "kaynak": "takvim"})

    fg = baglam.get("korku_acgozluluk") or {}
    if fg.get("deger") is not None:
        v = fg["deger"]
        if v <= 20:
            kalemler.append({"ad": f"Aşırı korku (F&G {v})", "kirim": 5, "kaynak": "otomatik"})
        elif v >= 80:
            kalemler.append({"ad": f"Aşırı açgözlülük (F&G {v}) - düzeltme riski", "kirim": 5, "kaynak": "otomatik"})

    vd = (baglam.get("vadeli") or {}).get(ana_sembol) or {}
    f = vd.get("funding_yuzde")
    if f is not None and abs(f) >= 0.05:
        kalemler.append({"ad": f"Aşırı funding ({f:+.3f}%) - kaldıraç tasfiye riski", "kirim": 4, "kaynak": "otomatik"})
    if vd.get("oi_degisim_24s_yuzde", 0) >= 10:
        kalemler.append({"ad": "Açık pozisyon 24s'te %10+ arttı - ani likidasyon riski", "kirim": 3, "kaynak": "otomatik"})

    dom = baglam.get("dominans") or {}
    dg = dom.get("degisim", {})
    st = dg.get("usdt", {}).get("24s", 0) + dg.get("usdc", {}).get("24s", 0)
    if st > 0.15:
        kalemler.append({"ad": f"Stablecoin dominansı yükseliyor (+{st:.2f})", "kirim": 4, "kaynak": "otomatik"})

    hb = baglam.get("haberler") or {}
    if hb.get("adet", 0) >= 5 and hb.get("ortalama_skor", 0) <= -0.5:
        kalemler.append({"ad": "Haber akışı belirgin olumsuz", "kirim": 4, "kaynak": "otomatik"})
    if hb.get("jeopolitik_baslik_sayisi", 0) >= 3 and not any(k["kaynak"] == "manuel" for k in kalemler):
        kalemler.append({"ad": "Jeopolitik başlıklar yoğun (manuel kırım eklemeyi düşün)", "kirim": 3, "kaynak": "otomatik"})

    if simdi.weekday() >= 5:
        kalemler.append({"ad": "Hafta sonu - düşük likidite", "kirim": 2, "kaynak": "otomatik"})

    toplam = sum(k["kirim"] for k in kalemler)
    return {"genel_puan": max(0.0, round(100 - toplam, 1)), "toplam_kirim": round(toplam, 1),
            "kalemler": kalemler, "yaklasan_olaylar": yaklasan}


def baglam_topla(semboller) -> dict:
    b = {"hatalar": {}}
    for ad, fn in (("dominans", dominanslar), ("korku_acgozluluk", korku_acgozluluk), ("haberler", haberler)):
        try:
            b[ad] = fn()
        except Exception as e:  # noqa: BLE001
            b[ad] = None
            b["hatalar"][ad] = str(e)
    b["vadeli"] = {}
    for s in semboller:
        try:
            b["vadeli"][s] = vadeli(s)
        except Exception as e:  # noqa: BLE001
            b["hatalar"][f"vadeli_{s}"] = str(e)
    return b
