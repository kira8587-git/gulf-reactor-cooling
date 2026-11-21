"""Monthly cost of the warm sea for one Barakah unit. Uses the v1 model and data."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = Path(__file__).resolve().parent
PRJ = HERE.parent   # repo root
sys.path.insert(0, str(PRJ))
from model import cards, calibrate, annual, sea
from model.plant import Plant
R, _ = cards.reactors(); S, C, _ = cards.sites()
r = calibrate.ready(R["APR1400"]); p = Plant(r, S["barakah"].salinity)
s = sea.load("barakah").loc["1996":"2025", "t_s"]
grid = np.arange(np.floor(s.min()) - 1, np.ceil(s.max()) + 1.01, 0.1)
curve = np.clip(annual.loss_curve(p, grid), 0, None)
loss_mw = pd.Series(np.interp(s.to_numpy(), grid, curve), index=s.index)
yrs = len(s) / 365.25
gwh = loss_mw.groupby(loss_mw.index.month).sum() * 24 * r.load_factor / yrs / 1e3      # GWh per calendar month, per unit
maed = gwh * C["price_aed_mwh"] / 1e3
mw = loss_mw.groupby(loss_mw.index.month).mean()
out = {"annual_gwh": float(gwh.sum()), "annual_maed": float(maed.sum()), "monthly_maed": [round(float(x), 2) for x in maed],
       "monthly_mean_loss_mw": [round(float(x), 1) for x in mw], "price_aed_mwh": C["price_aed_mwh"],
       "summer_share_jun_sep": float(maed.loc[6:9].sum() / maed.sum())}
print(json.dumps(out))
(HERE / "cost_by_month.json").write_text(json.dumps(out, indent=1))
plt.rcParams.update({"font.size": 13, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(8.6, 4.3))
names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
bars = ax.bar(names, maed.to_numpy(), color=["#c0392b" if m in (6, 7, 8, 9) else "#1f5fa8" for m in range(1, 13)])
for b, v in zip(bars, maed.to_numpy()):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.08, f"{v:.1f}", ha="center", fontsize=11)
ax.set_ylabel("Million AED per month, one unit")
ax.set_title(f"Cost of the warm sea by month: {maed.sum():.0f} million AED a year per unit", fontsize=14, weight="bold", color="#0f2a44")
ax.grid(axis="y", alpha=0.3)
fig.tight_layout(); fig.savefig(HERE / "cost_by_month.png", dpi=170)
