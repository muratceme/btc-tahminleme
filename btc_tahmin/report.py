"""Terminal özeti ve HTML panosu (cikti/rapor.html)."""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone

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
    s.append("")
    s.append(f"{GRI}{rapor['uyari']}{SIFIR}")
    s.append(f"Pano: {config.CIKTI_DIR / 'rapor.html'}")
    return "\n".join(s)


# ---------------------------------------------------------------- HTML
def _e(x) -> str:
    return html.escape(str(x))


def _risk_sinifi(r):
    if r is None:
        return "notr"
    return "iyi" if r < 40 else ("orta" if r < 60 else "kotu")


def _coin_panel(c: dict) -> str:
    oz = c["risk"]["ozet"]
    lr = oz.get("long_risk")
    ana = (f'<div class="dev {_risk_sinifi(lr)}">%{lr}</div><div class="alt">GÜN SONU LONG RİSKİ · '
           f'{oz["dayanak_sayisi"]} tutarlı sinyal · short riski %{oz["short_risk"]}</div>') if lr is not None else (
        f'<div class="dev notr">—</div><div class="alt">Şu an %{int(config.MIN_TUTARLILIK*100)}+ tutarlılıkta sinyal yok · '
        f'ham model long riski %{_e(oz.get("ham_model_long_risk"))} '
        f'(genel isabeti %{round((oz.get("ham_model_dogrulugu") or 0) * 100)}, düşük güven)</div>')
    kirimli = (f'<div class="kutu"><div class="etk">Puan kırımı dahil long riski</div>'
               f'<div class="deger {_risk_sinifi(oz["kirimli_long_risk"])}">%{oz["kirimli_long_risk"]}</div>'
               f'<div class="kucuk">Sadece bilgi — modele girmez</div></div>') if oz.get("kirimli_long_risk") is not None else ""
    dd = "".join(f'<div class="kutu"><div class="etk">{_e(k)} güvenle max düşüş</div>'
                 f'<div class="deger kotu">{v}%</div><div class="kucuk">gün sonuna kadar</div></div>'
                 for k, v in (oz.get("max_dusus") or {}).items())
    tek = "".join(f'<div class="kutu"><div class="etk">{_e(k)}</div><div class="deger">{_e(v)}</div></div>'
                  for k, v in c["teknik_ozet"].items())

    satir = []
    for r in c["risk"]["satirlar"]:
        if "max_dusus" in r:
            deg = f'<td colspan="2" class="kotu">max {r["max_dusus"]}%</td>'
            sg = '<span class="rozet notr">sınır</span>'
        else:
            deg = (f'<td class="{_risk_sinifi(r["long_risk"])}">%{r["long_risk"]}</td>'
                   f'<td class="{_risk_sinifi(r["short_risk"])}">%{r["short_risk"]}</td>')
            sg = '<span class="rozet iyi">SİNYAL</span>' if r["sinyal_var"] else '<span class="rozet notr">bekle</span>'
        satir.append(f'<tr class="{"" if r["sinyal_var"] else "soluk"}"><td><b>{_e(r["etiket"])}</b></td>'
                     f'<td><div class="cubuk"><span style="width:{(r["tutarlilik"]-0.5)*200:.0f}%"></span></div>'
                     f'%{r["tutarlilik"]*100:.1f}</td><td>{r["test_n"]}</td><td>{sg}</td>{deg}'
                     f'<td class="kaynak">{_e(r["kaynak"])}<div class="kucuk">{_e(r["detay"])}</div></td></tr>')
    risk_tbl = ("<table><thead><tr><th>Etiket</th><th>Tutarlılık</th><th>Test n</th><th>Durum</th><th>Long risk</th>"
                "<th>Short risk</th><th>Kaynak</th></tr></thead><tbody>" + "".join(satir) + "</tbody></table>") if satir else \
        '<p class="kucuk">%70 üzeri tutarlılıkta risk satırı bulunamadı.</p>'

    def kural_li(r):
        sinif = "iyi" if r["yon"].startswith("YESIL") else "kotu"
        kos = "".join(f'<span class="kosul">{_e(k)}</span>' for k in r["kosullar"])
        return (f'<li><span class="rozet {sinif}">{"YEŞİL" if sinif == "iyi" else "KIRMIZI"} %{r["tutarlilik"]*100:.0f}</span> '
                f'{kos}<span class="kucuk"> test n={r["test_n"]} · eğitim %{(r["egitim_oran"] or 0)*100:.0f} · '
                f'lift x{r["kaldirac_lift"]} · p={r["p_deger"]}</span></li>')

    aktif = c["sonraki_mum"]["aktif_kurallar"]
    aktif_html = "<ul class='kurallar'>" + "".join(kural_li(r) for r in aktif[:15]) + "</ul>" if aktif else \
        '<p class="kucuk">Son kapanan mumda tutarlı (%70+) bir kombinasyon aktif değil. Beklemek de bir pozisyondur.</p>'
    # Her model için tek satır: sinyal veren en tutarlı seviye (yoksa en tutarlı seviye)
    en_iyi: dict[str, dict] = {}
    for r in c["sonraki_mum"]["ml"]:
        a = en_iyi.get(r["model"])
        if a is None or (r["sinyal_var"], r["tutarlilik"]) > (a["sinyal_var"], a["tutarlilik"]):
            en_iyi[r["model"]] = r

    def ml_li(r):
        yesil = r["p_yukari_simdi"] >= 0.5
        yon = f'<span class="{"iyi" if yesil else "kotu"}">{"YEŞİL" if yesil else "KIRMIZI"} '
        yon += f'%{max(r["p_yukari_simdi"], 1 - r["p_yukari_simdi"]) * 100:.0f}</span>'
        durum = (f'<b class="iyi">SİNYAL</b> · tutarlılık %{r["tutarlilik"] * 100:.0f} (test n={r["test_n"]})'
                 if r["sinyal_var"] else f'<span class="notr">sinyal yok (eşik ±{r["guven_marji"]})</span>')
        return f'<li>{_e(r["model"])}: {yon} · {durum}</li>'
    ml = "".join(ml_li(r) for r in en_iyi.values())
    kutuphane = "<ul class='kurallar'>" + "".join(kural_li(r) for r in c["kural_kutuphanesi"]["sonraki_mum"][:25]) + "</ul>"
    kutuphane_gs = "<ul class='kurallar'>" + "".join(kural_li(r) for r in c["kural_kutuphanesi"]["gun_sonu"][:25]) + "</ul>"
    aktif_kos = "".join(f'<span class="kosul">{_e(k)}</span>' for k in c["aktif_kosullar"])

    return f"""
<section class="coin" id="{_e(c['sembol'])}">
  <div class="ust">
    <div><h2>{_e(c['sembol'])}</h2><div class="fiyat">{c['fiyat']:,.4f}
      <span class="{'iyi' if (c['degisim_24s'] or 0) >= 0 else 'kotu'}">{(c['degisim_24s'] or 0):+.2f}%</span></div>
      <div class="kucuk">Son kapanan {c['aralik']} mum: {_e(c['son_mum_zamani'][:16])} UTC · {c['veri_mum_sayisi']:,} mum veri</div></div>
    <div class="ana-risk">{ana}</div>
  </div>
  <div class="izgara">{kirimli}{dd}</div>
  <h3>Risk tablosu (yalnızca %{int(config.MIN_TUTARLILIK*100)}+ tutarlılık)</h3>{risk_tbl}
  <h3>Sonraki {c['aralik']} mum — şu an aktif kombinasyonlar</h3>{aktif_html}
  <ul class="ml">{ml}</ul>
  <h3>Teknik özet</h3><div class="izgara">{tek}</div>
  <details><summary>Şu an doğru olan tüm koşullar ({len(c['aktif_kosullar'])})</summary><div class="kosullar">{aktif_kos}</div></details>
  <details><summary>Kural kütüphanesi — sonraki mum ({c['kural_sayisi']['sonraki_mum']} kural)</summary>{kutuphane}</details>
  <details><summary>Kural kütüphanesi — gün sonu ({c['kural_sayisi']['gun_sonu']} kural)</summary>{kutuphane_gs}</details>
</section>"""


