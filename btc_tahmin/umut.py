"""Uzun vade çalışması: "umut olan yerler".

15 dakikalık mumda komisyon tipik hareketin büyük kısmını yiyor. Bu modül aynı strateji taramasını 1 saatlik ve
4 saatlik mumlarda (15m veriden üretilir) çalıştırır, her zaman diliminde "tipik hareket / komisyon" oranını ve
al-tut karşılaştırmasını verir, geçen stratejileri trendli / yatay rejimde ayrı ayrı ölçer.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, fable, performans
from .data import _yeniden_ornekle
from .features import veri_seti_hazirla


def _mum_dosyasi(sembol, aralik, o):
    from .pipeline import mum_dosyasi_yaz
    return mum_dosyasi_yaz(sembol, aralik, o)

ARALIKLAR = [("1h", "1 saat"), ("4h", "4 saat")]


def _ozet(o: pd.DataFrame, tarama: dict, aralik: str) -> dict:
    """Zaman dilimi özeti: tipik mum hareketi, komisyon oranı, test dönemi al-tut, geçen sayıları."""
    maliyet = performans.islem_maliyeti()
    hareket = float(np.nanmedian(np.abs(o["close"].pct_change()) * 100))
    s2 = int(len(o) * (config.EGITIM_ORANI + config.DOGRULAMA_ORANI))
    al_tut = float((o["close"].iloc[-1] / o["close"].iloc[s2] - 1) * 100)
    en_iyi = tarama["secilen"][0] if tarama.get("secilen") else None
    return {"aralik": aralik, "mum": int(len(o)), "tipik_hareket": round(hareket, 3), "maliyet": maliyet,
            "hareket_bolu_maliyet": round(hareket / maliyet, 2) if maliyet else None,
            "al_tut_test": round(al_tut, 2), "denenen": tarama["denenen"], "gecen": tarama["gecen"],
            "en_iyi": {"ad": en_iyi["ad"], "test_net": en_iyi["donemler"]["test"]["toplam_net"],
                       "test_kf": en_iyi["donemler"]["test"]["kar_faktoru"]} if en_iyi else None}


def calis(mumlar: dict, sembol: str, o15: pd.DataFrame, tarama15: dict) -> dict:
    """Her uzun zaman dilimi için tarama + sayfa verisi; 15m özeti karşılaştırma için eklenir."""
    sonuc = {"ozetler": [_ozet(o15, tarama15, "15m")], "dilimler": {}}
    for aralik, ad in ARALIKLAR:
        yeniden = {s: _yeniden_ornekle(d, aralik.replace("h", "h")) for s, d in mumlar.items() if d is not None and not d.empty}
        o, _, _ = veri_seti_hazirla(yeniden, ana=sembol)
        t = fable.tarama(o)
        rejim = fable.rejim_serisi(o)
        sayfa = fable.tarama_sayfa_verisi(o, t, rejim)
        trend_pay = float(rejim[int(len(o) * 0.8):].mean()) if len(o) else 0.0
        sonuc["dilimler"][aralik] = {"ad": ad, "tarama": {k: v for k, v in t.items() if k != "secilen"},
                                     "secilen_sayisi": len(t["secilen"]), "sayfa": sayfa, "mum_dosyasi": _mum_dosyasi(sembol, aralik, o),
                                     "rejim_simdi": "trend" if len(rejim) and rejim[-1] else "yatay",
                                     "test_trend_payi": round(trend_pay, 3), "veri_gun": int((o["time"].iloc[-1] - o["time"].iloc[0]).days)}
        sonuc["ozetler"].append(_ozet(o, t, aralik))
    return sonuc
