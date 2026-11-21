"""The exhaust-choke law: a closed-form sensitivity for any steam-cycle reactor.

Differentiating equation (3) with Gibbs (dh_e/dp = eta_LP v_s) and Clausius-Clapeyron
(dp/dT = h_fg / (T v_fg)) gives, exactly for this model,

    dP/dT_c = - eta_g eta_LP m_ex (v_s / v_fg) h_fg / T_c  (1 - M^2)        (choked: 0)

and, using Q_c ~ m_ex x_e h_fg and v_s/v_fg ~ x_s, the relative form

    sigma = (1/P) dP/dT_c ~ - eta_LP (x_s/x_e) (1 - eta)/eta (1/T_c) (1 - M^2)

With M -> 0 (no exhaust loss) this gives the textbook value, about 0.45 % per degC of cooling
water (Durmayaz & Sogut, 2006, whose heat-balance model neglects kinetic energy). Real turbines
have M > 0, so the textbook value is an upper bound, and below the choke (M = 1) colder water
gives nothing.
"""
from __future__ import annotations

from . import props
from .plant import Plant


def dp_dtc(plant: Plant, t_c: float) -> float:
    """Closed-form dP/dT_c in MW/K."""
    p = props.psat(t_c)
    if p <= plant.p_star:
        return 0.0
    s = props.sat_p(p)
    e = props.expansion_end(p, plant.h_in, plant.s_in, plant.r.eta_lp)
    t_k = t_c + props.T0
    return (-plant.r.eta_g * plant.r.eta_lp * plant.m_ex * (e["v_s"] / (s["vg"] - s["vf"]))
            * (s["hg"] - s["hf"]) / t_k * (1.0 - plant.mach2(p)) / 1e3)


def sigma_rule(eta_cycle: float, t_c: float = 40.0, eta_lp: float = 0.87, xs_over_xe: float = 0.95,
               mach2: float = 0.0) -> float:
    """Relative form, in % per K."""
    return -100.0 * eta_lp * xs_over_xe * (1.0 - eta_cycle) / eta_cycle / (t_c + props.T0) * (1.0 - mach2)
