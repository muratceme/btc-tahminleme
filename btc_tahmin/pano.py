"""HTML panosu (rapor.html) ve açıklama sayfası (nasil-calisir.html).

Tek dosyalık, internet gerektirmeyen sayfalar üretir (yalnızca yazı tipleri Google Fonts'tan gelir,
internet yoksa sistem yazı tipine düşer).
"""
from __future__ import annotations

import html
import math

from . import config
from .aciklama import AILELER, FORMASYONLAR, GRUP_SIRASI, hedef_metni, kosul_bilgisi

CSS = """
:root{--bg:#05070b;--panel:#0c1119;--panel2:#101722;--cizgi:rgba(148,163,184,.13);--cizgi2:rgba(148,163,184,.22);
--yazi:#e7eaf0;--soluk:#8b97a9;--soluk2:#5e6a7b;--altin:#d4af37;--altin2:#f3d778;--iyi:#16c784;--kotu:#ea3943;
--orta:#f0b90b;--mavi:#4f8cff;--mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
--sans:Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
*{box-sizing:border-box}html,body{max-width:100%;overflow-x:hidden}
body{margin:0;background:var(--bg);background-image:radial-gradient(1200px 500px at 15% -10%,rgba(212,175,55,.07),transparent 60%),
radial-gradient(900px 400px at 100% 0,rgba(79,140,255,.05),transparent 60%);color:var(--yazi);font:14px/1.55 var(--sans);
-webkit-font-smoothing:antialiased}
a{color:var(--altin2);text-decoration:none}a:hover{text-decoration:underline}
.mono,.sayi{font-family:var(--mono);font-variant-numeric:tabular-nums}
.iyi{color:var(--iyi)}.kotu{color:var(--kotu)}.orta{color:var(--orta)}.notr{color:var(--soluk)}.altin{color:var(--altin2)}
.kucuk{color:var(--soluk);font-size:12px}.cok-kucuk{color:var(--soluk2);font-size:11px}
/* üst bar */
.ust-bar{position:sticky;top:0;z-index:20;background:rgba(3,4,7,.92);backdrop-filter:blur(10px);border-bottom:1px solid var(--cizgi2)}
.ust-ic{max-width:1360px;margin:0 auto;padding:10px 16px;display:flex;align-items:center;gap:10px 22px;flex-wrap:wrap}
.marka{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:.14em;font-size:13px;white-space:nowrap}
.marka .elmas{width:22px;height:22px;transform:rotate(45deg);background:linear-gradient(135deg,var(--altin2),var(--altin) 55%,#8a6d17);
border-radius:3px;box-shadow:0 0 18px rgba(212,175,55,.35)}
.marka small{font-size:9px;letter-spacing:.2em;color:#000;background:var(--altin);padding:1px 5px;border-radius:2px;margin-left:2px}
nav.menu{display:flex;gap:4px}nav.menu a{color:var(--soluk);padding:6px 10px;border-radius:6px;font-weight:600;font-size:13px}
nav.menu a.aktif,nav.menu a:hover{color:var(--yazi);background:rgba(255,255,255,.06);text-decoration:none}
.canli{margin-left:auto;display:flex;align-items:center;gap:14px;font-size:12px;color:var(--soluk);flex-wrap:wrap}
.nokta{display:inline-flex;align-items:center;gap:6px;color:var(--iyi);font-weight:700;letter-spacing:.12em;font-size:11px}
.nokta i{width:8px;height:8px;border-radius:50%;background:var(--iyi);box-shadow:0 0 0 0 rgba(22,199,132,.6);animation:nabiz 2s infinite}
.nokta.eski{color:var(--orta)}.nokta.eski i{background:var(--orta);animation:none}
@keyframes nabiz{0%{box-shadow:0 0 0 0 rgba(22,199,132,.55)}70%{box-shadow:0 0 0 9px rgba(22,199,132,0)}100%{box-shadow:0 0 0 0 rgba(22,199,132,0)}}
/* kayan şerit */
.serit{border-top:1px solid var(--cizgi);overflow:hidden;white-space:nowrap;background:#030406}
.serit-ic{display:inline-flex;gap:34px;padding:7px 0;animation:kay 60s linear infinite;font-family:var(--mono);font-size:12px}
.serit:hover .serit-ic{animation-play-state:paused}.serit-ic span{color:var(--soluk)}.serit-ic b{color:var(--yazi);margin-right:6px}
@keyframes kay{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@media (prefers-reduced-motion:reduce){.serit-ic{animation:none}.nokta i{animation:none}.serit{overflow-x:auto}}
main{max-width:1360px;margin:0 auto;padding:20px 16px 40px}
/* kartlar */
.kart{background:linear-gradient(180deg,var(--panel2),var(--panel));border:1px solid var(--cizgi);border-radius:12px;padding:18px;
box-shadow:0 1px 0 rgba(255,255,255,.04) inset,0 10px 30px rgba(0,0,0,.35);min-width:0}
.kart-baslik{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:0 0 12px;font-size:11px;font-weight:700;
letter-spacing:.14em;text-transform:uppercase;color:var(--soluk)}
.kart-baslik .bilgi{display:inline-grid;place-items:center;width:18px;height:18px;border-radius:50%;border:1px solid var(--cizgi2);
color:var(--soluk);font-size:11px;letter-spacing:0;text-decoration:none}.kart-baslik .bilgi:hover{color:var(--altin2);border-color:var(--altin)}
.izgara-4{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(260px,100%),1fr));gap:16px;margin-bottom:16px}
.dev{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:44px;font-weight:700;line-height:1;letter-spacing:-.02em}
ul.liste{list-style:none;margin:10px 0 0;padding:0}ul.liste li{display:flex;gap:10px;justify-content:space-between;padding:6px 0;
border-top:1px solid var(--cizgi);font-size:13px}ul.liste li:first-child{border-top:0}
.etiket-sag{font-family:var(--mono);white-space:nowrap}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:9px 10px;border-bottom:1px solid var(--cizgi);text-align:left;vertical-align:top}
th{position:sticky;top:0;background:var(--panel);color:var(--soluk2);font-weight:700;font-size:10px;letter-spacing:.12em;text-transform:uppercase;white-space:nowrap}
td.sayi,th.sayi{text-align:right}tbody tr:hover{background:rgba(255,255,255,.025)}.tablo-sar{overflow-x:auto;margin:0 -4px}
.rozet{display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:.04em;
white-space:nowrap;border:1px solid currentColor;background:color-mix(in srgb,currentColor 12%,transparent)}
.cip{display:inline-flex;align-items:center;gap:6px;padding:3px 9px;margin:3px 4px 3px 0;border-radius:6px;font-size:12px;
background:rgba(255,255,255,.04);border:1px solid var(--cizgi);max-width:100%;overflow-wrap:anywhere;cursor:help}
.cip::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--soluk2);flex:none}
.cip.boga::before{background:var(--iyi)}.cip.ayi::before{background:var(--kotu)}.cip.asiri::before{background:var(--orta)}
/* coin sekmeleri */
.sekmeler{display:flex;gap:6px;margin:6px 0 16px;flex-wrap:wrap}
.sekme{font:600 13px var(--sans);color:var(--soluk);background:var(--panel);border:1px solid var(--cizgi);border-radius:10px;padding:9px 14px;
cursor:pointer;display:flex;gap:10px;align-items:center}.sekme b{color:var(--yazi);font-weight:800;letter-spacing:.06em}
.sekme[aria-selected=true]{border-color:var(--altin);box-shadow:0 0 0 1px var(--altin) inset;background:linear-gradient(180deg,rgba(212,175,55,.10),transparent)}
.js .coin[hidden]{display:none}
/* hero */
.hero{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:16px;margin-bottom:16px}
@media (max-width:1000px){.hero{grid-template-columns:1fr 1fr}.hero .karar-kart{grid-column:1/-1}}
@media (max-width:640px){.hero{grid-template-columns:1fr}}
.fiyat{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:38px;font-weight:700;letter-spacing:-.02em;line-height:1.1}
.degisim{font-family:var(--mono);font-size:14px;font-weight:700;padding:3px 8px;border-radius:6px;margin-left:8px;vertical-align:middle}
.degisim.iyi{background:rgba(22,199,132,.12)}.degisim.kotu{background:rgba(234,57,67,.12)}
.sembol{font-size:13px;font-weight:800;letter-spacing:.16em;color:var(--altin2)}
.gosterge{display:flex;flex-direction:column;align-items:center}.gosterge svg{width:100%;max-width:260px;height:auto}
.karar{font-size:12px;font-weight:800;letter-spacing:.12em;padding:6px 12px;border-radius:8px;margin-top:6px;text-align:center}
.karar.iyi{background:rgba(22,199,132,.12);border:1px solid rgba(22,199,132,.4)}
.karar.orta{background:rgba(240,185,11,.10);border:1px solid rgba(240,185,11,.4)}
.karar.kotu{background:rgba(234,57,67,.12);border:1px solid rgba(234,57,67,.4)}
.karar.notr{background:rgba(255,255,255,.04);border:1px solid var(--cizgi2);color:var(--soluk)}
.kpi-izgara{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.kpi{background:rgba(255,255,255,.025);border:1px solid var(--cizgi);border-radius:10px;padding:10px 12px;min-width:0}
.kpi .e{font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--soluk2)}
.kpi .d{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:20px;font-weight:700;margin-top:2px}
.kpi .a{font-size:11px;color:var(--soluk)}
.aciklama-kutu{border-left:3px solid var(--altin);background:rgba(212,175,55,.06);padding:12px 14px;border-radius:0 8px 8px 0;margin:0 0 16px;font-size:13.5px}
.aciklama-kutu b{color:var(--altin2)}
.iki-sutun{display:grid;grid-template-columns:1.4fr 1fr;gap:16px;margin-bottom:16px}@media (max-width:1000px){.iki-sutun{grid-template-columns:1fr}}
.bolum{margin-bottom:16px}
/* risk satırı */
.tut{display:flex;align-items:center;gap:8px;white-space:nowrap}.tut .cubuk{width:64px;height:6px;border-radius:3px;background:rgba(255,255,255,.07);overflow:hidden}
.tut .cubuk span{display:block;height:100%;background:linear-gradient(90deg,var(--altin),var(--altin2))}
tr.pasif td{opacity:.5}.satir-not{color:var(--soluk);font-size:12px;margin-top:4px;line-height:1.45}
.etk-hucre{font-family:var(--mono);font-weight:700;color:var(--altin2);white-space:nowrap}
/* sinyal haritası */
.denge{display:flex;height:8px;border-radius:4px;overflow:hidden;background:rgba(255,255,255,.06);margin:6px 0 4px}
.denge .b{background:var(--iyi)}.denge .a{background:var(--kotu)}.denge .x{background:var(--orta)}
.grup{margin-top:12px}.grup h4{margin:0 0 4px;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--soluk2)}
/* kurallar */
.kural{border:1px solid var(--cizgi);border-radius:10px;padding:12px;margin-bottom:10px;background:rgba(255,255,255,.015)}
.kural-ust{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px}
.kural-yuzde{font-family:var(--mono);font-size:20px;font-weight:800}
.grafik-btn{margin-left:auto;font-size:12px;font-weight:700;color:var(--altin2);border:1px solid rgba(212,175,55,.45);border-radius:8px;
padding:4px 10px;background:rgba(212,175,55,.07);white-space:nowrap}.grafik-btn:hover{background:rgba(212,175,55,.16);text-decoration:none}
.derin-kart{border-color:rgba(212,175,55,.35);box-shadow:0 0 0 1px rgba(212,175,55,.12) inset,0 10px 30px rgba(0,0,0,.35)}
.grafik-kutu{height:520px;margin-top:10px}.grafik-kucuk{height:200px;margin-top:10px}@media (max-width:640px){.grafik-kutu{height:380px}}
.kpi-4{grid-template-columns:repeat(auto-fit,minmax(min(150px,45%),1fr))}.kpi-4 .dev{font-size:clamp(20px,5vw,30px)!important}
.filtre{display:flex;gap:6px;flex-wrap:wrap}.filtre button{font:600 12px var(--sans);color:var(--soluk);background:var(--panel);border:1px solid var(--cizgi);
border-radius:8px;padding:6px 10px;cursor:pointer}.filtre button[aria-pressed=true]{color:var(--yazi);border-color:var(--altin)}
tr.tik{cursor:pointer}tr.secili td{background:rgba(212,175,55,.08)}
details{margin-top:12px}summary{cursor:pointer;color:var(--altin2);font-weight:600;font-size:13px}
ul.liste.haber li{align-items:flex-start;justify-content:flex-start}.haber .skor{font-family:var(--mono);font-weight:700;min-width:30px}
footer{max-width:1360px;margin:0 auto;padding:24px 16px 40px;color:var(--soluk2);font-size:12px;border-top:1px solid var(--cizgi)}
/* nasıl çalışır */
.doc{display:grid;grid-template-columns:240px 1fr;gap:28px;align-items:start}
@media (max-width:900px){.doc{grid-template-columns:1fr}.toc{position:static!important}}
.toc{position:sticky;top:76px;font-size:13px}.toc a{display:block;color:var(--soluk);padding:5px 10px;border-left:2px solid var(--cizgi)}
.toc a:hover{color:var(--yazi);border-color:var(--altin);text-decoration:none}
.doc h1{font-size:30px;margin:0 0 6px;letter-spacing:-.01em}.doc h2{font-size:20px;margin:0 0 10px;color:var(--altin2)}
.doc section{scroll-margin-top:80px}.doc p{color:#c9d0db;max-width:78ch}.doc .kart{margin-bottom:18px}
.akis{display:flex;align-items:stretch;gap:8px;flex-wrap:wrap;margin:14px 0}
.akis .adim{flex:1 1 150px;border:1px solid var(--cizgi2);border-radius:10px;padding:12px;background:rgba(255,255,255,.025)}
.akis .adim b{display:block;color:var(--altin2);font-size:11px;letter-spacing:.12em;text-transform:uppercase;margin-bottom:4px}
.akis .ok{align-self:center;color:var(--altin);font-size:18px}@media (max-width:640px){.akis .ok{transform:rotate(90deg);width:100%;text-align:center}}
.bolme{display:flex;height:34px;border-radius:8px;overflow:hidden;font-size:12px;font-weight:700;margin:10px 0}
.bolme div{display:grid;place-items:center;color:#05070b}
.ornek{font-family:var(--mono);background:#06090e;border:1px solid var(--cizgi);border-radius:8px;padding:12px 14px;font-size:12.5px;overflow-x:auto;white-space:pre}
"""

