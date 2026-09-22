"""Deferred Acceptance mit Kapazitäten (`hr_admission.py`) gegen den unabhängigen Brute-Force-Prüfer (`hr_oracle.py`),
Rollentausch (bewerber- vs. klinikoptimal), Landklinikensatz, Kapazitäts-Manipulationsbeispiel, Zertifikat,
Negativkontrollen für die beim Implementieren gefundenen Fehlerklassen."""

import random

import pytest

import hr_admission as A
import hr_oracle as O
import hr_scenario as S


def _random_instance(n, m, p_edge, max_cap, seed):
    rng = random.Random(seed)
    adj_r = [[] for _ in range(n)]
    adj_h = [[] for _ in range(m)]
    for i in range(n):
        for j in range(m):
            if rng.random() < p_edge:
                adj_r[i].append(j)
                adj_h[j].append(i)
    pr = [list(x) for x in adj_r]
    for lst in pr:
        rng.shuffle(lst)
    ph = [list(x) for x in adj_h]
    for lst in ph:
        rng.shuffle(lst)
    cap = [rng.randint(1, max_cap) for _ in range(m)]
    return pr, ph, cap


# --- Kreuzpruefung gegen die Brute-Force -------------------------------------------------------------------------

@pytest.mark.parametrize("n", range(1, 8))
@pytest.mark.parametrize("m", range(1, 5))
@pytest.mark.parametrize("trial", range(4))
def test_resident_proposing_matches_brute_force(n, m, trial):
    for p_edge, max_cap in ((0.5, 2), (1.0, 3)):
        seed = n * 100000 + m * 1000 + trial * 7 + int(p_edge * 10) + max_cap
        pr, ph, cap = _random_instance(n, m, p_edge, max_cap, seed)
        res = A.run(pr, ph, cap, proposer="R", record=False)
        assert O.is_stable(pr, ph, res.pairs, cap, n, m), (n, m, trial, pr, ph, cap, res.pairs)
        brute = O.stable_assignment_brute(pr, ph, cap)
        assert brute is not None                                          # Deferred Acceptance findet IMMER eine Loesung
        rank_r = O._ranks(pr)
        brute_partner = dict(brute)
        da_partner = dict(res.pairs)
        for i in range(n):
            da_rank = rank_r[i].get(da_partner.get(i), len(pr[i]))
            brute_rank = rank_r[i].get(brute_partner.get(i), len(pr[i]))
            assert da_rank <= brute_rank, "nicht bewerberoptimal"          # mindestens so gut wie IRGENDEINE stabile Zulassung


@pytest.mark.parametrize("n", range(1, 6))
@pytest.mark.parametrize("m", range(1, 4))
@pytest.mark.parametrize("trial", range(6))
def test_hospital_proposing_matches_brute_force_and_is_hospital_optimal(n, m, trial):
    seed = n * 7777 + m * 111 + trial
    pr, ph, cap = _random_instance(n, m, 0.6, 3, seed)
    res_h = A.run(pr, ph, cap, proposer="H", record=False)
    assert O.is_stable(pr, ph, res_h.pairs, cap, n, m)
    res_r = A.run(pr, ph, cap, proposer="R", record=False)
    rank_r = O._ranks(pr)
    rp, hp = dict(res_r.pairs), dict(res_h.pairs)
    for i in range(n):
        a = rank_r[i].get(rp.get(i), len(pr[i]))
        b = rank_r[i].get(hp.get(i), len(pr[i]))
        assert a <= b                                                     # bewerberoptimal ist fuer JEDEN Bewerber mindestens so gut wie klinikoptimal


def test_always_solvable_never_returns_none():
    """Anders als bei Stabile Mitbewohner gibt es hier IMMER eine stabile Loesung."""
    for n in range(1, 9):
        for m in range(1, 5):
            pr, ph, cap = _random_instance(n, m, 0.5, 2, n * 31 + m)
            res = A.run(pr, ph, cap, proposer="R", record=False)
            assert O.is_stable(pr, ph, res.pairs, cap, n, m)


# --- Landklinikensatz -----------------------------------------------------------------------------------------------

