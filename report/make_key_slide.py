"""Make the key presentation slide (16:9): Barakah's real output vs sea temperature, with the model.

    python report/make_key_slide.py        (after run_all.py and build_report.py)
Writes docs/key_slide.png and docs/key_slide.pdf.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES, DOCS = ROOT / "results", ROOT / "docs"
DOCS.mkdir(exist_ok=True)
S = json.loads((RES / "summary.json").read_text())
T = json.loads((RES / "report_numbers.json").read_text())
tab = pd.read_csv(RES / "e1_barakah_pris.csv")
cur = pd.read_csv(RES / "e1_barakah_model_curve.csv").sort_values("t_s")
REF = 1337.0                                     # Barakah reference unit power (net), PRIS
TEXTBOOK = 0.45                                  # % per degC, Durmayaz & Sogut (2006)

plt.rcParams.update({"font.size": 12, "axes.spines.top": False, "axes.spines.right": False})
fig = plt.figure(figsize=(13.33, 7.5))
fig.text(0.04, 0.93, "Barakah's real output follows the sea, and the model follows Barakah",
         fontsize=24, weight="bold", color="#0f2a44")
fig.text(0.04, 0.885, "Monthly net output of Barakah-1 to -4 in 2025 (IAEA PRIS) against the monthly mean sea temperature (NOAA)",
         fontsize=13, color="#444")

ax = fig.add_axes([0.06, 0.13, 0.55, 0.70])
for u, mk in zip(sorted(tab.unit.unique()), "osD^"):
    tu = tab[tab.unit == u]
    ax.plot(tu.t_s, tu.p_obs_adj_mw, mk, ms=8, mfc="white", mec="k", mew=1.4, label=u.title())
x0 = cur.t_s.min()
y0 = float(cur.model_mw.iloc[0])
xs = [x0, cur.t_s.max()]
ax.plot(xs, [y0, y0 - TEXTBOOK / 100 * REF * (xs[1] - x0)], ":", color="#c0392b", lw=2.2, label="textbook, 0.45 % per °C")
ax.plot(cur.t_s, cur.dcd_model_mw, "--", color="grey", lw=1.8, label="model, US design-document turbine")
ax.plot(cur.t_s, cur.model_mw, "-", color="#1f5fa8", lw=3, label="model, calibrated on Barakah")
ax.set_xlim(cur.t_s.min() - 0.8, cur.t_s.max() + 0.8)
ax.set_xlabel("Monthly mean sea temperature (°C)")
ax.set_ylabel("Net output per unit (MW)")
ax.grid(alpha=0.3)
ax.legend(fontsize=10, loc="lower left", ncol=2, frameon=False)

boxes = [(f"{T['E1.barakah_obs_pct']} % per °C", f"what Barakah really loses per °C of\nsea temperature, not the textbook 0.45 %"),
         (f"{T['E3.barakah_gwh']} GWh / yr", f"lost per unit to the warm sea ({T['E3.barakah_pct']} %,\nabout {T['E3.barakah_maed']} million AED; range {T['E6.range_low']}–{T['E6.range_high']})"),
         (f"{T['E1.louo']} MW", f"error when the model predicts\nan unseen Barakah unit, month by month")]
for i, (big, small) in enumerate(boxes):
    y = 0.70 - i * 0.235
    fig.patches.append(matplotlib.patches.FancyBboxPatch((0.655, y - 0.055), 0.31, 0.19, boxstyle="round,pad=0.008",
                                                         transform=fig.transFigure, fc="#eef4f9", ec="#3b6e99", lw=1.2))
    fig.text(0.675, y + 0.07, big, fontsize=26, weight="bold", color="#0f2a44", va="center")
    fig.text(0.675, y - 0.005, small, fontsize=13, color="#333", va="center")
fig.text(0.04, 0.035, "Model: four equations (energy balance, condenser, last turbine stage, choke) and one number calibrated on public data. "
         "Data: IAEA PRIS; NOAA OISST v2.1; ENEC; APR1400 design document.", fontsize=10, color="#666")
fig.savefig(DOCS / "key_slide.png", dpi=150)
fig.savefig(DOCS / "key_slide.pdf")
print("wrote docs/key_slide.png and docs/key_slide.pdf")
