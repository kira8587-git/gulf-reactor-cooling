"""Fill report_template.md with the numbers in results/ and make report.md (and report.pdf).

    python report/build_report.py          (run python run_all.py first)

Every result number in the report comes from results/ (unrounded) and is rounded once, here.
The PDF step needs pandoc and Node.js with Playwright; without them only report.md is made.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from model import annual, calibrate, cards, sea  # noqa: E402
from model.plant import Plant  # noqa: E402

RES = ROOT / "results"
S = json.loads((RES / "summary.json").read_text())
RAW, _ = cards.reactors()
SITES, C, _ = cards.sites()
R = {k: calibrate.ready(r) for k, r in RAW.items()}
E3 = pd.read_csv(RES / "e3_gulf_siting.csv")
E4 = pd.read_csv(RES / "e4_climate.csv")
E6 = pd.read_csv(RES / "e6_robustness.csv").set_index("change")
f0 = lambda x: f"{x:,.0f}"
f1 = lambda x: f"{x:,.1f}"
f2 = lambda x: f"{x:,.2f}"


def up(x: float, step: float) -> str:
    """Round UP to the given step (for 'at most' and 'below' statements)."""
    v = math.ceil(x / step - 1e-9) * step
    d = max(0, -int(math.floor(math.log10(step))))
    return f"{v:.{d}f}"


def tokens() -> dict:
    e1, e2, e5, e6 = S["E1"], S["E2"], S["E5"], S["E6"]
    bar = E3[(E3.site == "barakah") & (E3.reactor == "APR1400")].iloc[0]
    fuj = E3[(E3.site == "fujairah") & (E3.reactor == "APR1400")].iloc[0]
    mex = Plant(R["APR1400"].with_(m_ex_kg_s=None), SITES["barakah"].salinity).m_ex
    pl = Plant(R["APR1400"], SITES["barakah"].salinity)
    iters = max(pl.solve(t)["iterations"] for t in np.arange(15.0, 35.01, 0.5))
    tst = [e2[k]["t_star_sea_c"] for k in e2]
    sig = [e2[k][f"sigma_at_{t}c"] for k in e2 for t in (30, 35)]
    diff = fuj.loss_pct - bar.loss_pct
    fvs = "about as much as" if abs(diff) < 0.03 else ("slightly more than" if diff > 0 else "slightly less than")
    recal = [n for n in E6.index if "re-calibrated" in n]
    recal_max = max(max(abs(E6.loc[n, "low_gwh"] / e6["baseline_gwh"] - 1), abs(E6.loc[n, "high_gwh"] / e6["baseline_gwh"] - 1))
                    for n in recal) * 100
    turbine = [n for n in E6.index if n.startswith("Turbine")][0]
    lf = [n for n in E6.index if n.startswith("Load factor")][0]
    ext = [n for n in E6.index if n.startswith("PRIS external")][0]
    one = [n for n in E6.index if n.startswith("Calibrated on one unit")][0]
    sb = sea.load("barakah").loc["1996":"2025"]
    aug = sb[sb.index.month == 8].t_s.to_numpy()
    grid = np.arange(np.floor(aug.min()) - 0.5, np.ceil(aug.max()) + 0.55, 0.1)
    aug_loss = float(np.interp(aug, grid, annual.loss_curve(pl, grid)).mean())
    model_lines = sum(len(f.read_text().splitlines()) for f in (ROOT / "model").glob("*.py"))
    rest_lines = sum(len((ROOT / f).read_text().splitlines()) for f in ("experiments.py", "tests/test_model.py"))
    n_tests = len(re.findall(r"^def test_", (ROOT / "tests" / "test_model.py").read_text(), re.M))
    a = R["APR1400"]
    return {
        "E1.barakah_obs_pct": f2(e1["barakah_obs_pct_per_k"]), "E1.barakah_dcd_pct": f2(e1["barakah_dcd_model_pct_per_k"]),
        "E1.barakah_rms_pris": f1(e1["barakah_rms_pris_mw"]), "E1.barakah_rms_dcd": f1(e1["barakah_rms_dcd_mw"]),
        "E1.unit_months": str(e1["barakah_unit_months"]), "E1.barakah_range": f0(e1["barakah_obs_range_mw"]),
        "E1.louo": f1(e1["barakah_louo_rms_mw"]), "E1.rms_ext": f1(e1["barakah_rms_ext_mw"]),
        "E1.a_single_range": f"{min(e1['a_ex_single'].values()):.0f}–{max(e1['a_ex_single'].values()):.0f}",
        "E1.bushehr_rms": f1(e1["bushehr_rms_mw"]), "E1.bushehr_months": str(e1["bushehr_months"]),
        "E1.bushehr_range": f0(e1["bushehr_obs_range_mw"]),
        "E1.a_pris": f1(e1["a_ex_pris_m2"]), "E1.a_dcd": f1(e1["a_ex_dcd_m2"]), "E1.a_vver": f1(e1["a_ex_vver_m2"]),
        "E1.a_ratio": f0(100 * (e1["a_ex_pris_m2"] / e1["a_ex_dcd_m2"] - 1)),
        "E1.vwo_model": f1(e1["vwo_gain_model"]), "E1.vwo_dcd": f1(e1["vwo_gain_dcd"]), "E1.vwo_err": f1(e1["vwo_gain_error_mw"]),
        "E1.vwo_flow": f0(e1["vwo_exhaust_flow_increase_pct"]), "E1.mex_rule": f0(mex),
        "E1.noloss_pct": f2(e1["no_exhaust_loss_pct_per_k"]), "E1.dcd_pct": f2(e1["dcd_pct_per_k"]),
        "E1.kns_rms": f2(e1["kns_tc_rms_k"]), "E1.kns_max": f2(e1["kns_tc_max_k"]), "E1.kns_max1": f2(e1["kns_tc_max_k"]),
        "E1.kns_max25": up(e1["kns_tc_max_above_25_k"], 0.1),
        "E1.law_err": up(100 * e1["law_max_rel_error"], 0.0001) + " %",
        "E2.rule_apr": f2(abs(e2["APR1400"]["rule_m0_pct_per_k"])), "E2.iterations": str(iters),
        "E2.tstar_range": f"{round(min(tst))}–{round(max(tst))}",
        "E2.sigma_range": f"{max(sig):.2f} to {min(sig):.2f}".replace("-", "−"),
        "E3.barakah_gwh": f0(bar.loss_gwh), "E3.barakah_pct": f2(bar.loss_pct), "E3.barakah_maed": f0(bar.loss_maed),
        "E3.barakah_4units_maed": f0(4 * bar.loss_maed), "E3.barakah_aug": f1(bar.aug_mean),
        "E3.barakah_trend": f2(bar.trend_per_decade), "E3.fujairah_aug": f1(fuj.aug_mean), "E3.fujairah_vs": fvs,
        "E3.gradient": " → ".join(f"{r.site_name.split(' (')[0].split(',')[0]} {r.loss_pct:.2f} %" for r in
                                  E3[(E3.reactor == "APR1400") & (E3.site != "fujairah")].itertuples()),
        "E5.gain20": f1(e5["gain_at_20c_mw"]), "E5.annual": f0(e5["annual_gain_gwh_per_unit"]),
        "E5.lam": f"{e5['shadow_price_mw_per_k'][0]:.2f}–{e5['shadow_price_mw_per_k'][1]:.2f}",
        "E5.lam_maed": f1(e5["shadow_price_maed_per_k_yr_per_unit"]), "E5.v_b": f0(e5["v_b_design_m3_s"]),
        "E6.base": f0(e6["baseline_gwh"]), "E6.turbine_low": f0(E6.loc[turbine, "low_gwh"]),
        "E6.lf_high": f0(E6.loc[lf, "high_gwh"]), "E6.lf_low": f0(E6.loc[lf, "low_gwh"]), "E6.recal_max": up(recal_max, 0.1),
        "E6.ext_low": f0(E6.loc[ext, "low_gwh"]), "E6.single_low": f0(E6.loc[one, "low_gwh"]), "E6.single_high": f0(E6.loc[one, "high_gwh"]),
        "E6.range_low": f0(min(E6.loc[ext, "low_gwh"], E6.loc[one, "low_gwh"], E6.loc[turbine, "low_gwh"])),
        "E6.range_high": f0(max(E6.loc[one, "high_gwh"], bar.loss_gwh)),
        "E3.aug_loss_mw": f0(aug_loss),
        "E3.kuwait_pct": f2(E3[(E3.site == "kuwait") & (E3.reactor == "APR1400")].loss_pct.iloc[0]),
        "E4.plus2_pct": f0(100 * (E4[np.isclose(E4.delta_k, 2.0)].loss_gwh.iloc[0] / E4[np.isclose(E4.delta_k, 0.0)].loss_gwh.iloc[0] - 1)),
        "R.dtw": f2(a.dtw_des_k), "R.dtw1": f1(a.dtw_des_k), "R.itd": f1(a.itd_des_k),
        "CODE.model": f"{round(model_lines, -1):,}", "CODE.rest": f"{round(rest_lines, -1):,}", "CODE.tests": str(n_tests),
    }


def tables() -> dict:
    out = {}
    plants = {k: Plant(r, SITES["barakah"].salinity) for k, r in R.items()}
    calib = {"APR1400": "calibrated, Barakah-1 to -4", "VVER1000": "calibrated, Bushehr-1"}

    def mex(k):
        return f"{plants[k].m_ex:,.0f}" + ("" if RAW[k].m_ex_kg_s else " (rule)")

    def aex(k):
        return f"{R[k].a_ex_m2:,.1f}" + (f" ({calib.get(k, 'calibrated')})" if RAW[k].a_ex_m2 is None else " (assumed)")

    rows = [("$\\dot Q_\\mathrm{th}$", "heat into the steam cycle (MW)", lambda k: f"{R[k].q_th_mw:,.0f}"),
            ("$P_\\mathrm{ref}$", "gross output at the reference pressure (MW)", lambda k: f"{R[k].p_ref_mw:,.1f}"),
            ("$p_\\mathrm{ref}$", "reference condenser pressure (kPa)", lambda k: f"{R[k].pc_ref_kpa:.2f}"),
            ("$\\dot m_\\mathrm{ex}$", "LP exhaust steam flow (kg/s)", mex),
            ("$p_\\mathrm{in}, T_\\mathrm{in}$", "LP turbine inlet (kPa, °C)", lambda k: f"{R[k].lp_p_kpa:,.0f}, {R[k].lp_t_c:.0f}"),
            ("$\\eta_\\mathrm{LP}$, $\\eta_g$", "LP and generator efficiency", lambda k: f"{R[k].eta_lp:.2f}, {R[k].eta_g:.3f}"),
            ("$A_\\mathrm{ex}$", "effective exhaust area (m²)", aex),
            ("$\\Delta T_w$, ITD", "condenser design: water rise, condenser–sea gap (K)", lambda k: f"{R[k].dtw_des_k:.2f}, {R[k].itd_des_k:.1f}"),
            ("LF", "load factor", lambda k: f"{R[k].load_factor:.3f}")]
    out["reactor_cards"] = "\n".join(f"| {s} | {m} | " + " | ".join(fn(k) for k in R) + " |" for s, m, fn in rows)
    order = list(dict.fromkeys(E3.site))
    a = E3[E3.reactor == "APR1400"].set_index("site")
    out["sites"] = "\n".join(f"| {a.loc[s, 'site_name']} | {a.loc[s, 'mean_t_s']:.1f} | {a.loc[s, 'aug_mean']:.1f} | "
                             f"{a.loc[s, 'max_t_s']:.1f} | {a.loc[s, 'trend_per_decade']:+.2f} |" for s in order)
    e2 = S["E2"]
    keys = list(R)
    lines = [("Plant efficiency at 30 °C sea", lambda k: f"{100 * e2[k]['efficiency_at_30c']:.1f} %"),
             ("Choke temperature T* (sea)", lambda k: f"{e2[k]['t_star_sea_c']:.1f} °C"),
             ("Sensitivity at 30 °C", lambda k: f"{e2[k]['sigma_at_30c']:.2f} %/°C"),
             ("Sensitivity at 35 °C", lambda k: f"{e2[k]['sigma_at_35c']:.2f} %/°C"),
             ("No-exhaust-loss limit, eq. (6) with M = 0", lambda k: f"{e2[k]['rule_m0_pct_per_k']:.2f} %/°C"),
             ("Exhaust velocity at the reference pressure", lambda k: f"{e2[k]['exhaust_velocity_ref_m_s']:.0f} m/s")]
    out["e2"] = "\n".join(f"| {n} | " + " | ".join(fn(k) for k in keys) + " |" for n, fn in lines).replace("-", "−").replace("No−exhaust−loss", "No-exhaust-loss")
    piv = E3.pivot(index="site", columns="reactor", values="loss_pct")
    hdr = ("| Site | Days above T* (APR1400) | APR1400 loss (GWh/yr per unit) | APR1400 (%) | VVER-1000 (%) | SMR (%) |\n"
           "|---|---|---|---|---|---|\n")
    out["e3"] = hdr + "\n".join(f"| {a.loc[s, 'site_name']} | {a.loc[s, 'days_above_t_star']:.0f} | {a.loc[s, 'loss_gwh']:.0f} | "
                                f"{piv.loc[s, 'APR1400']:.2f} | {piv.loc[s, 'VVER1000']:.2f} | {piv.loc[s, 'SMR']:.2f} |" for s in order)
    out["e4"] = "\n".join(f"| +{r.delta_k:.1f} | {r.loss_gwh:.0f} | {r.days_above_design:.1f} | {r.days_shutdown:.1f} | "
                          f"{r.total_gwh:.0f} |" for r in E4.itertuples())
    return out


def main():
    text = (HERE / "report_template.md").read_text(encoding="utf-8")
    tok = tokens()
    for k, v in tok.items():
        text = text.replace("{{" + k + "}}", v)
    for k, v in tables().items():
        text = text.replace("{{TABLE." + k + "}}", v)
    if "{{" in text:
        raise SystemExit("unfilled placeholder: " + text[text.index("{{"):text.index("{{") + 40])
    (HERE / "report.md").write_text(text, encoding="utf-8")
    (RES / "report_numbers.json").write_text(json.dumps(tok, indent=1, ensure_ascii=False))
    print("wrote report/report.md")
    if shutil.which("pandoc") and shutil.which("node"):
        html = HERE / "report.html"
        mj = HERE / "vendor" / "tex-svg.js"                     # MathJax 3 (Apache-2.0), bundled for offline builds
        math = f"--mathjax={mj}" if mj.exists() else "--mathml"
        subprocess.run(["pandoc", str(HERE / "report.md"), "-f", "markdown+lists_without_preceding_blankline",
                        "-t", "html5", "-s", math, "--embed-resources", "--resource-path", str(HERE),
                        "--css", str(HERE / "style.css"), "--metadata", "pagetitle=The Cost of a Warm Gulf",
                        "-o", str(html)], check=True)
        npm = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
        subprocess.run(["node", str(HERE / "topdf.js"), str(html), str(HERE / "report.pdf"), "The Cost of a Warm Gulf"],
                       check=True, env={**os.environ, "NODE_PATH": npm})
        print("wrote report/report.pdf")


if __name__ == "__main__":
    main()
