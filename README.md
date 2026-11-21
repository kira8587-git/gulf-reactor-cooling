# The Cost of a Warm Gulf

A simple, general model of how much electricity any nuclear reactor in the Gulf loses because its cooling water (the sea) is warm.

- **Reactor** = about a dozen public numbers (`data/reactors.yaml`, each with its source).
- **Site** = daily sea temperature from NOAA satellites (`data/sst/`, `data/sites.yaml`).
- **Physics** = 4 equations: energy balance, condenser, last turbine stage, choke.
- **Calibration** = one number (the turbine's effective exhaust area), fitted to the public monthly output in IAEA PRIS of Barakah-1 to -4 and Bushehr-1 (`data/reference/pris_2025_monthly.csv`).
- **Results** = a closed-form sensitivity law and a choke temperature T* below which colder water is worthless; validation on the real output of Barakah's four units and Bushehr-1; losses at 7 Gulf sites for 3 reactor types and under warming; a cost function with one daily decision (cooling-water flow) that prices the 5 °C discharge rule.

**Read:** `report/report.pdf`. Every number's source: `docs/Sources_and_Data.pdf`.

## Run it
Python 3.10 or newer. On Linux or macOS:
```bash
cd gulf_heatsink_model
python -m pip install -r requirements.txt
python run_all.py
```
On Windows (Command Prompt):
```bat
cd /d "C:\D\gulf_heatsink_model"
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python run_all.py
```
This runs the tests and experiments E1–E6 in under a minute, offline. Figures, tables and `summary.json` are written to `results/`.

To rebuild the report with the latest numbers, run `python report/build_report.py`. It always writes `report/report.md`; the PDF step also needs pandoc and Node.js with Playwright. The key presentation slide is made by `python report/make_key_slide.py` (`docs/key_slide.png`).

## Files
| Path | What |
|---|---|
| `model/plant.py` | the four equations (condenser, last stage, choke, closure) |
| `model/law.py` | closed-form sensitivity law |
| `model/calibrate.py` | the one calibration: exhaust area from PRIS monthly output, or from a design heat balance |
| `model/annual.py` | annual loss and days above T* |
| `model/operate.py` | cost function, daily optimal cooling flow, shadow price of the discharge rule |
| `model/props.py`, `model/sea.py`, `model/cards.py` | steam and seawater properties; sea data; reading the cards |
| `experiments.py` | E1 validation · E2 reactor types · E3 Gulf siting · E4 climate · E5 operation · E6 robustness |
| `tests/test_model.py` | tests (run by `run_all.py`) |
| `data/` | reactor and site cards; sea temperature (7 sites); reference data: PRIS monthly output 2025 (Barakah-1, Bushehr-1), APR1400 design heat balance, KNS 2015 condenser table |
| `report/` | report template, build script, finished report |
| `docs/` | `Sources_and_Data.pdf`: the source of every number, formula and figure; `key_slide.png`: the key presentation slide |

## Add a reactor or a site
- **Reactor:** add a card to `data/reactors.yaml`: thermal power, reference output and condenser pressure, LP inlet state, LP efficiency, exhaust area, condenser design rise and gap, load factor. Each value needs a source. Leave the exhaust flow `null` to compute it from the energy balance, and the exhaust area `null` to calibrate it on the reactor's PRIS monthly output (add the rows to `data/reference/pris_2025_monthly.csv`).
- **Site:** add it to `data/sites.yaml` and run `python data/download_sst.py <name> <lat> <lon>`.