JS = """
document.documentElement.classList.add('js');
(function(){
  var sek=document.querySelectorAll('.sekme'),coin=document.querySelectorAll('.coin');
  function sec(id){sek.forEach(function(s){s.setAttribute('aria-selected',s.dataset.hedef===id)});
    coin.forEach(function(c){c.hidden=c.id!==id});try{localStorage.setItem('kr_sekme',id)}catch(e){}}
  sek.forEach(function(s){s.addEventListener('click',function(){sec(s.dataset.hedef)})});
  var ilk=null;try{ilk=localStorage.getItem('kr_sekme')}catch(e){}
  if(sek.length){sec(ilk&&document.getElementById(ilk)?ilk:sek[0].dataset.hedef)}
  var ts=document.body.dataset.ts?new Date(document.body.dataset.ts):null,yas=document.getElementById('yas'),
      saat=document.getElementById('saat'),nokta=document.getElementById('nokta');
  function tik(){var n=new Date();
    if(saat){saat.textContent=n.toLocaleTimeString('tr-TR',{timeZone:'Europe/Istanbul',hour:'2-digit',minute:'2-digit',second:'2-digit'})+' TSİ'}
    if(ts&&yas){var dk=Math.max(0,Math.round((n-ts)/60000));yas.textContent=dk<1?'az önce':dk+' dk önce';
      if(nokta){nokta.classList.toggle('eski',dk>30);nokta.lastChild.textContent=dk>30?' ESKİ VERİ':' CANLI'}}}
  tik();setInterval(tik,1000);
  var y=parseInt(document.body.dataset.yenile||'0',10);
  if(y>0){try{var sy=sessionStorage.getItem('kr_scroll');if(sy){window.scrollTo(0,+sy);sessionStorage.removeItem('kr_scroll')}}catch(e){}
    setTimeout(function(){try{sessionStorage.setItem('kr_scroll',window.scrollY)}catch(e){}location.reload()},y*1000)}
})();
"""

FONT = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">')


def _e(x) -> str:
    return html.escape(str(x))


def _sinif(r):
    if r is None:
        return "notr"
    return "iyi" if r < 40 else ("orta" if r < 60 else "kotu")


def _karar(r, n_sinyal):
    if r is None or n_sinyal == 0:
        return "notr", "SİNYAL YOK · BEKLE"
    return {"iyi": ("iyi", "LONG İÇİN UYGUN"), "orta": ("orta", "TEMKİNLİ"), "kotu": ("kotu", "LONG'DAN UZAK DUR")}[_sinif(r)]


def _fiyat(x: float) -> str:
    return f"{x:,.2f}" if x >= 100 else (f"{x:,.4f}" if x >= 1 else f"{x:,.5f}")


def _kaynak_adi(k: str) -> str:
    if k.startswith("GradientBoost"):
        return "Yapay zekâ · Gradient Boosting"
    if k.startswith("Lojistik"):
        return "Yapay zekâ · Lojistik regresyon"
    if k.startswith("Volatilite"):
        return "Volatilite rejimi · düşüş sınırı"
    if k.startswith("Kombinasyon"):
        return "İndikatör kombinasyonu"
    return k


def _cip(kosul: str) -> str:
    b = kosul_bilgisi(kosul)
    return f'<span class="cip {b["egilim"]}" title="{_e(b["aciklama"])}">{_e(b["etiket"])}</span>'


def _baslik(metin: str, capa: str | None = None) -> str:
    bilgi = f'<a class="bilgi" href="nasil-calisir.html#{capa}" title="Bu nedir?">?</a>' if capa else ""
    return f'<div class="kart-baslik"><span>{metin}</span>{bilgi}</div>'


def _gosterge(deger, alt_yazi: str, boyut_etiket: str = "LONG RİSKİ") -> str:
    """Yarım daire risk göstergesi (0 = güvenli, 100 = riskli)."""
    def nokta(v, r):
        a = math.pi * (1 - v / 100)
        return 100 + r * math.cos(a), 105 - r * math.sin(a)

    def yay(v1, v2, renk, op):
        x1, y1 = nokta(v1, 80)
        x2, y2 = nokta(v2, 80)
        return f'<path d="M{x1:.1f} {y1:.1f} A80 80 0 0 1 {x2:.1f} {y2:.1f}" stroke="{renk}" stroke-opacity="{op}" stroke-width="14" fill="none"/>'
    parcalar = [yay(0, 39.5, "var(--iyi)", .28), yay(40.5, 59.5, "var(--orta)", .28), yay(60.5, 100, "var(--kotu)", .28)]
    if deger is not None:
        renk = {"iyi": "var(--iyi)", "orta": "var(--orta)", "kotu": "var(--kotu)"}[_sinif(deger)]
        x, y = nokta(deger, 66)
        parcalar.append(yay(0, max(0.5, deger), renk, 1))
        parcalar.append(f'<line x1="100" y1="105" x2="{x:.1f}" y2="{y:.1f}" stroke="var(--yazi)" stroke-width="3" stroke-linecap="round"/>'
                        f'<circle cx="100" cy="105" r="6" fill="var(--yazi)"/>')
        metin = f'<text x="100" y="92" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="30" font-weight="800" fill="{renk}">%{deger:g}</text>'
    else:
        metin = '<text x="100" y="92" text-anchor="middle" font-family="JetBrains Mono,monospace" font-size="30" font-weight="800" fill="var(--soluk)">—</text>'
    return (f'<div class="gosterge"><svg viewBox="0 0 200 128" role="img" aria-label="{_e(boyut_etiket)} {deger}">'
            + "".join(parcalar) + metin +
            '<text x="20" y="124" font-size="9" fill="var(--soluk2)" text-anchor="middle">0</text>'
            '<text x="180" y="124" font-size="9" fill="var(--soluk2)" text-anchor="middle">100</text>'
            f'</svg><div class="cok-kucuk" style="letter-spacing:.14em">{_e(boyut_etiket)}</div>'
            f'<div class="kucuk" style="text-align:center;margin-top:2px">{alt_yazi}</div></div>')


def _sparkline(fiyatlar: list[float]) -> str:
    if not fiyatlar or len(fiyatlar) < 2:
        return ""
    lo, hi = min(fiyatlar), max(fiyatlar)
    ara = (hi - lo) or 1
    w, h = 320, 70
    pts = [(i * w / (len(fiyatlar) - 1), h - 4 - (p - lo) / ara * (h - 8)) for i, p in enumerate(fiyatlar)]
    yol = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    renk = "var(--iyi)" if fiyatlar[-1] >= fiyatlar[0] else "var(--kotu)"
    alan = f"0,{h} " + yol + f" {w},{h}"
    return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" style="width:100%;height:70px;display:block;margin-top:12px" aria-hidden="true">'
            f'<defs><linearGradient id="g{abs(hash(yol)) % 99999}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{renk}" stop-opacity=".25"/>'
            f'<stop offset="1" stop-color="{renk}" stop-opacity="0"/></linearGradient></defs>'
            f'<polygon points="{alan}" fill="url(#g{abs(hash(yol)) % 99999})"/>'
            f'<polyline points="{yol}" fill="none" stroke="{renk}" stroke-width="1.8" vector-effect="non-scaling-stroke"/></svg>'
            f'<div class="cok-kucuk" style="display:flex;justify-content:space-between"><span>son 96 mum</span>'
            f'<span class="mono">en düşük {_fiyat(lo)} · en yüksek {_fiyat(hi)}</span></div>')


