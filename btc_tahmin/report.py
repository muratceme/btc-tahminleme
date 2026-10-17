"""Terminal özeti ve HTML panosu (cikti/rapor.html)."""
from __future__ import annotations

import json

from . import config

YESIL, KIRMIZI, SARI, GRI, KALIN, SIFIR = "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m"


def _risk_renk(r):
    if r is None:
        return GRI
    return YESIL if r < 40 else (SARI if r < 60 else KIRMIZI)


def terminal(rapor: dict) -> str:
    s = []
    gp = rapor["genel_puan"]
    s.append(f"{KALIN}══════ BTC/ETH/XRP GÜN SONU RİSK RAPORU ({rapor['aralik']}) ══════{SIFIR}")
    s.append(f"Oluşturma: {rapor['olusturma'][:19]} UTC")
    s.append(f"{KALIN}GENEL PİYASA PUANI: %{gp['genel_puan']}{SIFIR}  (toplam kırım -{gp['toplam_kirim']})")
    for k in gp["kalemler"]:
        s.append(f"   -{k['kirim']:<4} {k['ad']}  [{k['kaynak']}]")
    b = rapor["baglam"]
    if b.get("dominans"):
        d = b["dominans"]["anlik"]
        s.append(f"Dominans: BTC {d['btc']:.2f}  ETH {d['eth']:.2f}  XRP {d['xrp']:.2f}  "
                 f"USDT {d['usdt']:.2f}  USDC {d['usdc']:.2f}  Stable {d['stable_toplam']:.2f}")
        for y in b["dominans"].get("yorum", []):
            s.append(f"   • {y}")
    if b.get("korku_acgozluluk"):
        f = b["korku_acgozluluk"]
        s.append(f"Korku/Açgözlülük: {f['deger']} ({f['sinif']}), dün {f['dun']}")
    for c in rapor["coinler"].values():
        oz = c["risk"]["ozet"]
        s.append("")
        s.append(f"{KALIN}▶ {c['sembol']}  {c['fiyat']:,.4f}  (24s {c['degisim_24s']:+}%)  son mum {c['son_mum_zamani'][:16]}{SIFIR}")
        lr = oz.get("long_risk")
        if lr is not None:
            s.append(f"  GÜN SONU LONG RİSKİ: {_risk_renk(lr)}{KALIN}%{lr}{SIFIR}  | SHORT riski %{oz['short_risk']}  "
                     f"({oz['dayanak_sayisi']} tutarlı sinyal)")
        else:
            s.append(f"  GÜN SONU LONG RİSKİ: {GRI}tutarlı sinyal yok{SIFIR}  (ham model tahmini: %{oz.get('ham_model_long_risk')}, "
                     f"genel isabeti %{round((oz.get('ham_model_dogrulugu') or 0) * 100)} — düşük güven)")
        if oz.get("kirimli_long_risk") is not None:
            s.append(f"  Puan kırımı dahil long riski: %{oz['kirimli_long_risk']}")
        if oz.get("max_dusus"):
            s.append("  Gün sonuna kadar max düşüş sınırı: " +
                     ", ".join(f"{k} güvenle {v}%" for k, v in oz["max_dusus"].items()))
        s.append(f"  {'Etiket':<8} {'Tutarlılık':>10} {'n':>6}  {'Sinyal':<7} {'Long':>6} {'Short':>6}  Kaynak")
        for r in c["risk"]["satirlar"][:15]:
            if "max_dusus" in r:
                s.append(f"  {r['etiket']:<8} {r['tutarlilik']*100:>9.1f}% {r['test_n']:>6}  {'-':<7} "
                         f"{'max':>6} {r['max_dusus']:>5}%  {r['kaynak']}")
            else:
                sg = "VAR" if r["sinyal_var"] else "yok"
                s.append(f"  {r['etiket']:<8} {r['tutarlilik']*100:>9.1f}% {r['test_n']:>6}  {sg:<7} "
                         f"{r['long_risk']:>5}% {r['short_risk']:>5}%  {r['kaynak'][:70]}")
        ak = c["sonraki_mum"]["aktif_kurallar"]
        if ak:
            s.append(f"  {KALIN}Sonraki {c['aralik']} mum için ŞU AN AKTİF kombinasyonlar:{SIFIR}")
            for r in ak[:8]:
                renk = YESIL if r["yon"].startswith("YESIL") else KIRMIZI
                s.append(f"   {renk}{r['yon'][:7]} %{r['tutarlilik']*100:.0f}{SIFIR} (test n={r['test_n']}): "
                         + " + ".join(r["kosullar"]))
        else:
            s.append(f"  {GRI}Sonraki mum için şu an aktif tutarlı kombinasyon yok.{SIFIR}")
        derin = c.get("derin", {}).get("aktif", [])
        if derin:
            from .aciklama import hedef_metni, kosul_bilgisi
            s.append(f"  {KALIN}DERİN TARAMA (%85+) · şu an aktif:{SIFIR}")
            for r in derin[:6]:
                yuk, metin = hedef_metni(r["hedef"], 1 if r["yon"].startswith("YESIL") else 0, c["aralik"])
                renk = YESIL if yuk else KIRMIZI
                s.append(f"   {renk}%{r['tutarlilik']*100:.0f} {metin}{SIFIR} (test n={r['test_n']}): "
                         + " + ".join(kosul_bilgisi(k)["etiket"] for k in r["kosullar"]))
    s.append("")
    sg = rapor.get("saglik") or []
    if sg:
        hata = [x for x in sg if x["durum"] == "hata"]
        s.append(f"Veri durumu: {YESIL}✓ {sum(x['durum'] == 'ok' for x in sg)} geldi{SIFIR} · "
                 f"{GRI}○ {sum(x['durum'] == 'normal' for x in sg)} boş ama normal{SIFIR} · "
                 f"{KIRMIZI if hata else GRI}✗ {len(hata)} hata{SIFIR}")
        for x in hata:
            s.append(f"   {KIRMIZI}✗ {x['metrik']}{SIFIR}: {x['aciklama']}")
    s.append(f"{GRI}{rapor['uyari']}{SIFIR}")
    s.append(f"Pano: {config.CIKTI_DIR / 'rapor.html'}")
    return "\n".join(s)


