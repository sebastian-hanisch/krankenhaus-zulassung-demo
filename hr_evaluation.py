"""Auswertung: eine Karte (`analyse`, `verdict`), viele Karten (`distribution`: Landklinikensatz-Sichtbarkeit,
Mehrdeutigkeit, Aufwand), Kapazitäts-/Reichweiten-Sweep, Manipulationsraten (Bewerber/Klinik-Vorlieben/Klinik-Kapazität),
Preis der Stabilität (Nebenabschnitt - Kliniken cap[j]-fach geklont, dann die unveränderte Ungarische Methode aus
`hr_hungarian.py` als gewöhnliches 1:1-Problem gelöst). Alles ganzzahlig und deterministisch; nur die
Anzeige-Statistiken (Anteile, Mittel, Mediane) sind Gleitkomma."""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

import hr_constants as C
import hr_strategy as ST
from hr_admission import certificate, run
from hr_hungarian import hungarian
from hr_oracle import all_stable_assignments_brute
from hr_preferences import DEFAULT_NOISE, preferences
from hr_scenario import capacity_manipulation_example, generate, rural_hospitals_example

NONE, SOLVED = "none", "solved"


def scenario_from_settings(card, n, m, reach, ballung, quote, seed):
    if card == C.CARD_RURAL:
        return rural_hospitals_example()
    if card == C.CARD_CAPACITY:
        return capacity_manipulation_example()
    return generate(n, m, reach, ballung, quote, seed)


@dataclass
class Analysis:
    scenario: object
    pref: str
    noise: int
    seed: int
    pr: list
    ph: list
    result: object          # hr_admission.Result, bewerberseitig
    hospital_optimal: object  # hr_admission.Result, klinikseitig
    cert: dict


def analyse(sc, pref=C.DEFAULT_PREF, noise=DEFAULT_NOISE, seed=0):
    pr, ph = preferences(sc, pref, noise, seed)
    res = run(pr, ph, sc.cap, proposer="R", record=True)
    res_h = run(pr, ph, sc.cap, proposer="H", record=False)
    cert = certificate(pr, ph, res.pairs, sc.cap, sc.n, sc.m, hospital_optimal_pairs=res_h.pairs)
    return Analysis(sc, pref, noise, seed, pr, ph, res, res_h, cert)


def verdict(a):
    sc, r = a.scenario, a.result
    feasible = any(sc.feasible[i].any() for i in range(sc.n)) if hasattr(sc.feasible, "any") else any(sc.feasible)
    code = SOLVED if feasible else NONE
    under = [j for j in range(sc.m) if r.fill[j] < sc.cap[j]]
    data = {"n": sc.n, "m": sc.m, "count": len(r.pairs), "unmatched": len(r.unmatched), "fill": r.fill, "cap": sc.cap,
            "total_cap": sum(sc.cap), "under_count": len(under), "under": tuple(under),
            "proposals": r.proposals, "rejections": r.rejections, "cert_ok": a.cert["all_ok"],
            "rural_ok": a.cert.get("s5_rural_hospitals"), "same_ro_ho": r.pairs == a.hospital_optimal.pairs}
    level = {NONE: "info", SOLVED: "success"}[code]
    return level, code, data


# --- Preis der Stabilitaet (Nebenabschnitt) ---------------------------------------------------------------------

class _CloneScenario:
    def __init__(self, n, m, cost, feasible):
        self.n, self.m, self.cost, self.feasible = n, m, cost, feasible

    def edges(self):
        return sorted((int(self.cost[i, j]), i, j) for i in range(self.n) for j in range(self.m) if self.feasible[i, j])


def _clone_scenario(sc):
    """Kliniken cap[j]-fach klonen (gleiche Kosten/Erreichbarkeit je Klon), damit `hr_hungarian.py` unveraendert eine
    gewoehnliche 1:1-Zuordnung loesen kann. `owner[spalte] = echte Klinik`."""
    m2 = sum(sc.cap)
    cost2 = np.zeros((sc.n, m2), dtype=np.int64)
    feasible2 = np.zeros((sc.n, m2), dtype=bool)
    owner = []
    col = 0
    for j in range(sc.m):
        for _ in range(sc.cap[j]):
            cost2[:, col] = sc.cost[:, j]
            feasible2[:, col] = sc.feasible[:, j]
            owner.append(j)
            col += 1
    return _CloneScenario(sc.n, m2, cost2, feasible2), owner


def price_of_stability(sc, pairs):
    """Praemie [%] der bewerberseitigen Zulassung gegenueber der billigsten Zuordnung MIT DERSELBEN PAARZAHL (nie mit
    dem globalen Optimum, das haette meist mehr Paare)."""
    if sc.lists is not None:
        return None    # feste Lehrbuchkarten: Positionen sind Dekoration, ein Kostenvergleich waere sinnlos
    clone_sc, owner = _clone_scenario(sc)
    hres = hungarian(clone_sc, record=False)
    kcost = [0]
    for w in hres.marginal:
        kcost.append(kcost[-1] + w)
    k = len(pairs)
    if k == 0 or k >= len(kcost) or kcost[k] == 0:
        return None
    real_cost = int(sum(sc.cost[i, j] for i, j in pairs))
    return 100.0 * (real_cost - kcost[k]) / kcost[k]


# --- viele Karten -----------------------------------------------------------------------------------------------

def _row(sc, pref, noise, seed):
    pr, ph = preferences(sc, pref, noise, seed)
    res = run(pr, ph, sc.cap, proposer="R", record=False)
    res_h = run(pr, ph, sc.cap, proposer="H", record=False)
    under = [j for j in range(sc.m) if res.fill[j] < sc.cap[j]]
    prem = price_of_stability(sc, res.pairs)
    return {"count": len(res.pairs), "unmatched": len(res.unmatched), "total_cap": sc.total_cap,
            "under_count": len(under), "any_under": len(under) > 0, "same_ro_ho": res.pairs == res_h.pairs,
            "proposals": res.proposals, "rejections": res.rejections, "premium": prem,
            "degree": sum(int(sc.feasible[i].sum()) for i in range(sc.n)) / max(sc.n, 1)}


