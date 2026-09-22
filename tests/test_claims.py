"""Jede Zahl in den Hilfetexten, Presets, Tabellen und Grenzen der App und der README ist hier über die 100 festen
Karten (DIST_SEEDS) bzw. die festen Sweep-/Manipulations-Seedmengen belegt. Alles rechnet mit ganzen Zahlen und einem
eigenen Zufallsgenerator - die Werte sind auf jeder Plattform dieselben; die Toleranzen decken nur die Rundung auf die
im Text genannten Stellen."""

import pytest

import hr_evaluation as ev


def near(value, expected, tol):
    assert abs(value - expected) <= tol, f"{value:.4f} statt {expected}"


@pytest.fixture(scope="module")
def dist():
    return ev.distribution(20, 5, 40, 0, 120)


def test_default_map_family(dist):
    d = dist
    near(d["degree"], 1.7395, 0.001)
    near(d["count"]["mean"], 15.2, 0.05)
    assert d["count"]["median"] == 15.0 and (d["count"]["min"], d["count"]["max"]) == (10, 20)
    near(d["unmatched"]["mean"], 4.8, 0.05)
    assert d["unmatched"]["median"] == 5.0


def test_rural_hospitals_visibility(dist):
    d = dist
    assert d["any_under_share"] == 1.0                                    # bei Quote 120% IMMER mindestens eine Klinik nicht voll
    near(d["under_count"]["mean"], 2.82, 0.005)
    assert d["under_count"]["median"] == 3.0 and (d["under_count"]["min"], d["under_count"]["max"]) == (1, 5)
    near(d["same_ro_ho_share"], 0.99, 0.005)                              # fast immer eindeutig (noise-Vorlieben)


def test_effort(dist):
    d = dist
    near(d["proposals"]["mean"], 19.0, 0.05)
    assert d["proposals"]["median"] == 19.0 and (d["proposals"]["min"], d["proposals"]["max"]) == (12, 27)


def test_price_of_stability(dist):
    d = dist
    near(d["premium"]["mean"], 10.11, 0.05)
    near(d["premium"]["median"], 9.04, 0.05)
    assert d["premium"]["min"] == 0.0


def test_quote_sweep_crosses_from_scarcity_to_rural_hospitals():
    """Unter 100% bleiben Bewerber unversorgt (Knappheit); ab 100% kippt die Geschichte: fast immer eine Klinik
    unbesetzt (Landklinikensatz) - und die unversorgten Bewerber sinken weiter, je mehr Kapazitaet dazu kommt."""
    rows = {r["quote"]: r for r in ev.quote_sweep(20, 5, 40)}
    expect_under = {60: 0.525, 80: 0.95, 100: 1.0, 110: 1.0, 120: 1.0, 130: 1.0, 150: 1.0, 180: 1.0}
    expect_unmatched = {60: 9.025, 80: 6.925, 100: 5.525, 110: 4.9, 120: 4.775, 130: 4.475, 150: 4.1, 180: 3.875}
    for q, share in expect_under.items():
        near(rows[q]["any_under_share"], share, 0.005)
    for q, um in expect_unmatched.items():
        near(rows[q]["unmatched_mean"], um, 0.05)
    ums = [rows[q]["unmatched_mean"] for q in (60, 80, 100, 110, 120, 130, 150, 180)]
    assert ums == sorted(ums, reverse=True)                                # streng fallend: mehr Kapazitaet, weniger unversorgte Bewerber


def test_reach_sweep_rural_hospitals_stays_visible_throughout():
    rows = {r["reach"]: r for r in ev.reach_sweep(20, 5)}
    expect_degree = {10: 0.1575, 15: 0.31625, 20: 0.515, 25: 0.78625, 30: 1.06625, 40: 1.7275, 60: 3.0975, 100: 4.87375}
    for reach, deg in expect_degree.items():
        near(rows[reach]["degree"], deg, 0.001)
        assert rows[reach]["any_under_share"] == 1.0                       # bei Quote 120% ueber die ganze Reichweite hinweg


def test_effort_against_size():
    rows = {r["n"]: r for r in ev.scale_table()}
    assert [rows[n]["m"] for n in (10, 20, 40, 80, 160, 320)] == [2, 5, 10, 20, 40, 80]
    expect = {10: 4.5, 20: 11.1, 40: 23.7, 80: 46.4, 160: 90.2, 320: 190.3}
    for n, proposals in expect.items():
        near(rows[n]["proposals"], proposals, 0.5)


def test_manipulation_rates():
    mr = ev.manipulation_residents()
    assert mr == {"gain": 0, "total": 300}                                # Bewerber gewinnen NIE durch Luegen
    mh = ev.manipulation_hospital_prefs()
    assert mh["gain"] == 5 and mh["total"] == 120                          # Klinik-Vorlieben zu verfaelschen hilft manchmal
    mch = ev.manipulation_capacity("H")
    assert mch["gain"] == 1 and mch["total"] == 112                        # klinikseitig: selten, aber real (Soenmez 1997)
    mcr = ev.manipulation_capacity("R")
    assert mcr["gain"] == 0 and mcr["total"] == 112                        # bewerberseitig: nie in dieser Stichprobe