# ------------------------------------------------------------------ coin bölümü
def _dayanak_metni(c: dict) -> str:
    oz = c["risk"]["ozet"]
    satir = c["risk"]["satirlar"]
    yon_sinyal = [s for s in satir if s["tur"].startswith("Yön") and s["sinyal_var"]]
    parca = []
    kalan = c.get("gun_sonuna_kalan_saat")
    if kalan is not None and kalan < config.GUN_SONU_MIN_KALAN_SAAT:
        parca.append(f"<b>Gün sonuna {kalan * 60:.0f} dakika kaldı.</b> Bu kadar kısa sürede gün sonu tahmini anlamlı değil; "
                     "yeni günün ilk mumlarını bekle. Sonraki mum kartları hâlâ geçerli.")
    if yon_sinyal:
        en = max(yon_sinyal, key=lambda s: s["tutarlilik"])
        parca.append(f"Şu an <b>{len(yon_sinyal)} tutarlı kaynak</b> sinyal veriyor. Gün sonu long riski bunların "
                     f"tutarlılıkla ağırlıklı ortalaması: <b>%{oz['long_risk']}</b>. En güvenilir kaynak "
                     f"<b>{_e(_kaynak_adi(en['kaynak']))}</b>; geçmiş testte bu güven seviyesinde <b>%{en['tutarlilik']*100:.0f}</b> doğru çıktı.")
    else:
        parca.append("Hiçbir model veya kombinasyon şu an <b>%70 ve üzeri</b> güvenle bir yön söyleyemiyor. "
                     f"Ham yapay zekâ tahmini long riski %{_e(oz.get('ham_model_long_risk'))}, ama bu tahminin genel isabeti "
                     f"%{round((oz.get('ham_model_dogrulugu') or 0) * 100)} olduğu için karar vermeye yetmez. <b>Bu durumda beklemek de bir pozisyondur.</b>")
    md = oz.get("max_dusus") or {}
    if md:
        k, v = max(md.items(), key=lambda kv: int(kv[0].strip("%")))
        parca.append(f"Düşüş tarafında: {k} ihtimalle gün sonuna kadar fiyat <b>{v}%</b>'den fazla düşmez. Stop seviyesi için referans alınabilir.")
    if oz.get("kirimli_long_risk") is not None:
        parca.append(f"Genel piyasa puan kırımları da hesaba katılırsa risk <b>%{oz['kirimli_long_risk']}</b> olur (sadece bilgi).")
    return " ".join(parca)


def _sinyal_haritasi(aktif: list[str]) -> str:
    gruplar: dict[str, list[tuple[str, dict]]] = {}
    say = {"boga": 0, "ayi": 0, "asiri": 0, "notr": 0}
    for k in aktif:
        b = kosul_bilgisi(k)
        gruplar.setdefault(b["grup"], []).append((k, b))
        say[b["egilim"]] += 1
    toplam = max(1, say["boga"] + say["ayi"] + say["asiri"])
    denge = (f'<div class="denge"><div class="b" style="width:{100*say["boga"]/toplam:.1f}%"></div>'
             f'<div class="x" style="width:{100*say["asiri"]/toplam:.1f}%"></div>'
             f'<div class="a" style="width:{100*say["ayi"]/toplam:.1f}%"></div></div>'
             f'<div class="kucuk"><span class="iyi">● {say["boga"]} yükseliş lehine</span> · '
             f'<span class="orta">● {say["asiri"]} aşırı bölge</span> · <span class="kotu">● {say["ayi"]} düşüş lehine</span> · '
             f'{say["notr"]} nötr</div>')
    govde = "".join(
        f'<div class="grup"><h4>{_e(g)}</h4>' + "".join(_cip(k) for k, _ in gruplar[g]) + "</div>"
        for g in GRUP_SIRASI if g in gruplar)
    return (_baslik("Sinyal haritası · şu an doğru olan koşullar", "sinyal-haritasi") + denge + govde +
            '<p class="cok-kucuk" style="margin-top:12px">Bu harita sadece anlık durumu anlatır. Bir koşulun üstüne gelince ne anlama geldiğini görürsün. '
            'Tahmini, geçmişte test edilmiş kurallar ve modeller yapar.</p>')


def _risk_tablosu(c: dict) -> str:
    satirlar = c["risk"]["satirlar"]
    if not satirlar:
        return '<p class="kucuk">%70 ve üzeri tutarlılıkta risk satırı bulunamadı.</p>'
    tr = []
    for r in satirlar:
        kaynak = _e(_kaynak_adi(r["kaynak"]))
        if r.get("kosullar"):
            kaynak += '<div style="margin-top:4px">' + "".join(_cip(k) for k in r["kosullar"]) + "</div>"
        if "max_dusus" in r:
            durum = '<span class="rozet notr">SINIR</span>'
            deg = f'<td class="sayi kotu" colspan="2">max {r["max_dusus"]}%</td>'
            not_ = (f'%{r["tutarlilik"]*100:.0f} ihtimalle gün sonuna kadar fiyat <b>{abs(r["max_dusus"])}%</b>\'den fazla düşmez. '
                    f'Long açarsan stop\'u bunun biraz altına koymak mantıklı.')
        else:
            durum = '<span class="rozet iyi">SİNYAL</span>' if r["sinyal_var"] else '<span class="rozet notr">BEKLE</span>'
            deg = (f'<td class="sayi {_sinif(r["long_risk"])}">%{r["long_risk"]}</td>'
                   f'<td class="sayi {_sinif(r["short_risk"])}">%{r["short_risk"]}</td>')
            if r["sinyal_var"]:
                not_ = (f'Şimdi long açarsan gün sonunda zararda olma ihtimali <b>%{r["long_risk"]}</b>. '
                        f'Bu kaynak geçmiş testte bu güvendeyken {r["test_n"]} örneğin %{r["tutarlilik"]*100:.0f}\'inde doğru çıktı.')
            else:
                not_ = (f'Model şu an bu tutarlılık için gereken güven eşiğinde değil. '
                        f'%{r["long_risk"]} sadece bilgi amaçlı, karar için kullanma.')
        tr.append(f'<tr class="{"" if r["sinyal_var"] else "pasif"}"><td class="etk-hucre">{_e(r["etiket"])}</td>'
                  f'<td><div class="tut"><div class="cubuk"><span style="width:{max(0, (r["tutarlilik"]-0.5)*200):.0f}%"></span></div>'
                  f'<span class="mono">%{r["tutarlilik"]*100:.1f}</span></div></td><td class="sayi">{r["test_n"]}</td><td>{durum}</td>{deg}'
                  f'<td style="min-width:260px">{kaynak}<div class="satir-not">{not_}</div></td></tr>')
    return ('<div class="tablo-sar"><table><thead><tr><th>Etiket</th><th>Tutarlılık</th><th class="sayi">Test n</th><th>Durum</th>'
            '<th class="sayi">Long risk</th><th class="sayi">Short risk</th><th>Kaynak ve anlamı</th></tr></thead><tbody>'
            + "".join(tr) + "</tbody></table></div>")


def _kural_karti(r: dict, aralik: str, sembol: str | None = None) -> str:
    yon = 1 if r["yon"].startswith("YESIL") else 0
    yukselis, hedef = hedef_metni(r["hedef"], yon, aralik)
    sinif = "iyi" if yukselis else "kotu"
    n, oran = r["test_n"], r["tutarlilik"]
    isabet = round(n * oran)
    buton = (f'<a class="grafik-btn" href="grafik.html?s={_e(sembol)}_{_e(aralik)}&amp;k={_e(r["id"])}">📈 Grafikte incele</a>'
             if sembol and r.get("id") else "")
    birim = "gün" if r["hedef"] == "gun_sonu" else "bağımsız"
    return (f'<div class="kural"><div class="kural-ust"><span class="rozet {sinif}">{"▲" if yukselis else "▼"} {_e(hedef)}</span>'
            f'<span class="kural-yuzde {sinif}">%{oran*100:.0f}</span><span class="kucuk">tutarlılık · {len(r["kosullar"])} koşul</span>{buton}</div>'
            + "".join(_cip(k) for k in r["kosullar"]) +
            f'<div class="satir-not">Hiç görülmemiş test döneminde bu {len(r["kosullar"])} koşul aynı anda <b>{n}</b> kez ({birim} oluşum) görüldü, '
            f'<b>{isabet}</b>\'inde tuttu. Normalde bu oran %{r["taban_oran"]*100:.0f} · kaldıraç x{r["kaldirac_lift"]} · '
            f'eğitimde %{(r["egitim_oran"] or 0)*100:.0f} · doğrulamada %{(r["dogrulama_oran"] or 0)*100:.0f}.</div></div>')


