"""Annual heat-sink loss at a site, and the time the sea spends above the choke temperature T*.

Below T* the reactor loses nothing (the turbine is choked); above it the daily loss grows with
the sea temperature. So what decides a site's annual loss is how many days, and by how much, its
sea is warmer than T*, not its hottest day.
"""
from __future__ import annotations

import numpy as np

from .plant import Plant


def loss_curve(plant: Plant, t_grid: np.ndarray) -> np.ndarray:
    """Daily loss (MW) vs sea temperature at design flow: output below the choked (cold-sea) maximum."""
    p_max = plant.gross(plant.t_c_choke)
    return np.array([p_max - plant.solve(float(t))["gross"] for t in t_grid])


def annual_loss(plant: Plant, t_s: np.ndarray, years: float) -> float:
    """MWh per year: the model on every day (interpolated on a 0.1 K grid), times 24 h and the load factor."""
    grid = np.arange(np.floor(np.min(t_s)) - 1, np.ceil(np.max(t_s)) + 1.01, 0.1)
    curve = np.clip(loss_curve(plant, grid), 0.0, None)
    return float(np.interp(t_s, grid, curve).sum() * 24 * plant.r.load_factor / years)


def days_above(t_s: np.ndarray, t_star: float, years: float) -> float:
    """Days per year with the sea warmer than T*."""
    return float((np.asarray(t_s) > t_star).sum() / years)
