"""Krankenhaus-Zulassung - Deferred Acceptance mit Kapazitaeten - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Zweite Erweiterung des Gale-Shapley-Asts der Matching-Linie: many-to-one statt 1:1 - jede Klinik kann mehrere Bewerber
aufnehmen. Anders als bei Stabile Mitbewohner gibt es hier IMMER eine Loesung; die neuen Befunde sind der reichere
Landklinikensatz und eine literaturbelegte Asymmetrie bei Kapazitaets-Manipulation. Siehe README.

Lauffaehig mit: streamlit run app.py
"""

import time

import numpy as np
import streamlit as st

import hr_constants as C
import hr_evaluation as ev
import hr_admission as A
from hr_presets import apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed, sync_query_params
from hr_visualization import build_map, build_progress, build_quote_sweep, build_reach_sweep, build_scale

st.set_page_config(page_title="Krankenhaus-Zulassung – Sebastian Hanisch", layout="wide")


def _f(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _int(x):
    return f"{x:,.0f}".replace(",", " ")


def _ms(s, digits=1):
    return "–" if s["mean"] is None else f"{_f(s['mean'], digits)} | {_f(s['median'], digits)}"


def _share(x):
    return "–" if x is None else f"{100 * x:.0f} %"


@st.cache_resource(show_spinner=False, max_entries=16)
def _analysis(params):
    card, pref, noise, n, m, reach, ballung, quote, seed = params
    sc = ev.scenario_from_settings(card, n, m, reach, ballung, quote, seed)
    return ev.analyse(sc, pref, noise, seed)


@st.cache_data(show_spinner=False)
def _distribution(n, m, reach, ballung, quote, pref, noise):
    return ev.distribution(n, m, reach, ballung, quote, pref, noise)


@st.cache_data(show_spinner=False)
def _quote_sweep(n, m, reach):
    return ev.quote_sweep(n, m, reach)


@st.cache_data(show_spinner=False)
def _reach_sweep(n, m, quote):
    return ev.reach_sweep(n, m, quote=quote)


@st.cache_data(show_spinner=False)
def _scale():
    return ev.scale_table()


@st.cache_data(show_spinner=False)
def _manip_residents():
    return ev.manipulation_residents()


@st.cache_data(show_spinner=False)
def _manip_hospital_prefs():
    return ev.manipulation_hospital_prefs()


@st.cache_data(show_spinner=False)
def _manip_capacity(proposer):
    return ev.manipulation_capacity(proposer)


st.title("🏥 Krankenhaus-Zulassung – wenn eine Klinik mehr als einen Platz hat")
st.markdown(
    """
**Gale-Shapley** paart 1:1. Hier kann jede Klinik **mehrere** Bewerber aufnehmen (Kapazität `q`) - Deferred Acceptance
funktioniert fast unverändert und findet **immer** eine stabile Zulassung. Die neuen Fragen sind andere: **welche**
Klinik bleibt trotz freier Plätze leer (**Landklinikensatz**, jetzt in seiner reicheren Fassung), und kann eine Klinik
durch **Untertreiben ihrer Kapazität** gewinnen? Die Antwort hängt überraschend davon ab, **wer vorschlägt**.
"""
)
st.caption(
    "Zweites von vier neuen Stücken der Matching-Linie (nach Stabile Mitbewohner), inspiriert von Alvin Roths Marktdesign-Arbeiten "
    "(Sönmez 1997 bewies die Kapazitäts-Manipulation, die diese Demo zeigt). Danach folgen Top Trading Cycles und Nierentausch, beide inzwischen gebaut."
)

with st.expander("So funktioniert Deferred Acceptance mit Kapazitäten", expanded=True):
    st.markdown(
        """
1. **Bewerbung beim eigenen Favoriten:** jeder Bewerber bewirbt sich der Reihe nach bei seinem nächsten Favoriten.
2. **Freier Platz? Sofort annehmen.** Hat die Klinik noch Kapazität übrig, wird IMMER angenommen, ohne Vergleich - genau das macht Kapazitäts-Manipulation später möglich.
3. **Voll? Mit dem schlechtesten Gehaltenen vergleichen.** Besser → verdrängen (der Verdrängte wird wieder frei), sonst ablehnen.
4. **Ende:** niemand kann mehr etwas verbessern - bewerberoptimal und immer stabil. Anders als bei Stabile Mitbewohner **gibt es hier immer eine Lösung**.
        """
    )

st.caption("🎯 Schnellstart – eine Beispielkarte laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name] or None)

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    card = st.session_state.get("card_select", C.CARD_NONE)
    if card == C.CARD_NONE:
        pref = st.radio("Vorlieben", list(C.PREF_LABELS), key="pref_radio", format_func=lambda k: C.PREF_LABELS[k])
        noise = st.slider("Streuung [min]", *bounds("noise_slider"), key="noise_slider", step=C.NOISE_STEP) if pref == "noise" else C.DEFAULT_NOISE
        n = st.slider("Bewerber", *bounds("n_slider"), key="n_slider")
        m = st.slider("Kliniken", *bounds("m_slider"), key="m_slider")
        reach = st.slider("Reichweite [min]", *bounds("reach_slider"), key="reach_slider", step=5)
        ballung = st.slider("Ballung [%]", *bounds("ballung_slider"), key="ballung_slider", step=25)
        quote = st.slider("Kapazitätsquote [%]", *bounds("quote_slider"), key="quote_slider", step=10,
                          help="Gesamtkapazität aller Kliniken als Prozent der Bewerberzahl. 100 % + vollständige Listen füllt immer alle; darunter bleiben Bewerber frei, darüber Kliniken.")
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.button("🎲 Neue Karte generieren", width="stretch", on_click=randomize_seed)
    else:
        pref, noise, ballung, seed = st.session_state.get("pref_radio", C.DEFAULT_PREF), C.DEFAULT_NOISE, C.DEFAULT_BALLUNG, st.session_state.get("seed_input", C.DEFAULT_SEED)
        n, m, reach, quote = C.DEFAULT_N, C.DEFAULT_M, C.DEFAULT_REACH, C.DEFAULT_QUOTE
        st.caption(f"Feste Karte ({C.CARD_LABELS[card]}) - es gibt nichts zu erzeugen.")

# --- Ablauf ------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Ablauf")
step_col, play_col = st.columns([6, 2])
params = (card, pref, int(noise), int(n), int(m), int(reach), int(ballung), int(quote), int(seed))
with st.spinner("Rechne..."):
    a = _analysis(params)
sc, res = a.scenario, a.result
level, code, d = ev.verdict(a)
n_events = res.n_events
if st.session_state.get("hr_step_owner") != params:
    st.session_state["hr_step"] = n_events
    st.session_state["hr_step_owner"] = params
with step_col:
    if n_events > 0:
        step = st.slider("Ereignis", 0, n_events, key="hr_step")
    else:
        step = 0
        st.caption("Kein Ereignis: keine Paare möglich.")
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch", disabled=n_events == 0)
sync_query_params({"card_select": card, "pref_radio": pref, "noise_slider": int(noise), "n_slider": int(n), "m_slider": int(m),
                   "reach_slider": int(reach), "ballung_slider": int(ballung), "quote_slider": int(quote), "seed_input": int(seed)})
view_slot = st.empty()


def _event_text(k):
    if k == 0:
        return f"Anfang: alle {sc.n} Bewerber sind frei, alle Kliniken leer. Noch keine Bewerbung."
    e = res.events[k - 1]
    if e.kind == A.EV_PROPOSE:
        return f"Bewerber {e.r} bewirbt sich bei Klinik {e.h}."
    if e.kind == A.EV_ACCEPT:
        return f"Klinik {e.h} nimmt Bewerber {e.r} an (noch ein freier Platz)."
    if e.kind == A.EV_DISPLACE:
        return f"Klinik {e.h} verdrängt Bewerber {e.r} zugunsten von {e.cause} (Klinik war voll, {e.cause} ist besser)."
    if e.kind == A.EV_REJECT:
        return f"Klinik {e.h} lehnt Bewerber {e.r} ab (voll, alle Gehaltenen sind besser)."
    return "unbekanntes Ereignis"


def _cert_table():
    c = a.cert
    ok = lambda b: "✅" if b else ("–" if b is None else "❌")
    rows = [("Gültigkeit", ok(c["s1_valid"])), ("Keine blockierende Paarung", ok(c["s2_no_blocking"])),
            ("Maximalität", ok(c["s3_maximal"])), ("Landklinikensatz (reich)", ok(c.get("s5_rural_hospitals")))]
    return {"Bestandteil": [r[0] for r in rows], "Ergebnis": [r[1] for r in rows]}


def _render(k):
    with view_slot.container():
        c1, c2 = st.columns([3, 2])
        c1.markdown(f"**Nach {k} von {n_events} Ereignissen** – " + _event_text(k))
        snap = A.state_at(res, k)
        pairs_now = [(i, j) for j in range(sc.m) for i in snap.held[j]]
        event = res.events[k - 1] if k > 0 else None
        c1.plotly_chart(build_map(sc, pairs_now, snap.fill, event), width="stretch", key=f"hr_map_{k}")
        c2.markdown("**Verlauf**")
        c2.plotly_chart(build_progress(res, k), width="stretch", key=f"hr_progress_{k}")
        if k == n_events:
            st.markdown("**Beweis:** stabil, und wer bleibt unbesetzt?")
            st.table(_cert_table())
            under = [j for j in range(sc.m) if snap.fill[j] < sc.cap[j]]
            if under:
                st.caption(f"Nicht voll: Klinik(en) {', '.join(str(j) for j in under)} - laut Landklinikensatz in JEDER stabilen Zulassung mit denselben Bewerbern (bewerber- und klinikoptimales Extrem stimmen hier überein: {d['same_ro_ho']}).")


if auto_play:
    frames = sorted({int(round(x)) for x in np.linspace(0, n_events, min(n_events, 40) + 1)})
    for k in frames:
        _render(k)
        time.sleep(min(0.6, 6.0 / max(len(frames), 1)))
    step = n_events
else:
    _render(step)

st.caption("Kreise: Bewerber (gefüllt = zugelassen, offen = frei). Quadrate: Kliniken, beschriftet mit Füllstand/Kapazität (lila = voll, orange = teilweise, rot = leer). "
           "Farbige Kante: das letzte Ereignis (grün = Annahme, rot = Verdrängung, grau gestrichelt = Ablehnung).")

st.markdown("---")

# --- Landklinikensatz und Kapazität -----------------------------------------------------------------------------

st.markdown("## 🎯 Wer bleibt unbesetzt, und lohnt sich Untertreiben?")
if code == ev.NONE:
    st.info("ℹ️ Kein einziges Paar ist möglich – die Reichweite ist zu klein.")
else:
    st.success(f"✅ {d['count']} Bewerber zugelassen, {d['unmatched']} unversorgt (harmlos, wenn die Klinik dafür wirklich keinen weiteren geeigneten Bewerber mehr hat) - stabil, {d['cert_ok'] and 'Zertifikat bestätigt' or 'Zertifikat NICHT bestätigt'}.")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Belegung", f"{sum(d['fill'])} / {d['total_cap']}", delta=f"{d['under_count']} Klinik(en) nicht voll", delta_color="off")
m2.metric("Bewerber unversorgt", f"{d['unmatched']}", delta=f"von {sc.n}", delta_color="off")
m3.metric("Bewerber- = klinikoptimal?", "Ja" if d["same_ro_ho"] else "Nein", help="Stimmen beide Extreme überein, gilt die Zulassung als eindeutig (bzw. der Landklinikensatz für JEDE dazwischenliegende stabile Zulassung, nicht nur die Extreme).")
prem = ev.price_of_stability(sc, res.pairs)
m4.metric("Preis der Stabilität", f"{_f(prem)} %" if prem is not None else "–", help="Mehrkosten gegenüber der billigsten Zuordnung mit derselben Bewerberzahl (Nebenaspekt, wie in gale-shapley-demo).")

st.markdown(f"**Nicht nur diese eine Karte:** {len(C.DIST_SEEDS)} feste Karten mit denselben Einstellungen (Bewerber {n}, Kliniken {m}, Reichweite {reach}, Quote {quote} %), getrennt vom Seed oben.")
if card == C.CARD_NONE:
    dist = _distribution(int(n), int(m), int(reach), int(ballung), int(quote), pref, int(noise))
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Karten mit unbesetzter Klinik", _share(dist["any_under_share"]))
    p2.metric("Bewerber unversorgt (Mittel | Median)", _ms(dist["unmatched"]))
    p3.metric("Eindeutig (Ø ≠ klinikoptimal selten)", _share(dist["same_ro_ho_share"]))
    p4.metric("Preis der Stabilität (Mittel | Median)", _ms(dist["premium"]) + " %" if dist["premium"]["mean"] is not None else "–")
else:
    st.info("Feste Karte: es gibt nur diese eine Ziehung. Für die Verteilung über viele Karten eine zufällige Karte wählen.")

st.markdown("---")

# --- Manipulation ------------------------------------------------------------------------------------------------

st.subheader("🔬 Lohnt sich Lügen?")
if st.button("Manipulationsproben rechnen (Bewerber, Klinik-Vorlieben, Klinik-Kapazität)", key="manip_start"):
    st.session_state["manip_on"] = True
if st.session_state.get("manip_on"):
    with st.spinner("Rechne erschöpfend über alle Meldungen..."):
        mr, mh, mch, mcr = _manip_residents(), _manip_hospital_prefs(), _manip_capacity("H"), _manip_capacity("R")
    st.table({"Wer": ["Bewerber (Vorlieben)", "Klinik (Vorlieben, Kapazität ehrlich)", "Klinik (Kapazität, klinikseitiges Vorschlagen)", "Klinik (Kapazität, bewerberseitiges Vorschlagen)"],
             "Gewinnt durch Lüge": [f"{r['gain']} von {r['total']}" for r in (mr, mh, mch, mcr)]})
    st.caption("Bewerber gewinnen nie (Theorem, hier erschöpfend bestätigt). Klinik-Vorlieben zu verfälschen hilft manchmal (wie schon bei den Aufträgen in `gale-shapley-demo`). "
               "Kapazität zu untertreiben hilft NUR unter klinikseitigem Vorschlagen (Sönmez 1997) - bewerberseitig (der Standard hier) so gut wie nie.")

st.markdown("---")

st.subheader("🔬 Wovon hängt es ab?")
if card == C.CARD_NONE:
    if st.button("Kapazitäts-Sweep (40 Karten je Quote)", key="quote_start"):
        st.session_state["quote_on"] = (int(n), int(m), int(reach))
    if st.session_state.get("quote_on") == (int(n), int(m), int(reach)):
        with st.spinner("Rechne..."):
            qrows = _quote_sweep(int(n), int(m), int(reach))
        c1, c2 = st.columns([3, 2])
        c1.plotly_chart(build_quote_sweep(qrows), width="stretch", key="hr_quote_chart")
        c2.table({"Quote": [r["quote"] for r in qrows], "unbesetzt [%]": [_share(r["any_under_share"]) for r in qrows], "unversorgt (Mittel)": [_f(r["unmatched_mean"], 1) for r in qrows]})
        st.caption("Unter 100 % bleiben Bewerber unversorgt (Knappheit); ab 100 % kippt die Geschichte: fast immer bleibt stattdessen eine Klinik unbesetzt (Landklinikensatz).")

    if st.button("Reichweiten-Sweep (40 Karten je Wert)", key="reach_start"):
        st.session_state["reach_on"] = (int(n), int(m), int(quote))
    if st.session_state.get("reach_on") == (int(n), int(m), int(quote)):
        with st.spinner("Rechne..."):
            rrows = _reach_sweep(int(n), int(m), int(quote))
        c1, c2 = st.columns([3, 2])
        c1.plotly_chart(build_reach_sweep(rrows), width="stretch", key="hr_reach_chart")
        c2.table({"Reichweite": [r["reach"] for r in rrows], "Grad": [_f(r["degree"], 2) for r in rrows], "unbesetzt [%]": [_share(r["any_under_share"]) for r in rrows]})

if st.button("Aufwand gegen die Größe (n = 10 bis 320)", key="scale_start"):
    st.session_state["scale_on"] = True
if st.session_state.get("scale_on"):
    with st.spinner("Rechne..."):
        srows = _scale()
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(build_scale(srows), width="stretch", key="hr_scale_chart")
    c2.table({"n": [r["n"] for r in srows], "Kliniken": [r["m"] for r in srows], "Bewerbungen": [_f(r["proposals"], 1) for r in srows]})

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **"Erst auffüllen" ist die einzig sinnvolle Klinik-Präferenz über Mengen** | Andere responsive Erweiterungen sind denkbar und können zu anderen Manipulationsbefunden führen. | (außerhalb der Linie) |
| **Paare, keine größeren Kreise/Ketten** | Manche Tauschbörsen (Wohnungen, Nieren) brauchen Zyklen statt Zulassungen. | **Top Trading Cycles → Nierentausch** (gebaut) |
| **Kapazität hat nur eine Obergrenze** | Quoten mit Unter- UND Obergrenze (z. B. Mindestgröße einer Abteilung) brauchen ein anderes Modell. | (außerhalb der Linie) |
"""
)
st.caption("Damit ist die vierteilige Erweiterung der Matching-Linie um den Gale-Shapley-Ast vollständig gebaut (Top Trading Cycles und Nierentausch folgten).")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** Bewerber $R$, Kliniken $H$ mit Kapazität $q_h$. Gesucht: eine Zulassung $\mu$ (jeder Bewerber höchstens
eine Klinik, jede Klinik höchstens $q_h$ Bewerber), sodass kein Paar $(r,h)$ blockiert - $r$ bevorzugt $h$ gegenüber
seinem jetzigen Zustand UND ($h$ hat einen freien Platz ODER bevorzugt $r$ gegenüber seinem schlechtesten Gehaltenen).

**Deferred Acceptance.** Bewerber schlagen vor; eine Klinik mit freiem Platz nimmt sofort an, eine volle Klinik
vergleicht mit dem schlechtesten Gehaltenen. Terminiert immer (jede Bewerbung wird höchstens einmal pro Bewerber
gemacht) mit einer stabilen, **bewerberoptimalen** Zulassung (Gale & Shapley 1962).

**Landklinikensatz (reiche Fassung).** In JEDER stabilen Zulassung hat jede Klinik dieselbe Füllzahl, und jede Klinik
unter Kapazität hat sogar überall dieselben Bewerber. Da die Menge der stabilen Zulassungen ein Verband ist, genügt
der Vergleich der beiden Extreme (bewerber- und klinikoptimal) - stimmen sie überein, gilt die Aussage für jede
dazwischenliegende stabile Zulassung.

**Kapazitäts-Manipulation (Sönmez 1997).** Klinik-Präferenzen über Bewerber-Mengen: die **"erst auffüllen"**-Erweiterung
(mehr Plätze ist immer besser, unter gleicher Anzahl gewinnt der individuell bessere Bewerber). Unter bewerberseitigem
Vorschlagen kann keine Klinik durch Untertreiben ihrer Kapazität gewinnen (für n=2, m=2 bewiesen - Sönmez' "Remark 1");
unter klinikseitigem Vorschlagen kann sie es (Sönmez' Proposition 1, hier an einer eigenen, unabhängig geprüften
Instanz gezeigt).

Implementiert in `hr_scenario.py` (Karte, Kapazitätsvergabe), `hr_preferences.py`, `hr_admission.py` (Kern mit
Ereignisprotokoll und Zertifikat), `hr_oracle.py` (Brute Force), `hr_strategy.py` (Manipulationsproben), `hr_hungarian.py`
(Preis der Stabilität über geklonte Kliniken, unverändert aus `gale-shapley-demo` übernommen).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
