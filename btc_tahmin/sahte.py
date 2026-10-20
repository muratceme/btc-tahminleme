"""Sahte keşif testi: bulunan kuralların kaçı şans eseri olabilir?

Kurallar binlerce aday arasından "testte tutanlar" diye seçilir. Rastgele fiyatta sistem 0 kural buluyor
(tests/sizinti_test.py), ama gerçek fiyatın rejimleri ve oto-korelasyonu var; orada gürültünün kaç kural
üretebileceği ancak şu yolla ölçülür:

  Hedefler (sonraki mum yeşil mi, gün sonu yukarı mı ...) koşullara göre TAM GÜN kaydırılır. Böylece
  gün içi yapı (gün sonuna kalan saat, seans) aynı kalır ama "bu koşulda sonra ne oldu" bağı kopar.
  Bu karıştırılmış veride madencilik tekrar tekrar çalıştırılır. Bulunan kural sayısı, gerçek veride
  bulunanla karşılaştırılır: karışık veride ortalama 3 kural çıkıyor ve gerçekte 12 varsa, gerçek
  kuralların yaklaşık dörtte biri şans eseri olabilir.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config, miner, models, pipeline


def gun_kaydir(hedef: pd.DataFrame, o: pd.DataFrame, gun: int) -> pd.DataFrame:
    """Hedef sütunlarını tam `gun` gün ileri kaydırır (dairesel)."""
    mum_gunde = int(round(pd.Timedelta(days=1) / o["time"].diff().median()))
    k = gun * mum_gunde
    return pd.DataFrame({c: np.roll(hedef[c].to_numpy(), k) for c in hedef.columns}, index=hedef.index)


def tek_tur(o, K, KT, hedef_k, derin: bool = True, model: bool = True) -> dict[str, int]:
    gun = pipeline._gun_serisi(o)
    sayim = {
        "sonraki_mum": len(miner.kurallari_ara(K, hedef_k["sonraki_yesil"], "sonraki_mum")),
        "gun_sonu": len(miner.kurallari_ara(K, hedef_k["gun_sonu_yukari"], "gun_sonu", gun=gun)),
    }
    if derin:
        sayim["derin"] = len(pipeline.derin_tarama(KT, hedef_k))
    if model:
        sayim["model"] = sum(1 for h in ("gun_sonu_yukari", "sonraki_yesil")
                             for r in models.yon_modelleri(o, hedef_k, h) if r["tur"] == "YON")
    return sayim


def sahte_kesif(o, K, KT, hedef, tekrar: int = 5, tohum: int = 0, derin: bool = True, model: bool = True,
                ilerleme=None) -> dict:
    rng = np.random.default_rng(tohum)
    toplam_gun = int((o["time"].iloc[-1] - o["time"].iloc[0]).days)
    turlar = []
    t0 = time.time()
    for i in range(tekrar):
        kay = int(rng.integers(7, max(8, toplam_gun - 7)))
        turlar.append(tek_tur(o, K, KT, gun_kaydir(hedef, o, kay), derin, model))
        if ilerleme:
            ilerleme(i + 1, tekrar, turlar[-1])
    anahtarlar = list(turlar[0].keys()) if turlar else []
    return {
        "tekrar": tekrar, "zaman": datetime.now(timezone.utc).isoformat(), "sure_sn": round(time.time() - t0),
        "turlar": turlar,
        "ortalama": {k: round(float(np.mean([t[k] for t in turlar])), 2) for k in anahtarlar},
        "maks": {k: int(max(t[k] for t in turlar)) for k in anahtarlar},
    }


def calistir_ve_kaydet(sembol: str, aralik: str, mumlar: dict, tekrar: int = 5, derin: bool = True) -> dict:
    from .features import ince_kosullar, veri_seti_hazirla
    o, K, hedef = veri_seti_hazirla(mumlar, ana=sembol)
    KT = pd.concat([K, ince_kosullar(o)], axis=1)

    def ilerleme(i, n, t):
        print(f"  · {sembol} karışık tur {i}/{n}: " + ", ".join(f"{k} {v}" for k, v in t.items()), flush=True)

    sonuc = sahte_kesif(o, K, KT, hedef, tekrar=tekrar, derin=derin, ilerleme=ilerleme)
    # Gerçek sayılar (önbellekten; yoksa şimdi aranır)
    gercek = pipeline.kurallari_getir(sembol, aralik, o, K, KT, hedef, hizli=True)
    sonuc["gercek"] = {k: len(v) for k, v in gercek.items()}
    sonuc["gercek"]["model"] = sum(1 for h in ("gun_sonu_yukari", "sonraki_yesil")
                                   for r in models.yon_modelleri(o, hedef, h) if r["tur"] == "YON")
    config.CIKTI_DIR.mkdir(parents=True, exist_ok=True)
    (config.CIKTI_DIR / f"sahte_{sembol}_{aralik}.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    return sonuc


def metin(sonuc: dict, sembol: str) -> str:
    s = [f"Sahte keşif testi · {sembol} · {sonuc['tekrar']} karışık tur ({sonuc['sure_sn']} sn)"]
    s.append(f"  {'Liste':<14}{'Gerçek':>8}{'Karışık ort.':>14}{'Karışık maks':>14}  Şans payı")
    for k, ort in sonuc["ortalama"].items():
        g = (sonuc.get("gercek") or {}).get(k, 0)
        pay = f"~%{min(100, 100 * ort / g):.0f}" if g else "—"
        s.append(f"  {k:<14}{g:>8}{ort:>14.1f}{sonuc['maks'][k]:>14}  {pay}")
    s.append("  Okuma: karışık veride çıkan kural sayısı, gerçek listede kaç kuralın şans olabileceğinin tahminidir.")
    return "\n".join(s)