def _coin(c: dict, kirim: dict) -> str:
    oz = c["risk"]["ozet"]
    lr = oz.get("long_risk")
    k_sinif, k_metin = _karar(lr, oz["dayanak_sayisi"])
    deg = c["degisim_24s"] or 0
    sembol = c["sembol"].replace("USDT", "")
    tek = c["teknik_ozet"]
    md = oz.get("max_dusus") or {}
    md_en = max(md.items(), key=lambda kv: int(kv[0].strip("%"))) if md else None

    hero = f"""
<div class="hero">
  <div class="kart">
    <div class="sembol">{_e(sembol)} / USDT · {_e(c['aralik'])}</div>
    <div style="margin-top:6px"><span class="fiyat">{_fiyat(c['fiyat'])}</span>
      <span class="degisim {'iyi' if deg >= 0 else 'kotu'}">{'▲' if deg >= 0 else '▼'} {deg:+.2f}%</span></div>
    <div class="cok-kucuk" style="margin-top:4px">Son kapanan mum {_e(c['son_mum_zamani'][11:16])} UTC · {c['veri_mum_sayisi']:,} mum geçmiş veri</div>
    {_sparkline(c.get('son_fiyatlar') or [])}
  </div>
  <div class="kart">
    {_baslik('Gün sonu long riski', 'risk-turleri')}
    {_gosterge(lr, f"{oz['dayanak_sayisi']} tutarlı sinyal" if lr is not None else "tutarlı sinyal yok")}
    <div style="display:flex;justify-content:center"><div class="karar {k_sinif}">{k_metin}</div></div>
  </div>
  <div class="kart karar-kart">
    {_baslik('Özet göstergeler')}
    <div class="kpi-izgara">
      <div class="kpi"><div class="e">Short riski</div><div class="d {_sinif(oz.get('short_risk'))}">{'%' + str(oz['short_risk']) if oz.get('short_risk') is not None else '—'}</div><div class="a">short açarsan zarar ihtimali</div></div>
      <div class="kpi"><div class="e">Kırım dahil</div><div class="d {_sinif(oz.get('kirimli_long_risk'))}">{'%' + str(oz['kirimli_long_risk']) if oz.get('kirimli_long_risk') is not None else '—'}</div><div class="a">genel puan %{kirim['genel_puan']:g} ile</div></div>
      <div class="kpi"><div class="e">Max düşüş</div><div class="d kotu">{(str(md_en[1]) + '%') if md_en else '—'}</div><div class="a">{_e(md_en[0]) + ' güvenle, gün sonuna kadar' if md_en else 'hesaplanamadı'}</div></div>
      <div class="kpi"><div class="e">RSI · ADX</div><div class="d">{tek['RSI']} · {tek['ADX']}</div><div class="a">Supertrend {_e(tek['Supertrend'])}</div></div>
    </div>
  </div>
</div>"""

    aktif = c["sonraki_mum"]["aktif_kurallar"]
    kural_html = "".join(_kural_karti(r, c["aralik"], c["sembol"]) for r in aktif[:8]) if aktif else (
        '<p class="kucuk">Son kapanan mumda %70+ tutarlılıkta bir kombinasyon aktif değil. '
        'Bu sık olur; tek mumun yönü büyük ölçüde rastgeledir. Sistem emin olmadığında susar.</p>')
    en_iyi: dict[str, dict] = {}
    for r in c["sonraki_mum"]["ml"]:
        a = en_iyi.get(r["model"])
        if a is None or (r["sinyal_var"], r["tutarlilik"]) > (a["sinyal_var"], a["tutarlilik"]):
            en_iyi[r["model"]] = r
    ml = ""
    for r in en_iyi.values():
        y = r["p_yukari_simdi"] >= 0.5
        durum = (f'<span class="rozet iyi">SİNYAL · %{r["tutarlilik"]*100:.0f} tutarlı</span>' if r["sinyal_var"]
                 else '<span class="rozet notr">emin değil</span>')
        ml += (f'<li><span>{_e(_kaynak_adi(r["model"]))}</span><span class="etiket-sag">'
               f'<span class="{"iyi" if y else "kotu"}">{"▲ YEŞİL" if y else "▼ KIRMIZI"} %{max(r["p_yukari_simdi"], 1-r["p_yukari_simdi"])*100:.0f}</span> {durum}</span></li>')
    ml_html = f'<ul class="liste" style="margin-bottom:12px">{ml}</ul>' if ml else ""

    kut = lambda lst: "".join(_kural_karti(r, c["aralik"], c["sembol"]) for r in lst[:20]) or '<p class="kucuk">Kural yok.</p>'  # noqa: E731
    derin_aktif = c.get("derin", {}).get("aktif", [])
    derin_lib = c["kural_kutuphanesi"].get("derin", [])
    derin_html = (
        _baslik(f"Derin tarama · %{int(config.DERIN_MIN_TUTARLILIK * 100)}+ · şu an aktif", "derin")
        + ('<p class="kucuk" style="margin-top:-4px">3-7 indikatörün ince eşiklerle aynı anda oluştuğu, hiç görülmemiş test döneminde '
           f'%{int(config.DERIN_MIN_TUTARLILIK * 100)} ve üzeri tutmuş kombinasyonlar. İşlem açarken ek teyit olarak bak.</p>')
        + ("".join(_kural_karti(r, c["aralik"], c["sembol"]) for r in derin_aktif[:10]) if derin_aktif else
           '<p class="kucuk">Son kapanan mumda %85+ derin kural aktif değil. Bu kurallar nadir oluşur; çıktığında değerlidir.</p>')
        + f'<details><summary>Tüm derin kurallar ({c["kural_sayisi"].get("derin", 0)} kural, en iyi 20) · aktif olmasalar da grafikte incelenebilir</summary>'
        f'<div style="margin-top:10px">{kut(derin_lib)}</div></details>')
    tek_ad = {"RSI": "RSI (14)", "ADX": "ADX trend gücü", "MACD_hist": "MACD histogram", "Supertrend": "Supertrend",
              "BB_%": "Bollinger %B", "ATR_%": "ATR (mum boyu %)", "EMA200_ustunde": "EMA200 üstünde", "VWAP_sapma_%": "VWAP sapması %"}
    tek_html = "".join(
        f'<div class="kpi"><div class="e">{_e(tek_ad.get(k, k))}</div><div class="d" style="font-size:16px">'
        f'{_e("Evet" if v is True else ("Hayır" if v is False else v))}</div></div>' for k, v in tek.items())

    return f"""
<section class="coin" id="{_e(c['sembol'])}">
{hero}
<div class="aciklama-kutu">{_dayanak_metni(c)}</div>
<div class="kart bolum derin-kart">{derin_html}</div>
<div class="kart bolum">{_baslik('Risk tablosu · yalnızca %70+ tutarlılık', 'tutarlilik')}{_risk_tablosu(c)}</div>
<div class="iki-sutun">
  <div class="kart">{_baslik(f"Sonraki {c['aralik']} mum · şu an aktif kombinasyonlar", 'kombinasyon')}{ml_html}{kural_html}</div>
  <div class="kart">{_sinyal_haritasi(c['aktif_kosullar'])}</div>
</div>
<div class="kart bolum">{_baslik('Teknik özet')}<div class="kpi-izgara" style="grid-template-columns:repeat(auto-fill,minmax(min(140px,45%),1fr))">{tek_html}</div>
  <details><summary>Kural kütüphanesi · sonraki mum ({c['kural_sayisi']['sonraki_mum']} kural, en iyi 20)</summary><div style="margin-top:10px">{kut(c['kural_kutuphanesi']['sonraki_mum'])}</div></details>
  <details><summary>Kural kütüphanesi · gün sonu ({c['kural_sayisi']['gun_sonu']} kural, en iyi 20)</summary><div style="margin-top:10px">{kut(c['kural_kutuphanesi']['gun_sonu'])}</div></details>
</div>
</section>"""


# ------------------------------------------------------------------ ortak iskelet
def _iskelet(baslik: str, aktif_sayfa: str, govde: str, serit: str = "", ts: str = "", yenile: int | None = None) -> str:
    menu = "".join(f'<a href="{u}" class="{"aktif" if aktif_sayfa == u else ""}">{a}</a>'
                   for u, a in (("rapor.html", "Pano"), ("nasil-calisir.html", "Nasıl çalışır?")))
    canli = ('<span class="nokta" id="nokta"><i></i> CANLI</span><span>Güncelleme: <b id="yas" class="mono">—</b></span>'
             if ts else "") + '<span id="saat" class="mono"></span>'
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#05070b">
<title>{_e(baslik)}</title>{FONT}<style>{CSS}</style></head>
<body data-ts="{_e(ts)}" data-yenile="{yenile or 0}">
<header class="ust-bar"><div class="ust-ic"><div class="marka"><span class="elmas"></span>KRİPTO RİSK TERMİNALİ<small>PRO</small></div>
<nav class="menu">{menu}</nav><div class="canli">{canli}</div></div>{serit}</header>
{govde}
<script>{JS}</script></body></html>"""


def pano_html(rapor: dict, yenile_sn: int | None = None) -> str:
    gp = rapor["genel_puan"]
    b = rapor["baglam"]
    coinler = rapor["coinler"]

    # kayan şerit
    oge = []
    for s, c in coinler.items():
        d = c["degisim_24s"] or 0
        lr = c["risk"]["ozet"].get("long_risk")
        oge.append(f'<span><b>{_e(s.replace("USDT", ""))}</b>{_fiyat(c["fiyat"])} <span class="{"iyi" if d >= 0 else "kotu"}">{d:+.2f}%</span>'
                   f' · risk <span class="{_sinif(lr)}">{"%" + str(lr) if lr is not None else "—"}</span></span>')
    dom = (b.get("dominans") or {}).get("anlik") or {}
    for k in ("btc", "eth", "xrp", "usdt", "usdc"):
        if k in dom:
            dg = ((b.get("dominans") or {}).get("degisim") or {}).get(k, {}).get("24s", 0)
            oge.append(f'<span><b>{k.upper()}.D</b>{dom[k]:.2f}% <span class="{"iyi" if dg >= 0 else "kotu"}">{dg:+.2f}</span></span>')
    fg = b.get("korku_acgozluluk")
    if fg:
        oge.append(f'<span><b>KORKU/AÇGÖZLÜLÜK</b>{fg["deger"]} · {_e(fg["sinif"])}</span>')
    oge.append(f'<span><b>GENEL PUAN</b><span class="altin">%{gp["genel_puan"]:g}</span></span>')
    for h in ((b.get("haberler") or {}).get("onemli") or [])[:6]:
        oge.append(f'<span><b class="{"iyi" if h["skor"] > 0 else ("kotu" if h["skor"] < 0 else "")}">◆</b>{_e(h["baslik"][:90])}</span>')
    serit = f'<div class="serit" aria-hidden="true"><div class="serit-ic">{"".join(oge)}{"".join(oge)}</div></div>'

    # komuta paneli
    kalemler = "".join(f'<li><span>{_e(k["ad"])} <span class="cok-kucuk">{_e(k["kaynak"])}</span></span>'
                       f'<span class="etiket-sag kotu">−{k["kirim"]:g}</span></li>' for k in gp["kalemler"]) or "<li>Kırım yok</li>"
    puan_renk = "iyi" if gp["genel_puan"] >= 85 else ("orta" if gp["genel_puan"] >= 70 else "kotu")
    kart_puan = (f'<div class="kart">{_baslik("Genel piyasa puanı", "kirimlar")}<div class="dev {puan_renk}">%{gp["genel_puan"]:g}</div>'
                 f'<div class="kucuk">100 üzerinden · modellere girmez, ortamı gösterir</div><ul class="liste">{kalemler}</ul></div>')

    if fg:
        fg_s = "kotu" if fg["deger"] <= 25 else ("orta" if fg["deger"] <= 45 else ("iyi" if fg["deger"] <= 74 else "kotu"))
        kart_fg = (f'<div class="kart">{_baslik("Korku / açgözlülük", "duygu")}<div class="dev {fg_s}">{fg["deger"]}</div>'
                   f'<div class="kucuk">{_e(fg["sinif"])} · dün {fg["dun"]} · geçen hafta {_e(fg.get("hafta_once"))}</div>'
                   f'<div class="denge" style="margin-top:14px;background:linear-gradient(90deg,var(--kotu),var(--orta),var(--iyi),var(--orta),var(--kotu))">'
                   f'</div><div style="position:relative;height:10px"><span style="position:absolute;left:calc({fg["deger"]}% - 5px);top:-4px;color:var(--yazi)">▲</span></div>')
    else:
        kart_fg = f'<div class="kart">{_baslik("Korku / açgözlülük", "duygu")}<div class="dev notr">—</div>'
    olay = "".join(f'<li><span>{_e(e["ad"])}</span><span class="etiket-sag">{e["saat_kaldi"]} sa</span></li>'
                   for e in gp.get("yaklasan_olaylar", [])) or "<li class='kucuk'>48 saat içinde kayıtlı olay yok</li>"
    kart_fg += f'<div class="kart-baslik" style="margin-top:16px"><span>Yaklaşan olaylar · 48 saat</span></div><ul class="liste">{olay}</ul></div>'

    if dom:
        dd = (b.get("dominans") or {}).get("degisim") or {}
        sat = "".join(
            f'<tr><td><b>{k.upper()}.D</b></td><td class="sayi">{dom[k]:.2f}%</td>'
            f'<td class="sayi {"iyi" if dd.get(k, {}).get("24s", 0) >= 0 else "kotu"}">{dd.get(k, {}).get("24s", 0):+.2f}</td>'
            f'<td class="sayi {"iyi" if dd.get(k, {}).get("7g", 0) >= 0 else "kotu"}">{dd.get(k, {}).get("7g", 0):+.2f}</td></tr>'
            for k in ("btc", "eth", "xrp", "usdt", "usdc"))
        sat += (f'<tr><td><b>STABLE.D</b></td><td class="sayi">{dom["stable_toplam"]:.2f}%</td><td></td><td></td></tr>'
                f'<tr><td><b>OTHERS.D</b></td><td class="sayi">{dom["others"]:.2f}%</td><td></td><td></td></tr>')
        yorum = "".join(f'<li><span>{_e(y)}</span></li>' for y in b["dominans"].get("yorum", []))
        kart_dom = (f'<div class="kart">{_baslik("Dominanslar", "dominans")}<div class="tablo-sar"><table><thead><tr><th>Endeks</th>'
                    f'<th class="sayi">Pay</th><th class="sayi">24s</th><th class="sayi">7g</th></tr></thead><tbody>{sat}</tbody></table></div>'
                    f'<ul class="liste">{yorum}</ul></div>')
    else:
        kart_dom = f'<div class="kart">{_baslik("Dominanslar", "dominans")}<p class="kucuk">Dominans verisi alınamadı.</p></div>'

    vd = "".join(f'<tr><td><b>{_e(s.replace("USDT", ""))}</b></td><td class="sayi">{_e(v.get("funding_yuzde"))}%</td>'
                 f'<td class="sayi">{_e(v.get("oi_degisim_24s_yuzde"))}%</td><td class="sayi">{_e(v.get("long_short_orani"))}</td>'
                 f'<td class="sayi">{_e(v.get("taker_alis_satis"))}</td></tr>' for s, v in (b.get("vadeli") or {}).items())
    kart_vadeli = (f'<div class="kart">{_baslik("Vadeli piyasa", "vadeli")}<div class="tablo-sar"><table><thead><tr><th>Çift</th>'
                   f'<th class="sayi">Funding</th><th class="sayi">OI 24s</th><th class="sayi">L/S</th><th class="sayi">Taker</th></tr></thead>'
                   f'<tbody>{vd or "<tr><td colspan=5 class=kucuk>veri yok</td></tr>"}</tbody></table></div>'
                   f'<p class="cok-kucuk">Funding pozitif ve yüksekse longlar kalabalık, ani düşüşte likidasyon zinciri riski var.</p></div>')

    sekmeler = "".join(
        f'<button class="sekme" role="tab" data-hedef="{_e(s)}"><b>{_e(s.replace("USDT", ""))}</b>'
        f'<span class="mono {_sinif(c["risk"]["ozet"].get("long_risk"))}">'
        f'{"%" + str(c["risk"]["ozet"]["long_risk"]) if c["risk"]["ozet"].get("long_risk") is not None else "—"}</span></button>'
        for s, c in coinler.items())

    hb = b.get("haberler") or {}
    haber = "".join(f'<li><span class="skor {"iyi" if h["skor"] > 0 else ("kotu" if h["skor"] < 0 else "notr")}">{h["skor"]:+d}</span>'
                    f'<span>{_e(h["baslik"])} <span class="cok-kucuk">{_e(h["kaynak"])}</span></span></li>' for h in hb.get("onemli", []))
    hatalar = "".join(f"<li><span>{_e(k)}: {_e(str(v)[:160])}</span></li>" for k, v in (b.get("hatalar") or {}).items())

    govde = f"""<main>
