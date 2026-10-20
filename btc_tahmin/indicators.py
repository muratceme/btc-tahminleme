"""Teknik indikatörler (saf pandas/numpy, dış kütüphane gerektirmez).

Her fonksiyon sadece o anki ve geçmiş mumları kullanır; geleceğe bakış yoktur.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def rma(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1 / n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = rma(d.clip(lower=0), n)
    dn = rma(-d.clip(upper=0), n)
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return rma(tr, n)


def adx(df: pd.DataFrame, n: int = 14):
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(df, n)
    pdi = 100 * rma(pd.Series(plus_dm, index=df.index), n) / a
    mdi = 100 * rma(pd.Series(minus_dm, index=df.index), n) / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return rma(dx, n), pdi, mdi


def stoch(df: pd.DataFrame, n: int = 14, k: int = 3, d: int = 3):
    ll = df["low"].rolling(n).min()
    hh = df["high"].rolling(n).max()
    kk = (100 * (df["close"] - ll) / (hh - ll).replace(0, np.nan)).rolling(k).mean()
    return kk, kk.rolling(d).mean()


def stoch_rsi(close: pd.Series, n: int = 14):
    r = rsi(close, n)
    lo, hi = r.rolling(n).min(), r.rolling(n).max()
    k = (100 * (r - lo) / (hi - lo).replace(0, np.nan)).rolling(3).mean()
    return k, k.rolling(3).mean()


def macd(close: pd.Series, f: int = 12, s: int = 26, sig: int = 9):
    m = ema(close, f) - ema(close, s)
    sg = ema(m, sig)
    return m, sg, m - sg


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    ma = close.rolling(n).mean()
    sd = close.rolling(n).std()
    return ma, ma + k * sd, ma - k * sd


def cci(df: pd.DataFrame, n: int = 20) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    ma = tp.rolling(n).mean()
    md = tp.rolling(n).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return (tp - ma) / (0.015 * md.replace(0, np.nan))


def mfi(df: pd.DataFrame, n: int = 14) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    mf = tp * df["volume"]
    pos = mf.where(tp > tp.shift(), 0.0).rolling(n).sum()
    neg = mf.where(tp < tp.shift(), 0.0).rolling(n).sum()
    return 100 - 100 / (1 + pos / neg.replace(0, np.nan))


def williams_r(df: pd.DataFrame, n: int = 14) -> pd.Series:
    hh = df["high"].rolling(n).max()
    ll = df["low"].rolling(n).min()
    return -100 * (hh - df["close"]) / (hh - ll).replace(0, np.nan)


def obv(df: pd.DataFrame) -> pd.Series:
    return (np.sign(df["close"].diff()).fillna(0) * df["volume"]).cumsum()


def supertrend(df: pd.DataFrame, n: int = 10, mult: float = 3.0) -> pd.Series:
    """+1 yükseliş trendi, -1 düşüş trendi."""
    a = atr(df, n).to_numpy()
    hl2 = ((df["high"] + df["low"]) / 2).to_numpy()
    c = df["close"].to_numpy()
    ub, lb = hl2 + mult * a, hl2 - mult * a
    yon = np.ones(len(df))
    fub, flb = ub.copy(), lb.copy()
    for i in range(1, len(df)):
        fub[i] = ub[i] if (ub[i] < fub[i - 1] or c[i - 1] > fub[i - 1]) else fub[i - 1]
        flb[i] = lb[i] if (lb[i] > flb[i - 1] or c[i - 1] < flb[i - 1]) else flb[i - 1]
        if c[i] > fub[i - 1]:
            yon[i] = 1
        elif c[i] < flb[i - 1]:
            yon[i] = -1
        else:
            yon[i] = yon[i - 1]
    return pd.Series(yon, index=df.index)


def ichimoku(df: pd.DataFrame):
    tenkan = (df["high"].rolling(9).max() + df["low"].rolling(9).min()) / 2
    kijun = (df["high"].rolling(26).max() + df["low"].rolling(26).min()) / 2
    span_a = ((tenkan + kijun) / 2).shift(26)
    span_b = ((df["high"].rolling(52).max() + df["low"].rolling(52).min()) / 2).shift(26)
    return tenkan, kijun, span_a, span_b


def vwap_gunluk(df: pd.DataFrame) -> pd.Series:
    gun = df["time"].dt.floor("D")
    tp = (df["high"] + df["low"] + df["close"]) / 3
    pv = (tp * df["volume"]).groupby(gun).cumsum()
    v = df["volume"].groupby(gun).cumsum()
    return pv / v.replace(0, np.nan)


def hepsini_hesapla(df: pd.DataFrame) -> pd.DataFrame:
    """Ham sürekli indikatör değerlerini ekler (ML modelleri bunları kullanır)."""
    o = df.copy()
    c = o["close"]
    o["rsi"] = rsi(c, 14)
    o["rsi_7"] = rsi(c, 7)
    o["stoch_k"], o["stoch_d"] = stoch(o)
    o["srsi_k"], o["srsi_d"] = stoch_rsi(c)
    o["macd"], o["macd_sig"], o["macd_hist"] = macd(c)
    for n in (9, 21, 50, 100, 200):
        o[f"ema{n}"] = ema(c, n)
    ma, ub, lb = bollinger(c)
    o["bb_pct"] = (c - lb) / (ub - lb).replace(0, np.nan)
    o["bb_genislik"] = (ub - lb) / ma
    o["bb_sikisma"] = o["bb_genislik"] < o["bb_genislik"].rolling(120).quantile(0.15)
    o["adx"], o["pdi"], o["mdi"] = adx(o)
    o["cci"] = cci(o)
    o["mfi"] = mfi(o)
    o["willr"] = williams_r(o)
    o["atr"] = atr(o)
    o["atr_pct"] = o["atr"] / c * 100
    ob = obv(o)
    o["obv_egim"] = (ob - ob.shift(10)) / o["volume"].rolling(10).sum().replace(0, np.nan)
    o["supertrend"] = supertrend(o)
    tk, kj, sa, sb = ichimoku(o)
    o["ichi_ust"] = np.maximum(sa, sb)
    o["ichi_alt"] = np.minimum(sa, sb)
    o["tenkan"], o["kijun"] = tk, kj
    o["vwap"] = vwap_gunluk(o)
    o["vwap_sapma"] = (c / o["vwap"] - 1) * 100
    o["roc_4"] = c.pct_change(4) * 100
    o["roc_16"] = c.pct_change(16) * 100
    o["hacim_z"] = (o["volume"] - o["volume"].rolling(96).mean()) / o["volume"].rolling(96).std()
    o["alis_orani"] = o["taker_buy_base"] / o["volume"].replace(0, np.nan)
    o["donchian_ust"] = o["high"].rolling(20).max().shift()
    o["donchian_alt"] = o["low"].rolling(20).min().shift()
    o["keltner_ust"] = ema(c, 20) + 2 * o["atr"]
    o["keltner_alt"] = ema(c, 20) - 2 * o["atr"]
    o["getiri_1"] = c.pct_change() * 100
    o["gunluk_yuksek_uzak"] = (c / o["high"].rolling(96).max() - 1) * 100
    o["gunluk_dusuk_uzak"] = (c / o["low"].rolling(96).min() - 1) * 100
    return o
