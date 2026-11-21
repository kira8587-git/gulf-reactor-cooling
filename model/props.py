"""Water, steam and seawater properties.

Steam: IAPWS-IF97, the international standard (Wagner et al., 2000), via the `iapws` package.
In the wet region a state is a mix of saturated liquid and vapour, so
    x = (s - s_f)/(s_g - s_f),   h = h_f + x h_fg,   v = v_f + x v_fg      (lever rule)
Seawater: Sharqawy, Lienhard & Zubair (2010), eqs. (8) and (9).

Units: kPa, degC, kJ/kg, kJ/(kg K), m3/kg, kg/m3, g/kg.
"""
from __future__ import annotations

from functools import lru_cache

from iapws import IAPWS97
from iapws import iapws97 as _if97

T0 = 273.15
G = 9.81


@lru_cache(maxsize=None)
def sat_p(p_kpa: float) -> dict:
    """Saturation properties at pressure p (kPa)."""
    p = p_kpa / 1000.0
    t = _if97._TSat_P(p)
    liq, vap = _if97._Region1(t, p), _if97._Region2(t, p)
    return {"t": t - T0, "p": p_kpa, "hf": liq["h"], "hg": vap["h"], "sf": liq["s"], "sg": vap["s"],
            "vf": liq["v"], "vg": vap["v"]}


def tsat(p_kpa: float) -> float:
    return sat_p(p_kpa)["t"]


@lru_cache(maxsize=None)
def psat(t_c: float) -> float:
    return _if97._PSat_T(t_c + T0) * 1000.0


def state_pt(p_kpa: float, t_c: float) -> tuple[float, float]:
    """(h, s) of superheated steam at (p, T)."""
    w = IAPWS97(P=p_kpa / 1000.0, T=t_c + T0)
    return w.h, w.s


def state_sat_vapour(p_kpa: float) -> tuple[float, float]:
    s = sat_p(p_kpa)
    return s["hg"], s["sg"]


def expansion_end(p_kpa: float, h_in: float, s_in: float, eta: float) -> dict:
    """End of a turbine expansion to pressure p with isentropic efficiency eta.
    Returns actual (h, v, x) and isentropic (x_s, v_s) end points (wet region)."""
    s = sat_p(p_kpa)
    x_s = (s_in - s["sf"]) / (s["sg"] - s["sf"])
    if not 0.0 < x_s < 1.0:
        raise ValueError("expansion end point is not in the wet region")
    h_s = s["hf"] + x_s * (s["hg"] - s["hf"])
    h = h_in - eta * (h_in - h_s)
    x = (h - s["hf"]) / (s["hg"] - s["hf"])
    return {"h": h, "v": s["vf"] + x * (s["vg"] - s["vf"]), "x": x,
            "x_s": x_s, "v_s": s["vf"] + x_s * (s["vg"] - s["vf"])}


def sw_density(t_c: float, s_gkg: float) -> float:
    """Seawater density, kg/m3 (Sharqawy et al. 2010, eq. 8)."""
    t, s = t_c, s_gkg / 1000.0
    rw = 9.999e2 + 2.034e-2 * t - 6.162e-3 * t**2 + 2.261e-5 * t**3 - 4.657e-8 * t**4
    return rw + s * (8.020e2 - 2.001 * t + 1.677e-2 * t**2 - 3.060e-5 * t**3 - 1.613e-5 * s * t**2)


def sw_cp(t_c: float, s_gkg: float) -> float:
    """Seawater specific heat, kJ/(kg K) (Sharqawy et al. 2010, eq. 9)."""
    S, T = s_gkg, t_c + T0
    a = 5.328 - 9.76e-2 * S + 4.04e-4 * S**2
    b = -6.913e-3 + 7.351e-4 * S - 3.15e-6 * S**2
    c = 9.6e-6 - 1.927e-6 * S + 8.23e-9 * S**2
    d = 2.5e-9 + 1.666e-9 * S - 7.125e-12 * S**2
    return a + b * T + c * T**2 + d * T**3