<div class="izgara-4">{kart_puan}{kart_fg}{kart_dom}{kart_vadeli}</div>
<div class="sekmeler" role="tablist">{sekmeler}</div>
{"".join(_coin(c, gp) for c in coinler.values())}
<div class="kart bolum">{_baslik(f"Haber akışı · son 24 saat · {hb.get('adet', 0)} başlık · skor {hb.get('toplam_skor', 0)}", 'haberler')}
<ul class="liste haber">{haber or "<li class=kucuk>haber alınamadı</li>"}</ul></div>
{f'<div class="kart bolum">{_baslik("Veri kaynağı uyarıları")}<ul class="liste kucuk">{hatalar}</ul></div>' if hatalar else ''}
</main>
<footer>{_e(rapor['uyari'])} · Her şeyin nasıl hesaplandığını <a href="nasil-calisir.html">Nasıl çalışır?</a> sayfasında bulabilirsin.</footer>"""
    return _iskelet("Kripto Risk Terminali", "rapor.html", govde, serit, rapor["olusturma"], yenile_sn)


# ------------------------------------------------------------------ nasıl çalışır
def nasil_calisir_html() -> str:
    def ind_tablo():
        satir = []
        for aile, (grup, ad, ne, durumlar) in AILELER.items():
            d = "".join(f'<span class="cip {eg}">{_e(et)}</span>' for et, eg in durumlar.values())
            satir.append(f"<tr><td><b>{_e(ad)}</b><div class='cok-kucuk'>{_e(grup)}</div></td><td>{_e(ne)}</td><td>{d}</td></tr>")
        return ("<div class='tablo-sar'><table><thead><tr><th>Gösterge</th><th>Ne ölçer?</th><th>Hangi durumlara bakılır</th></tr></thead><tbody>"
                + "".join(satir) + "</tbody></table></div>")

    def form_tablo():
        satir = "".join(f'<tr><td><span class="cip {eg}">{_e(et)}</span></td><td>{_e(ne)}</td></tr>' for et, eg, ne in FORMASYONLAR.values())
        return f"<div class='tablo-sar'><table><thead><tr><th>Formasyon</th><th>Anlamı</th></tr></thead><tbody>{satir}</tbody></table></div>"

    kirim_tablo = "".join(f"<tr><td>{a}</td><td class='sayi kotu'>−{k}</td><td>{n}</td></tr>" for a, k, n in [
        ("Manuel kırımlar (ör. İran savaşı)", "senin belirlediğin", "ayarlar/olaylar.json dosyasından. Savaş, regülasyon gibi modelin bilemeyeceği şeyler."),
        ("24 saat içinde yüksek etkili olay (FOMC, CPI)", "8", "Faiz kararı ve enflasyon verisi saatlerinde fiyat sert ve yönsüz hareket edebilir."),
        ("24 saat içinde orta etkili olay (NFP vb.)", "4", ""),
        ("Aşırı korku (F&G ≤ 20) veya aşırı açgözlülük (≥ 80)", "5", "Duygu uçlarda olduğunda ani dönüşler sıklaşır."),
        ("Aşırı funding (|oran| ≥ %0,05)", "4", "Kaldıraçlı pozisyonlar tek tarafa yığılmış; likidasyon zinciri riski."),
        ("Açık pozisyon (OI) 24 saatte %10+ arttı", "3", "Piyasaya hızla kaldıraç giriyor."),
        ("Stablecoin dominansı yükseliyor (+0,15 puan)", "4", "Para kriptodan nakde kaçıyor."),
        ("Haber akışı belirgin olumsuz", "4", "Son 24 saatteki başlıkların ortalama skoru −0,5'in altında."),
        ("Yoğun jeopolitik başlık (manuel kırım yoksa)", "3", "Savaş, füze, yaptırım gibi kelimeler 3+ başlıkta geçiyor."),
        ("Hafta sonu", "2", "Kurumsal katılım ve likidite düşük; fitiller uzar."),
    ])

    toc = [("ozet", "1. Tek cümlede sistem"), ("akis", "2. Adım adım akış"), ("veri", "3. Hangi veriler?"),
           ("indikatorler", "4. İndikatörler"), ("formasyonlar", "5. Formasyonlar"), ("baglam", "6. Bağlam koşulları"),
           ("kombinasyon", "7. Kombinasyon arama"), ("tutarlilik", "8. Tutarlılık nasıl ölçülür?"),
           ("derin", "8b. Derin tarama ve grafik"), ("risk-turleri", "9. Risk türleri"), ("sinyal-haritasi", "10. Sinyal haritası"), ("kirimlar", "11. Genel puan ve kırımlar"),
           ("dominans", "12. Dominanslar"), ("duygu", "13. Duygu ve vadeli"), ("haberler", "14. Haberler"),
           ("okuma", "15. Panoyu okuma rehberi"), ("sinirlar", "16. Sınırlar ve uyarılar"), ("sozluk", "17. Sözlük")]
    toc_html = "".join(f'<a href="#{i}">{_e(a)}</a>' for i, a in toc)

    def bol(i, baslik, icerik):
        return f'<section id="{i}" class="kart"><h2>{baslik}</h2>{icerik}</section>'

    s = []
    s.append(bol("ozet", "1. Tek cümlede sistem", """
<p>Sistem her 15 dakikada bir BTC, ETH ve XRP'nin grafiğine yüzlerce açıdan bakar. Geçmişte <b>“şu koşullar bir arada olduğunda ne oldu?”</b>
sorusunu sorar. Cevabı, hiç görmediği bir dönemde de tutan kuralları ve modelleri saklar. Bugün o koşullar oluşmuşsa sana
<b>gün sonu riskini</b> ve bu riskin <b>ne kadar güvenilir olduğunu</b> (tutarlılık) söyler.</p>
<p>Emin olmadığında <b>susar</b>. “Tutarlı sinyal yok” görmek normaldir ve bilinçli bir tasarımdır: Zayıf bir tahmin vermek, hiç vermemekten daha tehlikelidir.</p>"""))
    s.append(bol("akis", "2. Adım adım akış", """
<div class="akis">
<div class="adim"><b>1 · Veri</b>Binance'ten ~540 günlük 15m mumlar (BTC, ETH, XRP). Dominans, korku endeksi, funding ve haberler.</div><div class="ok">→</div>
<div class="adim"><b>2 · Koşullar</b>Her mum için ~140 evet/hayır sorusu: “RSI 30-45 arası mı?”, “Supertrend boğa mı?”, “Yutan boğa var mı?”…</div><div class="ok">→</div>
<div class="adim"><b>3 · Arama</b>Bu koşulların 1-5'li kombinasyonları ve yapay zekâ modelleri denenir.</div><div class="ok">→</div>
<div class="adim"><b>4 · Sınav</b>Bulunanlar hiç görülmemiş son döneme uygulanır. %70 altı elenir.</div><div class="ok">→</div>
<div class="adim"><b>5 · Risk</b>Şu an aktif olanlardan gün sonu riski ve tutarlılığı hesaplanır, panoya yazılır.</div>
</div>
<p class="kucuk">Canlı modda bu döngü her mum kapanışından ~20 saniye sonra tekrarlanır. Kural arama ağır olduğu için günde bir kez yapılır; aradaki turlarda mevcut kurallar şimdiki mumla kontrol edilir. Yapay zekâ modelleri her turda yeniden eğitilir.</p>"""))
    s.append(bol("veri", "3. Hangi veriler?", """
<div class="tablo-sar"><table><thead><tr><th>Veri</th><th>Kaynak</th><th>Ne için?</th></tr></thead><tbody>
<tr><td>15m mumlar (açılış, yüksek, düşük, kapanış, hacim, taker alış)</td><td>Binance spot</td><td>Tüm indikatörler, formasyonlar, modeller</td></tr>
<tr><td>10m mumlar</td><td>Binance 5m mumlarından birleştirilir</td><td>İstersen <span class="mono">--aralik 10m</span></td></tr>
<tr><td>1 saatlik ve 4 saatlik görünüm</td><td>15m mumlardan üretilir</td><td>Büyük resim (üst zaman dilimi)</td></tr>
<tr><td>BTC.D, ETH.D, XRP.D, USDT.D, USDC.D, toplam piyasa</td><td>CoinGecko</td><td>Para nereye akıyor?</td></tr>
<tr><td>Korku/Açgözlülük endeksi</td><td>alternative.me</td><td>Piyasa psikolojisi</td></tr>
<tr><td>Funding, açık pozisyon, long/short oranı, taker oranı</td><td>Binance Futures</td><td>Kaldıraç ve kalabalık pozisyonlar</td></tr>
<tr><td>Haber başlıkları</td><td>CoinDesk, Cointelegraph, Decrypt</td><td>Olumlu/olumsuz akış, jeopolitik</td></tr>
<tr><td>Olay takvimi ve manuel kırımlar</td><td>ayarlar/olaylar.json (sen düzenlersin)</td><td>FOMC, CPI, savaş gibi şeyler</td></tr>
</tbody></table></div>
<p class="kucuk">Henüz kapanmamış mum hiçbir hesaba girmez. Böylece yarım mum yanıltıcı sinyal vermez.</p>"""))
    s.append(bol("indikatorler", "4. İndikatörler", "<p>Her gösterge birkaç “durum”a bölünür. Renkler: "
                 '<span class="cip boga">yükseliş lehine</span><span class="cip ayi">düşüş lehine</span>'
                 '<span class="cip asiri">aşırı bölge (dönüş olabilir)</span><span class="cip notr">nötr</span></p>' + ind_tablo()))
    s.append(bol("formasyonlar", "5. Mum ve grafik formasyonları", "<p>Klasik Japon mum formasyonları ve basit grafik yapıları otomatik tespit edilir. "
                 "Pivot tabanlı formasyonlar (ikili dip/tepe, yükselen dipler) 2 mum gecikmeyle doğrulanır, böylece geleceğe bakılmaz.</p>" + form_tablo()))
    s.append(bol("baglam", "6. Bağlam koşulları", """
