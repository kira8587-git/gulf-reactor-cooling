# Extra checks

Checks added after the main report. Each script runs from the repo root and writes its results next to itself.

| Script | What it checks | Output |
|---|---|---|
| `fit_uncertainty.py` | How uncertain the fitted exit area is (bootstrap), plus fit statistics | `fit_uncertainty.json` |
| `cost_by_month.py` | The yearly loss of one APR1400 unit at Barakah, split by month and priced at 200 AED/MWh (a scenario value) | `cost_by_month.json`, `cost_by_month.png` |

**Bootstrap, in one paragraph.** The exit area is fitted to 36 monthly data points. To see how much it depends on which points we happened to have, the fit is repeated many times on resampled data (points drawn at random, with replacement). The spread of the refitted areas gives a 95 % interval: 105.5–112.5 m² when single unit-months are resampled, and 101–114 m² when whole calendar months are resampled. The second is wider and more honest, because all four units share each month's sea temperature, so the 36 points carry only 12 independent temperatures. That interval puts the annual loss at about 126–176 GWh per unit.

Run: `python extra_checks/fit_uncertainty.py` and `python extra_checks/cost_by_month.py`
