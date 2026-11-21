"""The plant model: four equations.

  (1) heat to reject   Q_c = Q_th - P / eta_g
  (2) condenser        T_c = T_in + Q_c / (eps m c_p),   eps = 1 - exp(-UA / (m c_p))
                       design point: flow V_des = Q_c/(rho c_p dT_w), eps_des = dT_w / ITD
                       UA = UA_des (V / V_des)^0.4        (only used when the flow is changed, E5)
  (3) last turbine     P = P_ref - eta_g m_ex [g(p_e) - g(p_ref)]
      stage            g(p) = h_e(p) + V(p)^2 / 2,   V = m_ex v_e / A_ex
                       h_e(p) = h_in - eta_LP (h_in - h(p, s_in))   (expansion line)
  (4) choke            p_e = max(p_c, p*),  p* = pressure where g is smallest (exhaust "Mach" M = 1)

Only the last turbine stage and the condenser feel the sea (the rest of the cycle
does not see the condenser pressure; Stodola's law: < 0.004 % change in steam flow for 4-12 kPa).
(1) and (2) are solved together by fixed-point iteration (it converges in a few steps
because a 1 K warmer condenser changes Q_c by only ~0.2 %).
"""
from __future__ import annotations

import math

from scipy.optimize import brentq, minimize_scalar

from . import props
from .cards import Reactor

UA_FLOW_EXPONENT = 0.4   # assumed: water side about half of the resistance x Dittus-Boelter exponent 0.8
P_MIN_KPA = 0.62         # lowest pressure searched for the choke: just above the IF97 limit (0.6117 kPa at 0.01 degC)


class Plant:
    def __init__(self, r: Reactor, salinity: float = 42.0, offset_k: float = 0.0):
        if r.a_ex_m2 is None:
            raise ValueError(f"{r.key}: exhaust area unknown (run the calibration, E1)")
        self.r, self.offset = r, offset_k
        self.h_in, self.s_in = props.state_pt(r.lp_p_kpa, r.lp_t_c)
        self.q_c_ref = r.q_th_mw - r.p_ref_mw / r.eta_g
        if r.m_ex_kg_s is None:              # condenser energy balance: Q_c = m_ex x_e h_fg
            e, s = props.expansion_end(r.pc_ref_kpa, self.h_in, self.s_in, r.eta_lp), props.sat_p(r.pc_ref_kpa)
            self.m_ex = self.q_c_ref * 1e3 / (e["x"] * (s["hg"] - s["hf"]))
        else:
            self.m_ex = r.m_ex_kg_s
        self.p_star = self._choke_pressure()
        self.g_ref = self.g(max(r.pc_ref_kpa, self.p_star))
        self.rho, self.cp = props.sw_density(30.0, salinity), props.sw_cp(30.0, salinity)
        self.v_des = self.q_c_ref * 1e3 / (self.rho * self.cp * r.dtw_des_k)              # m3/s
        self.eps_des = r.dtw_des_k / r.itd_des_k                                           # effectiveness at design
        if not 0.0 < self.eps_des < 1.0:
            raise ValueError(f"{r.key}: design rise must be smaller than the design temperature gap")
        self.ua_des = -self.rho * self.v_des * self.cp / 1e3 * math.log(1.0 - self.eps_des)   # MW/K

    # --- turbine -----------------------------------------------------------------
    def g(self, p_kpa: float) -> float:
        """Energy that leaves the last stage per kg: h_e + V^2/2 (kJ/kg)."""
        e = props.expansion_end(p_kpa, self.h_in, self.s_in, self.r.eta_lp)
        v = self.m_ex * e["v"] / self.r.a_ex_m2
        return e["h"] + v * v / 2000.0

    def _choke_pressure(self) -> float:
        res = minimize_scalar(lambda lp: self.g(math.exp(lp)), bounds=(math.log(P_MIN_KPA), math.log(30.0)),
                              method="bounded", options={"xatol": 1e-9})
        return math.exp(res.x)

    def gross(self, t_c: float) -> float:
        """Equations (3)-(4): gross output (MW) at condenser temperature t_c."""
        p_e = max(props.psat(t_c), self.p_star)
        return self.r.p_ref_mw - self.r.eta_g * self.m_ex * (self.g(p_e) - self.g_ref) / 1e3

    def exhaust_velocity(self, p_kpa: float) -> float:
        e = props.expansion_end(max(p_kpa, self.p_star), self.h_in, self.s_in, self.r.eta_lp)
        return self.m_ex * e["v"] / self.r.a_ex_m2

    def mach2(self, p_kpa: float) -> float:
        """M^2 = V^2 / (eta_LP kappa p v_s), kappa = -dln p / dln v_e along the expansion line."""
        e = props.expansion_end(p_kpa, self.h_in, self.s_in, self.r.eta_lp)
        lo = props.expansion_end(p_kpa * (1 - 1e-4), self.h_in, self.s_in, self.r.eta_lp)["v"]
        hi = props.expansion_end(p_kpa * (1 + 1e-4), self.h_in, self.s_in, self.r.eta_lp)["v"]
        kappa = -(math.log(1 + 1e-4) - math.log(1 - 1e-4)) / (math.log(hi) - math.log(lo))
        v = self.m_ex * e["v"] / self.r.a_ex_m2
        return v * v / (self.r.eta_lp * kappa * p_kpa * 1e3 * e["v_s"])

    # --- condenser and closure ---------------------------------------------------
    def solve(self, t_s: float, v_w: float | None = None) -> dict:
        """Operating point at sea temperature t_s with condenser cooling flow v_w (m3/s)."""
        v_w = self.v_des if v_w is None else v_w
        t_in = t_s + self.offset
        mcp = self.rho * v_w * self.cp / 1e3                                   # MW/K
        eps = 1.0 - math.exp(-self.ua_des * (v_w / self.v_des) ** UA_FLOW_EXPONENT / mcp)
        t_c = t_in + 10.0
        for it in range(100):
            q_c = self.r.q_th_mw - self.gross(t_c) / self.r.eta_g
            t_new = t_in + q_c / (eps * mcp)
            if abs(t_new - t_c) < 1e-7:
                break
            t_c = t_new
        else:
            raise RuntimeError("condenser loop did not converge")
        t_c = t_new
        p = self.gross(t_c)
        return {"t_s": t_s, "t_in": t_in, "t_c": t_c, "p_c": props.psat(t_c), "gross": p,
                "q_c": self.r.q_th_mw - p / self.r.eta_g, "eps": eps, "v_w": v_w,
                "rise": (self.r.q_th_mw - p / self.r.eta_g) / mcp, "choked": props.psat(t_c) <= self.p_star,
                "iterations": it + 1}

    @property
    def t_c_choke(self) -> float:
        return props.tsat(self.p_star)

    def t_s_choke(self) -> float:
        """Sea temperature below which colder water gives no more power (design flow)."""
        return brentq(lambda t: self.solve(t)["t_c"] - self.t_c_choke, -5.0, 45.0, xtol=1e-6)
