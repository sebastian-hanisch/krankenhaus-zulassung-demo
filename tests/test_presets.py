"""Presets: jedes hat einen Hilfetext, die genannten Zahlen stimmen, Regler-/Schrittgitter sind gültig."""

import hr_constants as C
import hr_evaluation as ev
from hr_presets import PRESET_KEYS, SETTING_SPECS, STEPS


def test_every_preset_has_help_text():
    for name in C.PRESETS:
        assert name in C.PRESET_HELP and C.PRESET_HELP[name]


def test_preset_keys_cover_every_setting_spec():
    assert set(PRESET_KEYS.values()) == set(SETTING_SPECS)
    for name, p in C.PRESETS.items():
        assert set(p) == set(PRESET_KEYS), name


def test_bounds_and_step_grid_are_valid():
    for state_key, spec in SETTING_SPECS.items():
        if spec.lo is not None and spec.hi is not None and isinstance(spec.default, (int, float)):
            assert spec.lo <= spec.default <= spec.hi, state_key
    for key, step in STEPS.items():
        lo, hi = SETTING_SPECS[key].lo, SETTING_SPECS[key].hi
        assert (hi - lo) % step == 0, key


def test_presets_do_not_collide_with_dist_seeds():
    for name, p in C.PRESETS.items():
        assert p["seed"] not in C.DIST_SEEDS, name


def _verdict_for(name):
    p = C.PRESETS[name]
    sc = ev.scenario_from_settings(p["card"], p["n"], p["m"], p["reach"], p["ballung"], p["quote"], p["seed"])
    a = ev.analyse(sc, p["pref"], p["noise"], p["seed"])
    return ev.verdict(a)


def test_presets_show_what_the_help_text_says():
    level, code, d = _verdict_for("🏥 Landklinikensatz")
    assert code == ev.SOLVED and d["fill"] == (2, 2, 0) and d["under_count"] == 1

    level, code, d = _verdict_for("💉 Kapazität untertreiben")
    assert code == ev.SOLVED and d["fill"] == (1, 1) and d["cap"] == (2, 1)

    level, code, d = _verdict_for("🗺️ Mittlere Karte")
    assert code == ev.SOLVED and d["count"] == 17 and d["under_count"] == 2

    level, code, d = _verdict_for("📉 Knappe Kapazität")
    assert code == ev.SOLVED and d["unmatched"] > 0

    level, code, d = _verdict_for("📈 Reichliche Kapazität")
    assert code == ev.SOLVED and d["under_count"] >= 1

    level, code, d = _verdict_for("📏 Nur Entfernung")
    assert code == ev.SOLVED and d["same_ro_ho"] is True


def test_default_preset_medium_map_matches_test_claims():
    """20/5/40/120 % ist zugleich der Standard UND die Basis von tests/test_claims.py - hier nur der Einzelfall (Seed 20)."""
    sc = ev.scenario_from_settings(C.CARD_NONE, C.DEFAULT_N, C.DEFAULT_M, C.DEFAULT_REACH, C.DEFAULT_BALLUNG, C.DEFAULT_QUOTE, C.DEFAULT_SEED)
    a = ev.analyse(sc, C.DEFAULT_PREF, C.DEFAULT_NOISE, C.DEFAULT_SEED)
    lvl, code, d = ev.verdict(a)
    assert code == ev.SOLVED and d["count"] == 17


def test_capacity_manipulation_preset_reproduces_the_asymmetry():
    """Direkte Verknuepfung mit dem in hr_admission getesteten Kernbefund: klinikseitig gewinnt Klinik 0 durch
    Untertreiben, bewerberseitig nicht."""
    import hr_admission as A
    sc = C.PRESETS["💉 Kapazität untertreiben"]
    scenario = ev.scenario_from_settings(sc["card"], sc["n"], sc["m"], sc["reach"], sc["ballung"], sc["quote"], sc["seed"])
    pr, ph = scenario.lists
    true_h = A.run(pr, ph, scenario.cap, proposer="H", record=False)
    under_h = A.run(pr, ph, (scenario.cap[0] - 1, scenario.cap[1]), proposer="H", record=False)
    held_true = [i for i, j in true_h.pairs if j == 0]
    held_under = [i for i, j in under_h.pairs if j == 0]
    assert held_true == [1] and held_under == [0]
