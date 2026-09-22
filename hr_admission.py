"""Deferred Acceptance mit Kapazitäten (Gale & Shapley 1962, "College Admissions"-Fassung): dieselbe Bewerbungs-
/Verdrängungs-Mechanik wie im 1:1-Fall (`gale-shapley-demo/gs_algorithm.py`), der EINZIGE strukturelle Unterschied ist,
dass `held[j]` (was eine Klinik gerade hält) eine BEGRENZTE LISTE ist statt eines einzelnen Werts.

Bewerberseitiges Vorschlagen (`proposer="R"`, der Standard in dieser Demo): jeder Bewerber bewirbt sich der Reihe nach
bei seinem nächsten Favoriten. Hat die Klinik noch einen freien Platz, wird IMMER SOFORT angenommen (kein Vergleich -
das ist die Stelle, die Kapazitäts-Manipulation überhaupt erst interessant macht, siehe `hr_strategy.py`). Ist die
Klinik voll, wird der Bewerber mit dem aktuell SCHLECHTESTEN gehaltenen Bewerber verglichen: besser -> verdrängen (der
Verdrängte wird wieder frei), sonst ablehnen. Terminiert immer mit einer stabilen, bewerberoptimalen Zulassung -
anders als bei Stabile Mitbewohner gibt es hier IMMER eine Lösung (der Beweis ist derselbe wie im 1:1-Fall, Kapazitäten
ändern daran nichts).

Klinikseitiges Vorschlagen (`proposer="H"`, für das klinikoptimale Extrem, den Landklinikensatz-Beweis und Sönmez'
Kapazitäts-Manipulationsbeispiel) läuft über dieselbe Mechanik mit vertauschten Rollen: jede Klinik bekommt `cap[j]`
unabhängige "Bewerbungs-Slots" (Klone mit derselben Vorliebenliste `ph[j]`, aber eigenem Fortschritt), jeder Bewerber
hat Kapazität 1 und vergleicht ankommende Vorschläge nach der ECHTEN Klinik-Identität (nicht nach dem Klon).

**Wichtige Falle, die beim Implementieren tatsächlich zuschlägt (Kapazitäts-Manipulationsexperiment testet das
absichtlich):** `cap[j] == 0` lässt `held[j]` leer - `max(held[j], key=...)` auf einer leeren Liste stürzt ab. Eine
Klinik ohne Kapazität ist immer voll UND hat nichts zu vergleichen: sofort ablehnen, ohne den Vergleichszweig zu
betreten.

Effort wird gezählt (Bewerbungen, Ablehnungen/Verdrängungen), nie in Sekunden. Ereignisprotokoll mit einem
Schnappschuss je Ereignis (`state_at`), Zertifikat (`certificate`) unabhängig von der Bewerbung."""

from dataclasses import dataclass

EV_PROPOSE, EV_ACCEPT, EV_DISPLACE, EV_REJECT = "propose", "accept", "displace", "reject"


@dataclass(frozen=True)
class Event:
    kind: str           # propose | accept | displace | reject
    r: int = -1          # Bewerber (bei klinikseitigem Vorschlagen: die tatsaechliche Klinik-Identitaet steht in h)
    h: int = -1          # Klinik
    cause: int = -1       # displace: wer neu angenommen wurde und dies ausloeste
    proposals: int = 0    # kumulative Bewerbungen bis einschliesslich dieses Ereignisses


@dataclass(frozen=True)
class Snapshot:
    fill: tuple          # aktuelle Belegung je Klinik
    held: tuple           # aktuell gehaltene Bewerber je Klinik (Tupel von Tupeln, sortiert)
    matched_r: tuple      # welche Bewerber gerade gehalten werden (-1 falls nirgends spezifisch benoetigt, hier bool)


@dataclass(frozen=True)
class Result:
    n: int
    m: int
    cap: tuple
    proposer: str                  # "R" oder "H"
    pairs: tuple                    # (Bewerber, Klinik), sortiert nach Bewerber - die Zulassung
    fill: tuple                     # Belegung je Klinik (== len(held[j]))
    unmatched: tuple                # Bewerber ohne Klinik
    proposals: int
    rejections: int                 # Ablehnungen + Verdraengungen zusammen
    events: tuple
    snapshots: tuple

    @property
    def n_events(self):
        return len(self.events)

    def pairs_by_hospital(self):
        out = {j: [] for j in range(self.m)}
        for i, j in self.pairs:
            out[j].append(i)
        return out


class _Stats:
    def __init__(self):
        self.proposals = 0
        self.rejections = 0