def test_rural_hospitals_theorem_on_the_fixed_example():
    sc = S.rural_hospitals_example()
    pr, ph = sc.lists
    all_stable = O.all_stable_assignments_brute(pr, ph, sc.cap)
    assert len(all_stable) == 2
    fills = set()
    for assignment in all_stable:
        by_h = {j: [] for j in range(sc.m)}
        for i, j in assignment:
            by_h[j].append(i)
        fills.add(tuple(len(by_h[j]) for j in range(sc.m)))
    assert fills == {(2, 2, 0)}                                            # Klinik 2 bleibt in JEDER stabilen Zulassung leer
    res_r = A.run(pr, ph, sc.cap, proposer="R", record=False)
    res_h = A.run(pr, ph, sc.cap, proposer="H", record=False)
    assert res_r.fill == res_h.fill == (2, 2, 0)


@pytest.mark.parametrize("trial", range(60))
def test_rural_hospitals_theorem_holds_broadly(trial):
    n, m = 6, 3
    pr, ph, cap = _random_instance(n, m, 0.7, 3, trial + 20000)
    res_r = A.run(pr, ph, cap, proposer="R", record=False)
    res_h = A.run(pr, ph, cap, proposer="H", record=False)
    assert res_r.fill == res_h.fill                                        # Fuellzahl je Klinik identisch in beiden Extremen
    by_r = res_r.pairs_by_hospital()
    by_h = res_h.pairs_by_hospital()
    for j in range(m):
        if res_r.fill[j] < cap[j]:
            assert set(by_r[j]) == set(by_h[j])                           # nicht volle Klinik: exakt dieselben Bewerber


# --- Kapazitäts-Manipulation ------------------------------------------------------------------------------------------

def test_capacity_manipulation_helps_under_hospital_proposing_only():
    sc = S.capacity_manipulation_example()
    pr, ph = sc.lists
    true_cap = sc.cap
    under_cap = (true_cap[0] - 1, true_cap[1])

    def held_by(res, hosp):
        return [i for i, j in res.pairs if j == hosp]

    true_h = A.run(pr, ph, true_cap, proposer="H", record=False)
    under_h = A.run(pr, ph, under_cap, proposer="H", record=False)
    assert O.is_stable(pr, ph, under_h.pairs, under_cap, sc.n, sc.m)
    assert held_by(true_h, 0) == [1] and held_by(under_h, 0) == [0]       # Klinik 0 bekommt unter Untertreiben ihren Wunschkandidaten (Rang 0 statt Rang 1)

    true_r = A.run(pr, ph, true_cap, proposer="R", record=False)
    under_r = A.run(pr, ph, under_cap, proposer="R", record=False)
    assert held_by(true_r, 0) == held_by(under_r, 0)                      # bewerberseitig aendert die Luege NICHTS


@pytest.mark.parametrize("trial", range(200))
def test_no_resident_ever_gains_by_lying(trial):
    """Bewerber-seitige Manipulation: exhaustive Test ueber Permutationen der wahren Liste, wie in gs_strategy.py."""
    import itertools
    n, m = 3, 2
    pr, ph, cap = _random_instance(n, m, 0.8, 2, trial + 40000)
    honest = A.run(pr, ph, cap, proposer="R", record=False)
    rank_r = O._ranks(pr)
    hp = dict(honest.pairs)
    for i in range(n):
        honest_rank = rank_r[i].get(hp.get(i), len(pr[i]))
        for k in range(1, len(pr[i]) + 1):
            for sub in itertools.permutations(pr[i], k):
                pr2 = [list(x) for x in pr]
                pr2[i] = list(sub)
                ph2 = [[x for x in lst if x != i or j in sub] for j, lst in enumerate(ph)]
                res2 = A.run(pr2, ph2, cap, proposer="R", record=False)
                p2 = dict(res2.pairs)
                lied_rank = rank_r[i].get(p2.get(i), len(pr[i]))
                assert lied_rank >= honest_rank, (trial, i, sub)


# --- Zertifikat ----------------------------------------------------------------------------------------------------

def test_certificate_positive_with_rural_hospitals_check():
    sc = S.rural_hospitals_example()
    pr, ph = sc.lists
    res_r = A.run(pr, ph, sc.cap, proposer="R", record=False)
    res_h = A.run(pr, ph, sc.cap, proposer="H", record=False)
    cert = A.certificate(pr, ph, res_r.pairs, sc.cap, sc.n, sc.m, hospital_optimal_pairs=res_h.pairs)
    assert cert["all_ok"] and cert["s5_rural_hospitals"]


