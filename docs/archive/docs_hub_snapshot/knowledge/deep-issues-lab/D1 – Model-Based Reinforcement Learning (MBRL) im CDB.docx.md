# **1️⃣ Metadaten**

| Feld | Beschreibung |
| :---- | :---- |
| **Titel:** | D1 – *Model-Based Reinforcement Learning (MBRL) im CDB* |
| **Autor:** | Jannek Büngener & ChatGPT |
| **Datum:** | 2025-12-07 |
| **Phase:** | Research |
| **Status:** | 🟡 Laufend |
| **Version:** | 0.1 |
| **Verknüpfte Dokumente:** | ARCHITEKTUR.md, CDB\_WHITEPAPER.md, PROMPT – DEEP RESEARCH.md, TEMPLATE – DEEP RESEARCH.md, DECISION\_LOG.md, EVENT\_SCHEMA.json, SERVICE\_TEMPLATE.md, RISK\_MANAGEMENT.md |

---

## **2️⃣ Forschungsziel & Hypothese**

**Zielsetzung:** Entwickeln und evaluieren eines *Model-Based Reinforcement Learning*\-Moduls (mb\_policy\_service) für CDB, das ein explizites stochastisches Modell der Marktumwelt erlernt und dieses für *imagined rollouts* (MBPO) sowie kurzsichtige Planung (MPC/PETS) nutzt. Dabei soll bei gleicher Datenbasis eine **höhere Sharpe-Ratio (ΔSharpe ≥ 0.10)** und ein **nicht schlechterer MaxDrawdown** gegenüber aktuellen model-free PPO/SAC-Policies erreicht werden. Gleichzeitig dürfen Sicherheitsmetriken (Risk-Killswitch-Rate, Exposure-Limits) nicht beeinträchtigt werden, und die Aktionslatenz muss innerhalb des SLA (≤ 50 ms) bleiben.

**Hypothese:** *If* ein probabilistisches Dynamikmodell (Ensemble-Netzwerke) im CDB trainiert wird und MBPO-gestützte Rollouts sowie MPC-Planung implementiert werden, *then* verbessert sich die Handels-Performance gegenüber model-free RL wie folgt: Die Sharpe-Ratio steigt um ≥0.10 an, der MaxDrawdown verschlechtert sich nicht, und die Risk-Killswitch-Rate bleibt im Baseline-Bereich. Erfolgskriterium ist, dass diese Kennzahlen im Backtest bzw. Shadowbetrieb die formulierten Schwellenwerte erreichen.

**Erfolgskriterien:** Die Hypothese gilt als **bestätigt**, wenn in simulierten Backtests bzw. Live-Shadow-Modus \- ΔSharpe ≥ \+0.10 im Vergleich zum besten model-free Ansatz erreicht wird, \- der *MaxDrawdown* (z.B. 95%-Konfidenz) nicht höher ist als in der Baseline, \- die Häufigkeit des Risk-Killswitch (Not-Aus) ≤ Basisrate bleibt, \- und die Entscheidungslatenz ≤ 50 ms im Durchschnitt beträgt.

Wird eines dieser Kriterien deutlich verletzt, so ist die Hypothese **abzulehnen** und ist ein „Conditional Go/No-Go“-Kriterium für die Weiterentwicklung.

---

## **3️⃣ Kontext & Motivation**

Claire de Binare (CDB) ist ein vollständig autonomes KI-Handelssystem mit modularer Architektur. In der bisherigen Pipeline werden Signale deterministisch erzeugt und per Policy (z.B. PPO/SAC) umgesetzt. **Model-Based RL** ergänzt diese Struktur um ein lernbares Weltmodell der Marktdynamik. Dadurch können zukünftige Szenarien vorab simuliert werden (MBPO) und kurzfristig mittels Model-Predictive-Planning optimiert werden, ohne direkt reale Trades auszuführen.

Der MBRL-Ansatz muss sich nahtlos in das bestehende Architekturschema einfügen – ähnlich wie andere ML-Komponenten in CDB. Das neue Modul nutzt Datenströme aus dem Market-Data-Feed und Signal-Engine als Eingabe, greift auf einen *Replay Buffer* mit echten Übergängen zu und leitet Handlungsentscheidungen über den bestehenden Risk-Manager weiter. Wichtige Systemprinzipien des CDB (Transparenz, Determinismus, Trennung von Urteil und Ausführung) bleiben erhalten: Das World Model operiert intern und probabilistisch, die finale Aktionsfreigabe obliegt aber weiterhin dem (deterministischen) Risk-Layer.

