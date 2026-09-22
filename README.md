# Krankenhaus-Zulassung – wenn eine Klinik mehr als einen Platz hat – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-krankenhaus-zulassung-demo.streamlit.app/)**

Elftes Stück der **Matching-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", zweite von vier Erweiterungen des Gale-Shapley-Asts (nach [stabile-mitbewohner-demo](https://github.com/sebastian-hanisch/stabile-mitbewohner-demo)) – inspiriert von Alvin Roths Arbeiten zu Marktdesign ohne Geld.

**Gale-Shapley** paart 1:1. Hier kann jede Klinik **mehrere** Bewerber aufnehmen (Kapazität `q`, das Original-Beispiel von Gale & Shapley 1962, "College Admissions"). Deferred Acceptance funktioniert fast unverändert und findet **immer** eine stabile Zulassung – anders als bei Stabile Mitbewohner ist Existenz hier kein Thema. Die neuen Fragen sind andere: **welche** Klinik bleibt trotz freier Plätze leer (**Landklinikensatz**, jetzt in seiner reicheren Fassung), und kann eine Klinik durch **Untertreiben ihrer Kapazität** gewinnen? Die Antwort hängt überraschend davon ab, **wer vorschlägt** – ein Ergebnis, das Sönmez (1997, *JET*) zuerst bewiesen hat.
```
greedy-matching-demo (Wurzel: eine gewählte Zuordnung bleibt)                     [gebaut]
  ├─ augmenting-path-demo … weighted-blossom-demo (Konvergenz)                    [gebaut]
  ├─ gale-shapley-demo (Vorlieben statt Kosten, stabil)                            [gebaut]
  │    ├─ stabile-mitbewohner-demo (eine Gruppe statt zwei Seiten)                 [gebaut]
  │    ├─ krankenhaus-zulassung-demo (many-to-one, Kapazitäten)                    [dieses Stück]
  │    └─ top-trading-cycles-demo (Tausch ohne Geld, Wohnungsmarkt)                [gebaut]
  │         └─ nierentausch-demo (Kompatibilität statt Präferenz, kurze Zyklen)    [gebaut]
  └─ online-matching-demo (Aufträge kommen nacheinander)                          [gebaut]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` über die 100 festen Karten (Seeds 100000–100099) bzw. die festen Sweep-/Manipulations-Seedmengen belegt: 20 Bewerber, 5 Kliniken, Reichweite 40, Kapazitätsquote 120 %, Vorlieben "Entfernung mit Streuung ±20 min". Aufwand = **Bewerbungen**, nie Sekunden.

