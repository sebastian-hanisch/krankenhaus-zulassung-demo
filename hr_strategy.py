"""Manipulation: gewinnt jemand durch Lügen? Bewerber-Vorlieben (mirror von `gs_strategy.py`s Fahrzeugseite - erschöpfend
über alle Permutationen jeder Kürzungslänge der WAHREN Liste), Klinik-Vorlieben (mirror der Auftragsseite) und - neu,
ohne Vorbild im 1:1-Fall - Klinik-KAPAZITÄT.

**Klinik-Präferenzen über Bewerber-MENGEN brauchen eine explizite Konvention** ("responsive" allein reicht nicht
eindeutig aus - mehrere unterschiedliche, alle "responsive" Erweiterungen sind denkbar und können zu unterschiedlichen
Manipulationsbefunden führen). Hier: die literaturkonforme **"erst auffüllen"**-Erweiterung (lexikographisch: zuerst
die Anzahl belegter Plätze - mehr ist immer besser -, dann die sortierten Ränge der belegten Bewerber, aufgefüllt mit
einem Rang schlechter als jeder echte). `_fill_first_score` gibt für ein gehaltenes Set den Vergleichswert zurück
(kleiner = besser)."""

import itertools

from hr_admission import run

WORSE_THAN_ANY = 10 ** 9


def _fill_first_score(rank_h, j, held, true_cap):
    ranks = sorted(rank_h[j].get(i, WORSE_THAN_ANY) for i in held)
    padded = ranks + [WORSE_THAN_ANY] * (true_cap - len(ranks))
    return (-len(held), tuple(padded))


def _partner_rank(pr, res, i):
    partner = dict(res.pairs).get(i)
    return {x: k for k, x in enumerate(pr[i])}.get(partner, len(pr[i]))


def best_response_resident(pr, ph, cap, idx):
    """Erschoepfend: bester erreichbarer Rang fuer Bewerber `idx` ueber jede Permutation jeder Kuerzungslaenge seiner
    WAHREN Liste. Rueckgabe (ehrlicher Rang, bester erreichbarer Rang, die dazu fuehrende Meldung)."""
    true_list = pr[idx]
    honest_res = run(pr, ph, cap, proposer="R", record=False)
    honest = _partner_rank(pr, honest_res, idx)
    best, best_report = honest, list(true_list)
    for k in range(1, len(true_list) + 1):
        for sub in itertools.permutations(true_list, k):
            pr2 = [list(x) for x in pr]
            pr2[idx] = list(sub)
            ph2 = [[x for x in lst if x != idx or j in sub] for j, lst in enumerate(ph)]
            res2 = run(pr2, ph2, cap, proposer="R", record=False)
            score = _partner_rank(pr, res2, idx)
            if score < best:
                best, best_report = score, list(sub)
    return honest, best, best_report


def best_response_hospital_prefs(pr, ph, cap, idx):
    """Erschoepfend: bester erreichbarer Fuellzustand fuer Klinik `idx` (Kapazitaet ehrlich!) ueber jede Permutation
    jeder Kuerzungslaenge ihrer WAHREN Liste, bewertet ueber `_fill_first_score`."""
    true_list = ph[idx]
    rank_h_true = {x: k for k, x in enumerate(true_list)}
    honest_res = run(pr, ph, cap, proposer="R", record=False)
    honest_held = [i for i, j in honest_res.pairs if j == idx]
    honest = _fill_first_score({idx: rank_h_true}, idx, honest_held, cap[idx])
    best, best_report = honest, list(true_list)
    for k in range(1, len(true_list) + 1):
        for sub in itertools.permutations(true_list, k):
            ph2 = [list(x) for x in ph]
            ph2[idx] = list(sub)
            pr2 = [[x for x in lst if x != idx or i in sub] for i, lst in enumerate(pr)]
            res2 = run(pr2, ph2, cap, proposer="R", record=False)
            held2 = [i for i, j in res2.pairs if j == idx]
            score = _fill_first_score({idx: rank_h_true}, idx, held2, cap[idx])
            if score < best:
                best, best_report = score, list(sub)
    return honest, best, best_report


def best_response_capacity(pr, ph, cap, idx, proposer="H"):
    """Erschoepfend: bester erreichbarer Fuellzustand fuer Klinik `idx` (Vorlieben ehrlich!) ueber jede gemeldete
    Kapazitaet 0..cap[idx] (mehr als die wahre Kapazitaet zu melden ist nicht sinnvoll moeglich - eine Klinik kann
    nicht mehr Betten anbieten, als sie hat). `proposer`: "H" (klinikseitiges Vorschlagen, wo Manipulation nachweisbar
    hilft) oder "R" (bewerberseitig, wo sie nie hilft - siehe hr_evaluation/Tests)."""
    true_cap = cap[idx]
    rank_h_true = {x: k for k, x in enumerate(ph[idx])}
    honest_res = run(pr, ph, cap, proposer=proposer, record=False)
    honest_held = [i for i, j in honest_res.pairs if j == idx]
    honest = _fill_first_score({idx: rank_h_true}, idx, honest_held, true_cap)
    best, best_q = honest, true_cap
    for q in range(0, true_cap):
        cap2 = list(cap)
        cap2[idx] = q
        res2 = run(pr, ph, cap2, proposer=proposer, record=False)
        held2 = [i for i, j in res2.pairs if j == idx]
        score = _fill_first_score({idx: rank_h_true}, idx, held2, true_cap)
        if score < best:
            best, best_q = score, q
    return honest, best, best_q