def _run_one_sided(prop_lists, recv_rank, recv_cap, n_recv, record):
    """Kern: `prop_lists[k]` = Vorliebenliste des Vorschlagenden k (Kapazitaet immer 1), `recv_rank[j]` = Rangtabelle
    des Empfaengers j, `recv_cap[j]` = Kapazitaet des Empfaengers j. Rueckgabe: (held: dict j -> sortierte Liste der
    gehaltenen Vorschlagenden, stats, events, snapshots)."""
    n_prop = len(prop_lists)
    lst = [list(p) for p in prop_lists]
    ptr = [0] * n_prop
    held = {j: [] for j in range(n_recv)}
    stats = _Stats()
    events = [] if record else None
    snaps = [] if record else None

    def emit(kind, **kw):
        if events is not None:
            events.append(Event(kind=kind, proposals=stats.proposals, **kw))
            snaps.append(Snapshot(fill=tuple(len(held[j]) for j in range(n_recv)), held=tuple(tuple(sorted(held[j])) for j in range(n_recv)), matched_r=()))

    free = list(range(n_prop))[::-1]
    while free:
        p = free.pop()
        while ptr[p] < len(lst[p]):
            j = lst[p][ptr[p]]
            ptr[p] += 1
            stats.proposals += 1
            emit(EV_PROPOSE, r=p, h=j)
            if len(held[j]) < recv_cap[j]:
                held[j].append(p)
                emit(EV_ACCEPT, r=p, h=j)
                break
            worst = max(held[j], key=lambda x: recv_rank[j][x]) if held[j] else None
            if worst is not None and recv_rank[j][p] < recv_rank[j][worst]:
                held[j].remove(worst)
                held[j].append(p)
                stats.rejections += 1
                emit(EV_DISPLACE, r=worst, h=j, cause=p)
                free.append(worst)
                break
            stats.rejections += 1
            emit(EV_REJECT, r=p, h=j)
    if record:
        snaps.insert(0, Snapshot(fill=tuple(0 for _ in range(n_recv)), held=tuple(() for _ in range(n_recv)), matched_r=()))
    return held, stats, events, snaps


def run(pr, ph, cap, proposer="R", record=True):
    """`pr[i]` = Bewerber i's Vorlieben (Kliniken, beste zuerst), `ph[j]` = Klinik j's Vorlieben (Bewerber), `cap[j]` =
    Kapazitaet je Klinik. `proposer`: "R" (Bewerber schlagen vor, Standard) oder "H" (Kliniken schlagen vor, fuer das
    klinikoptimale Extrem)."""
    n, m = len(pr), len(ph)
    rank_h = [{x: k for k, x in enumerate(h)} for h in ph]

    if proposer == "R":
        held, stats, events, snaps = _run_one_sided(pr, rank_h, list(cap), m, record)
        pairs = tuple(sorted((i, j) for j in range(m) for i in held[j]))
        fill = tuple(len(held[j]) for j in range(m))
        matched = {i for i, _ in pairs}
        unmatched = tuple(i for i in range(n) if i not in matched)
        return Result(n=n, m=m, cap=tuple(cap), proposer="R", pairs=pairs, fill=fill, unmatched=unmatched,
                      proposals=stats.proposals, rejections=stats.rejections,
                      events=tuple(events) if record else (), snapshots=tuple(snaps) if record else ())

    # Klinikseitig: jede Klinik j wird zu cap[j] Klonen (eigene Vorliebenliste ph[j], eigener Fortschritt),
    # jeder Bewerber hat Kapazitaet 1 und vergleicht nach der ECHTEN Klinik-Identitaet (rank_r[i][echte_klinik]).
    rank_r = [{x: k for k, x in enumerate(r)} for r in pr]
    clone_owner = []
    clone_lists = []
    for j in range(m):
        for _ in range(cap[j]):
            clone_owner.append(j)
            clone_lists.append(list(ph[j]))

    # Empfaenger (Bewerber) vergleichen Klone nach dem Rang der ECHTEN Klinik: rank_by_clone[i][clone_id] = rank_r[i][clone_owner[clone_id]]
    rank_by_clone = [{cid: rank_r[i].get(clone_owner[cid], len(pr[i])) for cid in range(len(clone_owner)) if clone_owner[cid] in rank_r[i]} for i in range(n)]
    held, stats, events, snaps = _run_one_sided(clone_lists, rank_by_clone, [1] * n, n, record)
    pairs = tuple(sorted((r, clone_owner[c]) for r in range(n) for c in held[r]))
    fill = [0] * m
    for _r, h in pairs:
        fill[h] += 1
    matched = {i for i, _ in pairs}
    unmatched = tuple(i for i in range(n) if i not in matched)
    # Ereignisse auf echte Klinik-Identitaeten zurueckuebersetzen (h-Feld enthaelt bisher den Klon-Index)
    if record:
        events = tuple(Event(kind=e.kind, r=e.r, h=clone_owner[e.h] if e.h >= 0 else -1, cause=e.cause, proposals=e.proposals) for e in events)
    return Result(n=n, m=m, cap=tuple(cap), proposer="H", pairs=pairs, fill=tuple(fill), unmatched=unmatched,
                  proposals=stats.proposals, rejections=stats.rejections,
                  events=events if record else (), snapshots=tuple(snaps) if record else ())


