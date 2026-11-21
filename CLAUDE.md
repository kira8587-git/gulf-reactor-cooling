# Project context for Claude

## What this is
`gulf-reactor-cooling`: a simple, general model of how much electricity a
steam-cycle nuclear reactor loses because its cooling water (the sea) is warm.
Gulf focus. Barakah (APR1400, UAE) is the main example and Bushehr-1 (VVER-1000,
Iran) is a second check. Single author. Public repo, to be extended later with
more details and use cases.

## Rules
- Single author. Do not mention any competition, slides, co-authors or group work anywhere in the repo.
- v1 code, data and results are frozen (tag `v1.0`). Do not change them.
- Keep explanations simple. Every number must have a source (see
  `docs/source_register.csv`). No mistakes: check numbers against `results/`.
- Say "simple first-law model" (Durmayaz & Sogut 2006, 0.45 %/°C) rather than
  "textbook value" in new writing.
- The author will rebuild the model as v2. For v2, give hints and explanations,
  not finished code. Use the v1 numbers below as the answer key.

## The model: 4 equations and 1 fitted number
1. Energy balance: Q_c = Q_th - P/eta_g
2. Condenser (eps-NTU): T_c = T_s + Q_c/(eps m c_p). Design: water warms 6.26 K
   (ENEC, 100 m3/s); condenser 9.4 K above the sea (KNS 2015); eps = 0.666.
3. Last turbine stage: P = P_ref - eta_g m_ex [g(p_e) - g(p_ref)],
   g = h_e + V^2/2, V = m_ex v_e / A_ex
4. Choke: p_e = max(p_c, p*), p* = argmin g
- Fitted: effective exhaust area A_ex = 109.1 m2, from IAEA PRIS 2025 monthly
  output of Barakah-1 to -4 (36 unit-months, plus one constant per unit).
  The APR1400 design document (DCD) gives 96.8 m2.
- Law: loss per degC = (simple first-law value) x (1 - M^2). M = 0 if the exit
  speed is ignored, 1 at the choke.

## Frozen v1 results (answer key)
- Fit RMS: 3.1 MW (all units), 3.3 MW (unit left out), 5.0 MW (DCD area, only
  each unit's constant fitted). Bushehr-1: 5.1 MW (5 months).
- Loss per degC: simple first-law model 0.45 %; this model with exhaust loss off
  0.44 %; DCD turbine 0.24 %; Barakah real 0.26 %.
- Choke sea temperature T* = 19.3 degC (APR1400); Barakah's sea is above it
  about 355 days a year.
- Annual loss 157 GWh per unit (1.55 %), range 101-172. +2 degC warming: 208 GWh.
- Sites (APR1400): Kuwait 1.15 % -> Barakah 1.55 % -> Fujairah 1.59 %.
- Bootstrap 95 % interval for A_ex: 105.5-112.5 m2 (unit-month resampling),
  101-114 m2 (calendar-month) -> 126-176 GWh.

## Known weaknesses (research list)
- Only one year of data (12 distinct months); points not independent.
- Satellite sea-surface temperature, not measured intake temperature.
- Choke not seen directly in data (coldest month 20.3 degC).
- PRIS "external" summer losses counted as heat; if grid losses, 101 GWh.
- Condenser heat-transfer coefficient held constant.
- SMR card not calibrated.

## Licences
MIT for code; CC BY 4.0 for report and figures (`LICENSE-REPORT.md`); data
under its sources' terms (NOAA public domain, IAEA PRIS own terms).

## Run
`python -m pip install -r requirements.txt && python run_all.py` (tests, then
experiments E1-E6, about a minute, offline). Report: `python report/build_report.py`.
