"""Experiments E1-E6. Run:  python experiments.py   (outputs in results/)

E1  validation: APR1400 design heat balance, KNS 2015 condenser, Barakah-1 and Bushehr-1 monthly output
    (IAEA PRIS 2025), closed-form law vs numerical derivative, and the textbook comparison
E2  output and sensitivity vs sea temperature for three reactor types; choke temperature T*
E3  Gulf siting: days above T* and annual loss for every reactor at every site
E4  climate warming: loss vs warming, design-limit and shutdown days
E5  the cost function and the daily decision: optimal cooling flow, price of the 5 degC rule
E6  robustness: one-at-a-time changes of the assumed numbers
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from model import annual, calibrate, cards, law, operate, props, sea  # noqa: E402
from model.plant import Plant  # noqa: E402

OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 160, "font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})
COL = {"APR1400": "#1f5fa8", "VVER1000": "#c0392b", "SMR": "#27864a"}
GULF = ["kuwait", "bushehr", "jubail", "ras_laffan", "saudi_uae_border", "barakah", "fujairah"]
PERIOD = ("1996", "2025")                       # 30 recent years of daily data
TEXTBOOK_PCT_PER_K = 0.45                       # Durmayaz & Sogut (2006), p. 799: 0.45 % of output per 1 degC of cooling water
SUMMARY = {}


def setup():
    R, _ = cards.reactors()
    S, C, _ = cards.sites()
    R = {k: calibrate.ready(r) for k, r in R.items()}
    return R, S, C


def plant(r, site, offset=0.0) -> Plant:
    return Plant(r, site.salinity, offset)


def sites_with_data(S):
    return [k for k in GULF if (cards.DATA / "sst" / f"{k}.csv").exists()]


def period(site_key):
    s = sea.load(site_key).loc[PERIOD[0]:PERIOD[1], "t_s"].to_numpy()
    return s, len(s) / 365.25


# -----------------------------------------------------------------------------
def e1(R, S, C):
    raw, _ = cards.reactors()
    r = R["APR1400"]
    a_dcd = calibrate.exhaust_area(raw["APR1400"])
    r_dcd = raw["APR1400"].with_(a_ex_m2=a_dcd)
    out = {"a_ex_dcd_m2": a_dcd, "a_ex_pris_m2": r.a_ex_m2, "a_ex_vver_m2": R["VVER1000"].a_ex_m2}
    # (a) design heat balance: calibrate on MGR, predict VWO
    m_mgr, d_mgr = calibrate.gain(r_dcd, a_dcd, "MGR")
    m_vwo, d_vwo = calibrate.gain(r_dcd, a_dcd, "VWO")
    out.update(mgr_gain_dcd=d_mgr, vwo_gain_model=m_vwo, vwo_gain_dcd=d_vwo, vwo_gain_error_mw=m_vwo - d_vwo)
    df = calibrate.dcd_points()
    mgr = df[df.case == "MGR"].set_index("condenser_inhga")
    dtc = props.tsat(mgr.loc[2.6].p_c_kpa) - props.tsat(mgr.loc[1.5].p_c_kpa)
    out["dcd_dtc_k"] = dtc
    out["dcd_pct_per_k"] = 100 * d_mgr / mgr.loc[2.6].p_mw / dtc
    no_loss = calibrate.gain(raw["APR1400"], 1e5, "MGR")[0]                 # exhaust loss switched off (V ~ 0)
    out["no_exhaust_loss_gain_mw"] = no_loss
    out["no_exhaust_loss_pct_per_k"] = 100 * no_loss / mgr.loc[2.6].p_mw / dtc
    out["vwo_exhaust_flow_increase_pct"] = 100 * (df[(df.case == "VWO") & (df.condenser_inhga == 2.6)].lp_exhaust_lbh.iloc[0]
                                                  / mgr.loc[2.6].lp_exhaust_lbh - 1)
    # (b) Barakah-1 to -4 monthly output (PRIS 2025): calibration, out-of-sample tests, design-document prediction
    apr = raw["APR1400"]
    fit = calibrate.exhaust_area_from_output(apr)                          # all four units (the card's value)
    pred = calibrate.compare_output(apr, a_dcd)                             # design-document turbine, only L fitted
    ext = calibrate.exhaust_area_from_output(apr, add_external=True)        # if PRIS 'external' losses were not the sea
    units = fit["units"]
    single = {u: calibrate.exhaust_area_from_output(apr, units=[u]) for u in units}
    louo_res = []
    for u in units:                                                          # fit on three units, predict the fourth
        a_o = calibrate.exhaust_area_from_output(apr, units=[x for x in units if x != u])["a_ex"]
        t_u = calibrate.compare_output(apr, a_o, units=[u])["table"]
        louo_res += list(t_u.p_obs_mw - t_u.p_model_mw)
        out[f"louo_a_ex_without_{u}"] = a_o
    tab = fit["table"].assign(p_dcd_model_mw=pred["table"].p_model_mw.to_numpy())
    tab["p_obs_adj_mw"] = tab.p_obs_mw + tab.level_mw - fit["level_mean_mw"]             # unit offsets removed (for plots)

    def slope(col):
        y = tab[col] - tab.groupby("unit")[col].transform("mean")
        x = tab.t_s - tab.groupby("unit").t_s.transform("mean")
        return float(np.sum(x * y) / np.sum(x * x))

    ref = calibrate.pris_points("APR1400").ref_net_mw.iloc[0]
    t_star = plant(r, S["barakah"]).t_s_choke()
    tab.to_csv(OUT / "e1_barakah_pris.csv", index=False)
    lo_u, hi_u = min(single, key=lambda u: single[u]["a_ex"]), max(single, key=lambda u: single[u]["a_ex"])
    out.update(barakah_units=len(units), barakah_unit_months=len(tab), barakah_rms_pris_mw=fit["rms_mw"],
               barakah_rms_dcd_mw=pred["rms_mw"], barakah_rms_ext_mw=ext["rms_mw"], a_ex_ext_m2=ext["a_ex"],
               barakah_louo_rms_mw=float(np.sqrt(np.mean(np.square(louo_res)))),
               a_ex_single={u: single[u]["a_ex"] for u in units}, rms_single={u: single[u]["rms_mw"] for u in units},
               a_ex_single_low_unit=lo_u, a_ex_single_high_unit=hi_u,
               barakah_obs_range_mw=float(tab.p_obs_adj_mw.max() - tab.p_obs_adj_mw.min()),
               barakah_obs_pct_per_k=-100 * slope("p_obs_mw") / ref, barakah_model_pct_per_k=-100 * slope("p_model_mw") / ref,
               barakah_dcd_model_pct_per_k=-100 * slope("p_dcd_model_mw") / ref,
               barakah_tmin=float(tab.t_s.min()), barakah_tmax=float(tab.t_s.max()))
    g12, t12 = (np.array(x) for x in calibrate._year_curve(apr, round(float(fit["a_ex"]), 4), 0.0, "barakah"))
    gd12, _ = (np.array(x) for x in calibrate._year_curve(apr, round(float(a_dcd), 4), 0.0, "barakah"))
    curves = pd.DataFrame({"month": range(1, 13), "t_s": t12, "model_mw": g12 - fit["level_mean_mw"],
                           "dcd_model_mw": gd12 - pred["level_mean_mw"]}).sort_values("t_s")
    curves.to_csv(OUT / "e1_barakah_model_curve.csv", index=False)
    # (c) Bushehr-1 monthly output (PRIS 2025): VVER-1000 card calibrated on it
    vfit = calibrate.exhaust_area_from_output(raw["VVER1000"])
    vfit["table"].to_csv(OUT / "e1_bushehr_pris.csv", index=False)
    out.update(bushehr_rms_mw=vfit["rms_mw"], bushehr_months=len(vfit["table"]),
               bushehr_obs_range_mw=float(vfit["table"].p_obs_mw.max() - vfit["table"].p_obs_mw.min()))
    # (d) condenser temperatures vs the KNS 2015 simulator (Barakah condenser design; design point = August row)
    k = pd.read_csv(cards.DATA / "reference" / "kns2015_table4_barakah_condenser.csv", comment="#")
    pl = plant(r, S["barakah"])
    mcp = pl.rho * pl.v_des * pl.cp / 1e3
    q_c = 3987.0 - k.power_mwe / r.eta_g                                   # KNS thermal power basis 3,987 MWt
    k["tc_model"] = k.sea_temp_c + q_c / (pl.eps_des * mcp)
    k["tc_err"] = k.tc_model - k.t_sat_c
    k.to_csv(OUT / "e1_kns_check.csv", index=False)
    above = k[k.sea_temp_c > t_star]
    out.update(kns_tc_rms_k=float(np.sqrt(np.mean(k.tc_err ** 2))), kns_tc_max_k=float(k.tc_err.abs().max()),
               kns_tc_max_above_tstar_k=float(above.tc_err.abs().max()),
               kns_tc_max_above_25_k=float(k[k.sea_temp_c > 25].tc_err.abs().max()))
    # (e) closed-form law vs numerical derivative, three reactors
    errs = []
    for key in R:
        p = plant(R[key], S["barakah"])
        for tc in np.arange(p.t_c_choke + 1.0, 50.0, 1.0):
            num = (p.gross(tc + 0.01) - p.gross(tc - 0.01)) / 0.02
            errs.append(abs(law.dp_dtc(p, tc) / num - 1))
    out["law_max_rel_error"] = float(max(errs))
    # figure
    fig, ax = plt.subplots(2, 2, figsize=(10, 6.6))
    a = ax[0, 0]
    for case, mk in (("MGR", "o"), ("VWO", "s")):
        c = df[df.case == case].sort_values("p_c_kpa")
        hi = c[c.condenser_inhga == 2.6].iloc[0]
        p = Plant(r_dcd.with_(m_ex_kg_s=hi.m_ex_kg_s, p_ref_mw=hi.p_mw, pc_ref_kpa=hi.p_c_kpa))
        pcs = np.linspace(4.0, 12.0, 60)
        a.plot(pcs, [p.gross(props.tsat(x)) for x in pcs], color=COL["APR1400"], ls="-" if case == "MGR" else "--",
               label=f"model, {case} ({'calibration' if case == 'MGR' else 'prediction'})")
        a.plot(c.p_c_kpa, c.p_mw, mk, color="k", mfc="none", label=f"design document, {case}")
    a.set(xlabel="Condenser pressure (kPa)", ylabel="Gross output (MW)", title="(a) APR1400 design heat balance")
    a.legend(fontsize=6.5)
    a = ax[0, 1]
    for u, mk in zip(units, "osD^"):
        tu = tab[tab.unit == u]
        a.plot(tu.t_s, tu.p_obs_adj_mw, mk, color="k", mfc="none" if u != units[0] else "k", ms=4.5, label=u.title())
    a.plot(curves.t_s, curves.dcd_model_mw, "--", color="grey", label=f"model, design-document turbine (RMS {pred['rms_mw']:.1f} MW)")
    a.plot(curves.t_s, curves.model_mw, "-", color=COL["APR1400"], lw=2, label=f"model, calibrated on Barakah (RMS {fit['rms_mw']:.1f} MW)")
    a.set(xlabel="Monthly mean sea temperature (°C)", ylabel="Net output (MW)", title="(b) Barakah-1 to -4 real output, 2025")
    a.legend(fontsize=6, ncol=2)
    a = ax[1, 0]
    vt = vfit["table"].sort_values("t_s")
    a.plot(vt.t_s, vt.p_obs_mw, "ko", label="Bushehr-1, PRIS 2025 (full months)")
    a.plot(vt.t_s, vt.p_model_mw, "o-", color=COL["VVER1000"], ms=3, label=f"model, VVER-1000 card (RMS {vfit['rms_mw']:.1f} MW)")
    a.set(xlabel="Monthly mean sea temperature (°C)", ylabel="Net output (MW)", title="(c) Bushehr-1 real output")
    a.legend(fontsize=6.5)
    a = ax[1, 1]
    a.plot(k.t_sat_c, k.tc_model, "o", color=COL["APR1400"])
    lim = [k.t_sat_c.min() - 1, k.t_sat_c.max() + 1]
    a.plot(lim, lim, "k--", lw=0.8)
    a.set(xlabel="Simulator condenser temperature (°C)", ylabel="Model (°C)", title="(d) Condenser vs KNS 2015 simulator")
    fig.tight_layout()
    fig.savefig(OUT / "fig_e1_validation.png")
    plt.close(fig)
    SUMMARY["E1"] = out
    return out


# -----------------------------------------------------------------------------
def e2(R, S, C):
    t = np.arange(14.0, 38.51, 0.5)
    rows, out = [], {}
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.4))
    for key, r in R.items():
        p = plant(r, S["barakah"])
        g = np.array([p.solve(x)["gross"] for x in t])
        sig = 100 * np.gradient(g, t) / g
        t_star = p.t_s_choke()
        eta = p.solve(30.0)["gross"] / r.q_th_mw
        rows += [{"reactor": key, "t_s": a, "gross": b, "sigma_pct_per_k": c} for a, b, c in zip(t, g, sig)]
        out[key] = {"t_star_sea_c": t_star, "t_star_condenser_c": p.t_c_choke, "efficiency_at_30c": eta,
                    "sigma_at_30c": float(np.interp(30, t, sig)), "sigma_at_35c": float(np.interp(35, t, sig)),
                    "rule_m0_pct_per_k": law.sigma_rule(eta, 40.0, r.eta_lp), "m_ex_kg_s": p.m_ex, "a_ex_m2": r.a_ex_m2,
                    "exhaust_velocity_ref_m_s": p.exhaust_velocity(r.pc_ref_kpa), "v_des_m3_s": p.v_des, "eps_des": p.eps_des}
        ax[0].plot(t, 100 * (g / g.max() - 1), color=COL[key], label=r.name.split(" (")[0])
        ax[0].axvline(t_star, color=COL[key], ls=":", lw=0.8)
        ax[1].plot(t, sig, color=COL[key], label=f"{r.name.split(' (')[0]} (T* = {t_star:.1f} °C)")
    ax[1].axhline(-TEXTBOOK_PCT_PER_K, color="grey", ls="--", lw=1, label="textbook 0.45 %/°C (Durmayaz & Sogut 2006)")
    ax[0].set(xlabel="Sea temperature (°C)", ylabel="Output change (%)", title="Output vs sea temperature")
    ax[0].legend(fontsize=7)
    ax[1].set(xlabel="Sea temperature (°C)", ylabel="Sensitivity (% per °C)", title="Sensitivity and choke temperature T*")
    ax[1].legend(fontsize=6.5, loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_e2_sensitivity.png")
    plt.close(fig)
    pd.DataFrame(rows).to_csv(OUT / "e2_output_curves.csv", index=False)
    SUMMARY["E2"] = out
    return out


# -----------------------------------------------------------------------------
def e3(R, S, C):
    rows = []
    for sk in sites_with_data(S):
        df = sea.load(sk)
        s, yrs = period(sk)
        tr = sea.trend_per_decade(df)
        for rk, r in R.items():
            p = plant(r, S[sk])
            t_star = p.t_s_choke()
            loss = annual.annual_loss(p, s, yrs)
            potential = p.gross(p.t_c_choke) * 8760 * r.load_factor
            rows.append({"site": sk, "site_name": S[sk].name, "reactor": rk, "mean_t_s": s.mean(),
                         "aug_mean": df.loc[PERIOD[0]:PERIOD[1]].query("index.dt.month == 8").t_s.mean(),
                         "max_t_s": s.max(), "trend_per_decade": tr[0], "t_star": t_star,
                         "days_above_t_star": annual.days_above(s, t_star, yrs), "loss_gwh": loss / 1e3,
                         "loss_pct": 100 * loss / potential, "loss_maed": loss * C["price_aed_mwh"] / 1e6,
                         "co2_kt": loss * C["ef_t_mwh"] / 1e3})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "e3_gulf_siting.csv", index=False)
    names = [S[k].name for k in sites_with_data(S)]
    piv = df.pivot(index="site_name", columns="reactor", values="loss_pct").reindex(names)
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 3.6), gridspec_kw={"width_ratios": [1, 1.3]})
    a = df[df.reactor == "APR1400"].set_index("site_name").reindex(names)
    ax[0].barh(a.index, a.days_above_t_star, color="#5b7fa6")
    ax[0].invert_yaxis()
    ax[0].set(xlabel=f"Days per year with the sea above T* ({a.t_star.iloc[0]:.1f} °C), APR1400", title="Time above T*")
    w = 0.27
    y = np.arange(len(piv))
    for i, rk in enumerate(R):
        ax[1].barh(y + (i - 1) * w, piv[rk], height=w, color=COL[rk], label=R[rk].name.split(" (")[0])
    ax[1].set_yticks(y, piv.index)
    ax[1].invert_yaxis()
    ax[1].set(xlabel="Annual heat-sink loss (% of cold-sea output)", title="Loss by site and reactor",
              xlim=(0, 1.45 * float(piv.max().max())))
    ax[1].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / "fig_e3_siting.png")
    plt.close(fig)
    SUMMARY["E3"] = {"table": df.to_dict(orient="records")}
    return {"rows": len(df)}


# -----------------------------------------------------------------------------
def e4(R, S, C):
    r = R["APR1400"]
    p = plant(r, S["barakah"])
    s, yrs = period("barakah")
    p_max = p.gross(p.t_c_choke)
    rows = []
    for d in np.arange(0.0, 3.01, 0.5):
        x = s + d
        shut = float((x > C["t_shutdown_c"]).sum() / yrs)
        rows.append({"delta_k": d, "loss_gwh": annual.annual_loss(p, np.minimum(x, C["t_shutdown_c"]), yrs) / 1e3,
                     "days_above_design": float((x > C["t_design_c"]).sum() / yrs), "days_shutdown": shut,
                     "shutdown_gwh": shut * 24 * r.load_factor * p_max / 1e3})
    df = pd.DataFrame(rows)
    df["total_gwh"] = df.loss_gwh + df.shutdown_gwh
    df.to_csv(OUT / "e4_climate.csv", index=False)
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.3))
    ax[0].plot(df.delta_k, df.loss_gwh, "o-", color=COL["APR1400"], label="efficiency loss")
    ax[0].plot(df.delta_k, df.total_gwh, "s-", color="#b9770e", label="+ shutdown days above 38.5 °C")
    ax[0].set(xlabel="Warming of the Gulf (K)", ylabel="Energy lost per unit (GWh/yr)", title="Barakah, APR1400")
    ax[0].legend(fontsize=7)
    ax[1].bar(df.delta_k - 0.1, df.days_above_design, width=0.2, label="days above 36.5 °C (design)")
    ax[1].bar(df.delta_k + 0.1, df.days_shutdown, width=0.2, label="days above 38.5 °C (shutdown)")
    ax[1].set(xlabel="Warming of the Gulf (K)", ylabel="Days per year", title="Limit days (1996-2025 weather + warming)")
    ax[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_e4_climate.png")
    plt.close(fig)
    second = np.diff(df.total_gwh.to_numpy(), 2)
    SUMMARY["E4"] = {"table": df.to_dict(orient="records"), "convex": bool((second > 0).all())}
    return SUMMARY["E4"]


# -----------------------------------------------------------------------------
def e5(R, S, C):
    r = R["APR1400"]
    p = plant(r, S["barakah"])
    t = np.arange(14.0, 38.51, 0.5)
    rows = []
    for x in t:
        b, d = operate.best(p, float(x), C), operate.design(p, float(x), C)
        rows.append({"t_s": x, "v_w_opt": b["v_w"], "v_b_opt": b["v_b"], "net_opt": b["net"], "net_design": d["net"],
                     "v_b_design": d["v_b"], "gain_mw": b["net"] - d["net"], "pump_opt": b["pump"], "pump_design": d["pump"]})
    df = pd.DataFrame(rows)
    s, yrs = period("barakah")
    gain_gwh = float(np.interp(s, df.t_s, df.gain_mw).sum() * 24 * r.load_factor / yrs / 1e3)
    months = sea.typical_year(sea.load("barakah"))
    mid = [pd.Timestamp(2001, m, 15).dayofyear for m in range(1, 13)]                      # 15th of each month
    mt = pd.DataFrame({"month": range(1, 13), "t_s": [months[d - 1] for d in mid]})
    mt["shadow_price_mw_per_k"] = [operate.shadow_price(p, float(x), C) for x in mt.t_s]
    df.to_csv(OUT / "e5_operation.csv", index=False)
    mt.to_csv(OUT / "e5_shadow_price.csv", index=False)
    fig, ax = plt.subplots(1, 3, figsize=(11, 3.2))
    ax[0].plot(df.t_s, df.v_w_opt, color=COL["APR1400"], label="condenser flow (optimal)")
    ax[0].plot(df.t_s, df.v_b_opt, color=COL["APR1400"], ls="--", label="dilution flow (optimal)")
    ax[0].axhline(p.v_des, color="grey", label="design condenser flow")
    ax[0].set(xlabel="Sea temperature (°C)", ylabel="Flow (m³/s)", title="The daily decision")
    ax[0].legend(fontsize=7)
    ax[1].plot(df.t_s, df.gain_mw, color=COL["APR1400"])
    ax[1].set(xlabel="Sea temperature (°C)", ylabel="Net output gained (MW)", title="Optimal vs design operation")
    ax[2].plot(mt.t_s, mt.shadow_price_mw_per_k, "o-", color=COL["VVER1000"])
    ax[2].set(xlabel="Monthly mean sea temperature (°C)", ylabel="MW per K", title="Price of the 5 °C discharge rule")
    fig.tight_layout()
    fig.savefig(OUT / "fig_e5_operation.png")
    plt.close(fig)
    lam = mt.shadow_price_mw_per_k.mean()
    SUMMARY["E5"] = {"annual_gain_gwh_per_unit": gain_gwh, "gain_at_20c_mw": float(np.interp(20, df.t_s, df.gain_mw)),
                     "gain_at_34c_mw": float(np.interp(34, df.t_s, df.gain_mw)), "v_des_m3_s": p.v_des,
                     "v_b_design_m3_s": float(np.interp(30, df.t_s, df.v_b_design)),
                     "shadow_price_mw_per_k": [float(mt.shadow_price_mw_per_k.min()), float(mt.shadow_price_mw_per_k.max())],
                     "shadow_price_maed_per_k_yr_per_unit": float(lam * 8760 * r.load_factor * C["price_aed_mwh"] / 1e6)}
    return SUMMARY["E5"]


# -----------------------------------------------------------------------------
def e6(R, S, C):
    raw, _ = cards.reactors()
    base = R["APR1400"]
    s, yrs = period("barakah")
    sal = S["barakah"].salinity

    def run(r, offset=0.0, recal=True):
        if recal:
            r = calibrate.ready(r.with_(a_ex_m2=None), offset)
        p = Plant(r, sal, offset)
        return annual.annual_loss(p, s, yrs) / 1e3, p.t_s_choke(), r.a_ex_m2

    ref = run(base, recal=False)
    a_dcd = calibrate.exhaust_area(raw["APR1400"])
    lf_lo, lf_hi = 0.706, 0.849               # lowest / highest PRIS lifetime load factor of a Barakah unit (Barakah-4 page; Barakah-1 statistics service)
    single = {u: calibrate.exhaust_area_from_output(raw["APR1400"], units=[u])["a_ex"] for u in
              calibrate.exhaust_area_from_output(raw["APR1400"])["units"]}
    a_ext = calibrate.exhaust_area_from_output(raw["APR1400"], add_external=True)["a_ex"]
    cases = [("LP efficiency 0.84 / 0.90 (A_ex re-calibrated)", dict(eta_lp=0.84), dict(eta_lp=0.90), True),
             ("LP inlet temperature 245 / 275 °C (re-calibrated)", dict(lp_t_c=245.0), dict(lp_t_c=275.0), True),
             ("Condenser gap ITD 8.9 / 9.9 K (re-calibrated)", dict(itd_des_k=8.9), dict(itd_des_k=9.9), True),
             ("Load factor 0.706 / 0.849 (PRIS range, Barakah units)", dict(load_factor=lf_lo), dict(load_factor=lf_hi), False),
             ("Calibrated on one unit only (lowest / highest)", dict(a_ex_m2=min(single.values())), dict(a_ex_m2=max(single.values())), False),
             ("PRIS external losses: grid / sea (base)", dict(a_ex_m2=a_ext), dict(a_ex_m2=base.a_ex_m2), False),
             ("Turbine from design document / Barakah output", dict(a_ex_m2=a_dcd), dict(a_ex_m2=base.a_ex_m2), False)]
    rows = []
    for name, lo, hi, recal in cases:
        a, b = run(base.with_(**lo), recal=recal), run(base.with_(**hi), recal=recal)
        rows.append({"change": name, "low_gwh": a[0], "high_gwh": b[0], "low_t_star": a[1], "high_t_star": b[1],
                     "low_a_ex": a[2], "high_a_ex": b[2]})
    a, b = run(base, 0.0, True), run(base, 1.5, True)
    rows.append({"change": "Intake 0 / +1.5 K warmer than satellite (re-calibrated)", "low_gwh": a[0], "high_gwh": b[0],
                 "low_t_star": a[1], "high_t_star": b[1], "low_a_ex": a[2], "high_a_ex": b[2]})
    df = pd.DataFrame(rows)
    df["swing"] = (df.high_gwh - df.low_gwh).abs()
    df = df.sort_values("swing")
    df.to_csv(OUT / "e6_robustness.csv", index=False)
    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    for i, rr in enumerate(df.itertuples()):
        ax.plot([rr.low_gwh, rr.high_gwh], [i, i], color="#5b7fa6", lw=6, solid_capstyle="butt")
    ax.axvline(ref[0], color="k", lw=1)
    ax.set_yticks(range(len(df)), df.change, fontsize=7.5)
    ax.set(xlabel="Annual heat-sink loss per unit, Barakah (GWh/yr)", title=f"Robustness (baseline {ref[0]:.0f} GWh/yr)")
    fig.tight_layout()
    fig.savefig(OUT / "fig_e6_robustness.png")
    plt.close(fig)
    SUMMARY["E6"] = {"baseline_gwh": ref[0], "baseline_t_star": ref[1], "rows": df.to_dict(orient="records")}
    return SUMMARY["E6"]


def main(argv):
    R, S, C = setup()
    for name in (argv or ["e1", "e2", "e3", "e4", "e5", "e6"]):
        print(f"--- {name.upper()}", flush=True)
        res = globals()[name](R, S, C)
        print(json.dumps(res, indent=1, default=float)[:1500], flush=True)
    old = json.loads((OUT / "summary.json").read_text()) if (OUT / "summary.json").exists() and argv else {}
    old.update(SUMMARY)
    (OUT / "summary.json").write_text(json.dumps(old, indent=2, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
