"""Kartengenerierung, Kapazitätsvergabe, Vorlieben-Grundeigenschaften und die Plumbing der Auswertung."""

import hr_constants as C
import hr_evaluation as ev
import hr_preferences as P
import hr_scenario as S


def test_splitmix_vector_and_a_pinned_point_list():
    rng = S.SplitMix64(0)
    assert [rng.next() for _ in range(2)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4]


def test_capacity_scales_to_the_quote():
    for n, m, quote, seed in ((20, 5, 100, 1), (20, 5, 150, 2), (40, 10, 80, 3)):
        sc = S.generate(n, m, 40, 0, quote, seed)
        assert len(sc.cap) == m and all(c >= 1 for c in sc.cap)
        assert abs(sum(sc.cap) - round(n * quote / 100)) <= m           # Rundung je Klinik, aber Summe nah an der Zielquote


def test_capacity_stream_independent_of_points():
    """Zwei Karten mit gleichem Seed aber unterschiedlicher Reichweite haben verschiedene Punkte, aber dieselbe
    Kapazitaetsverteilung (eigener Strom) - Reichweite und Kapazitaet lassen sich unabhaengig einstellen."""
    sc1 = S.generate(20, 5, 20, 0, 120, 7)
    sc2 = S.generate(20, 5, 80, 0, 120, 7)
    assert sc1.cap == sc2.cap
    assert sc1.feasible.tolist() != sc2.feasible.tolist()                 # unterschiedliche Reichweite -> tatsaechlich unterschiedliche Karte


def test_preferences_strict_and_restricted_to_reachable():
    sc = S.generate(15, 4, 25, 0, 100, 3)
    for model in ("dist", "noise", "random"):
        pr, ph = P.preferences(sc, model, seed=3)
        for i in range(sc.n):
            assert sorted(pr[i]) == sorted(j for j in range(sc.m) if sc.feasible[i, j])
            assert len(set(pr[i])) == len(pr[i])
        for j in range(sc.m):
            assert sorted(ph[j]) == sorted(i for i in range(sc.n) if sc.feasible[i, j])


def test_fixed_cards_have_matching_lists_and_capacities():
    sc = S.rural_hospitals_example()
    assert sc.n == 4 and sc.m == 3 and sc.cap == (2, 2, 2)
    pr, ph = sc.lists
    assert len(pr) == 4 and len(ph) == 3
    sc2 = S.capacity_manipulation_example()
    assert sc2.n == 2 and sc2.m == 2 and sc2.cap == (2, 1)


def test_analyse_and_verdict_solved():
    sc = ev.scenario_from_settings(C.CARD_NONE, 20, 5, 40, 0, 120, 20)
    a = ev.analyse(sc, "noise", 20, 20)
    level, code, data = ev.verdict(a)
    assert code == ev.SOLVED and level == "success"
    assert data["cert_ok"] is True and data["rural_ok"] is True


def test_analyse_and_verdict_none():
    seed = next(k for k in range(500) if S.generate(C.N_MIN, C.M_MIN, C.REACH_MIN, 0, 100, k).feasible.sum() == 0)
    sc = ev.scenario_from_settings(C.CARD_NONE, C.N_MIN, C.M_MIN, C.REACH_MIN, 0, 100, seed)
    a = ev.analyse(sc, "noise", 20, seed)
    level, code, data = ev.verdict(a)
    assert code == ev.NONE and level == "info"


def test_price_of_stability_none_on_fixed_cards():
    sc = S.rural_hospitals_example()
    a = ev.analyse(sc, "noise", 20, 1)
    assert ev.price_of_stability(sc, a.result.pairs) is None


def test_distribution_and_sweeps_shapes():
    d = ev.distribution(12, 3, 30, 0, 100, seeds=range(20))
    assert d["n_valid"] == 20
    qs = ev.quote_sweep(12, 3, 30, seeds=range(10), quotes=(80, 120))
    assert len(qs) == 2
    rs = ev.reach_sweep(12, 3, quote=100, seeds=range(10), reaches=(20, 40))
    assert len(rs) == 2


def test_scale_table_repeatable():
    a1, a2 = ev.scale_table(), ev.scale_table()
    assert a1 == a2