<ul class="liste">
<li><span><b>Üst zaman dilimi:</b> 1 saatlik ve 4 saatlik grafikte trend (EMA21/50), RSI aşırılığı, Supertrend. 15m sinyali büyük trendle aynı yöndeyse daha anlamlıdır.</span></li>
<li><span><b>Diğer coinler:</b> BTC analiz edilirken ETH ve XRP'nin son 1 saatlik hareketi, RSI'ı, BTC'den güçlü olup olmadığı ve BTC paritesi (ETH/BTC) koşul olarak eklenir. ETH analizinde ise BTC ve XRP eklenir.</span></li>
<li><span><b>Seans:</b> Asya (03-11 TSİ), Avrupa (11-16), ABD (16-24), geç ABD (00-03). ABD açılışı gibi saatlerde davranış değişir.</span></li>
<li><span><b>Hafta sonu:</b> Düşük likidite.</span></li>
</ul>"""))
    s.append(bol("kombinasyon", "7. Kombinasyon arama", """
<p>Senin örneğindeki gibi: <i>“1. indikatör X, 2. indikatör Y … 5. indikatör Z iken sonraki mum hep yeşil gelmiş.”</i></p>
<p>~140 koşulun tüm 5'li kombinasyonları milyarlarca eder; hepsini denemek imkânsız. Bu yüzden <b>ışın araması (beam search)</b> yapılır:</p>
<ol><li>Tek tek her koşul denenir, en umut verici 250'si tutulur.</li>
<li>Her birine ikinci bir koşul eklenir. Ekleme oranı iyileştiriyorsa en iyi 250'si tutulur.</li>
<li>Bu 5 koşula kadar sürer. Aynı göstergenin iki durumu (ör. iki farklı RSI bandı) aynı kombinasyona girmez.</li></ol>
<p>İki hedef ayrı ayrı aranır: <b>sonraki mumun rengi</b> ve <b>gün sonu kapanışının şimdiki fiyattan yüksek olup olmadığı</b>. Her iki yön (yeşil ve kırmızı) de aranır.</p>
<div class="ornek">Örnek kural kartı:
▲ YEŞİL %78   sonraki 15m mum
  RSI 30-45 · MACD negatif ama toparlanıyor · 4 saatlik trend yukarı · Fiyat VWAP'ın altında · Avrupa seansı
  Test döneminde bu 5 koşul aynı anda 46 kez oluştu, 36'sında sonraki mum yeşil geldi.
  Normalde bu oran %51 · kaldıraç x1.53</div>
<p class="kucuk"><b>Kaldıraç (lift)</b>: kuralın oranının normal orana bölümü. x1.5 = normalden %50 daha sık. <b>p</b> değeri ise bu sonucun şans eseri çıkma ihtimalidir; küçük olması iyidir.</p>"""))
    s.append(bol("tutarlilik", "8. Tutarlılık nasıl ölçülür?", """
