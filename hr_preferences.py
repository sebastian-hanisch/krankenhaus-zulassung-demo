"""Vorlieben: jede Seite ordnet ihre möglichen Partner (die Reichweite macht die Listen unvollständig, aber beidseitig
gleich: j erreichbar von i <=> i erreichbar von j).

Drei Modelle, alle ganzzahlig und über einen eigenen Zufallsgenerator (SplitMix64) statt numpy:
- `dist`: beide Seiten ordnen nach der Fahrzeit c_ij. Beide Seiten haben dieselbe Wertung ⇒ die bewerberoptimale und
  die klinikoptimale Zulassung sind identisch und eindeutig.
- `noise`: jede Seite schätzt die Fahrzeit selbst: c_ij + Streuung in [-k, k] Minuten, je Seite und Paar unabhängig
  gezogen. k = 0 ist `dist`, große k nähern sich `random`.
- `random`: unabhängige Zufallsvorlieben, ohne Bezug zu den Kosten.
Gleichstände werden nach dem Index gebrochen (Bewerber nach Klinikindex, Kliniken nach Bewerberindex); die Listen sind
also strikt.
"""

from hr_scenario import SplitMix64

MASK = (1 << 64) - 1
PREF_LABELS = {"dist": "Nur Entfernung", "noise": "Entfernung mit Streuung", "random": "Zufall"}
DEFAULT_PREF = "noise"
NOISE_MIN, NOISE_MAX, NOISE_STEP, DEFAULT_NOISE = 5, 60, 5, 20
SIDE_R, SIDE_H = 1, 2


def _draw(seed, side, i, j, bits):
    """Reproduzierbare Ziehung 0 .. 2^bits - 1 für (Seed, Seite, Bewerber, Klinik): unabhängig von n, m und Reichweite."""
    state = seed & MASK
    for part in (side, i, j):
        state = (state * 1000003 + part + 1) & MASK
    return SplitMix64(state).below(1 << bits)


def _noise(seed, side, i, j, k):
    return ((2 * k + 1) * _draw(seed, side, i, j, 20) >> 20) - k


def preferences(sc, model, noise=DEFAULT_NOISE, seed=0):
    """Strikte Vorlieben (pr, ph): pr[i] = Kliniken von Bewerber i, beste zuerst; ph[j] = Bewerber von Klinik j, beste
    zuerst. Karten mit festen Listen liefern diese unverändert."""
    if getattr(sc, "lists", None) is not None:
        pr, ph = sc.lists
        return [list(x) for x in pr], [list(x) for x in ph]
    n, m, c = sc.n, sc.m, sc.cost
    if model == "dist":
        kr = lambda i, j: int(c[i, j])
        kh = lambda j, i: int(c[i, j])
    elif model == "noise":
        kr = lambda i, j: int(c[i, j]) + _noise(seed, SIDE_R, i, j, noise)
        kh = lambda j, i: int(c[i, j]) + _noise(seed, SIDE_H, i, j, noise)
    elif model == "random":
        kr = lambda i, j: _draw(seed, SIDE_R, i, j, 30)
        kh = lambda j, i: _draw(seed, SIDE_H, i, j, 30)
    else:
        raise ValueError(model)
    pr = [sorted((j for j in range(m) if sc.feasible[i, j]), key=lambda j: (kr(i, j), j)) for i in range(n)]
    ph = [sorted((i for i in range(n) if sc.feasible[i, j]), key=lambda i: (kh(j, i), i)) for j in range(m)]
    return pr, ph


def ranks(lists):
    """Rangtabellen: ranks[a][b] = Platz von b in der Liste von a (0 = beste)."""
    return [{x: k for k, x in enumerate(lst)} for lst in lists]
