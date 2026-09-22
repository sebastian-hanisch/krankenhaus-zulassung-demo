"""Szenario: Bewerber und Kliniken auf einer Karte, jede Klinik mit einer Kapazität (wie viele Bewerber sie aufnehmen
kann - der einzige strukturelle Unterschied zu `gale-shapley-demo`s 1:1-Szenario).

Alles ist ganzzahlig und läuft über einen eigenen Zufallsgenerator (SplitMix64 auf Python-Ints) statt über
`numpy.random`: numpy garantiert keine über Versionen stabilen Zufallsströme, die CI installiert aber wöchentlich die
neueste Version. So sind Voreinstellungen, Seeds und jede im Text genannte Zahl auf Windows und Linux dieselben.
Kosten = auf ganze Minuten aufgerundete Entfernung (per `isqrt`, ohne Gleitkomma); ein Paar ist möglich, wenn die
Entfernung höchstens die Reichweite beträgt.

Kapazitäten kommen aus einem EIGENEN `SplitMix64`-Strom (unabhängig von den Punktkoordinaten, damit sich Reichweite
und Kapazität unabhängig voneinander einstellen lassen): jede Klinik bekommt ein zufälliges Gewicht, die Gewichte
werden so skaliert, dass die Gesamtkapazität ungefähr `n * quote / 100` ergibt (`quote` = neuer Regler "Kapazitätsquote
[%]"). Bei Quote 100 % und vollständigen Listen füllt sich die Karte immer vollständig (Hall-Argument); erst ab
Quote > 100 % wird der Landklinikensatz sichtbar (manche Kliniken bleiben trotz freier Plätze unbesetzt)."""

from dataclasses import dataclass
from math import isqrt

import numpy as np

_MASK = (1 << 64) - 1
MAP_SIZE = 100
N_CENTRES = 3


class SplitMix64:
    """Kleiner, gut gemischter 64-Bit-Zufallsgenerator (Vigna); reine Ganzzahl-Arithmetik."""

    def __init__(self, seed):
        self.state = seed & _MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & _MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
        return z ^ (z >> 31)

    def below(self, n):
        """Ganzzahl in 0..n-1 (die Modulo-Verzerrung bei n <= 101 liegt um 1e-17)."""
        return self.next() % n


def travel_cost(dx, dy):
    """Aufgerundete Entfernung in Minuten und das Quadrat der Entfernung (beides ganzzahlig)."""
    d2 = dx * dx + dy * dy
    r = isqrt(d2)
    return r + (1 if d2 > r * r else 0), d2


@dataclass(frozen=True)
class Scenario:
    residents: tuple       # ((x, y), ...)
    hospitals: tuple
    reach: int
    cost: np.ndarray       # (n, m) int64, Anfahrtszeit in Minuten
    feasible: np.ndarray   # (n, m) bool, Entfernung <= Reichweite
    cap: tuple              # Kapazität je Klinik, Länge m
    lists: tuple = None     # feste Vorlieben (pr, ph) bei den Lehrbuchkarten; sonst None (Vorlieben aus hr_preferences)

    @property
    def n(self):
        return len(self.residents)

    @property
    def m(self):
        return len(self.hospitals)

    @property
    def total_cap(self):
        return sum(self.cap)

    def edges(self):
        """Alle möglichen Paare als (Kosten, Bewerber, Klinik), aufsteigend sortiert (Gleichstand: kleinster Index)."""
        return sorted((int(self.cost[i, j]), i, j) for i in range(self.n) for j in range(self.m) if self.feasible[i, j])


def from_points(residents, hospitals, reach, cap, lists=None):
    n, m = len(residents), len(hospitals)
    cost = np.zeros((n, m), dtype=np.int64)
    feasible = np.zeros((n, m), dtype=bool)
    for i, (rx, ry) in enumerate(residents):
        for j, (hx, hy) in enumerate(hospitals):
            c, d2 = travel_cost(rx - hx, ry - hy)
            cost[i, j] = c
            feasible[i, j] = d2 <= reach * reach
    return Scenario(tuple(map(tuple, residents)), tuple(map(tuple, hospitals)), int(reach), cost, feasible, tuple(cap), lists)