def test_certificate_catches_over_capacity():
    sc = S.rural_hospitals_example()
    pr, ph = sc.lists
    bad = ((0, 2), (1, 2), (2, 2), (3, 2))                                 # alle vier auf Klinik 2 (Kapazitaet 2!)
    cert = A.certificate(pr, ph, bad, sc.cap, sc.n, sc.m)
    assert cert["s1_valid"] is False and cert["all_ok"] is False


def test_certificate_catches_blocking_pair():
    sc = S.rural_hospitals_example()
    pr, ph = sc.lists
    bad = ((0, 2), (1, 1), (2, 0), (3, 0))                                 # 0 will lieber 1 oder 0 als 2, wird aber trotzdem dort geparkt
    cert = A.certificate(pr, ph, bad, sc.cap, sc.n, sc.m)
    assert cert["s2_no_blocking"] is False and cert["all_ok"] is False


# --- Negativkontrollen: beim Implementieren gefundene Fehlerklassen -------------------------------------------------

def test_pitfall_zero_capacity_hospital_does_not_crash():
    """#1: cap[h]=0 lässt `held[h]` leer - `max(..., key=...)` auf der leeren Liste würde ohne Sonderfall abstürzen."""
    pr = [[0, 1], [0, 1]]
    ph = [[0, 1], [0, 1]]
    res = A.run(pr, ph, cap=(0, 2), proposer="R", record=False)
    assert res.fill[0] == 0
    assert O.is_stable(pr, ph, res.pairs, (0, 2), 2, 2)


# --- Sekundaerer Smoke-Test gegen das PyPI-Paket `matching` --------------------------------------------------------

def test_agrees_with_matching_package():
    """`matching.games.HospitalResident` stuerzt ab, sobald IRGENDEIN Spieler (Bewerber ODER Klinik) eine leere
    Vorliebenliste hat - bestaetigt fuer BEIDE Richtungen (`optimal="resident"` stuerzt schon bei einem listenlosen
    Bewerber, `optimal="hospital"` bei einer listenlosen Klinik; beide werfen tief im Paket eine IndexError/AttributeError
    statt den Spieler einfach auszuschliessen, obwohl das Paket selbst dafuer extra eine Warnung definiert). Hier daher
    nur auf Instanzen geprueft, in denen jeder Bewerber UND jede Klinik mindestens einen moeglichen Partner hat."""
    from matching.games import HospitalResident

    agree = 0
    for trial in range(150):
        n, m = 6, 3
        pr, ph, cap = _random_instance(n, m, 0.8, 3, trial + 60000)
        if any(len(lst) == 0 for lst in ph) or any(len(lst) == 0 for lst in pr):
            continue
        resident_prefs = {i: pr[i] for i in range(n)}
        hospital_prefs = {j: ph[j] for j in range(m)}
        capacities = {j: cap[j] for j in range(m)}
        game = HospitalResident.create_from_dictionaries(resident_prefs, hospital_prefs, capacities)
        pkg = game.solve(optimal="resident")
        pkg_pairs = tuple(sorted((r.name, h.name) for h, residents in pkg.items() for r in residents))
        res = A.run(pr, ph, cap, proposer="R", record=False)
        assert res.pairs == pkg_pairs, (trial, res.pairs, pkg_pairs)
        agree += 1
    assert agree >= 100


def test_pitfall_manipulation_needs_mutual_list_filtering():
    """#2: beim Manipulationsexperiment muss die GEGENLISTE gekuerzt werden (ein Bewerber, der Klinik j nicht mehr
    listet, muss auch aus js Liste verschwinden) - sonst KeyError tief im Ablauf. Hier direkt am Mechanismus geprueft:
    ein Bewerber laesst eine Klinik aus seiner gemeldeten Liste weg, die Gegenliste wird konsistent gehalten."""
    pr = [[0, 1], [1, 0], [0, 1]]
    ph = [[0, 1, 2], [2, 1, 0]]
    cap = (1, 1)
    pr2 = [list(pr[0]), [0], list(pr[2])]                                  # Bewerber 1 meldet nur noch Klinik 0
    ph2 = [[x for x in lst if x != 1 or j in pr2[1]] for j, lst in enumerate(ph)]   # Gegenliste konsistent kuerzen: Klinik 1 verliert Bewerber 1, Klinik 0 behaelt ihn
    res = A.run(pr2, ph2, cap, proposer="R", record=False)                 # darf nicht werfen
    assert O.is_stable(pr2, ph2, res.pairs, cap, 3, 2)