@lru_cache(maxsize=256)
def cell_rows(n, m, reach, ballung, quote, pref, noise, seeds):
    return tuple(_row(generate(n, m, reach, ballung, quote, sd), pref, noise, sd) for sd in seeds)


def _mean(v):
    return float(np.mean(v)) if len(v) else None


def _med(v):
    return float(np.median(v)) if len(v) else None


def _stat(values):
    return {"mean": _mean(values), "median": _med(values), "min": min(values) if len(values) else None, "max": max(values) if len(values) else None}


def distribution(n, m, reach, ballung, quote, pref=C.DEFAULT_PREF, noise=DEFAULT_NOISE, seeds=C.DIST_SEEDS):
    rows = list(cell_rows(n, m, reach, ballung, quote, pref, noise, tuple(seeds)))
    prem = [r["premium"] for r in rows if r["premium"] is not None]
    return {
        "n_seeds": len(seeds), "n_valid": len(rows),
        "count": _stat([r["count"] for r in rows]), "unmatched": _stat([r["unmatched"] for r in rows]),
        "under_count": _stat([r["under_count"] for r in rows]), "any_under_share": _mean([r["any_under"] for r in rows]),
        "same_ro_ho_share": _mean([r["same_ro_ho"] for r in rows]),
        "proposals": _stat([r["proposals"] for r in rows]),
        "premium": _stat(prem), "degree": _mean([r["degree"] for r in rows]),
    }


def quote_sweep(n, m, reach, ballung=0, pref=C.DEFAULT_PREF, noise=DEFAULT_NOISE, seeds=C.SWEEP_SEEDS, quotes=C.QUOTE_SWEEP):
    out = []
    for q in quotes:
        d = distribution(n, m, reach, ballung, q, pref, noise, seeds)
        if d["n_valid"] == 0:
            continue
        out.append({"quote": q, "any_under_share": d["any_under_share"], "unmatched_mean": d["unmatched"]["mean"], "count_mean": d["count"]["mean"]})
    return out


def reach_sweep(n, m, ballung=0, quote=C.DEFAULT_QUOTE, pref=C.DEFAULT_PREF, noise=DEFAULT_NOISE, seeds=C.SWEEP_SEEDS, reaches=C.REACH_SWEEP):
    out = []
    for r in reaches:
        d = distribution(n, m, r, ballung, quote, pref, noise, seeds)
        if d["n_valid"] == 0:
            continue
        out.append({"reach": r, "degree": d["degree"], "any_under_share": d["any_under_share"], "same_ro_ho_share": d["same_ro_ho_share"]})
    return out


@lru_cache(maxsize=8)
def scale_table(ns=C.SCALE_NS, seeds=C.SCALE_SEEDS):
    """Aufwand (Vorschlaege) gegen Groesse, m = n / 4, Reichweite so, dass der mittlere Grad etwa gleich bleibt."""
    import math
    out = []
    for n in ns:
        m = max(1, n // 4)
        reach = max(3, math.isqrt(C.SCALE_DEGREE_AREA // n))
        props = []
        for sd in seeds:
            sc = generate(n, m, reach, 0, C.DEFAULT_QUOTE, sd)
            pr, ph = preferences(sc, "noise", DEFAULT_NOISE, sd)
            res = run(pr, ph, sc.cap, proposer="R", record=False)
            props.append(res.proposals)
        out.append({"n": n, "m": m, "reach": reach, "proposals": _mean(props)})
    return out


# --- Manipulation ----------------------------------------------------------------------------------------------

@lru_cache(maxsize=8)
def manipulation_residents(pref=C.DEFAULT_PREF, noise=DEFAULT_NOISE, n=5, m=2, seeds=C.MANIP_SEEDS):
    gain = total = 0
    for sd in seeds:
        sc = generate(n, m, 300, 0, 100, sd)
        pr, ph = preferences(sc, pref, noise, sd)
        for i in range(n):
            honest, best, _ = ST.best_response_resident(pr, ph, sc.cap, i)
            total += 1
            gain += best < honest
    return {"gain": gain, "total": total}


@lru_cache(maxsize=8)
def manipulation_hospital_prefs(pref=C.DEFAULT_PREF, noise=DEFAULT_NOISE, n=5, m=2, seeds=C.MANIP_SEEDS):
    gain = total = 0
    for sd in seeds:
        sc = generate(n, m, 300, 0, 100, sd)
        pr, ph = preferences(sc, pref, noise, sd)
        for j in range(m):
            honest, best, _ = ST.best_response_hospital_prefs(pr, ph, sc.cap, j)
            total += 1
            gain += best < honest
    return {"gain": gain, "total": total}


@lru_cache(maxsize=8)
def manipulation_capacity(proposer, pref=C.DEFAULT_PREF, noise=DEFAULT_NOISE, n=4, m=2, seeds=C.MANIP_SEEDS):
    gain = total = 0
    for sd in seeds:
        sc = generate(n, m, 300, 0, 150, sd)          # reichlich Kapazitaet, damit ueberhaupt jemand voll wird
        pr, ph = preferences(sc, pref, noise, sd)
        for j in range(m):
            if sc.cap[j] < 2:
                continue
            honest, best, _ = ST.best_response_capacity(pr, ph, sc.cap, j, proposer=proposer)
            total += 1
            gain += best < honest
    return {"gain": gain, "total": total}