def html_rapor(rapor: dict, yenile_sn: int | None = None) -> str:
    gp = rapor["genel_puan"]
    b = rapor["baglam"]
    serit = " ".join(f'<a href="#{_e(s)}" class="tik"><b>{_e(s.replace("USDT", ""))}</b> {c["fiyat"]:,.4f} '
                     f'<span class="{"iyi" if (c["degisim_24s"] or 0) >= 0 else "kotu"}">{(c["degisim_24s"] or 0):+.2f}%</span>'
                     f' · risk <span class="{_risk_sinifi(c["risk"]["ozet"].get("long_risk"))}">'
                     f'{"%"+str(c["risk"]["ozet"]["long_risk"]) if c["risk"]["ozet"].get("long_risk") is not None else "—"}</span></a>'
                     for s, c in rapor["coinler"].items())
    kalemler = "".join(f'<li><span class="kotu">-{k["kirim"]:g}</span> {_e(k["ad"])} <span class="kucuk">[{_e(k["kaynak"])}]</span></li>'
                       for k in gp["kalemler"]) or "<li>Kırım yok</li>"
    olay = "".join(f'<li>{_e(e["ad"])} — <b>{e["saat_kaldi"]} saat</b> ({_e(e.get("etki", ""))})</li>'
                   for e in gp.get("yaklasan_olaylar", [])) or "<li class='kucuk'>48 saat içinde kayıtlı olay yok</li>"

    dom_html = "<p class='kucuk'>Dominans verisi alınamadı.</p>"
    if b.get("dominans"):
        d = b["dominans"]
        dg = d.get("degisim", {})
        hucre = "".join(
            f'<div class="kutu"><div class="etk">{k.upper()}.D</div><div class="deger">{d["anlik"][k]:.2f}%</div>'
            f'<div class="kucuk">24s {dg.get(k, {}).get("24s", 0):+.2f} · 7g {dg.get(k, {}).get("7g", 0):+.2f}</div></div>'
            for k in ("btc", "eth", "xrp", "usdt", "usdc"))
        hucre += (f'<div class="kutu"><div class="etk">STABLE.D</div><div class="deger">{d["anlik"]["stable_toplam"]:.2f}%</div></div>'
                  f'<div class="kutu"><div class="etk">OTHERS.D</div><div class="deger">{d["anlik"]["others"]:.2f}%</div></div>'
                  f'<div class="kutu"><div class="etk">Toplam piyasa 24s</div><div class="deger">{d["toplam_mcap_degisim_24s"]:+.2f}%</div></div>')
        yorum = "".join(f"<li>{_e(y)}</li>" for y in d.get("yorum", []))
        dom_html = (f'<div class="izgara">{hucre}</div><ul>{yorum}</ul>'
                    f'<div class="kucuk">24s değişim kaynağı: {_e(d.get("degisim_kaynagi_24s", ""))}</div>')

    fg = b.get("korku_acgozluluk")
    fg_html = (f'<div class="dev {"kotu" if fg["deger"] < 30 or fg["deger"] > 75 else "orta"}">{fg["deger"]}</div>'
               f'<div class="alt">{_e(fg["sinif"])} · dün {fg["dun"]} · geçen hafta {_e(fg.get("hafta_once"))}</div>') if fg else "—"
    vadeli = "".join(
        f'<tr><td>{_e(s)}</td><td>{_e(v.get("funding_yuzde"))}%</td><td>{_e(v.get("oi_degisim_24s_yuzde"))}%</td>'
        f'<td>{_e(v.get("long_short_orani"))}</td><td>{_e(v.get("taker_alis_satis"))}</td></tr>'
        for s, v in (b.get("vadeli") or {}).items())
    hb = b.get("haberler") or {}
    haber = "".join(f'<li><span class="{"iyi" if h["skor"] > 0 else ("kotu" if h["skor"] < 0 else "notr")}">'
                    f'{h["skor"]:+d}</span> {_e(h["baslik"])} <span class="kucuk">{_e(h["kaynak"])}</span></li>'
                    for h in hb.get("onemli", []))
    hatalar = "".join(f"<li>{_e(k)}: {_e(v)[:160]}</li>" for k, v in (b.get("hatalar") or {}).items())
    coinler = "".join(_coin_panel(c) for c in rapor["coinler"].values())
    yenile = f'<meta http-equiv="refresh" content="{yenile_sn}">' if yenile_sn else ""
    olusturma = datetime.fromisoformat(rapor["olusturma"]).astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">{yenile}