| Frage | Ergebnis |
|---|---|
| Landklinikensatz sichtbar | ✅ Auf **100 %** der Karten bleibt mindestens eine Klinik unbesetzt (Mittel 2,82 von 5 Kliniken, Median 3) – bei Kapazitätsquote 120 % ist das die Regel, keine Ausnahme. |
| Knapp vs. reichlich | ⚠️ Unter 100 % Quote bleiben **Bewerber** unversorgt (60 % → 9,0 im Mittel unversorgt); ab 100 % kippt die Geschichte: fast immer bleibt stattdessen eine **Klinik** unbesetzt, und die unversorgten Bewerber sinken weiter (180 % Quote → nur noch 3,9 im Mittel). |
| Eindeutigkeit | ✅ Bei Entfernung mit Streuung sind bewerber- und klinikoptimale Zulassung auf **99 von 100** Karten identisch (`noise`-Vorlieben, wie im 1:1-Fall selten mehrdeutig). |
| Bewerber-Lüge | ✅ **0 von 300** Bewerbern können durch falsche Vorlieben gewinnen (Theorem, erschöpfend geprüft) – wie im 1:1-Fall. |
| Klinik-Lüge (Vorlieben) | ⚠️ **5 von 120** Kliniken können durch falsche Vorlieben gewinnen (Kapazität ehrlich) – dieselbe Größenordnung wie die Auftragsseite in `gale-shapley-demo`. |
| Klinik-Lüge (Kapazität), klinikseitig | ⚠️ **1 von 112** geprüften (Klinik, Karte)-Paaren gewinnt durch Untertreiben der Kapazität – selten, aber real (Sönmez 1997, Proposition 1), an einer eigenen, unabhängig geprüften Instanz exakt nachvollzogen. |
| Klinik-Lüge (Kapazität), bewerberseitig | ✅ **0 von 112** – unter dem hier verwendeten, bewerberseitigen Vorschlagen (der Standard dieser Demo) hilft Untertreiben nicht (Sönmez' "Remark 1" für n=2, m=2). |
| Preis der Stabilität | ⚠️ Mittel **10,1 %**, Median **9,0 %** gegenüber der billigsten Zuordnung mit derselben Bewerberzahl (Nebenaspekt, wie in `gale-shapley-demo`, hier über geklonte Klinik-Spalten auf die unveränderte Ungarische Methode zurückgeführt). |
| Aufwand gegen Größe | ✅ `m = n/4`, mittlerer Grad ≈ konstant, n = 10/20/40/80/160/320: **4,5 / 11,1 / 23,7 / 46,4 / 90,2 / 190,3** Bewerbungen – knapp über linear. |

## Was nicht funktioniert hat / widerlegte Vorab-Hypothesen

- **Ein Fehler im eigenen Brute-Force-Orakel, nicht im Algorithmus.** Der erste Entwurf von `hr_oracle.py` prüfte "blockiert diese Person die Karte" schon WÄHREND der Konstruktion (nur gegen die bereits entschiedenen Bewerber) und schnitt darauf basierend Zweige ab – das ist ungültig: ob "bleibt frei" eine Blockade erzeugt, hängt von der VOLLSTÄNDIGEN Zulassung ab, nicht vom bisher entschiedenen Präfix. Gefunden durch einen eigenen Sanity-Check (nicht durch die spätere Testsuite) auf einem trivialen n=2-Beispiel, das die Brute-Force fälschlich für unlösbar erklärte – obwohl Deferred Acceptance beweisbar IMMER eine Lösung findet. Die Suche baut jetzt erst eine vollständige, nur kapazitätsbeschränkte Zuordnung und prüft Stabilität als eigenständigen letzten Schritt.
- **Sönmez' eigene Zahlen ließen sich nicht zitieren.** Das verfügbare Material enthielt die Theoreme, aber nicht seine exakten Beispiel-Präferenzlisten im Wortlaut. Statt sie zu raten, wurde eine eigene, kleine (n=2, m=2) Instanz gesucht und per Brute-Force unabhängig verifiziert, die denselben qualitativen Befund zeigt (klinikseitig gewinnt Klinik 0 durch Untertreiben, bewerberseitig ändert sich nichts) – ehrlicher als eine unbelegte Zahl zu behaupten.
- **Ein Test entlarvte einen eigenen Bug in der Testfixture, nicht im Produktivcode.** Der Manipulations-Testfall filterte die Gegenliste einer Klinik mit `i in sub` (ist der Bewerber IRGENDWO in seiner Falschmeldung) statt `j in sub` (ist GENAU DIESE Klinik in der Falschmeldung) – dieselbe Fehlerklasse, die der Plan im Voraus als Risiko benannt hatte, ist tatsächlich aufgetreten, nur in der Testfixture statt im Kernmodul.
- **`cap=0` bricht nicht nur `hr_admission.py`, sondern auch das eigene Orakel und Zertifikat.** Der Sonderfall "Klinik voll UND leer, nichts zu vergleichen" musste an drei Stellen unabhängig ergänzt werden (Kernalgorithmus, Brute-Force-Prüfer, Zertifikat) – ein Regressionstest allein im Kernmodul hätte die beiden anderen nicht abgedeckt.
- **`matching.games.HospitalResident` stürzt öfter ab als der bereits bekannte Fehlerfall.** Nicht nur `optimal="hospital"` bei einer listenlosen Klinik (bereits von der Vorarbeit dokumentiert), sondern auch `optimal="resident"` bei einem listenlosen BEWERBER wirft eine unbehandelte `IndexError` – das Paket dient deshalb nur als sekundärer Smoke-Test auf Instanzen, in denen jeder Bewerber UND jede Klinik mindestens einen möglichen Partner hat.

## Was die Demo zeigt

- **Suche und Ablauf:** Schritt-Slider und ▶️ über die Ereignisse (Bewerbung, Annahme, Verdrängung, Ablehnung): die Karte mit Bewerbern (Kreise) und Kliniken (Quadrate, beschriftet mit Füllstand/Kapazität, Farbe nach Belegungsgrad); am Ende der **Beweis** (Gültigkeit, keine blockierende Paarung, Maximalität, Landklinikensatz reich) und welche Klinik(en) unbesetzt bleiben.
- **Wie gut?** Belegung, unversorgte Bewerber, bewerber- = klinikoptimal?, Preis der Stabilität; Verteilung über 100 feste Karten.
- **Lohnt sich Lügen?** Erschöpfende Manipulationsproben: Bewerber-Vorlieben, Klinik-Vorlieben, Klinik-Kapazität (getrennt nach bewerber-/klinikseitigem Vorschlagen).
- **Wovon hängt es ab?** Kapazitäts-Sweep (Knappheit ↔ Landklinikensatz), Reichweiten-Sweep, Aufwand gegen Größe.
- **Feste Presets:** Landklinikensatz · Kapazität untertreiben · Mittlere Karte · Knappe/Reichliche Kapazität · Zufällige Vorlieben · Nur Entfernung · Klinik lügt bei den Vorlieben; **Wo die Annahmen enden.**

## Modell und Verfahren

- **Graph:** dieselbe Fahrgemeinschaften-artige Karte wie `gale-shapley-demo` (Bewerber, Kliniken, `SplitMix64`-Zufallsgenerator), **neu:** jede Klinik bekommt eine Kapazität aus einem eigenen, von den Punktkoordinaten unabhängigen Zufallsstrom, skaliert über einen neuen Regler "Kapazitätsquote [%]" (Gesamtkapazität als Prozent der Bewerberzahl).
- **Deferred Acceptance mit Kapazitäten (`hr_admission.py`):** wie `gale-shapley-demo`s Kern, aber `held[Klinik]` ist eine begrenzte Liste statt eines einzelnen Werts. Freier Platz → sofort annehmen (kein Vergleich); voll → mit dem schlechtesten Gehaltenen vergleichen, ggf. verdrängen. Klinikseitiges Vorschlagen (für das klinikoptimale Extrem) läuft über dieselbe Mechanik mit `cap[j]`-fach geklonten Kliniken.
- **Landklinikensatz (reich):** Füllzahl je Klinik UND (für nicht volle Kliniken) die Bewerbermenge sind in JEDER stabilen Zulassung identisch – geprüft über den Vergleich der beiden Extreme (Gitter-Eigenschaft), nicht durch volle Aufzählung.
- **Kapazitäts-Manipulation:** Klinik-Präferenzen über Bewerber-Mengen nach der **"erst auffüllen"**-Konvention (mehr Plätze immer besser, sonst der individuell bessere Bewerber) – eine andere, ebenfalls "responsive" Konvention könnte zu einem anderen Befund führen, deshalb explizit benannt statt stillschweigend angenommen.

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `hr_constants.py` | Regler-Grenzen, Presets und Hilfetexte, feste Seed-Mengen |
| `hr_presets.py` | Permalink-, Preset- und Zufalls-Seed-Logik (mit `card_select` für die zwei festen Lehrbuchkarten) |
| `hr_scenario.py` | Karte (aus `gale-shapley-demo` übernommen), **neu:** Kapazitätsvergabe, zwei feste Lehrbuchkarten |
| `hr_preferences.py` | Vorlieben (nur Entfernung / Streuung / Zufall) |
| `hr_admission.py` | **Neu:** Deferred Acceptance mit Kapazitäten (beide Vorschlagsrichtungen, Ereignisprotokoll, Zertifikat) |
| `hr_oracle.py` | **Neu:** Brute Force (eine oder alle stabilen Zulassungen, für Tests) |
| `hr_strategy.py` | **Neu:** Manipulationsproben (Bewerber-/Klinik-Vorlieben, Klinik-Kapazität) |
| `hr_hungarian.py`, `hr_augment.py`, `hr_greedy.py` | Unverändert aus `gale-shapley-demo` übernommen (Preis der Stabilität über geklonte Klinik-Spalten) |
| `hr_evaluation.py` | Einordnung, Verteilung, Sweeps, Manipulationsraten, Preis der Stabilität |
| `hr_visualization.py` | Plotly-Abbildungen (Achsen gesperrt, Kliniken als beschriftete Quadrate) |
| `tests/` | Algorithmus (Kreuzprüfung gegen Brute Force, Rollentausch, Landklinikensatz, Manipulationsbeweise, Negativkontrollen), Auswertung, Presets, belegte Zahlen, AppTest-Rauchtests |

Die kopierten Bausteine werden durch Tests bewacht (Zufallsgenerator-Vektor). Alle Daten sind synthetisch; die Laufzeit braucht nur numpy, pandas, plotly und streamlit (das Paket `matching` ist reines Testorakel, nie zur Laufzeit importiert).

## Lokal starten

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\streamlit run app.py
```

## Tests ausführen

```bash
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python -m pytest tests -v
```

Die Logik rechnet ausschließlich mit ganzen Zahlen; die im Text genannten Anteile und Mittelwerte sind deshalb auf jeder Plattform identisch.
Die CI (`.github/workflows/tests.yml`) läuft auf Ubuntu mit Python 3.12, bei jedem Push und wöchentlich mit den jeweils neuesten Bibliotheksversionen.
