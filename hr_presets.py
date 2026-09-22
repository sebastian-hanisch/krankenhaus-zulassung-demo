"""SETTING_SPECS-Permalink-Muster, Presets und Zufalls-Seed-Button (Standardmuster des Portfolios, siehe gm_presets.py in
greedy-matching-demo). `card_select` spielt hier die Rolle von `net_select` in den Vorgängerdemos: "none" (zufällige
Karte, alle Regler sichtbar) oder eine der beiden festen Lehrbuchkarten (Regler ausgeblendet)."""

import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

import hr_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None


def _choice(options):
    def cast(value):
        value = str(value)
        if value not in options:
            raise ValueError(value)
        return value
    return cast


SETTING_SPECS = {
    "card_select": SettingSpec("card", _choice(C.CARD_LABELS), C.CARD_NONE),
    "pref_radio": SettingSpec("pref", _choice(C.PREF_LABELS), C.DEFAULT_PREF),
    "noise_slider": SettingSpec("noise", int, C.DEFAULT_NOISE, C.NOISE_MIN, C.NOISE_MAX),
    "n_slider": SettingSpec("n", int, C.DEFAULT_N, C.N_MIN, C.N_MAX),
    "m_slider": SettingSpec("m", int, C.DEFAULT_M, C.M_MIN, C.M_MAX),
    "reach_slider": SettingSpec("reach", int, C.DEFAULT_REACH, C.REACH_MIN, C.REACH_MAX),
    "ballung_slider": SettingSpec("ballung", int, C.DEFAULT_BALLUNG, C.BALLUNG_MIN, C.BALLUNG_MAX),
    "quote_slider": SettingSpec("quote", int, C.DEFAULT_QUOTE, C.QUOTE_MIN, C.QUOTE_MAX),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, 0, C.SEED_MAX),
}
PRESET_KEYS = {"card": "card_select", "pref": "pref_radio", "noise": "noise_slider", "n": "n_slider", "m": "m_slider",
               "reach": "reach_slider", "ballung": "ballung_slider", "quote": "quote_slider", "seed": "seed_input"}
STEPS = {"reach_slider": 5, "ballung_slider": 25, "noise_slider": C.NOISE_STEP, "quote_slider": 10}


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
                if isinstance(value, float) and not math.isfinite(value):
                    continue
                if spec.lo is not None:
                    value = max(spec.lo, value)
                if spec.hi is not None:
                    value = min(spec.hi, value)
                st.session_state[state_key] = value
            except (ValueError, TypeError):
                pass
    for key, step in STEPS.items():
        if key in st.session_state:
            lo = SETTING_SPECS[key].lo
            st.session_state[key] = int(lo + round((st.session_state[key] - lo) / step) * step)
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][key]


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, C.SEED_MAX)