<p>En önemli kısım burası. Geçmişe bakıp kural bulmak kolaydır; zor olan, <b>kuralın gelecekte de tutması</b>dır. Bu yüzden veri kronolojik olarak üçe bölünür:</p>
<div class="bolme"><div style="flex:60;background:var(--mavi)">%60 EĞİTİM · kurallar aranır</div>
<div style="flex:20;background:var(--orta)">%20 DOĞRULAMA</div><div style="flex:20;background:var(--iyi)">%20 TEST</div></div>
<ul class="liste">
<li><span><b>Eğitim:</b> Kurallar burada bulunur. Burada %70+ değilse aday bile olmaz.</span></li>
<li><span><b>Doğrulama:</b> Adaylar burada elenir. Sadece eğitim verisine “ezber” yapan kurallar burada düşer.</span></li>
<li><span><b>Test:</b> Hiç dokunulmamış son dönem. Panoda gördüğün <b>tutarlılık her zaman bu dönemdeki isabet oranıdır.</b> %70 altındaki hiçbir şey gösterilmez.</span></li>
</ul>
<p><b>Gün sonu hedefinde özel kural:</b> Aynı günün 15m mumlarının hepsi aynı gün sonu kapanışına bakar. Bu yüzden 30 mumu 30 ayrı örnek saymak oranı yapay olarak şişirir. Sistem her günden yalnızca <b>ilk sinyali</b> sayar; test n = farklı gün sayısıdır. En az 20 farklı gün gerekir. Gün sonuna 1 saatten az kalmış mumlar gün sonu hesabına hiç girmez; çünkü günün son mumunda “gün sonu” o mumun kendisidir ve sonuç önceden bellidir. Bu kural olmasaydı model bunu ezberleyip sahte %95+ isabet gösterirdi.</p>
<p><b>Yapay zekâ modellerinde:</b> Model önce geçmişin %40'ıyla eğitilir, sonraki dilimi tahmin eder. Sonra pencere ileri kayar (walk-forward). Güven eşiği ilk dilimlerde seçilir, tutarlılık en son dilimde ölçülür.</p>
<p><b>Sağlama:</b> Sistem tamamen rastgele üretilmiş sahte fiyat verisiyle test edildi ve <b>sıfır</b> kural buldu; yapay zekâ isabeti %50'de kaldı. Yani rastgelelikten sahte formasyon üretmiyor ve geleceğe bakmıyor.</p>"""))
    s.append(bol("derin", "8b. Derin tarama (%85+) ve grafikte inceleme", """
<p>Normal taramadan daha derin ve daha seçici bir arama. “A indikatörü 30 civarındayken, B 20 civarındayken … X 10 civarındayken sonraki 3 mum artı gelmiş” türünden kuralları arar.</p>
<ul class="liste">
<li><span><b>İnce eşikler:</b> RSI 5'er puanlık aralıklarla (35-40, 40-45 …), Stochastic/MFI/Williams %R 10'ar puanlık, CCI 50'şer, ADX 5'er puanlık aralıklarla. Bollinger %B, MACD gücü, EMA21'e uzaklık, VWAP sapması, 4 saatlik getiri, hacim ve alıcı payı da dar aralıklara bölünür. Toplam ~280 koşul taranır.</span></li>
<li><span><b>3 ile 7 koşul</b> aynı anda: tek ya da iki indikatörlü basit kurallar burada gösterilmez.</span></li>
<li><span><b>Hedefler:</b> sonraki mum · 2/3/4/8 mum sonra fiyat yukarıda mı aşağıda mı · sonraki 2 veya 3 mumun hepsi yeşil mi / hepsi kırmızı mı.</span></li>
<li><span><b>Eşik %85:</b> Eğitimde %85+, doğrulamada %80+ ve hiç görülmemiş testte <b>%85+</b> tutmayan kural gösterilmez. Her dönemde en az 30 / 10 / 15 bağımsız oluşum gerekir.</span></li>
<li><span><b>Bağımsızlık:</b> “3 mum sonra” hedefinde art arda gelen 3 sinyal aynı mumları paylaşır. Bu yüzden birbirine 3 mumdan yakın tekrarlar tek sayılır. Oranlar şişirilmez.</span></li>
<li><span><b>Sağlama:</b> 540 günlük tamamen rastgele fiyat verisinde derin tarama <b>0</b> kural buldu.</span></li>
</ul>
<p><b>Grafikte incele:</b> Her kuralın yanındaki 📈 butonu ayrı bir sayfa açar:</p>
<ul class="liste">
<li><span>Mum grafiğinde kuralın <b>tüm geçmişteki</b> oluşumları işaretlidir: yeşil ok = tuttu, kırmızı daire = tutmadı, altın kare = şu an aktif.</span></li>
<li><span>Tüm zamanlar / eğitim / doğrulama / test isabet oranları ve tuttuğunda ortalama ne kadar hareket ettiği.</span></li>
<li><span><b>Birikimli isabet çizgisi:</b> Çizgi zaman içinde yatay ve yüksek kalıyorsa kural her dönemde tutmuştur. Sona doğru düşüyorsa kural zayıflıyor olabilir.</span></li>
<li><span>Oluşum tablosunda bir satıra tıklayınca grafik o ana gider. Giriş, çıkış fiyatı ve değişim yazar.</span></li>
</ul>
<p class="kucuk">Derin kurallar nadir oluşur. Çoğu zaman “şu an aktif derin kural yok” görürsün. Aktif olduğunda, işlem açarken ek teyit olarak kullan.</p>"""))
    s.append(bol("risk-turleri", "9. Risk türleri", """
<div class="tablo-sar"><table><thead><tr><th>Ad</th><th>Ne söyler?</th><th>Tutarlılık neyi ölçer?</th></tr></thead><tbody>
<tr><td><b>Long riski</b></td><td>Şimdi long açarsan gün sonunda (TSİ 23:59) zararda olma ihtimali.</td><td>Model bu güvendeyken gün sonu yönünü ne sıklıkla doğru bildi.</td></tr>
<tr><td><b>Short riski</b></td><td>Şimdi short açarsan zararda olma ihtimali (= 100 − long riski).</td><td>Aynı.</td></tr>
<tr><td><b>Max düşüş</b></td><td>Gün sonuna kadar fiyatın şimdiden en fazla ne kadar aşağı sarkacağı. Volatilite rejimi (düşük/orta/yüksek) ve güne kalan saate göre hesaplanır.</td><td>Bu sınırın test döneminde aşılmama oranı. %90 = 10 seferin 9'unda sınır tuttu.</td></tr>
<tr><td><b>Kırım dahil long riski</b></td><td>Long riski + genel puan kırımlarının etkisi: risk + kırım × (100 − risk) / 100.</td><td>Ölçülmez. Sadece bilgi amaçlıdır.</td></tr>
</tbody></table></div>
<p><b>Risk-A, Risk-B, …</b> satırları tutarlılığa göre sıralanır. Her satırın kaynağı farklıdır:</p>
<ul class="liste">
<li><span><b>Yapay zekâ · Gradient Boosting:</b> Yüzlerce karar ağacının birleşimi. Göstergeler arasındaki karmaşık ilişkileri yakalar.</span></li>
<li><span><b>Yapay zekâ · Lojistik regresyon:</b> Daha basit, doğrusal bir model. Aşırı uyuma daha dayanıklıdır.</span></li>
<li><span><b>İndikatör kombinasyonu:</b> Kombinasyon aramasında bulunan ve şu an aktif olan bir gün sonu kuralı.</span></li>
<li><span><b>Volatilite rejimi · düşüş sınırı:</b> İstatistiksel düşüş sınırı.</span></li>
</ul>
<p>Aynı model birden fazla satırda görünebilir. Örneğin Gradient Boosting <b>%90 seviyesinde</b> sadece çok emin olduğunda sinyal verir (nadiren), <b>%70 seviyesinde</b> daha sık sinyal verir. <span class="rozet iyi">SİNYAL</span> modelin şu an o eşiği geçtiğini, <span class="rozet notr">BEKLE</span> geçmediğini gösterir.</p>
<p><b>Ana gösterge</b> (yarım daire), sinyal veren satırların tutarlılıkla ağırlıklı ortalamasıdır. Karar etiketi: <span class="iyi">%40 altı “Long için uygun”</span>, <span class="orta">40-60 “Temkinli”</span>, <span class="kotu">60 üstü “Long'dan uzak dur”</span>.</p>"""))
    s.append(bol("sinyal-haritasi", "10. Sinyal haritası", """
<p>Son kapanan mumda doğru olan tüm koşulların gruplanmış hâlidir (Trend, Momentum, Hacim, Volatilite, Formasyon, Üst zaman dilimi, Diğer coinler, Zaman). Üstteki renkli çubuk kaç koşulun yükseliş, kaç koşulun düşüş lehine olduğunu gösterir.</p>
<p><b>Dikkat:</b> Bu harita bir tahmin değil, bir fotoğraftır. “12 yeşil 5 kırmızı” görmek tek başına yükseliş demek değildir. Tahmini, test edilmiş kurallar ve modeller yapar. Harita, riskin <i>neden</i> öyle çıktığını sezmen içindir.</p>"""))
    s.append(bol("kirimlar", "11. Genel piyasa puanı ve kırımlar", f"""
<p>100'den başlar, her risk unsuru puan düşürür. Örneğin İran savaşı −10 ise genel puan %90 olur. <b>Bu puan modellere girmez.</b>
Sebebi şu: Savaş gibi olaylar geçmiş veride yeterince yok ve ne zaman biteceği belli değil. Modele sokmak istatistiği bozar. Ama senin görmen önemli; bu yüzden ayrı gösterilir.</p>
<div class="tablo-sar"><table><thead><tr><th>Unsur</th><th class="sayi">Kırım</th><th>Neden?</th></tr></thead><tbody>{kirim_tablo}</tbody></table></div>
<p><b>Manuel kırım ekleme:</b> <span class="mono">ayarlar/olaylar.json</span> içinde <span class="mono">genel_puan_kirimlari</span> listesine
<span class="mono">{{"ad": "...", "kirim_yuzde": 5, "aktif": true}}</span> ekle. Kapatmak için <span class="mono">"aktif": false</span>. Claude Code'da <span class="mono">/btc-rapor kirim: Fed belirsizliği 5</span> yazarak da ekleyebilirsin.</p>"""))
    s.append(bol("dominans", "12. Dominanslar nasıl okunur?", """
<div class="tablo-sar"><table><thead><tr><th>Durum</th><th>Anlamı</th></tr></thead><tbody>
<tr><td>USDT.D + USDC.D yükseliyor</td><td>Yatırımcılar kriptodan nakde (stablecoin) geçiyor. <span class="kotu">Long için olumsuz.</span></td></tr>
<tr><td>USDT.D + USDC.D düşüyor</td><td>Nakit kriptoya giriyor. <span class="iyi">Long için olumlu.</span></td></tr>
<tr><td>BTC.D ↑ ve toplam piyasa ↓</td><td>Altcoinlerden BTC'ye kaçış. ETH ve XRP için olumsuz.</td></tr>
<tr><td>BTC.D ↑ ve toplam piyasa ↑</td><td>BTC liderliğinde ralli.</td></tr>
<tr><td>BTC.D ↓ ve toplam piyasa ↑</td><td>Altcoin sezonu sinyali. ETH ve XRP lehine.</td></tr>
<tr><td>ETH.D / XRP.D ↑</td><td>O coine özel ilgi artıyor.</td></tr>
</tbody></table></div>
<p class="kucuk">CoinGecko'nun ücretsiz servisi geçmiş dominans vermez. 24 saatlik değişim ilk çalıştırmalarda 5 coinin market cap payından <i>tahmin</i> edilir. Program düzenli çalıştıkça kendi kayıtlarından <b>gerçek</b> değişimi kullanır; panoda hangisinin kullanıldığı yazar.</p>"""))
    s.append(bol("duygu", "13. Duygu ve vadeli piyasa", """
<ul class="liste">
<li><span><b>Korku/Açgözlülük (0-100):</b> 0-25 aşırı korku, 75-100 aşırı açgözlülük. Uçlar genelde dönüş öncesi görülür. ≤20 veya ≥80 ise 5 puan kırım.</span></li>
<li id="vadeli"><span><b>Funding:</b> Vadeli işlemlerde longların shortlara (pozitifse) ödediği ücret. Yüksek pozitif = longlar kalabalık; ani düşüşte zincirleme likidasyon olabilir.</span></li>
<li><span><b>Açık pozisyon (OI):</b> Açıktaki toplam vadeli pozisyon. Hızlı artış = piyasaya kaldıraç giriyor.</span></li>
<li><span><b>Long/Short oranı:</b> Hesapların ne kadarının long olduğu. 1'in çok üstündeyse kalabalık long.</span></li>
<li><span><b>Taker alış/satış:</b> Piyasa emriyle alanların satanlara oranı. 1 üstü agresif alım.</span></li>
</ul>"""))
    s.append(bol("haberler", "14. Haberler", """
<p>Son 24 saatin başlıkları üç kaynaktan çekilir ve anahtar kelimeyle puanlanır. Olumlu kelimeler: approval, inflow, rally, rate cut, ceasefire… Olumsuz kelimeler: hack, war, ban, crash, lawsuit, sanction…
Puan basit ve hızlıdır; nüansı kaçırabilir. Bu yüzden modellere girmez, sadece kırım ve bilgi için kullanılır. Jeopolitik kelimeler 3+ başlıkta geçiyorsa sana manuel kırım eklemeni hatırlatır.</p>"""))
    s.append(bol("okuma", "15. Panoyu okuma rehberi", """
<ol>
<li><b>Üstteki genel puana bak.</b> %90 üstü normal ortam. %70-85 arasında pozisyon boyutunu küçült. %70 altında çok dikkatli ol.</li>
<li><b>Coin sekmesini seç</b> (BTC / ETH / XRP).</li>
<li><b>Yarım daire göstergeye bak.</b> Gri “—” ve “SİNYAL YOK · BEKLE” görüyorsan sistem emin değil; işlem açmak zorunda değilsin.</li>
<li><b>Altın çizgili kutudaki açıklamayı oku.</b> Riskin neye dayandığını düz cümleyle anlatır.</li>
<li><b>Risk tablosuna bak.</b> Önce SİNYAL veren satırlar önemli. Tutarlılık yüksek ve test n büyükse (gün sonu için 30+, sonraki mum için 50+) daha güvenilir.</li>
<li><b>Max düşüş</b> değerini stop seviyesi için kullan. %90 satırı “10 günün 9'unda fiyat bundan fazla düşmedi” demektir.</li>
<li><b>Sonraki mum kartları</b> kısa vadeli giriş zamanlaması için. Gün sonu riskiyle aynı yöndeyse daha anlamlı.</li>
</ol>
<div class="ornek">Örnek okuma:
Genel puan %88 (İran −10, hafta sonu −2)
BTC long riski %31 → LONG İÇİN UYGUN   (3 tutarlı sinyal, en iyisi %84)
Max düşüş: %90 güvenle −1.8%
Sonraki mum: ▲ YEŞİL %78 (n=46)

→ Yorum: İstatistik long lehine. Ortam riskli olduğu için normalden küçük pozisyon,
  stop −1.8%'in biraz altına. Karar yine senin.</div>"""))
    s.append(bol("sinirlar", "16. Sınırlar ve uyarılar", """
<ul class="liste">
<li><span><b>Geçmiş, geleceğin garantisi değildir.</b> Tutarlılık test dönemine aittir. Piyasa rejimi değişirse (ör. yeni bir savaş, ETF onayı) oranlar düşebilir.</span></li>
<li><span><b>Tek mum çoğunlukla gürültüdür.</b> Bu yüzden sistem sık sık “sinyal yok” der. Bu bir hata değil, dürüstlüktür.</span></li>
<li><span><b>Test n küçükse temkinli ol.</b> 20 örnekte %80 ile 200 örnekte %80 aynı güven değildir.</span></li>
<li><span><b>Çok sayıda kural denendiği için</b> bazıları şans eseri iyi görünebilir. Üç aşamalı eleme ve p değeri bunu azaltır, sıfırlamaz.</span></li>
<li><span><b>Haber ve olay etkisi</b> modellere girmez. Ani haber anlarında hiçbir teknik model güvenilir değildir.</span></li>
<li><span><b>Bu araç yatırım tavsiyesi değildir.</b> İşlem kararı ve risk yönetimi sana aittir.</span></li>
</ul>"""))
    s.append(bol("sozluk", "17. Sözlük", """
<div class="tablo-sar"><table><tbody>
<tr><td><b>Long / Short</b></td><td>Yükselişe / düşüşe pozisyon almak.</td></tr>
<tr><td><b>Tutarlılık</b></td><td>Hiç görülmemiş test döneminde doğru çıkma oranı.</td></tr>
<tr><td><b>Test n</b></td><td>Tutarlılığın kaç örnekten hesaplandığı (gün sonu için farklı gün sayısı).</td></tr>
<tr><td><b>Kaldıraç (lift)</b></td><td>Kuralın oranı ÷ normal oran. 1'den büyükse kural bilgi taşıyor.</td></tr>
<tr><td><b>p değeri</b></td><td>Sonucun tamamen şans eseri çıkma ihtimali. 0,05 altı anlamlı kabul edilir.</td></tr>
<tr><td><b>Walk-forward</b></td><td>Modeli sadece geçmişle eğitip bir sonraki dönemi tahmin ettirerek ileri kaydırma.</td></tr>
<tr><td><b>Beam search</b></td><td>Her adımda sadece en iyi adayları tutarak kombinasyon arama yöntemi.</td></tr>
<tr><td><b>ATR</b></td><td>Ortalama mum boyu; volatilitenin ölçüsü.</td></tr>
<tr><td><b>Dominans (.D)</b></td><td>Bir coinin toplam kripto piyasa değeri içindeki payı.</td></tr>
<tr><td><b>Funding</b></td><td>Vadeli işlemlerde long ve short taraf arasında periyodik ödeme.</td></tr>
<tr><td><b>OI</b></td><td>Open interest, açık pozisyon toplamı.</td></tr>
<tr><td><b>TSİ</b></td><td>Türkiye saati (UTC+3). Gün sonu TSİ 23:59 kabul edilir.</td></tr>
</tbody></table></div>"""))

    govde = f"""<main><div class="doc"><nav class="toc">{toc_html}</nav><div>
<h1>Nasıl çalışır?</h1><p class="kucuk" style="margin-bottom:20px">Panodaki her sayının nereden geldiğini, neye bakıldığını ve nasıl okunacağını adım adım anlatır.
Panodaki <span class="bilgi" style="display:inline-grid;place-items:center;width:18px;height:18px;border-radius:50%;border:1px solid var(--cizgi2)">?</span> işaretleri buradaki ilgili bölüme götürür.</p>
{"".join(s)}</div></div></main>
<footer>Bu sistem istatistiksel bir karar destek aracıdır, yatırım tavsiyesi değildir. · <a href="rapor.html">Panoya dön</a></footer>"""
    return _iskelet("Nasıl Çalışır · Kripto Risk Terminali", "nasil-calisir.html", govde)



