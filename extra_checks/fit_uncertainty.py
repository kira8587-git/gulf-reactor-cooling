"""Extra check, not in the report: how uncertain is the fitted exit area?
Bootstrap of the Barakah fit, two ways:
  (a) resample unit-months within each unit; (b) resample whole calendar months (all units share the month's sea temperature).
Also: degrees of freedom, residual standard deviation, R^2, and the annual loss as a function of the exit area."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
PRJ = Path(__file__).resolve().parents[1]   # repo root
sys.path.insert(0, str(PRJ))
from model import cards, calibrate, annual, sea
from model.plant import Plant
R, _ = cards.reactors(); apr = R["APR1400"]
pts = calibrate.pris_points("APR1400"); pts = pts[pts.full_month].reset_index(drop=True)
y = pts.p_obs_mw.to_numpy(); mon = pts.month.to_numpy(); unit = pts.unit.to_numpy(); units = sorted(set(unit))
grid = np.arange(85.0, 135.01, 0.5)
G = np.array([calibrate._year_curve(apr, round(float(a), 4), 0.0, "barakah")[0] for a in grid])     # (areas, 12 months)
def fit(idx):
    best = None
    for k in range(len(grid)):
        g = G[k][mon[idx] - 1]; r = y[idx] - g
        for u in units:
            m = unit[idx] == u
            if m.any(): r[m] -= r[m].mean()
        sse = float(r @ r)
        if best is None or sse < best[0]: best = (sse, grid[k])
    return best
sse0, a0 = fit(np.arange(len(y)))
n, p = len(y), 1 + len(units)
yc = y - pd.Series(y).groupby(unit).transform("mean").to_numpy()
out = {"n_points": n, "fitted_numbers": p, "degrees_of_freedom": n - p, "a_ex_grid_best": a0,
       "rms_mw": (sse0 / n) ** 0.5, "residual_sd_mw": (sse0 / (n - p)) ** 0.5, "r2_within_unit": 1 - sse0 / float(yc @ yc),
       "distinct_months": int(len(set(mon)))}
rng = np.random.default_rng(2026); B = 2000
a_unit, a_month = [], []
for _ in range(B):
    idx = np.concatenate([rng.choice(np.where(unit == u)[0], size=(unit == u).sum()) for u in units]); a_unit.append(fit(idx)[1])
    ms = rng.choice(sorted(set(mon)), size=len(set(mon))); idx = np.concatenate([np.where(mon == m)[0] for m in ms])
    if all((unit[idx] == u).any() for u in units): a_month.append(fit(idx)[1])
s = sea.load("barakah").loc["1996":"2025", "t_s"].to_numpy(); yrs = len(s) / 365.25
ag = np.arange(85.0, 135.01, 5.0)
loss = np.array([annual.annual_loss(Plant(apr.with_(a_ex_m2=float(a)), 42.0), s, yrs) / 1e3 for a in ag])
L = lambda a: float(np.interp(a, ag, loss))
for name, arr in (("resample_unit_months", a_unit), ("resample_calendar_months", a_month)):
    lo, hi = np.percentile(arr, [2.5, 97.5])
    out[name] = {"reps": len(arr), "a_ex_95": [float(lo), float(hi)], "a_ex_sd": float(np.std(arr)), "loss_gwh_95": [L(lo), L(hi)]}
out["loss_at_best_gwh"] = L(a0)
out["loss_per_m2_gwh"] = float((L(a0 + 5) - L(a0 - 5)) / 10)
print(json.dumps(out, indent=1))
Path(__file__).with_name("fit_uncertainty.json").write_text(json.dumps(out, indent=1))
