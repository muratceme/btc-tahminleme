"""Kombinasyon madenciliği.

"İndikatör-1 X, İndikatör-2 Y, ... İndikatör-5 Z iken sonraki mum %N yeşil geldi"
türünden kuralları arar.

Aşırı uyumu (overfitting) azaltmak için veri kronolojik olarak üçe bölünür:
  1) EĞİTİM   : kurallar burada aranır (beam search)
  2) DOĞRULAMA: aday kurallar burada elenir
  3) TEST     : hiç görülmemiş veride son not verilir -> "tutarlılık" budur
Raporlanan tutarlılık daima TEST dönemindeki isabet oranıdır.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config

if hasattr(np, "bitwise_count"):
    def _say(a: np.ndarray, axis=-1):
        return np.bitwise_count(a).sum(axis=axis, dtype=np.int64)
else:  # numpy < 2
    _TABLO = np.array([bin(i).count("1") for i in range(256)], dtype=np.int64)

    def _say(a: np.ndarray, axis=-1):
        return _TABLO[a].sum(axis=axis)


def wilson_alt(basari: float, n: float, z: float = 1.64) -> float:
    if n <= 0:
        return 0.0
    p = basari / n
    pay = p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return pay / (1 + z * z / n)


def binom_p(basari: int, n: int, p0: float) -> float:
    """Tek yönlü: oranın p0'dan büyük olma ihtimali için p-değeri (normal yaklaşım)."""
    if n == 0:
        return 1.0
    z = (basari - n * p0) / math.sqrt(n * p0 * (1 - p0))
    return 0.5 * math.erfc(z / math.sqrt(2))


def aile(kosul: str) -> str:
    """Koşulun ait olduğu gösterge. İnce eşikli koşullar ("RSI~:35-40") ana göstergeyle aynı ailedir."""
    return kosul.split(":", 1)[0].rstrip("~")


def kural_id(hedef: str, yon: int, kosullar) -> str:
    return hashlib.md5(f"{hedef}|{yon}|{'&'.join(sorted(kosullar))}".encode()).hexdigest()[:10]


def ayristir(idx: np.ndarray, gun=None, blok: int = 1) -> np.ndarray:
    """Birbirine bağımlı tekrarları ayıklar.
    gun verilirse her günün ilk sinyali; blok > 1 ise birbirinden en az `blok` mum uzak sinyaller kalır
    (ör. '3 mum sonra' hedefinde art arda 3 sinyal aynı mumları paylaşır)."""
    if len(idx) == 0:
        return idx
    if gun is not None:
        _, ilk = np.unique(gun[idx], return_index=True)
        return idx[np.sort(ilk)]
    if blok <= 1:
        return idx
    kalan, son = [], -10**9
    for i in idx:
        if i - son >= blok:
            kalan.append(i)
            son = i
    return np.asarray(kalan, dtype=idx.dtype)


@dataclass
class Kural:
    kosullar: tuple[str, ...]
    hedef: str
    yon: int                       # 1 = yeşil/yukarı, 0 = kırmızı/aşağı
    egitim: tuple[int, int] = (0, 0)      # (n, isabet)
    dogrulama: tuple[int, int] = (0, 0)
    test: tuple[int, int] = (0, 0)
    test_gun: int = 0
    taban_oran: float = 0.5
    aktif: bool = False
    ekstra: dict = field(default_factory=dict)

    @property
    def tutarlilik(self) -> float:
        n, h = self.test
        return h / n if n else 0.0

    def sozluk(self) -> dict:
        def o(t):
            return round(t[1] / t[0], 4) if t[0] else None
        return {
            "id": kural_id(self.hedef, self.yon, self.kosullar),
            "kosullar": list(self.kosullar),
            "hedef": self.hedef,
            "yon": "YESIL/YUKARI" if self.yon == 1 else "KIRMIZI/ASAGI",
            "tutarlilik": round(self.tutarlilik, 4),
            "test_n": self.test[0],
            "test_bagimsiz_gun": self.test_gun,
            "egitim_n": self.egitim[0], "egitim_oran": o(self.egitim),
            "dogrulama_n": self.dogrulama[0], "dogrulama_oran": o(self.dogrulama),
            "taban_oran": round(self.taban_oran, 4),
            "kaldirac_lift": round(self.tutarlilik / self.taban_oran, 3) if self.taban_oran else None,
            "p_deger": round(binom_p(self.test[1], self.test[0], self.taban_oran), 5),
            "aktif_su_an": bool(self.aktif),
        }