def _capacities(m, n, quote, seed):
    """m Kliniken, Gesamtkapazität ~= n * quote / 100, ungleich verteilt (eigener Strom, unabhaengig von den Punkten).
    Jede Klinik hat mindestens Kapazitaet 1."""
    rng = SplitMix64(seed ^ 0x4B5A4E4B454E4B)   # eigener, von der Punktziehung unabhaengiger Strom
    weights = [1 + rng.below(5) for _ in range(m)]
    total_weight = sum(weights)
    target = max(m, round(n * quote / 100))
    cap = [max(1, round(target * w / total_weight)) for w in weights]
    # Rundung kann die Zielsumme leicht verfehlen: Differenz auf die groesste Klinik umlegen
    diff = target - sum(cap)
    if diff != 0:
        idx = max(range(m), key=lambda j: weights[j])
        cap[idx] = max(1, cap[idx] + diff)
    return tuple(cap)


def generate(n, m, reach, ballung, quote, seed):
    """Zufaellige Karte. `ballung` in ganzen Prozent: 0 = gleichmaessig verteilt, 100 = alle Punkte um drei Zentren.
    `quote`: Gesamtkapazitaet als Prozent von n."""
    rng = SplitMix64(seed)
    lo, hi = 15, MAP_SIZE - 15
    centres = [(lo + rng.below(hi - lo + 1), lo + rng.below(hi - lo + 1)) for _ in range(N_CENTRES)]

    def point():
        ux, uy = rng.below(MAP_SIZE + 1), rng.below(MAP_SIZE + 1)
        cx, cy = centres[rng.below(N_CENTRES)]
        jx, jy = rng.below(21) - 10, rng.below(21) - 10
        x = ((100 - ballung) * ux + ballung * (cx + jx)) // 100
        y = ((100 - ballung) * uy + ballung * (cy + jy)) // 100
        return min(max(x, 0), MAP_SIZE), min(max(y, 0), MAP_SIZE)

    residents = [point() for _ in range(n)]
    hospitals = [point() for _ in range(m)]
    cap = _capacities(m, n, quote, seed)
    return from_points(residents, hospitals, reach, cap)


# --- feste Lehrbuchkarten ------------------------------------------------------------------------------------------

def rural_hospitals_example():
    """4 Bewerber, 3 Kliniken, cap=(2,2,2): zwei stabile Zulassungen, in BEIDEN bleibt Klinik 2 (jedermanns letzte
    Wahl) komplett leer, obwohl 2 freie Plaetze da sind und alle vier Bewerber sie in ihrer Liste haben - der
    Landklinikensatz an einer von Hand nachvollziehbaren Karte. Positionen sind Dekoration (Reichweite 200 macht
    ohnehin jeden erreichbar, die echten Vorlieben kommen aus `lists`)."""
    pr = ((1, 0, 2), (1, 0, 2), (0, 1, 2), (1, 0, 2))
    ph = ((0, 3, 2, 1), (1, 2, 0, 3), (2, 3, 1, 0))
    residents = [(15, 20), (35, 20), (55, 20), (75, 20)]
    hospitals = [(20, 70), (50, 70), (80, 70)]
    return from_points(residents, hospitals, reach=200, cap=(2, 2, 2), lists=(pr, ph))


def capacity_manipulation_example():
    """Eigens gefundene und unabhaengig gepruefte Instanz (n=2, m=2) fuer das Phaenomen, das Soenmez (1997, JET,
    "Manipulation via Capacities in Two-Sided Matching Markets") als Erster bewiesen hat: unter KLINIKSEITIGEM
    Vorschlagen kann eine Klinik durch Untertreiben ihrer Kapazitaet gewinnen (hier: Klinik 0 meldet 1 statt 2 Plaetze
    und bekommt dadurch ihren Wunschkandidaten Bewerber 0 statt Bewerber 1); unter BEWERBERSEITIGEM Vorschlagen
    aendert die Luege nichts (Sonderfall n=2, m=2 - Soenmez' eigener Satz nennt dies "Remark 1"). Kein Zitat der
    Original-Zahlen (die waren im verfuegbaren Material nicht im Wortlaut vorhanden) - stattdessen eine eigene, per
    Brute-Force bestaetigte Instanz mit demselben, literaturbelegten qualitativen Befund."""
    pr = ((1, 0), (0, 1))
    ph = ((0, 1), (1, 0))
    residents = [(20, 30), (60, 30)]
    hospitals = [(20, 70), (60, 70)]
    return from_points(residents, hospitals, reach=200, cap=(2, 1), lists=(pr, ph))


def build(n, m, reach, ballung, quote, seed):
    return generate(n, m, reach, ballung, quote, seed)
