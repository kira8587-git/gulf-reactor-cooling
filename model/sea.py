"""Daily sea temperature at a site: loading, gap filling, typical year, trend.

Gaps (NOAA's server copy misses ~1,200 days, mostly 1992-1998) are filled with the
1991-2020 mean for that day of the year plus the linearly interpolated departure
from it; every filled day is flagged.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .cards import DATA


def _doy(idx: pd.DatetimeIndex) -> np.ndarray:
    d = idx.dayofyear.to_numpy().copy()
    d[idx.is_leap_year & (d >= 60)] -= 1                      # 29 Feb -> 28 Feb
    return d


def climatology(s: pd.Series, years=(1991, 2020), smooth: int = 15) -> np.ndarray:
    """Mean for each of 365 days, smoothed with a 15-day moving average that wraps the year."""
    s = s[(s.index.year >= years[0]) & (s.index.year <= years[1])].dropna()
    m = s.groupby(_doy(s.index)).mean().reindex(range(1, 366)).interpolate(limit_direction="both").to_numpy()
    k = smooth // 2
    return np.convolve(np.r_[m[-k:], m, m[:k]], np.ones(smooth) / smooth, mode="valid")


def load(site_key: str) -> pd.DataFrame:
    raw = pd.read_csv(DATA / "sst" / f"{site_key}.csv", parse_dates=["date"]).set_index("date")["sst_c"]
    full = pd.date_range(raw.index.min(), raw.index.max(), freq="D")
    s = raw.reindex(full)
    clim = climatology(s)[_doy(full) - 1]
    anom = pd.Series(s.to_numpy() - clim, index=full).interpolate(limit_direction="both").to_numpy()
    out = pd.DataFrame({"t_s": np.where(s.isna(), clim + anom, s.to_numpy()), "filled": s.isna().to_numpy()},
                       index=full)
    out.index.name = "date"
    return out


def typical_year(df: pd.DataFrame) -> np.ndarray:
    return climatology(df["t_s"])


def trend_per_decade(df: pd.DataFrame, last_year: int = 2025) -> tuple[float, float]:
    """Least-squares trend of annual means, degC per decade, with its standard error."""
    y = df["t_s"].groupby(df.index.year).mean()
    y = y[y.index <= last_year]
    x, v = y.index.to_numpy(float), y.to_numpy()
    xm = x.mean()
    b = np.sum((x - xm) * (v - v.mean())) / np.sum((x - xm) ** 2)
    a = v.mean() - b * xm
    se = np.sqrt(np.sum((v - a - b * x) ** 2) / (len(x) - 2) / np.sum((x - xm) ** 2))
    return 10 * b, 10 * se