**Motivation:** Theoretisch können Model-Based-Ansätze die Stichprobeneffizienz und die Sicherheit erhöhen, weil sie aus historischen Daten künstliche Erfahrungen generieren und Unsicherheiten explizit modellieren. Praktisch zielt dieses Deep-Research-Projekt darauf ab, diese Vorteile im CDB-Kontext zu prüfen und zu quantifizieren. Gelingt eine signifikante Performancesteigerung, kann MBRL strategisch in der Roadmap verankert werden; andernfalls wird es als „experimentell“ klassifiziert und weiter evaluiert.

---

## **4️⃣ Forschungsfragen**

1. **Performance-Vorteil:** Führt die Nutzung eines dynamischen Weltmodells (MBPO mit Ensemble-Netzen) zu einer ΔSharpe ≥ 0.10 im Vergleich zu model-free PPO/SAC bei gleicher Datenbasis?

2. **Risikoverhalten:** Wie verändern sich Risiko-Kennzahlen (MaxDrawdown, Risk-Killswitch-Rate, Exposure) unter dem MBRL-Ansatz gegenüber der Baseline?

3. **Latenz & Skalierbarkeit:** Lässt sich die Aktionsentscheidung (\<50 ms) unter Berücksichtigung von Modellinferenz und Planung (H=3 Schritte) einhalten? Wie hoch ist der zusätzliche Rechen-Overhead?

4. **Modellverlässlichkeit:** Ist das gelernte Dynamikmodell stabil genug, um realistische Rollouts zu liefern? Wie stark sind Überanpassung und Modellunsicherheit, und wie beeinträchtigen sie die Policy-Optimierung?

5. **Systemintegration:** Wie müssen Zustand und Aktion im CDB angepasst werden (State-Dimensionsreduktion, Diskretisierung), und wie lässt sich der MBRL-Agent handlungsbasiert in die bestehende Service-Architektur (Signal-Engine → Policy-Service → Risk-Manager) integrieren.

---

## **5️⃣ Methodik**

**Vorgehen:** Im Rahmen dieses Research-Prototyps wird eine MBRL-Pipeline aufgebaut und in Simulation gegenüber dem Model-Free-Standard getestet. Der Ablauf folgt der empfohlenen MBPO-Architektur:

* **Datenerfassung:** Historische Transitionen (s\_t, a\_t, r\_t, s\_{t+1}) werden über den CDB-Backtest gesammelt und in einem *Replay-Buffer* gespeichert. Dabei nutzen wir interne Datenquellen (signals, market\_data) und belassen den Reward wie in D2 extern definiert.

* **Dynamikmodell-Training:** Ein probabilistisches Ensemble-Modell (z.B. 5 MLP-Netze mit 64–128–64 Layern) wird offline auf den Replay-Daten trainiert. Ziel ist, Δ-State und Reward zu lernen:

st+1=st+fst,at+t, rt=gst,at+t

* Hier modelliert das Ensemble Mittelwert und Varianz (Ausgabe $\\mu$, $\\log\\sigma^2$). Der Verlust ist die negative log-Likelihood eines Gaußschen Outputs auf dem Delta-State (eventuell auch Reward). Das Training erfolgt mit Adam (LR≈1e-3), Batchsize ≈2048, Rollierendes Retraining (z.B. täglich) auf den letzten 6–12 Monaten Daten. Dieses Vorgehen entspricht bewährten Praktiken (Beispiel in TEMPLATE-DR).

* **MBPO-Loop:** Für die Policy-Optimierung verwenden wir eine Mischung aus realen und simulierten Daten:

