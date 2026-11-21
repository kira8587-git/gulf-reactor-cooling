"""Download daily sea-surface temperature for the Gulf sites in data/sites.yaml.

Source: NOAA 1/4-degree Daily Optimum Interpolation SST v2.1 (OISST; Huang et al., 2021,
J. Climate 34, 2923-2939), from the NOAA CoastWatch ERDDAP server.

For each site we take the 3 x 3 block of 0.25-degree cells around it, drop land cells,
and average the two ocean cells nearest the site. The files are already included;
run this only to refresh them or to add a new site:

    python data/download_sst.py                 # every site in data/sites.yaml without a file
    python data/download_sst.py kuwait 28.72 48.38
"""
from __future__ import annotations

import io
import math
import sys
import time
from pathlib import Path

import pandas as pd
import requests
import yaml

HERE = Path(__file__).resolve().parent
BASES = ["https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg_LonPM180.csv",
         "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg.csv"]   # same data, two copies
YEARS = (1982, 2025)


def _cell(x: float) -> float:
    return math.floor(x * 4) / 4 + 0.125


def _fetch(lat: float, lon: float, y0: int, y1: int, tries: int = 6) -> pd.DataFrame:
    la, lo = _cell(lat), _cell(lon)
    q = (f"?sst%5B({y0}-01-01T12:00:00Z):1:({y1}-12-31T12:00:00Z)%5D%5B(0.0)%5D"
         f"%5B({la - 0.25:.3f}):1:({la + 0.25:.3f})%5D%5B({lo - 0.25:.3f}):1:({lo + 0.25:.3f})%5D")
    wait = 10.0
    for k in range(tries):
        for base in BASES:
            try:
                r = requests.get(base + q, timeout=300)
                if r.ok:
                    return pd.read_csv(io.StringIO(r.text), skiprows=[1])
            except requests.RequestException:
                pass
        print(f"  server busy, retry in {wait:.0f} s", flush=True)
        time.sleep(wait)
        wait = min(2 * wait, 300.0)
    raise RuntimeError(f"download failed {y0}-{y1}")


def download(name: str, lat: float, lon: float) -> Path:
    parts = []
    for y0 in range(YEARS[0], YEARS[1] + 1, 5):
        y1 = min(y0 + 4, YEARS[1])
        print(f"[{name}] {y0}-{y1}", flush=True)
        parts.append(_fetch(lat, lon, y0, y1))
    df = pd.concat(parts, ignore_index=True)
    df["date"] = pd.to_datetime(df["time"]).dt.date
    df["cell"] = df.latitude.map("{:.3f}N".format) + "_" + df.longitude.map("{:.3f}E".format)
    wide = df.pivot_table(index="date", columns="cell", values="sst")
    ocean = [c for c in wide.columns if wide[c].notna().mean() > 0.5]
    dist = lambda c: math.hypot(float(c.split("_")[0][:-1]) - lat,
                                (float(c.split("_")[1][:-1]) - lon) * math.cos(math.radians(lat)))
    near = sorted(ocean, key=dist)[:2]
    out = wide[near].copy()
    out["sst_c"] = out.mean(axis=1, skipna=False)
    out = out.dropna(subset=["sst_c"])
    path = HERE / "sst" / f"{name}.csv"
    out.to_csv(path, float_format="%.3f")
    print(f"[{name}] {len(out)} days from cells {near} -> {path.name}", flush=True)
    return path


def main(argv: list[str]) -> int:
    if len(argv) == 3:
        download(argv[0], float(argv[1]), float(argv[2]))
        return 0
    sites = yaml.safe_load((HERE / "sites.yaml").read_text())["sites"]
    for key, s in sites.items():
        if not (HERE / "sst" / f"{key}.csv").exists():
            download(key, s["lat"]["v"], s["lon"]["v"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
