"""Tests: properties, physics, the law, calibration and validation, annual loss, the decision, the data."""
import sys
from pathlib import Path

import numpy as np
import pytest
from iapws import IAPWS97

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from model import annual, calibrate, cards, law, operate, props, sea  # noqa: E402
from model.plant import Plant  # noqa: E402


@pytest.fixture(scope="module")
def setup():
    R, _ = cards.reactors()
    S, C, _ = cards.sites()
    R = {k: calibrate.ready(r) for k, r in R.items()}
    P = {k: Plant(r, S["barakah"].salinity) for k, r in R.items()}
    return R, S, C, P


# properties -------------------------------------------------------------------
def test_steam_tables_match_iapws_reference_points():
    assert props.tsat(100.0) + props.T0 == pytest.approx(372.755919, abs=1e-5)       # IF97 Table 36
    assert props.psat(300.0 - props.T0) == pytest.approx(3.53658941, rel=1e-7)        # IF97 Table 35 (kPa)


def test_wet_expansion_matches_full_iapws():
    h_in, s_in = props.state_pt(1333.0, 260.0)
    e = props.expansion_end(8.0, h_in, s_in, 1.0)
    assert e["h"] == pytest.approx(IAPWS97(P=0.008, s=s_in).h, abs=1e-6)


def test_seawater_properties():
    assert props.sw_density(25, 35) == pytest.approx(1023.3, abs=0.6)                # TEOS-10: 1023.34
    assert props.sw_cp(25, 35) == pytest.approx(3.999, rel=0.003)                     # TEOS-10: 3.999


# physics ------------------------------------------------------------------------
def test_condenser_design_point(setup):
    _, _, _, P = setup
    p = P["APR1400"]
    assert p.v_des == pytest.approx(100.0, rel=0.002)                                 # ENEC: 6,000 m3/min
    o = p.solve(30.0)
    mcp = p.rho * p.v_des * p.cp / 1e3
    assert o["t_c"] - o["t_in"] == pytest.approx(o["q_c"] / (o["eps"] * mcp), rel=1e-6)
    assert o["q_c"] + o["gross"] / p.r.eta_g == pytest.approx(p.r.q_th_mw)            # energy balance
    assert o["iterations"] < 15


def test_choke_is_the_maximum_and_continuous(setup):
    _, _, _, P = setup
    for p in P.values():
        pmax = p.gross(p.t_c_choke)
        assert all(p.gross(t) <= pmax + 1e-9 for t in np.arange(15, 50, 0.5))
        assert p.gross(p.t_c_choke - 3) == pytest.approx(pmax)                     # flat below the choke
        assert abs(p.gross(p.t_c_choke + 0.01) - pmax) < 1e-3                       # no jump


def test_choke_search_stays_inside_the_steam_tables(setup):
    R, S, _, _ = setup
    p = Plant(R["APR1400"].with_(a_ex_m2=1e5), S["barakah"].salinity)              # no exhaust loss at all
    assert p.p_star >= 0.62 - 1e-9


def test_law_equals_numerical_derivative(setup):
    _, _, _, P = setup
    for p in P.values():
        for tc in np.arange(p.t_c_choke + 1, 50, 3.0):
            num = (p.gross(tc + 0.01) - p.gross(tc - 0.01)) / 0.02
            assert law.dp_dtc(p, tc) == pytest.approx(num, rel=1e-3)
        assert law.dp_dtc(p, p.t_c_choke - 1) == 0.0


def test_textbook_value_is_an_upper_bound(setup):
    _, _, _, P = setup
    assert -0.50 < law.sigma_rule(0.36) < -0.40
    for p in P.values():
        g = [p.solve(t)["gross"] for t in (29.5, 30.5)]
        assert abs(100 * (g[1] - g[0]) / g[0]) < abs(law.sigma_rule(g[0] / p.r.q_th_mw))


def test_exhaust_flow_rule_matches_the_heat_balance(setup):
    R, S, _, _ = setup
    p = Plant(R["APR1400"].with_(m_ex_kg_s=None), S["barakah"].salinity)
    assert p.m_ex == pytest.approx(1176.0, rel=0.06)


# calibration and validation ------------------------------------------------------
def test_design_document_calibration_and_prediction(setup):
    R, _, _, _ = setup
    r = R["APR1400"].with_(a_ex_m2=None)
    a = calibrate.exhaust_area(r)
    m, d = calibrate.gain(r, a, "MGR")
    assert m == pytest.approx(d, abs=1e-3)                                           # calibration
    m, d = calibrate.gain(r, a, "VWO")
    assert abs(m - d) < 2.0                                                          # prediction


def test_real_output_barakah_and_bushehr(setup):
    raw, _ = cards.reactors()
    a_dcd = calibrate.exhaust_area(raw["APR1400"])
    assert calibrate.compare_output(raw["APR1400"], a_dcd)["rms_mw"] < 8.0         # prediction from the DCD alone
    assert calibrate.exhaust_area_from_output(raw["APR1400"])["rms_mw"] < 4.0       # calibrated on Barakah-1 to -4
    one = calibrate.exhaust_area_from_output(raw["APR1400"], units=["BARAKAH-1", "BARAKAH-2", "BARAKAH-3"])["a_ex"]
    assert calibrate.compare_output(raw["APR1400"], one, units=["BARAKAH-4"])["rms_mw"] < 5.0   # predicts the 4th unit
    assert calibrate.exhaust_area_from_output(raw["VVER1000"])["rms_mw"] < 7.0      # calibrated on Bushehr-1


# annual loss, climate, decision ------------------------------------------------------
def test_no_loss_when_the_sea_stays_below_t_star(setup):
    _, _, _, P = setup
    p = P["APR1400"]
    cold = np.full(365, p.t_s_choke() - 2.0)
    assert annual.annual_loss(p, cold, 1.0) == pytest.approx(0.0, abs=1e-6)
    assert annual.days_above(cold, p.t_s_choke(), 1.0) == 0


def test_warming_cost_is_convex(setup):
    _, _, _, P = setup
    p = P["APR1400"]
    s = sea.load("barakah").loc["2016":"2025", "t_s"].to_numpy()
    loss = [annual.annual_loss(p, s + d, 10) for d in (0.0, 1.0, 2.0)]
    assert loss[2] - 2 * loss[1] + loss[0] > 0


def test_optimal_operation(setup):
    _, _, C, P = setup
    p = P["APR1400"]
    for t in (20.0, 30.0, 35.0):
        b, d = operate.best(p, t, C), operate.design(p, t, C)
        assert b["net"] >= d["net"] - 1e-6
        assert b["q_c"] * 1e3 / (p.rho * p.cp * (b["v_w"] + b["v_b"])) <= C["dt_max_k"] + 1e-6
        assert b["ok"] and d["ok"]
    assert operate.shadow_price(p, 30.0, C) > 0


# data -------------------------------------------------------------------------------
def test_every_number_has_a_source():
    with pytest.raises(ValueError):
        cards._values({"x": {"v": 1.0}}, "test")
    with pytest.raises(ValueError):
        cards._values({"x": {"v": "1.0e6", "src": "text read from YAML"}}, "test")


def test_sea_data_gap_filling_and_trend():
    df = sea.load("barakah")
    assert not df.t_s.isna().any() and df.filled.sum() == 1194
    assert sea.trend_per_decade(df)[0] == pytest.approx(0.36, abs=0.05)