def state_at(res, k):
    return res.snapshots[k]


# --- Zertifikat -----------------------------------------------------------------------------------------------------

def certificate(pr, ph, pairs, cap, n, m, hospital_optimal_pairs=None):
    """Beweis, unabhaengig von der Bewerbung: eigene, frische Rangtabellen aus `pr`/`ph`.
    (s1) Gueltig - jeder Bewerber hoechstens einmal, keine Klinik ueber Kapazitaet.
    (s2) Keine blockierende Paarung: (r,h) nicht gepaart, r bevorzugt h gegenueber jetzigem Zustand UND (h hat einen
         freien Platz ODER bevorzugt r gegenueber seinem schlechtesten Gehaltenen).
    (s3) Maximalitaet - kein Bewerber UND keine Klinik mit freiem Platz sind gegenseitig erreichbar und ungepaart.
    (s4) Zaehlidentitaet.
    (s5) Landklinikensatz (reich), NUR wenn `hospital_optimal_pairs` mitgegeben wird: Belegung je Klinik UND (fuer
         nicht volle Kliniken) die Bewerbermenge stimmen zwischen beiden Extremen ueberein - stimmen sie ueberein,
         gilt die Aussage (Gitter-Eigenschaft) fuer JEDE dazwischenliegende stabile Zulassung, nicht nur die beiden Pole.
    """
    rank_r = [{x: k for k, x in enumerate(r)} for r in pr]
    rank_h = [{x: k for k, x in enumerate(h)} for h in ph]

    by_hospital = {j: [] for j in range(m)}
    matched_r = {}
    duplicate = False
    over_cap = False
    for i, j in pairs:
        if i in matched_r:
            duplicate = True
        matched_r[i] = j
        by_hospital[j].append(i)
    for j in range(m):
        if len(by_hospital[j]) > cap[j]:
            over_cap = True
    s1_valid = not duplicate and not over_cap

    def resident_prefers(i, h_candidate):
        cur = matched_r.get(i)
        if h_candidate not in rank_r[i]:
            return False
        if cur is None:
            return True
        return rank_r[i][h_candidate] < rank_r[i][cur]

    def hospital_wants(j, i_candidate):
        if i_candidate not in rank_h[j]:
            return False
        held = by_hospital[j]
        if len(held) < cap[j]:
            return True
        if not held:
            return False                                                  # cap[j] == 0: voll UND leer, nichts zu vergleichen
        worst = max(held, key=lambda x: rank_h[j][x])
        return rank_h[j][i_candidate] < rank_h[j][worst]

    s2_no_blocking = True
    for i in range(n):
        for j in range(m):
            if matched_r.get(i) == j:
                continue
            if resident_prefers(i, j) and hospital_wants(j, i):
                s2_no_blocking = False

    unmatched_r = [i for i in range(n) if i not in matched_r]
    s3_maximal = True
    for i in unmatched_r:
        for j in range(m):
            if j in rank_r[i] and len(by_hospital[j]) < cap[j]:
                s3_maximal = False

    s4_count = sum(len(v) for v in by_hospital.values()) == len(pairs)

    out = {"s1_valid": s1_valid, "s2_no_blocking": s2_no_blocking, "s3_maximal": s3_maximal, "s4_count": s4_count,
           "matched": tuple(sorted(matched_r)), "unmatched": tuple(unmatched_r), "fill": tuple(len(by_hospital[j]) for j in range(m))}

    if hospital_optimal_pairs is not None:
        by_hospital_opt = {j: [] for j in range(m)}
        for i, j in hospital_optimal_pairs:
            by_hospital_opt[j].append(i)
        fill_opt = tuple(len(by_hospital_opt[j]) for j in range(m))
        s5 = fill_opt == out["fill"]
        if s5:
            for j in range(m):
                if out["fill"][j] < cap[j]:
                    if set(by_hospital[j]) != set(by_hospital_opt[j]):
                        s5 = False
        out["s5_rural_hospitals"] = s5
        out["all_ok"] = s1_valid and s2_no_blocking and s3_maximal and s4_count and s5
    else:
        out["all_ok"] = s1_valid and s2_no_blocking and s3_maximal and s4_count
    return out