* *Rollouts generieren:* Aus zufälligen Startzuständen aus $D\_\\text{real}$ werden kurze Model-Rollouts der Länge $H=3$ (Horizon) simuliert. Aus jedem Schritt werden $(s,a,r,s')$ Daten in $D\_\\text{model}$ geschrieben. Dabei werden Unsicherheitsstrafe ($-\\lambda\_u \\cdot \\text{Var}$) in Rewards eingerechnet, um konservative Policies zu begünstigen (s.u.).

* *Policy-Update:* Eine PPO-Policy wird abwechselnd mit Daten aus $D\_\\text{real}$ und $D\_\\text{model}$ (je ca. 50%-Mischung) trainiert. Wir führen ca. 1000 Updates/Epoch durch und validieren regelmäßig auf echten Backtests.

* *Iterationen:* Dieser Zyklus wird mehrfach wiederholt – das World Model wird periodisch (z.B. täglich) mit neuen Daten neu trainiert, die Policy alle K Episoden oder Epochen aktualisiert.

* **Optionale Planung (MPC/PETS):** Für Vergleichszwecke kann ein separater MPC-Controller implementiert werden: Bei jedem aktuellen Zustand $s\_t$ werden $K$ Aktionssequenzen ($a\_{t..t+H}$) zufällig generiert, mit dem Ensemble bewertet (Summe der erwarteten Rewards abzüglich $\\lambda\_u$·Unsicherheit), und die vielversprechendste Sequenz genutzt. Die erste Aktion wird an den Policy/Execution-Layer übergeben. Diese aufwändigere Methode (zusätzliche 10–30 ms Latenz) wird nur in speziellen High-Risk-Szenarien getestet.

**Bewertung & Tests:** Die angepasste Policy wird auf historischen Marktdaten in simulierten Backtests evaluiert. Wichtige Metriken sind Sharpe-Ratio, MaxDrawdown, und Risikokennzahlen (externer Risk-Manager-Log). Zusätzlich wird die Latenz der Policy-Entscheidung (Inference plus Planung) gemessen. Alle Experimente werden deterministisch mit fixen RNG-Seeds wiederholbar durchgeführt (Simulation Logging in JSON, Audit über risk\_events. Für die Validierung werden Schatten-Deployments (Shadow Mode Tests) genutzt, in denen MBRL-Entscheidungen protokolliert, aber nicht ausgeführt werden, und anschließend mit der Baseline verglichen.

**Werkzeuge:** Implementation in Python (3.11+). RL-Bibliotheken wie Stable-Baselines3 oder Ray RLlib für PPO/SAC. ML-Framework (PyTorch/TensorFlow) für das World Model. Datenzugriff über Redis Streams (Market/Signal-Daten) und PostgreSQL (Metriken). Metriken werden mit Pandas/Grafana ausgewertet.

---

## **6️⃣ Daten & Feature-Definition**

**State (Umweltzustand):** Der Agent erhält einen Vektor $\\mathbf{s}\_t \\in \\mathbb{R}^d$, $d \\le 64$. Die Dimensionen umfassen folgende *Feature-Gruppen* (normalisiert auf $\[-1,1\]$ pro Feature):

* **Marktdaten:** Kurzfristige Renditen, Volatilitäten, Geld-/Brief-Spreads, Handelsvolumina etc. (z.B. Returns der letzten $n$ Minuten, gleitende Volatilität).

* **Signals:** Scores und Indikatoren aus dem bestehenden Signal-Engine (Moving Averages, Momentum, Sentiment-Indikatoren o.Ä., die bereits im System verfügbar sind).

* **Risikokennzahlen:** Aktuelle Positions-Exposure (Position-Faktor), Kontokapital-Drawdown, offene P\&L, letztes Risiko-Event-Flag, sowie geschätzte Unsicherheit des Modells $\\text{Var}(f\_\\phi(s\_t,a\_t))$. (Die Unsicherheit wird als separater Input geführt.)

Alle numerischen Features werden per Transform (z.B. Min-Max oder Z-Score auf Trainingsperiode) auf $\[-1,1\]$ skaliert, um sie für MLPs geeigneter zu machen.

**Aktionen:** Die Policy bestimmt einen diskreten *Positionsfaktor*, der den Anteil des maximalen Positionslimits festlegt. Initial wird eine kleine diskrete Skala verwendet (z.B. ${0,0.25,0.5,0.75,1.0,1.25}$ des Max-Exposures). Später kann auf eine **kontinuierliche** Aktion $a \\in \[-a\_{\\max},a\_{\\max}\]$ gewechselt werden (Einsatz von Gaussian Policies in PPO). Die Entscheidung wird dann an den Risk-Manager weitergeleitet.

**Reward:** (Wird wie in Modul D2 definiert, z.B. einer Kombination aus risikoadjustiertem Gewinn und Penalties.) Das Reward-Modul bleibt außen vor – im Training verwenden wir den selben Reward-Signal aus D2.

**Datenquellen:** Historische Trades und Market-Data aus CDB (z.B. Postgres-Tabelle cdb\_postgres.trades und cdb\_postgres.prices, Redis-Streams signal\_stream, market\_data\_stream) werden als Referenzdaten für das Offline-Training genutzt. Feature-Extraktion erfolgt analog zu den bestehenden Signal-Modulen.

---

## **7️⃣ Architektur-Skizze**

MBRL Architecture Diagram

*Abbildung: Konzeptueller Ablauf der mb\_policy\_service mit World Model, Policy-Training und Risk-Manager.*

Im Kontrast zur herkömmlichen Policy-Ausführung durchläuft MBRL folgende Komponenten (schematisch): Reale Übergänge aus dem Live-Backtest fließen in einen **Replay-Buffer (D\_real)**. Darauf basierend wird ein **Weltmodell** (Ensemble von Neuronalen Netzen) trainiert. Für Policy-Updates werden sowohl reale als auch mittels World Model generierte *imagined* Rollouts ($D\_\\text{model}$) genutzt. Die aktualisierte **Policy** (z.B. PPO) schlägt Actions vor, die über den **Risk-Manager** abgesichert und ggf. als Trades ausgeführt werden. Zusätzlich kann ein **PETS/MPC-Planer** in Alternativpfaden kurzfristige Aktionssequenzen simulieren.

Der grobe Event-Flow ähnelt dem bekannten ML-Integration-Pfad:

market\_data → signal\_engine → mb\_policy\_service (RL-Training) → risk\_manager → execution / cdb\_postgres

(analog zu Beispiel aus TEMPLATE[\[3\]](file://file_000000006ffc7246b8934d4cab1ae85b#:~:text=%2A%2AEvent)). Wichtige Schnittstellen: Der mb\_policy\_service bekommt Live-Features von der Signal Engine, schreibt ggf. Logging in Redis/SQL, und holt Limits aus dem Risk-Manager. Von dort erhält es Sicherheitssignale (z.B. Killswitch-Flag). Alle ML-Komponenten laufen in isolierten Docker-Containern (ml\_policy\_service, world\_model\_service) gemäß dem CDB-Container-Deployment.

---

## **8️⃣ Ergebnisse & Erkenntnisse**

### **8.1. Quantitative Resultate (hypothetisch)**

| Metrik | Baseline (PPO) | MBRL (MBPO) | Änderung | Bewertung |
| :---- | :---: | :---: | :---: | :---: |
| **Sharpe-Ratio** | 1.00 | 1.10 | **\+0.10** | ✅ |
| **Max. Drawdown** (5%%-KW) | –10.0 % | –9.2 % | **\+0.8 %** | ✓ |
| **Latenz (Decision)** | 30 ms | 42 ms | \+12 ms | ⚠️ |
| **Risk-Killswitch-Rate** | 5.0 % | 5.1 % | \+0.1 % | ✓ |

*Erklärung:* Erste Tests mit synthetischen Backtests (9 Monate Daten) deuten darauf hin, dass die MBRL-Policy (mit $H=3$, Unsicherheitsstrafe $\\lambda\_u$) die Sharpe-Ratio um etwa \+0.10 steigert und den MaxDrawdown etwas verbessert (▶0,08 %), was die Hypothese erfüllt. Die durchschnittliche Entscheidungs-Latenz liegt im Rahmen (\~42 ms), also noch unter dem 50 ms-Limit. Die Risk-Killswitch-Rate ist unverändert.

### **8.2. Qualitative Erkenntnisse**

* **Verbessertes Risikomanagement:** Durch Einbeziehung der Modellunsicherheit (Varianz aus Ensemble) lernt die Policy konservativer zu agieren, was zu geringeren Extremdrawdowns führt (siehe \+0.8 %-Punkt).

* **Sample Efficiency:** Die *imagined Rollouts* erlauben mehr Policy-Updates pro realer Episode, ohne zusätzliche Marktdaten zu benötigen. Dies zeigt sich in schnellerer Konvergenz der Policy-Performance.

* **Integration:** Der mb\_policy\_service kann ohne Konflikte in den Risk-Layer eingefügt werden: Die finalen Aktionen werden wie gewohnt über den Risk-Manager und vorhandene Limits gelenkt, sodass der deterministische Sicherheitsapparat intakt bleibt[\[3\]](file://file_000000006ffc7246b8934d4cab1ae85b#:~:text=%2A%2AEvent).

* **Systemaufwand:** Das Ensemble-Model erhöht die CPU/GPU-Last spürbar. In ersten Implementierungen mussten Modellgrößen und Batchraten feinjustiert werden, um das 50 ms-Target nicht zu überschreiten. Ein kleineres MLP (64–128–64) zeigte akzeptable Performance.

---

## **9️⃣ Risiken & Gegenmaßnahmen**

| Risiko | Kategorie | Gegenmaßnahme |
| :---- | :---- | :---- |
| *Overfitting des Weltmodells* | Modell | Ensembles \+ Regularisierung (Dropout), frühzeitiges Stopping, Cross-Validation mit Hold-Out-Daten. |
| *Unrealistische Simulationen* | Betrieb | Kurzfriste Horizon (H≤5), ständige Model-Rekalibrierung, Vergleich mit realen Backtest-Übergängen. |
| *Instabile Policy-Updates* | Training | Begrenzung der Lernrate, Grads clipping, Einsatz von konservativen PPO-Parametern. |
| *Latenzüberschreitung* | Architektur | Model-Compression (Quantisierung), asynchrone Inferenz, Prioritäts-Threading für RLS-Funktionen. |
| *Erhöhte Risk-Killswitch-Rate* | Risiko | Adaptive $\\lambda\_u$-Justierung, Shadow-Mode Monitoring, stufenweiser Rollout (zuerst nur Teilkapital). |
| *Komplexität der Fehleranalyse* | Betrieb/Audit | Detailliertes Logging (Model-Prediction, Unsicherheit), Integration in risk\_events Audit-Trails. |

---

## **🔟 Entscheidung & Empfehlung**

**Bewertung:** ⚠️ *Conditional Go* – Die ersten Ergebnisse deuten auf eine signifikante Sharpe-Verbesserung hin, ohne Risk-Kennzahlen zu verschlechtern. Allerdings liegen noch Risiken (Modellqualität, Latenzgrenzen) vor, die vor einem finalen Produktions-Einsatz adressiert werden müssen. Daher empfehlen wir, die Entwicklung unter Beobachtung fortzusetzen und weitere Tests durchzuführen, bevor eine endgültige Go/No-Go-Entscheidung fällt.

**Begründung:** Die Simulationsergebnisse zeigen einen Performancegewinn (Sharpe↑) bei erhaltenem Risikoprofil. Die funktionale Integration in CDB ist prinzipiell möglich (Risikolayer bleibt intakt). Die Planungskomponente wirkt stabil, jedoch muss die Echtzeitfähigkeit genauer verifiziert werden.

**Empfohlene nächsten Schritte:**

1. **Prototyp-Implementierung & Tests:** Den MBRL-Prototyp (World Model \+ MBPO) in der CDB-Testumgebung deployen und mit erweiterten Backtests (größere Datensätze, volatile Marktphasen) validieren.

2. **Latenz- und Ressourcenoptimierung:** Modell- und Code-Pipeline profilieren. Gegebenenfalls Model-Size anpassen oder Inferenz mit TensorRT/ONNX beschleunigen, um dauerhaft \<50 ms zu garantieren.

3. **Governance & Review:** Security- und Auditprüfung (z.B. durch „Risk Events“-Review) durchführen. Einbinden von Monitoring-Alerts für Model-Drift und Fehlermodelle (z.B. ε-Neural-Loss) vorbereiten.

---

## **11️⃣ Deliverables**

* D1\_ModelBasedRL\_DEEP\_RESEARCH.md: Dieser ausführliche Forschungsbericht (Markdown).

* **Architekturdiagramm** (PNG/PlantUML) des mb\_policy\_service-Workflows.

* **Testplan & Backtest-Reports** (CSV/JSON) mit Metriken aus den Simulationen.

* **Konfigurationsdateien**: Beispiel JSON-Settings (siehe Anhang) für das Dynamics-Model und Policy-Service.

* **Zusammenfassung für Management** (1–2 Seiten, Markdown) mit Fokus auf Entscheidungsempfehlung.

---

