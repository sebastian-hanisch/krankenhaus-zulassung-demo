"""Orakel für Tests: Brute Force über alle kapazitätsverträglichen Zulassungen, unabhängig von `hr_admission.py`
hergeleitet - exakt wie `bl_oracle.py`/`sr_oracle.py` in den Vorgängerdemos als unabhängiger Prüfer gedacht.

**Wichtig, beim Bauen selbst gefunden:** ein erster Entwurf prüfte "blockiert diese Person die Karte" schon WÄHREND
der Konstruktion (nur gegen die bereits entschiedenen Bewerber) und schnitt darauf basierend Zweige ab - das ist
UNGÜLTIG: ob "bleibt frei" eine Blockade erzeugt, hängt von der VOLLSTÄNDIGEN Zulassung ab (eine Klinik, die jetzt
noch freie Plätze hat, kann später von einem besseren, noch nicht entschiedenen Bewerber gefüllt werden - dann blockiert
der jetzt geprüfte Bewerber gar nicht mehr). Die Suche unten baut deshalb erst eine VOLLSTÄNDIGE, kapazitätsverträgliche
Zuordnung (das Beschneiden dabei ist rein kapazitätsbasiert, also unbedenklich) und prüft Stabilität erst am Ende, als
eigenständigen Schritt - exakt das Muster von `bl_oracle.py`/`sr_oracle.py`. Nur für kleine n gedacht (n <= ~8-9)."""

PRACTICAL_MAX_N = 9


def _ranks(lists):
    return [{x: k for k, x in enumerate(p)} for p in lists]


def _blocking_pairs(pr, ph, pairs, cap, n, m):
    rank_r = _ranks(pr)
    rank_h = _ranks(ph)
    matched_r = {}
    by_hospital = {j: [] for j in range(m)}
    for i, j in pairs:
        matched_r[i] = j
        by_hospital[j].append(i)
    out = []
    for i in range(n):
        for j in range(m):
            if matched_r.get(i) == j or j not in rank_r[i]:
                continue
            cur = matched_r.get(i)
            r_prefers = cur is None or rank_r[i][j] < rank_r[i][cur]
            if not r_prefers:
                continue
            if i not in rank_h[j]:
                continue
            held = by_hospital[j]
            if len(held) < cap[j]:
                h_wants = True
            elif held:
                worst = max(held, key=lambda x: rank_h[j][x])
                h_wants = rank_h[j][i] < rank_h[j][worst]
            else:
                h_wants = False                                          # cap[j] == 0: voll UND leer, nichts zu vergleichen
            if h_wants:
                out.append((i, j))
    return out


def is_stable(pr, ph, pairs, cap, n, m):
    return len(_blocking_pairs(pr, ph, pairs, cap, n, m)) == 0


def _complete_assignments(pr, cap, n, m):
    """Erzeugt JEDE kapazitätsverträgliche vollständige Zuordnung (jeder Bewerber frei oder einer erreichbaren,
    nicht vollen Klinik zugeordnet) - reines Kapazitäts-Pruning, keine Stabilitätsannahme."""
    fill = [0] * m
    assign = {}

    def backtrack(i):
        if i == n:
            yield tuple(sorted(assign.items()))
            return
        assign.pop(i, None)
        yield from backtrack(i + 1)          # bleibt frei
        for j in pr[i]:
            if fill[j] < cap[j]:
                assign[i] = j
                fill[j] += 1
                yield from backtrack(i + 1)
                fill[j] -= 1
        assign.pop(i, None)

    yield from backtrack(0)


def stable_assignment_brute(pr, ph, cap):
    """Irgendeine stabile Zulassung (Tupel aus (Bewerber, Klinik)) - existiert bei Deferred Acceptance immer, die
    Suche bleibt aber unabhängig davon vollständig (findet auch, falls die Eingabe fehlerhaft wäre, korrekt None)."""
    n, m = len(pr), len(ph)
    for assignment in _complete_assignments(pr, cap, n, m):
        if is_stable(pr, ph, assignment, cap, n, m):
            return assignment
    return None


def all_stable_assignments_brute(pr, ph, cap, max_n=PRACTICAL_MAX_N):
    """ALLE stabilen Zulassungen (nicht nur eine) - für die Eindeutigkeitsmessung, nur kleine n."""
    n, m = len(pr), len(ph)
    if n > max_n:
        raise ValueError(f"all_stable_assignments_brute: n={n} > max_n={max_n}")
    found = set()
    for assignment in _complete_assignments(pr, cap, n, m):
        if is_stable(pr, ph, assignment, cap, n, m):
            found.add(assignment)
    return sorted(found)