# ------------------------------------------------------------------ grafik sayfası
GRAFIK_JS = r"""
(function(){
var OFS=10800, q=new URLSearchParams(location.search), S=q.get('s')||'', K=q.get('k')||'';
var $=function(id){return document.getElementById(id)};
function hata(m){$('icerik').innerHTML='<div class="kart"><p>'+m+'</p><p class="kucuk"><a href="rapor.html">← Panoya dön</a></p></div>'}
function esc(x){return String(x).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function tarih(t){var d=new Date((t+OFS)*1000);return d.toISOString().slice(0,16).replace('T',' ')}
function fiyat(x){return x==null?'—':(x>=100?x.toLocaleString('tr-TR',{maximumFractionDigits:2}):x.toLocaleString('tr-TR',{maximumFractionDigits:5}))}
if(!/^[A-Z0-9]+_[0-9]+m$/.test(S)){hata('Geçersiz adres.');return}
if(typeof LightweightCharts==='undefined'){hata('Grafik kütüphanesi yüklenemedi (cikti/statik klasörü eksik). Raporu yeniden üret.');return}
var sc=document.createElement('script');sc.src='veri/'+S+'.js?'+Date.now();
sc.onerror=function(){hata('Grafik verisi bulunamadı. Önce raporu üret: <span class="mono">python -m btc_tahmin rapor</span>')};
sc.onload=function(){var D=(window.KR||{})[S];if(!D){hata('Veri okunamadı.');return}var R=D.kurallar[K];
  if(!R){hata('Bu kural güncel raporda yok (kurallar her gün yeniden aranır). Panodan yeni bir kural seç.');return}ciz(D,R)};
document.head.appendChild(sc);

function ciz(D,R){
  var up=R.yukselis, sinif=up?'iyi':'kotu', BOL=['Eğitim','Doğrulama','Test','ŞU AN'];
  document.title=D.sembol.replace('USDT','')+' · '+R.hedef+' · Kural grafiği';
  var O=R.olusumlar, biten=O.filter(function(o){return o[2]>=0}), tut=biten.filter(function(o){return o[2]===1});
  function oran(a){var t=a.filter(function(o){return o[2]===1}).length;return a.length?(100*t/a.length).toFixed(0)+'%':'—'}
  function ort(a){if(!a.length)return '—';var s=0;a.forEach(function(o){s+=o[5]});return (s/a.length>=0?'+':'')+(s/a.length).toFixed(2)+'%'}
  var tutmayan=biten.filter(function(o){return o[2]===0}), aktif=O.some(function(o){return o[1]===3});
  var cips=R.kosullar.map(function(k){return '<span class="cip '+k.egilim+'" title="'+esc(k.aciklama)+'">'+esc(k.etiket)+'</span>'}).join('');
  $('icerik').innerHTML=
   '<div class="kart bolum"><div class="kart-baslik"><span>'+esc(D.sembol)+' · '+esc(D.aralik)+' · kural grafiği</span><a href="rapor.html" class="kucuk">← Panoya dön</a></div>'+
   '<div class="kural-ust"><span class="rozet '+sinif+'">'+(up?'▲ ':'▼ ')+esc(R.hedef)+'</span><span class="kural-yuzde '+sinif+'">%'+Math.round(R.tutarlilik*100)+'</span>'+
   '<span class="kucuk">test tutarlılığı · '+R.kosullar.length+' koşul'+(aktif?' · <b class="altin">ŞU AN AKTİF</b>':'')+'</span></div>'+
   '<div style="margin-top:6px">'+cips+'</div>'+
   '<p class="satir-not">Aşağıdaki grafikte bu koşulların <b>tüm geçmişte</b> aynı anda oluştuğu her an işaretli. '+
   '<span class="iyi">Yeşil ok</span> = tuttu, <span class="kotu">kırmızı daire</span> = tutmadı, <span class="altin">altın</span> = şu an aktif (sonuç bekleniyor). '+
   (R.blok>1?'Birbirine '+R.blok+' mumdan yakın tekrarlar tek sayılır (aynı mumları paylaştıkları için).':'')+' Saatler TSİ.</p></div>'+
   '<div class="izgara-4 kpi-4">'+
    kpi('Tüm zamanlar',tut.length+' / '+biten.length,'isabet '+oran(biten))+
    kpi('Eğitim · doğrulama',oran(biten.filter(function(o){return o[1]===0}))+' · '+oran(biten.filter(function(o){return o[1]===1})),'kuralın bulunduğu ve elendiği dönemler')+
    kpi('Test (hiç görülmemiş)',oran(biten.filter(function(o){return o[1]===2})),'n = '+biten.filter(function(o){return o[1]===2}).length+' · normal oran %'+Math.round(R.taban_oran*100))+
    kpi('Ortalama hareket',ort(tut)+' / '+ort(tutmayan),'tuttuğunda / tutmadığında (çıkış fiyatına kadar)')+
   '</div>'+
   '<div class="kart bolum"><div class="kart-baslik"><span>Mum grafiği · tüm oluşumlar</span>'+
   '<div class="filtre" id="filtre"><button data-f="hepsi" aria-pressed="true">Tümü</button><button data-f="test">Sadece test</button>'+
   '<button data-f="tuttu">Tuttu</button><button data-f="tutmadi">Tutmadı</button></div></div>'+
   '<div id="grafik" class="grafik-kutu"></div><p class="cok-kucuk">Tekerlekle yakınlaş, sürükleyerek kaydır. Tablodaki bir satıra tıklayınca grafik o ana gider.</p></div>'+
   '<div class="kart bolum"><div class="kart-baslik"><span>Zaman içinde isabet · birikimli</span></div>'+
   '<div id="grafik2" class="grafik-kucuk"></div><p class="cok-kucuk">Çizgi yatay ve yüksek kalıyorsa kural her dönemde tutmuş demektir. Sona doğru düşüyorsa kural zayıflıyor olabilir. Kesikli çizgi: normal (rastgele) oran.</p></div>'+
   '<div class="kart bolum"><div class="kart-baslik"><span>Tüm oluşumlar ('+O.length+') · en yeni üstte</span></div><div class="tablo-sar" style="max-height:460px;overflow-y:auto"><table><thead><tr>'+
   '<th>Tarih (TSİ)</th><th>Dönem</th><th class="sayi">Giriş</th><th class="sayi">Çıkış</th><th class="sayi">Değişim</th><th>Sonuç</th></tr></thead><tbody id="tablo"></tbody></table></div></div>';

  var renk={yazi:'#8b97a9',cizgi:'rgba(148,163,184,.08)',kenar:'rgba(148,163,184,.22)'};
  var ortak={layout:{background:{type:'solid',color:'transparent'},textColor:renk.yazi,fontFamily:'JetBrains Mono, monospace'},
    grid:{vertLines:{color:renk.cizgi},horzLines:{color:renk.cizgi}},rightPriceScale:{borderColor:renk.kenar},
    timeScale:{borderColor:renk.kenar,timeVisible:true,secondsVisible:false},crosshair:{mode:0},autoSize:true,
    localization:{locale:'tr-TR',dateFormat:'dd.MM.yy'}};
  var ch=LightweightCharts.createChart($('grafik'),ortak);
  var mum=ch.addCandlestickSeries({upColor:'#16c784',downColor:'#ea3943',borderVisible:false,wickUpColor:'#16c784',wickDownColor:'#ea3943'});
  var zam=D.mumlar.map(function(m){return m[0]});
  mum.setData(D.mumlar.map(function(m){return {time:m[0]+OFS,open:m[1],high:m[2],low:m[3],close:m[4]}}));
  function isaret(f){var L=O.filter(function(o){return f==='hepsi'||(f==='test'&&o[1]>=2)||(f==='tuttu'&&o[2]===1)||(f==='tutmadi'&&o[2]===0)});
    mum.setMarkers(L.map(function(o){var bek=o[2]<0;return {time:o[0]+OFS,position:up?'belowBar':'aboveBar',
      color:bek?'#f3d778':(o[2]===1?'#16c784':'#ea3943'),shape:bek?'square':(o[2]===1?(up?'arrowUp':'arrowDown'):'circle'),
      text:bek?'ŞİMDİ':''}}))}
  isaret('hepsi');
  function git(t){var lo=0,hi=zam.length-1;while(lo<hi){var m=(lo+hi)>>1;if(zam[m]<t)lo=m+1;else hi=m}
    ch.timeScale().setVisibleLogicalRange({from:lo-70,to:lo+40});window.scrollTo({top:$('grafik').getBoundingClientRect().top+scrollY-120,behavior:'smooth'})}
  if(O.length){var t0=O[O.length-1][0],lo=0,hi=zam.length-1;while(lo<hi){var m=(lo+hi)>>1;if(zam[m]<t0)lo=m+1;else hi=m}
    ch.timeScale().setVisibleLogicalRange({from:lo-70,to:lo+40})}
  document.querySelectorAll('#filtre button').forEach(function(b){b.addEventListener('click',function(){
    document.querySelectorAll('#filtre button').forEach(function(x){x.setAttribute('aria-pressed',x===b)});isaret(b.dataset.f)})});

  var ch2=LightweightCharts.createChart($('grafik2'),ortak), taban=R.taban_oran*100,
    cizgi=ch2.addLineSeries({color:'#f3d778',lineWidth:2,priceFormat:{type:'percent'},
      autoscaleInfoProvider:function(f){var r=f();if(!r)return r;r.priceRange.minValue=Math.min(r.priceRange.minValue,taban-5);r.priceRange.maxValue=Math.max(r.priceRange.maxValue,100);return r}});
  var h=0,n=0,nokta=[];biten.forEach(function(o){n++;h+=o[2];nokta.push({time:o[0]+OFS,value:100*h/n})});
  var tekil=[];nokta.forEach(function(p){if(tekil.length&&tekil[tekil.length-1].time===p.time)tekil[tekil.length-1]=p;else tekil.push(p)});
  cizgi.setData(tekil);cizgi.createPriceLine({price:R.taban_oran*100,color:'#8b97a9',lineStyle:2,lineWidth:1,axisLabelVisible:true,title:'normal'});
  ch2.timeScale().fitContent();

  var satir=O.slice().reverse().map(function(o){var s=o[2]<0?'<span class="rozet altin">BEKLENİYOR</span>':(o[2]===1?'<span class="rozet iyi">✓ TUTTU</span>':'<span class="rozet kotu">✕ TUTMADI</span>');
    var d=o[5]==null?'—':'<span class="'+(o[5]>=0?'iyi':'kotu')+'">'+(o[5]>=0?'+':'')+o[5].toFixed(2)+'%</span>';
    return '<tr class="tik" data-t="'+o[0]+'"><td class="mono">'+tarih(o[0])+'</td><td>'+BOL[o[1]]+'</td><td class="sayi mono">'+fiyat(o[3])+'</td><td class="sayi mono">'+fiyat(o[4])+'</td><td class="sayi mono">'+d+'</td><td>'+s+'</td></tr>'}).join('');
  $('tablo').innerHTML=satir;
  $('tablo').addEventListener('click',function(e){var tr=e.target.closest('tr');if(!tr)return;
    document.querySelectorAll('#tablo tr.secili').forEach(function(x){x.classList.remove('secili')});tr.classList.add('secili');git(+tr.dataset.t)});
}
function kpi(e,d,a){return '<div class="kart"><div class="kart-baslik"><span>'+e+'</span></div><div class="dev" style="font-size:30px">'+d+'</div><div class="kucuk">'+a+'</div></div>'}
})();
"""


def grafik_html() -> str:
    govde = ('<main id="icerik"><div class="kart"><p class="kucuk">Grafik yükleniyor…</p></div></main>'
             '<script src="statik/lightweight-charts.standalone.production.js"></script>'
             f'<script>{GRAFIK_JS}</script>'
             '<footer>Grafik: TradingView Lightweight Charts™ (Apache 2.0). Geçmiş isabet geleceğin garantisi değildir.</footer>')
    return _iskelet("Kural Grafiği · Kripto Risk Terminali", "grafik.html", govde)
