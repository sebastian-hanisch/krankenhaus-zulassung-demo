"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen der Demo "Krankenhaus-Zulassung"."""

from hr_preferences import DEFAULT_NOISE, DEFAULT_PREF, NOISE_MAX, NOISE_MIN, NOISE_STEP, PREF_LABELS  # noqa: F401

N_MIN, N_MAX, DEFAULT_N = 4, 40, 20          # Bewerber
M_MIN, M_MAX, DEFAULT_M = 2, 10, 5            # Kliniken
REACH_MIN, REACH_MAX, DEFAULT_REACH = 10, 150, 40
BALLUNG_MIN, BALLUNG_MAX, DEFAULT_BALLUNG = 0, 100, 0
QUOTE_MIN, QUOTE_MAX, DEFAULT_QUOTE = 50, 200, 120   # Gesamtkapazitaet als % der Bewerberzahl
DEFAULT_SEED = 20
SEED_MAX = 2_000_000_000

DIST_SEEDS = tuple(range(100000, 100100))
SWEEP_SEEDS = DIST_SEEDS[:40]
SCALE_NS = (10, 20, 40, 80, 160, 320)
SCALE_SEEDS = DIST_SEEDS[:10]
SCALE_DEGREE_AREA = 12000
QUOTE_SWEEP = (60, 80, 100, 110, 120, 130, 150, 180)
REACH_SWEEP = (10, 15, 20, 25, 30, 40, 60, 100)
MANIP_SEEDS = tuple(range(60))     # eigene, kleine Seed-Menge fuer die (teuren) erschoepfenden Manipulationsproben

COLORS = {"held": "#1f77b4", "propose": "#2ca02c", "displace": "#d62728", "reject": "#c8c8c8", "resident": "#2e7d32",
          "hospital": "#7b1fa2", "full": "#1f77b4", "under": "#ff7f0e", "empty": "#d62728"}

CARD_NONE, CARD_RURAL, CARD_CAPACITY = "none", "rural", "capacity"
CARD_LABELS = {CARD_NONE: "Zufällige Karte", CARD_RURAL: "Landklinikensatz (fest)", CARD_CAPACITY: "Kapazitäts-Manipulation (fest)"}

_BASE = dict(card=CARD_NONE, pref=DEFAULT_PREF, noise=DEFAULT_NOISE, n=DEFAULT_N, m=DEFAULT_M, reach=DEFAULT_REACH, ballung=DEFAULT_BALLUNG, quote=DEFAULT_QUOTE, seed=DEFAULT_SEED)
PRESETS = {
    "🏥 Landklinikensatz": {**_BASE, "card": CARD_RURAL},
    "💉 Kapazität untertreiben": {**_BASE, "card": CARD_CAPACITY},
    "🗺️ Mittlere Karte": {**_BASE},
    "📉 Knappe Kapazität": {**_BASE, "quote": 80},
    "📈 Reichliche Kapazität": {**_BASE, "quote": 150},
    "🎲 Zufällige Vorlieben": {**_BASE, "pref": "random"},
    "📏 Nur Entfernung": {**_BASE, "pref": "dist"},
    "🤥 Klinik lügt bei den Vorlieben": {**_BASE, "n": 10, "m": 3, "seed": 7},
}
# Jede Zahl in diesen Texten ist in tests/test_claims.py und tests/test_presets.py belegt
PRESET_HELP = {
    "🏥 Landklinikensatz": "Vier Bewerber, drei Kliniken mit je 2 Plätzen: zwei stabile Zulassungen (bewerber- und klinikoptimal), und in BEIDEN bleibt Klinik 2 (jedermanns letzte Wahl) komplett leer - trotz zweier freier Plätze und obwohl alle vier Bewerber sie in ihrer Liste haben. Das ist der Landklinikensatz an einer von Hand nachvollziehbaren Karte.",
    "💉 Kapazität untertreiben": "Zwei Bewerber, zwei Kliniken: meldet Klinik 0 (wahre Kapazität 2) nur 1 Platz, bekommt sie unter KLINIKSEITIGEM Vorschlagen ihren Wunschkandidaten statt ihrer zweiten Wahl. Bewerberseitig (der Standard in dieser Demo) ändert dieselbe Lüge nichts - eine echte, literaturbelegte Asymmetrie (Sönmez 1997).",
    "🗺️ Mittlere Karte": "20 Bewerber, 5 Kliniken, Kapazitätsquote 120 %: eine typische Karte mit sichtbarem Landklinikensatz, aber nicht jeder bleibt unversorgt.",
    "📉 Knappe Kapazität": "Kapazitätsquote 80 % (weniger Plätze als Bewerber): hier bleiben BEWERBER unversorgt, nicht Kliniken - die andere, intuitivere Geschichte derselben Karte.",
    "📈 Reichliche Kapazität": "Kapazitätsquote 150 %: fast immer bleibt trotzdem mindestens eine Klinik unbesetzt - der Landklinikensatz ist hier die Regel, keine Ausnahme.",
    "🎲 Zufällige Vorlieben": "Ohne jeden Bezug zu Fahrzeiten: deutlich häufiger mehrere stabile Zulassungen als bei geschätzten Fahrzeiten.",
    "📏 Nur Entfernung": "Wenn alle nach derselben Fahrzeit ordnen, sind bewerber- und klinikoptimale Zulassung identisch - keine einzige Karte mit Unterschied.",
    "🤥 Klinik lügt bei den Vorlieben": "Anders als bei der Kapazität kann eine Klinik durch falsche VORLIEBEN (bei ehrlicher Kapazität) auch bewerberseitig gewinnen - wie schon bei den Aufträgen in `gale-shapley-demo`.",
}