class _Bolum:
    """Bir veri dilimini bit dizilerine paketler."""

    def __init__(self, K: np.ndarray, y: np.ndarray):
        self.n = int(len(y))
        self.X = np.packbits(K.T, axis=1)                  # (m, n/8)
        self.y1 = np.packbits(y == 1)
        self.y0 = np.packbits(y == 0)
        self.hepsi = np.packbits(np.ones(len(y), dtype=bool))

    def say(self, maske: np.ndarray) -> tuple[int, int, int]:
        return int(_say(maske)), int(_say(maske & self.y1)), int(_say(maske & self.y0))


def kurallari_ara(K: pd.DataFrame, y: pd.Series, hedef_adi: str, gun: pd.Series | None = None,
                  max_kosul: int = config.MAX_KOSUL, beam: int = config.BEAM_GENISLIK,
                  min_destek: int = config.MIN_DESTEK_EGITIM, min_test: int = config.MIN_DESTEK_TEST,
                  min_tutarlilik: float = config.MIN_TUTARLILIK, blok: int = 1, yonler=(1, 0),
                  min_kosul: int = 1, esikler: tuple[int, int, int] | None = None) -> list[Kural]:
    gecerli = y.notna().to_numpy()
    Kv = K.to_numpy()[gecerli]
    yv = y.to_numpy()[gecerli].astype(int)
    gun_v = gun.to_numpy()[gecerli] if gun is not None else None
    n = len(yv)
    s1 = int(n * config.EGITIM_ORANI)
    s2 = int(n * (config.EGITIM_ORANI + config.DOGRULAMA_ORANI))
    egt, dog, tst = _Bolum(Kv[:s1], yv[:s1]), _Bolum(Kv[s1:s2], yv[s1:s2]), _Bolum(Kv[s2:], yv[s2:])
    taban1 = yv[:s1].mean()
    isimler = list(K.columns)
    aileler = np.array([aile(k) for k in isimler])
    m = len(isimler)

    # Tek koşullu sayımlar (vektörel)
    sup = _say(egt.X)
    h1 = _say(egt.X & egt.y1)
    h0 = _say(egt.X & egt.y0)

    adaylar: dict[tuple[tuple[int, ...], int], tuple[int, int]] = {}

    def puan(h, s):
        return wilson_alt(h, s)

    for yon, hy, taban in ((1, h1, taban1), (0, h0, 1 - taban1)):
        if yon not in yonler:
            continue
        seviye = []
        for j in range(m):
            if sup[j] >= min_destek:
                seviye.append(((j,), puan(hy[j], sup[j]), egt.X[j]))
        seviye.sort(key=lambda t: -t[1])
        seviye = seviye[:beam]
        for kom, _, _ in seviye:
            adaylar[(kom, yon)] = None
        yb = egt.y1 if yon == 1 else egt.y0
        for _ in range(max_kosul - 1):
            yeni: dict[tuple[int, ...], tuple[float, np.ndarray, int]] = {}
            for kom, p_ebeveyn, maske in seviye:
                kullanilan = set(aileler[list(kom)])
                ortak = egt.X & maske                       # (m, bytes)
                s = _say(ortak)
                h = _say(ortak & yb)
                for j in np.nonzero(s >= min_destek)[0]:
                    if aileler[j] in kullanilan:
                        continue
                    anahtar = tuple(sorted(kom + (int(j),)))
                    if anahtar in yeni:
                        continue
                    p = puan(int(h[j]), int(s[j]))
                    if p <= p_ebeveyn:          # yeni koşul bir şey katmıyorsa ekleme
                        continue
                    yeni[anahtar] = (p, maske, int(j))   # maske ebeveynin (paylaşımlı), kopya değil
            secim = sorted(yeni.items(), key=lambda t: -t[1][0])[:beam]
            seviye = [(k, v[0], v[1] & egt.X[v[2]]) for k, v in secim]
            if not seviye:
                break
            for kom, _, _ in seviye:
                adaylar[(kom, yon)] = None

    def maske_olustur(b: _Bolum, kom):
        mk = b.hepsi.copy()
        for j in kom:
            mk &= b.X[j]
        return mk

    def istatistik(b: _Bolum, kom, yon, a, z):
        """(n, isabet). Bağımsız olmayan tekrarlar ayıklanır (bkz. ayristir):
        gün sonu hedefinde her günün ilk sinyali, N mumluk hedefte birbirinden N mum uzak sinyaller."""
        mk = maske_olustur(b, kom)
        if gun_v is None and blok <= 1:
            n_, h1_, h0_ = b.say(mk)
            return n_, (h1_ if yon == 1 else h0_)
        idx = ayristir(np.nonzero(np.unpackbits(mk)[:b.n])[0], None if gun_v is None else gun_v[a:z], blok)
        sec = yv[a:z][idx]
        return len(sec), int((sec == yon).sum())

    # Gün sonu hedefinde örnekler "gün" olduğundan eşikler gün sayısına göre
    if esikler is not None:
        min_e, min_d, min_t = esikler
    else:
        min_e, min_d, min_t = (min_destek, max(5, min_test // 2), min_test) if gun_v is None else (25, 12, 20)
    son_satir = K.iloc[-1].to_numpy()
    sonuc: list[Kural] = []
    for (kom, yon) in adaylar:
        if len(kom) < min_kosul:
            continue
        ne, e_h = istatistik(egt, kom, yon, 0, s1)
        if ne < min_e or e_h / ne < min_tutarlilik:
            continue
        nd, d_h = istatistik(dog, kom, yon, s1, s2)
        if nd < min_d or d_h / nd < (min_tutarlilik - 0.05 if gun_v is None else min_tutarlilik):
            continue
        nt, t_h = istatistik(tst, kom, yon, s2, n)
        if nt < min_t or t_h / nt < min_tutarlilik:
            continue
        sonuc.append(Kural(
            kosullar=tuple(isimler[j] for j in kom), hedef=hedef_adi, yon=yon,
            egitim=(ne, e_h), dogrulama=(nd, d_h), test=(nt, t_h), test_gun=nt if gun_v is not None else 0,
            taban_oran=float(yv[s2:].mean() if yon == 1 else 1 - yv[s2:].mean()),
            aktif=bool(all(son_satir[j] for j in kom)),
        ))
    sonuc.sort(key=lambda r: (-wilson_alt(r.test[1], r.test[0]), -r.test[0]))
    return _benzerleri_ele(sonuc)


def _benzerleri_ele(kurallar: list[Kural], maks: int = 300) -> list[Kural]:
    """Daha iyi bir kurala sadece ek koşul ekleyip iyileştirmeyen (üst küme) kuralları gösterme.
    Daha genel (alt küme) kurallar kalır: sık tetiklendikleri için şu an aktif olabilirler."""
    secilen: list[Kural] = []
    for k in kurallar:
        ks = set(k.kosullar)
        if any(s.yon == k.yon and set(s.kosullar) <= ks for s in secilen):
            continue
        secilen.append(k)
        if len(secilen) >= maks:
            break
    return secilen
