"""The cost function and the one daily decision.

Cost of a warm sea (per day):   J = price x [P_best - P_net] x 24 h
Decision u: condenser cooling flow V_w (the bypass V_b dilutes the warm outflow).

    maximise   P_net(V_w) = P_gross(T_c(V_w)) - P_pump(V_w, V_b)
    subject to (V_w + V_b) >= Q_c / (rho c_p dT_max)      discharge rule  (V_b = cheapest bypass)
               V_w >= V_w,min (tube velocity),  V_w + V_b <= V_max (intake capacity)
    P_pump = rho g [ V_w (H_s + H_f (V_w/V_des)^2) + V_b H_b ] / eta_p

One variable on an interval: an optimum exists (Weierstrass) and a bounded scalar
search finds it. The shadow price of the discharge rule is the gain in optimal net
output per degree of relaxation (envelope theorem), by finite difference.
"""
from __future__ import annotations

from scipy.optimize import minimize_scalar

from . import props
from .plant import Plant


def evaluate(plant: Plant, t_s: float, v_w: float, c: dict, dt_max: float) -> dict:
    op = plant.solve(t_s, v_w)
    need = op["q_c"] * 1e3 / (plant.rho * plant.cp * dt_max)
    v_b = max(0.0, need - v_w)
    pump = plant.rho * props.G * (v_w * (c["pump_static_m"] + c["pump_friction_m"] * (v_w / plant.v_des) ** 2)
                                  + v_b * c["bypass_head_m"]) / c["pump_eff"] / 1e6
    ok = v_w + v_b <= c["flow_max_factor"] * plant.v_des + 1e-9
    return {**op, "v_b": v_b, "pump": pump, "net": op["gross"] - pump, "ok": ok}


def best(plant: Plant, t_s: float, c: dict, dt_max: float | None = None) -> dict:
    """Optimal condenser flow for one day."""
    dt_max = c["dt_max_k"] if dt_max is None else dt_max
    lo, hi = c["flow_min_factor"] * plant.v_des, c["flow_max_factor"] * plant.v_des
    f = lambda v: -evaluate(plant, t_s, v, c, dt_max)["net"] if evaluate(plant, t_s, v, c, dt_max)["ok"] else 1e9
    res = minimize_scalar(f, bounds=(lo, hi), method="bounded", options={"xatol": 1e-3})
    return evaluate(plant, t_s, float(res.x), c, dt_max)


def design(plant: Plant, t_s: float, c: dict) -> dict:
    """Reference operation: design condenser flow, bypass only if the rule needs it."""
    return evaluate(plant, t_s, plant.v_des, c, c["dt_max_k"])


def shadow_price(plant: Plant, t_s: float, c: dict, d: float = 0.25) -> float:
    """MW of optimal net output gained per K of relaxation of the discharge rule."""
    up = best(plant, t_s, c, c["dt_max_k"] + d)["net"]
    dn = best(plant, t_s, c, c["dt_max_k"] - d)["net"]
    return (up - dn) / (2 * d)
