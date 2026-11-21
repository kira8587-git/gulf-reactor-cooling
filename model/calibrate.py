"""The one calibration: the effective exhaust area A_ex of the last turbine stage.

A_ex sets how much of a colder sea the turbine can turn into power (through the exhaust loss),
and it is the one number public data rarely give. We obtain it in one of two ways:

  (a) from real operation (preferred): the reactor's monthly output in IAEA PRIS. In months when the
      unit was online all month, its output minus the plant's own losses follows the sea temperature.
      We fit  P_obs(month) = mean over the month's days of P_model(T_s, A_ex) - L,
      where L is a constant (house load and rating), by least squares on A_ex (Brent's method).
  (b) from a design heat balance: the published output gain between two condenser pressures
      (APR1400 design document), solved for A_ex (Brent's method). Used here as a cross-check.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.optimize import brentq, minimize_scalar

from . import cards, props, sea
from .cards import DATA, Reactor
from .plant import Plant

LBH = 0.45359237 / 3600.0          # lb/h -> kg/s (exact definition of the pound)
KPA_PER_INHG = 3.386389            # NIST SP 811
FULL_MONTH = 99.5                  # operating factor (%) for a month to count as "online all month"


# ---------------------------------------------------------------- (a) real operation, IAEA PRIS
def pris_points(reactor_key: str | None = None, add_external: bool = False) -> pd.DataFrame:
    """Monthly PRIS data with the unit's capable output p_obs (MW net) = ref x (LF + plant's own losses).
    add_external=True also adds back the 'external' losses (sensitivity: if they were grid-related, not the sea)."""
    df = pd.read_csv(DATA / "reference" / "pris_2025_monthly.csv", comment="#")
    df["p_obs_mw"] = df.ref_net_mw * (df.lf_pct + 100.0 - df.ucf_pct + (df.xuf_pct if add_external else 0.0)) / 100.0
    df["full_month"] = df.of_pct >= FULL_MONTH
    return df if reactor_key is None else df[df.reactor == reactor_key]


def monthly_gross(plant: Plant, site_key: str, months, year: int = 2025) -> tuple[np.ndarray, np.ndarray]:
    """Model gross output (MW) averaged over the days of each month, and the monthly mean sea temperature."""
    s = sea.load(site_key).loc[str(year), "t_s"]
    grid = np.arange(np.floor(s.min()) - 0.5, np.ceil(s.max()) + 0.55, 0.05)
    curve = np.array([plant.solve(float(t))["gross"] for t in grid])
    g = [np.interp(s[s.index.month == m].to_numpy(), grid, curve).mean() for m in months]
    t = [s[s.index.month == m].mean() for m in months]
    return np.array(g), np.array(t)


@lru_cache(maxsize=None)
def _year_curve(r: Reactor, a_ex: float, offset_k: float, site: str) -> tuple:
    sal = cards.sites()[0][site].salinity
    g, t = monthly_gross(Plant(r.with_(a_ex_m2=a_ex), sal, offset_k), site, list(range(1, 13)))
    return tuple(g), tuple(t)


def compare_output(r: Reactor, a_ex: float, offset_k: float = 0.0, units=None, add_external: bool = False) -> dict:
    """Model vs PRIS for the full months of the chosen units (default: all units of this reactor type),
    with one constant L per unit fitted (house load and rating). Returns the rms (MW) and the table."""
    pts = pris_points(r.key, add_external)
    pts = pts[pts.full_month & (pts.unit.isin(units) if units is not None else True)].reset_index(drop=True)
    site = pts.site.iloc[0]
    g12, t12 = _year_curve(r, round(float(a_ex), 4), float(offset_k), site)
    g = np.array(g12)[pts.month.to_numpy() - 1]
    y = pts.p_obs_mw.to_numpy()
    level = pd.Series(g - y).groupby(pts.unit).transform("mean").to_numpy()
    pred = g - level
    rms = float(np.sqrt(np.mean((y - pred) ** 2)))
    table = pd.DataFrame({"unit": pts.unit, "month": pts.month, "t_s": np.array(t12)[pts.month.to_numpy() - 1],
                          "p_obs_mw": y, "p_model_mw": pred, "level_mw": level})
    return {"a_ex": float(a_ex), "rms_mw": rms, "table": table, "site": site, "units": sorted(pts.unit.unique()),
            "level_mean_mw": float(np.mean(level))}


@lru_cache(maxsize=None)
def _fit_output(r: Reactor, offset_k: float, units: tuple | None = None, add_external: bool = False) -> float:
    res = minimize_scalar(lambda a: compare_output(r, a, offset_k, units, add_external)["rms_mw"], bounds=(40.0, 300.0),
                          method="bounded", options={"xatol": 0.01})
    return float(res.x)


def exhaust_area_from_output(r: Reactor, offset_k: float = 0.0, units=None, add_external: bool = False) -> dict:
    u = tuple(units) if units is not None else None
    return compare_output(r, _fit_output(r, offset_k, u, add_external), offset_k, u, add_external)


# ---------------------------------------------------------------- (b) design heat balance (APR1400 DCD)
def dcd_points() -> pd.DataFrame:
    df = pd.read_csv(DATA / "reference" / "apr1400_dcd_heat_balance.csv", comment="#")
    df["p_c_kpa"] = df.condenser_inhga * KPA_PER_INHG
    df["p_mw"] = df.generator_output_kw / 1e3
    df["m_ex_kg_s"] = df.lp_exhaust_lbh * LBH
    return df


def gain(r: Reactor, a_ex: float, case: str, df: pd.DataFrame | None = None) -> tuple[float, float]:
    """Model and published output gain from 2.6 to 1.5 inHgA for one load case (MW)."""
    df = dcd_points() if df is None else df
    c = df[df.case == case].set_index("condenser_inhga")
    hi, lo = c.loc[2.60], c.loc[1.50]
    pl = Plant(r.with_(a_ex_m2=a_ex, m_ex_kg_s=hi.m_ex_kg_s, p_ref_mw=hi.p_mw, pc_ref_kpa=hi.p_c_kpa))
    model = pl.gross(props.tsat(lo.p_c_kpa)) - pl.gross(props.tsat(hi.p_c_kpa))
    return model, lo.p_mw - hi.p_mw


def exhaust_area(r: Reactor, case: str = "MGR") -> float:
    """A_ex from the design heat balance (APR1400 only)."""
    df = dcd_points()
    return brentq(lambda a: gain(r, a, case, df)[0] - gain(r, a, case, df)[1], 50.0, 400.0, xtol=1e-6)


# ---------------------------------------------------------------- choose
def ready(r: Reactor, offset_k: float = 0.0) -> Reactor:
    """The reactor card with its exhaust area: as given, else calibrated on PRIS output, else on the DCD."""
    if r.a_ex_m2 is not None:
        return r
    if not pris_points(r.key).empty:
        return r.with_(a_ex_m2=_fit_output(r, offset_k))
    if r.key == "APR1400":
        return r.with_(a_ex_m2=exhaust_area(r))
    raise ValueError(f"{r.key}: give a_ex_m2, monthly PRIS data or a heat balance to calibrate it")