<title>Kripto Risk Terminali</title>
<style>
:root{{--bg:#07090d;--panel:#0f141c;--cizgi:#1f2a38;--yazi:#d7dde6;--soluk:#7c8a9c;--iyi:#22c55e;--kotu:#ef4444;--orta:#f59e0b;--vurgu:#fbbf24}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--yazi);font:14px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
html,body{{max-width:100%;overflow-x:hidden}}header{{position:sticky;top:0;z-index:5;background:#000;border-bottom:1px solid var(--vurgu);padding:8px 16px;display:flex;gap:6px 18px;flex-wrap:wrap;align-items:center}}
header .logo{{color:var(--vurgu);font-weight:700;letter-spacing:.08em}}.tik{{color:var(--yazi);text-decoration:none;white-space:nowrap}}
main{{max-width:1280px;margin:0 auto;padding:16px}}
.panel,.coin,.ust-izgara>*{{min-width:0}}.panel,.coin{{background:var(--panel);border:1px solid var(--cizgi);border-radius:6px;padding:16px;margin-bottom:16px}}
.ust-izgara{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(280px,100%),1fr));gap:16px}}
h2{{margin:0;color:var(--vurgu)}}h3{{color:var(--vurgu);font-size:13px;letter-spacing:.06em;text-transform:uppercase;border-bottom:1px solid var(--cizgi);padding-bottom:4px;margin-top:22px}}
.ust{{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}}.fiyat{{font-size:26px;font-weight:700}}
.ana-risk{{text-align:right}}.dev{{font-size:44px;font-weight:800;line-height:1}}.alt{{color:var(--soluk);font-size:12px}}
.izgara{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(150px,45%),1fr));gap:8px;margin-top:10px}}
.kutu{{border:1px solid var(--cizgi);border-radius:4px;padding:8px;background:#0b1017}}.etk{{color:var(--soluk);font-size:11px;text-transform:uppercase}}.deger{{font-size:18px;font-weight:700}}
.iyi{{color:var(--iyi)}}.kotu{{color:var(--kotu)}}.orta{{color:var(--orta)}}.notr{{color:var(--soluk)}}.kucuk{{color:var(--soluk);font-size:11px}}
.tablo-sar{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:6px 8px;border-bottom:1px solid var(--cizgi);text-align:left;vertical-align:top}}
th{{color:var(--soluk);font-weight:600;font-size:11px;text-transform:uppercase}}tr.soluk td{{opacity:.55}}td.kaynak{{max-width:460px;word-break:break-word}}
.cubuk{{width:60px;height:5px;background:#1f2a38;display:inline-block;margin-right:6px;vertical-align:middle}}.cubuk span{{display:block;height:100%;background:var(--vurgu)}}
.rozet{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px;font-weight:700;border:1px solid currentColor}}
.kosul{{display:inline-block;max-width:100%;overflow-wrap:anywhere;background:#16202c;border:1px solid var(--cizgi);padding:1px 6px;margin:2px;border-radius:3px;font-size:12px}}
ul{{padding-left:18px;overflow-wrap:anywhere}}ul.kurallar li{{margin:6px 0}}details{{margin-top:10px}}summary{{cursor:pointer;color:var(--vurgu)}}
.puan{{font-size:56px;font-weight:800;color:var(--vurgu);line-height:1}}footer{{color:var(--soluk);font-size:12px;padding:16px;text-align:center}}
@media (max-width:640px){{main{{padding:16px}}.ana-risk{{text-align:left}}.dev{{font-size:36px}}td.kaynak{{min-width:220px}}}}
</style></head><body>
<header><span class="logo">◆ KRİPTO RİSK TERMİNALİ</span>{serit}<span class="kucuk">{olusturma} · {_e(rapor['aralik'])}</span></header>
<main>
<div class="ust-izgara">
  <div class="panel"><h3 style="margin-top:0">Genel piyasa puanı</h3><div class="puan">%{gp['genel_puan']:g}</div>
    <div class="kucuk">Modellere girmez, sadece görmen için. Toplam kırım -{gp['toplam_kirim']:g}</div><ul>{kalemler}</ul></div>
  <div class="panel"><h3 style="margin-top:0">Korku / Açgözlülük</h3>{fg_html}
    <h3>Yaklaşan olaylar (48s)</h3><ul>{olay}</ul></div>
  <div class="panel"><h3 style="margin-top:0">Vadeli piyasa</h3><div class="tablo-sar"><table><thead><tr><th>Çift</th><th>Funding</th><th>OI 24s</th><th>L/S</th><th>Taker A/S</th></tr></thead>
    <tbody>{vadeli or "<tr><td colspan=5 class=kucuk>veri yok</td></tr>"}</tbody></table></div></div>
</div>
<div class="panel"><h3 style="margin-top:0">Dominanslar</h3>{dom_html}</div>
{coinler.replace("<table>", '<div class="tablo-sar"><table>').replace("</table>", "</table></div>")}
<div class="panel"><h3 style="margin-top:0">Haber akışı (son 24s) · skor {hb.get('toplam_skor', 0)} · {hb.get('adet', 0)} başlık</h3><ul>{haber or "<li class=kucuk>haber alınamadı</li>"}</ul></div>
{f'<div class="panel"><h3 style="margin-top:0">Veri kaynağı hataları</h3><ul class="kucuk">{hatalar}</ul></div>' if hatalar else ''}
<div class="panel kucuk"><b>Nasıl okunur?</b> <b>Long risk</b> = şimdi long açarsan gün sonunda (TSİ 23:59) zararda olma ihtimali.
<b>Tutarlılık</b> = o satırın, modelin hiç görmediği son test döneminde doğru çıkma oranı. <b>Test n</b> = bu oranın kaç örnekten hesaplandığı (küçükse temkinli ol).
<b>SİNYAL</b> = model şu an o tutarlılığı sağlayan güven eşiğinin üstünde; <b>bekle</b> = model şu an emin değil, risk sayısı bilgi amaçlıdır.
<b>Max düşüş</b> = gün sonuna kadar fiyatın şu andan en fazla ne kadar sarkacağı (stop seviyesi için).</div>
</main><footer>{_e(rapor['uyari'])}</footer></body></html>"""


def kaydet(rapor: dict, yenile_sn: int | None = None):
    config.CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    yol = config.CIKTI_DIR / "rapor.html"
    yol.write_text(html_rapor(rapor, yenile_sn), encoding="utf-8")
    return yol


def json_oku():
    return json.loads((config.CIKTI_DIR / "rapor.json").read_text(encoding="utf-8"))
