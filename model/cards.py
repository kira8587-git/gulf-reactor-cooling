"""Read the reactor and site cards (data/reactors.yaml, data/sites.yaml).

Every number has a value and a source; a missing source is an error.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def _read(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _values(entries: dict, where: str) -> tuple[dict, dict]:
    vals, srcs = {}, {}
    for k, e in entries.items():
        if not isinstance(e, dict) or "v" not in e or not e.get("src"):
            raise ValueError(f"{where}.{k}: needs a value 'v' and a source 'src'")
        v = e["v"]
        if isinstance(v, str) and k not in ("name",):
            raise ValueError(f"{where}.{k}: expected a number, got text {v!r}")
        vals[k], srcs[k] = (float(v) if isinstance(v, (int, float)) else v), e["src"]
    return vals, srcs


@dataclass(frozen=True)
class Reactor:
    key: str
    name: str
    q_th_mw: float
    p_ref_mw: float
    pc_ref_kpa: float
    m_ex_kg_s: float | None
    lp_p_kpa: float
    lp_t_c: float
    eta_lp: float
    a_ex_m2: float | None
    eta_g: float
    dtw_des_k: float          # condenser design water temperature rise (K)
    itd_des_k: float          # condenser design temperature gap: condenser minus sea (K)
    load_factor: float

    def with_(self, **kw) -> "Reactor":
        return replace(self, **kw)


@dataclass(frozen=True)
class Site:
    key: str
    name: str
    lat: float
    lon: float
    salinity: float


def reactors() -> tuple[dict[str, Reactor], dict]:
    raw = _read(DATA / "reactors.yaml")
    out, sources = {}, {}
    for key, entries in raw.items():
        vals, srcs = _values(entries, key)
        out[key] = Reactor(key=key, **vals)
        sources[key] = srcs
    return out, sources


def sites() -> tuple[dict[str, Site], dict, dict]:
    raw = _read(DATA / "sites.yaml")
    out, sources = {}, {}
    for key, entries in raw["sites"].items():
        vals, srcs = _values(entries, key)
        out[key] = Site(key=key, **vals)
        sources[key] = srcs
    common, csrc = _values(raw["common"], "common")
    sources["common"] = csrc
    return out, common, sources