def kaydet(rapor: dict, yenile_sn: int | None = None):
    config.CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    import shutil
    from pathlib import Path

    from .pano import grafik_html, nasil_calisir_html, pano_html
    (config.CIKTI_DIR / "nasil-calisir.html").write_text(nasil_calisir_html(), encoding="utf-8")
    (config.CIKTI_DIR / "grafik.html").write_text(grafik_html(), encoding="utf-8")
    statik = config.CIKTI_DIR / "statik"
    statik.mkdir(exist_ok=True)
    for f in (Path(__file__).parent / "statik").iterdir():
        shutil.copy2(f, statik / f.name)
    yol = config.CIKTI_DIR / "rapor.html"
    yol.write_text(pano_html(rapor, yenile_sn), encoding="utf-8")
    return yol


def json_oku():
    return json.loads((config.CIKTI_DIR / "rapor.json").read_text(encoding="utf-8"))


def saglik_tablosu(satirlar: list[dict]) -> str:
    isaret = {"ok": f"{YESIL}✓ geldi        {SIFIR}", "normal": f"{GRI}○ boş · normal {SIFIR}", "hata": f"{KIRMIZI}✗ HATA         {SIFIR}"}
    s, grup = [], None
    for x in satirlar:
        if x["grup"] != grup:
            grup = x["grup"]
            s.append(f"\n{KALIN}{grup}{SIFIR}")
        s.append(f"  {isaret[x['durum']]} {x['metrik']:<38} {GRI}{x['aciklama']}{SIFIR}")
    say = {d: sum(1 for x in satirlar if x["durum"] == d) for d in ("ok", "normal", "hata")}
    s.append(f"\nToplam: ✓ {say['ok']} geldi · ○ {say['normal']} boş ama normal · ✗ {say['hata']} hata")
    s.append("○ = o an söylenecek güvenilir bir şey yok (hata değil).  ✗ = gelmesi gereken veri gelmedi, sebebi yanında.")
    return "\n".join(s)
