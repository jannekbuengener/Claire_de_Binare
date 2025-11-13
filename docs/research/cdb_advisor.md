---
status: archived
migration_status: resolved
## note: "Legacy file-links entfernt, Textreferenzen beibehalten (ADR-027)"

**ML-basierter “Signal-Advisor” im deterministischen Handelssystem*.***

**Executive Summary (Management Summary)**

In diesem Konzeptpapier wird die geplante Integration eines **Machine-Learning (ML)** basierten Signal Advisors in das bestehende **deterministische Trading-Framework "Claire de Binaire"** skizziert. Ziel ist es, zu evaluieren, ob und wie ein ML-Modul die Interpretation von Marktsituationen verbessern und die **Konfidenz von Handelssignalen** erhöhen kann – **unter Wahrung von Erklärbarkeit (Explainability), Auditierbarkeit und Risikoabschirmung**. Das Dokument fasst Hypothese, Forschungsfragen, Vorgehensmethodik sowie technische und organisatorische Rahmenbedingungen zusammen. Es enthält eine klare Gliederung der Forschungsstränge (Methodik, Features, Modelle, Erklärungsmethoden, Risiko-Governance, Tests, Mensch-Maschine-Interface) und einen Aufgabenplan für die Umsetzung der Studie. Am Ende stehen **konkrete Deliverables** (Bericht, Entscheidungsgrundlage, Datenmodell-Vorschlag, Governance-Leitlinien) sowie eine Abgrenzung des Vorhabens. Die finale Ausarbeitung soll als 20–25-seitiger Bericht in Markdown/PDF-Format erfolgen – mit prägnanten Kapiteln, Tabellen (z.B. Modellvergleich, Risiko-Mapping), einer Diagramm Visualisierung der ML-Integration im *Shadow Mode* und einem abschließenden **Go/No-Go** Entscheidungsvorschlag. Dieses Briefing dient als Grundlage, um das Forschungsprojekt effizient und nachvollziehbar durchzuführen und letztlich zu entscheiden, **wie weit ein ML-Advisor in einem streng regelbasierten System gehen darf**, ohne die **deterministische Nachvollziehbarkeit und Sicherheit** zu kompromittieren.

**1\. Einleitung und Hintergrund**

Claire de Binaire ist ein algorithmisches Handelssystem, das bislang **rein deterministisch** und regelbasiert arbeitet. Eine zentrale **Strategie-Engine** generiert Handelssignale anhand fester Indikatoren (z.B. Momentum, Volumen), und ein mehrlagiger **Risikomanager** überwacht strikt die Einhaltung vordefinierter Limits bevor Trades ausgeführt werden . Diese Architektur
1 2

gewährleistet hohe Nachvollziehbarkeit und Kontrolle: Jede Entscheidung folgt klaren If/Else-Regeln, 3 4
was Auditierbarkeit und Vorhersehbarkeit sicherstellt . Im aktuellen Stand (MVP Core) ist die Signal-Engine **modular, aber vollständig regelbasiert** ausgelegt . Eine mögliche Erweiterung um
5

6
KI/ML-Methoden wurde zwar von Anfang an als *Roadmap-Option* benannt , ist jedoch erst für eine 7
zukünftige Phase vorgesehen (Phase 4+, nach Stabilisierung des Kernsystems) .

Angesichts zunehmender Marktkomplexität und der Verfügbarkeit datengetriebener Ansätze stellt sich nun die Frage, ob **Machine Learning** helfen kann, **Handelssignale präziser** und *adaptive*r zu gestalten, ohne die bestehenden Sicherungsmechanismen zu unterlaufen. Andere Open-Source-Trading Plattformen wie Freqtrade oder OctoBot haben bereits ML-Komponenten integriert, was auf ein innovatives Potenzial hindeutet. Claire de Binaire bietet mit seiner entkoppelten Microservice Architektur (Event-getrieben via Message-Bus) eine geeignete Spielwiese, um einen ML-basierten *Signal* 6
*Advisor* als separaten Service anzudocken , der parallel zur bestehenden Strategie-Engine läuft.  1
Die Herausforderung besteht darin, **die Vorteile probabilistischer Modelle zu nutzen, ohne die deterministische Integrität des Systems aufzugeben**. Dieses Briefing umreißt die Forschungsziele und \-fragen, den methodischen Ansatz sowie technische und governance-bezogene Überlegungen, um eine fundierte Entscheidungsgrundlage für oder gegen eine ML-Integration zu erarbeiten.

**2\. Zielsetzung und Forschungshypothese**

**Zielsetzung:** Das Forschungsprojekt soll systematisch evaluieren, **ob ein ML-Modul die Marktinterpretation und Signalqualität signifikant verbessern kann**, und falls ja, unter welchen Auflagen. Es geht **nicht** um eine sofortige Implementierung ins produktive Trading, sondern um einen kontrollierten *Proof-of-Concept* und eine Entscheidungsgrundlage. Die Ergebnisse sollen klar aufzeigen, ob eine Integration des ML-Advisors ein **Go**, **Conditional Go** (unter Auflagen) oder **No-Go** erhält – unter Berücksichtigung von Performance, Risiken und Umsetzungskosten.

**Forschungshypothese:** *Ein Machine-Learning-Modul kann in Echtzeit-Marktdaten Muster erkennen und Handelssignale mit höherer Qualität/Konfidenz generieren als die rein regelbasierte Strategie – vorausgesetzt, Explainability (Erklärbarkeit der Modellentscheidungen), Auditierbarkeit (lückenlose Nachvollziehbarkeit im Nachhinein) und Risikoabschirmung (keine Gefährdung der bestehenden Risk-Limits) bleiben vollständig gewährleistet.*

Diese Hypothese impliziert, dass **ML-gestützte Signale bessere Ergebnisse liefern** (z.B. höhere Trefferquote oder Profitabilität im Backtest) **ohne** unkontrollierte Risiken einzuführen. Insbesondere soll überprüft werden, ob der ML-Advisor *zusätzliche Marktdynamiken* einfängt, die mit festen Regeln schwer zu modellieren sind, und ob er die **Konfidenz bestehender Signale erhöhen** bzw. unsichere Signale filtern kann. All dies muss jedoch im Rahmen eines streng überwachten, deterministischen Entscheidungsprozesses passieren. Die Hypothese wird angenommen, wenn die ML-Integration in Tests eine **messbare Verbesserung** (quantitative Kennzahlen) zeigt **und zugleich** qualitativ nachweist, dass Erklärbarkeit und Kontrollierbarkeit gegeben sind.

**3\. Zentrale Forschungsfragen**

Das Projekt adressiert mehrere **Kernfragen** aus unterschiedlichen Blickwinkeln – **strategisch**,  **technologisch**, **architektonisch** sowie **ethisch/regulatorisch**:

•
**Strategische Reichweite:** *Wie weit darf ein ML-basierter Advisor in einem deterministischen System gehen?* – Soll das ML-Modul lediglich als **Unterstützer/Filter** agieren (z.B. Warnungen oder Bestätigung von Regel-Signalen) oder **eigene Handelssignale autonom erzeugen**? Wie stellt man sicher, dass trotz ML-Unterstützung die *letztendliche Entscheidungslogik deterministisch, nachvollziehbar und vom Risk-Layer kontrolliert* bleibt? Diese Frage tangiert auch Verantwortlichkeiten und Vertrauen: Würde man einem „Black Box“-Modell erlauben, Trades auszulösen, oder bleibt der Mensch/(Regel-)Engine in letzter Instanz in charge?

•
**Modellauswahl & Echtzeit-Tauglichkeit:** *Welche ML-Modelle sind realistisch für die Verarbeitung*

*von Echtzeit-Features geeignet?* Konkret im Fokus stehen **klassische tabellarische Modelle** (z.B. Gradient Boosting wie XGBoost) vs. **Sequenzmodelle** für Zeitreihen (wie LSTM-Netze, Temporal Convolutional Networks (TCN) oder Transformer-basierte Ansätze (TST)). Bewertet werden müssen **Latenz** (Inference in ms-Bereich für Sekundendaten?), **Trainingsaufwand** (Datenvolumen, Re-Training-Frequenz), **Erklärbarkeit** (Baum-Modelle bieten intrinsische Feature Importance, während tiefe Netze komplexer sind) und **Robustheit**. Welche dieser Modellklassen lässt sich pragmatisch in eine Streaming-Pipeline einbinden, ohne das System auszubremsen?

2
Gibt es Hardware-Anforderungen (GPU ja/nein) und wie häufig müsste ein Modell neu trainiert werden, um aktuell zu bleiben?

•
**Risikomanagement & Ausreißerbehandlung:** *Wie schützt man den bestehenden Risk-Layer vor*
*probabilistischen Ausreißern eines ML-Modells?* – Da ML-Modelle mit **Wahrscheinlichkeiten** arbeiten und gelegentlich stark fehlerhafte Vorschläge (Ausreißer) liefern können, muss geklärt werden, welche **Schutzmechanismen** eingebaut werden. Braucht es zusätzliche **Gating-Regeln** im Risikomanager, speziell für ML-Signale (z.B. wenn ein ML-Signal ungewöhnlich hohe Positionsgröße oder Confidenz fordert, wird es verworfen oder nur manuell bestätigt)? Wie können wir sicherstellen, dass **kein einzelnes Fehlverhalten des Modells** das System in Gefahr bringt? Hier spielt auch die **Kalibrierung der Konfidenz** eine Rolle: z.B. könnte man festlegen, dass ML-Signale nur ab einer bestimmten Konfidenzschwelle überhaupt berücksichtigt werden
. Außerdem: Wie erkennt man *driftende* oder *degradierte* Modelle rechtzeitig (Stichwort: 8
Monitoring der Modellgüte) und zieht sie aus dem Verkehr? Diese Frage hat auch regulatorische Implikationen – etwa Compliance mit Vorschriften, die bei automatisierten Handelssystemen robuste **Kill-Switches und Limit-Regeln** verlangen (MiFID II in EU fordert z.B. Risiko-Limits und menschliche Aufsicht bei algorithmischem Trading, was hier durch den Risk-Manager prinzipiell 1
umgesetzt wird ).

Neben diesen Hauptfragen werden weitere Aspekte betrachtet, etwa **Organisatorisches** (wie fügt sich das in den Entwicklungsprozess ein? Braucht das Team neue Skills für ML-Modelle? Wie testet man das sicher?) sowie **Kosten/Nutzen** (lohnt sich der Mehraufwand an Komplexität gegenüber dem erwarteten Performancegewinn?).

**4\. Forschungsstränge und Fokusbereiche**

Um die obigen Fragen zu beantworten, wird das Untersuchungsfeld in mehrere **Forschungsstränge** bzw. *Workstreams* aufgeteilt. Jeder Strang beleuchtet einen kritischen Teilaspekt der ML-Advisor Integration:

**4.1 ML-Methodik: Tabellarisch vs. Zeitreihenmodellierung**

Es werden zwei grundlegende ML-Ansätze verglichen: **Tabellarische Prädiktionsmodelle** (z.B. Entscheidungsbaum-Ensembles wie XGBoost) und **Sequenzmodelle** für Zeitreihen (z.B. LSTM, TCN, Transformer). Hier geht es um die Eignung der Modelle für Finanzzeitreihen und Echtzeit-Inferenz: \- **XGBoost/GBTs:** Nutzen einzelne Kerzen/aggregierte Features als Input (Feature-Vector pro Zeitschritt). Erwartung: Schnelle Inferenz (\< 10ms), einfacher zu erklären (Feature Importances, SHAP) und weniger Datenhungrig. Allerdings benötigen sie manuelles Feature Engineering, um zeitliche Muster abzubilden. \- **LSTM (Long Short-Term Memory):** Kann sequentielle Muster (z.B. Trendwechsel) automatisch erlernen. Erwartung: Liefert potenziell höhere Prognosegüte für zeitabhängige Muster, jedoch evtl. langsamere Inferenz und schwieriger zu interpretieren. Benötigt hyperparameter tuning und ausreichend Trainingsdaten, um nicht zu überfitten. \- **TCN (Temporal CNN):** Konvolutionales Netz für Zeitreihen, könnte schneller trainieren als LSTM (parallele Faltung statt sequentielles Recurrent Processing) und stabilere Langzeit-Abhängigkeiten erfassen. Müsste gegen LSTM hinsichtlich Latenz und Prognosegüte evaluiert werden. \- **Transformer-basierter Ansatz (TST):** State-of-the-Art im Zeitreihenbereich, sehr flexibel (Self-Attention erfasst weit zurückliegende Patterns). Allerdings rechenintensiv und in kleinen Datensätzen oft nicht überlegen. Könnte als experimenteller Kandidat betrachtet werden, jedoch fraglich, ob er für Realtime (1m-Intervalle, begrenzte Datenfenster) praktikabel ist.

3
**Ziel dieses Strangs**: Für die kurzen Zeiteinheiten (z.B. 1-Minuten-Candles) und begrenzten Feature Sätze herausfinden, welcher Modelltyp **praktisch am besten performt**. Kriterien sind u.a. *Prognosequalität* (z.B. Vorhersagegenauigkeit der nächsten Preisrichtung), *Effizienz* (Inferenz- und Trainingsdauer), *Stabilität* und *Erklärbarkeit*. Eventuell wird eine **Tabelle** erstellt, die die Modelleigenschaften gegenüberstellt (siehe Tabelle 1 unten).

*Tabelle 1: Vorläufiger Modellvergleich* (Beispiel)

| Modell Stärken und  Eigenschaften Schwächen/Risiken Echtzeit EignungErklärbarkeit |
| ----- |
| \+ Sehr schnelle  Inferenz; \+ Gut für  \- Könnte plötzliche  tabellarische  Trendwechsel  Features; \+ Liefert  schlechter  **Hoch** (Tree SHAP  **XGBoost**  Feature Importance  erkennen (ohne  **Hoch** (ms  ermöglicht  (Baum  (SHAP) .\<br\>-  9 Features dafür); \-  Bereich)  genaue  Ensemble)  Benötigt manuelles  Potenziell  Beitragswerte)  Feature Engineering  überschätzt lineare  für Zeitbezug; \-  Zusammenhänge.  Nicht sequenziell  lernend.  |
| \+ Erfasst  Zeitabhängigkeiten  automatisch; \+  \- Latenz höher  Kann sequentielle  (Sequenzielles  Muster (Trends,  Propagieren); \-  **Mittel  Mittel** (nur XAI,  Muster)  Erklärbarkeit  (Optimierbar,  keine direkte  **LSTM** (RNN)  lernen.\<br\>-  mittels z.B.  kleines Netz  Feature  Benötigt viele  Integrated  nötig)  Wichtung) Trainingsdaten; \-  Gradients nötig  Gefahr des  (aufwändig).  Overfittings; \-  Erklärung komplex  (nicht intuitiv).  |
| \+ Parallelisierbare  Verarbeitung  ganzer Zeitfenster;  \+ Gut in  \- Eher  praxisnahen  experimentell; \-  **Mittel**  Zeitreihen  **Mittel** (Batch  **TCN** (Temp.  Erklärbarkeit  (komplizierte  Aufgaben; \+ Evtl.  Inferenz  CNN)  ähnlich schwierig  Interpretation  stabiler im Training  möglich)  (Filtervisualisierung  der Filter) als LSTM.\<br\>-  nötig).  Architekturauswahl  komplex; \- Braucht  ebenfalls große  Datenmengen.  |

4

| Modell Stärken und  Eigenschaften Schwächen/Risiken Echtzeit EignungErklärbarkeit |
| ----- |
| \+ Sehr  leistungsfähig bei  langen Sequenzen;  \+ Kann vielfältige  \- Hoher  Muster entdecken  Ressourcenbedarf  **Eingeschränkt  Niedrig** (selbst  (Attention  (GPU empfohlen); \-  **Transformer**  (für kurze  für Experten  Mechanismus).\<br\>-  Latenz potenziell  (TST)  Intervalle evtl.  schwer  Sehr  hoch  Overkill)  nachzuvollziehen) rechenaufwändig; \-  (mehrschichtige  Benötigt  Berechnung).  gigantische Daten,  sonst Overfitting; \-  Black-box Charakter.  |

*Anmerkung:* Diese Tabelle dient der Orientierung für die Modellauswahl. Konkrete Messungen (Inference-Zeiten, Prognosegüte) werden im Experiment ermittelt. Entscheidend ist, **ob ein simpler Ansatz (z.B. XGBoost) bereits ausreicht**, um Mehrwert zu erzielen, oder ob komplexere Sequenzmodelle signifikant besser sind.

**4.2 Feature Engineering & Signalqualität**

Ein wesentlicher Erfolgsfaktor sind die **Input-Features** für das ML-Modul. In diesem Strang wird untersucht: *Welche Metriken und Datenquellen liefern die höchste Signalqualität?* Geplant ist, zunächst einen **minimierten Featuresatz** zu definieren, um Overfitting zu vermeiden – z.B. **5 Kern-Features**: \- Klassische technische Indikatoren wie **Momentum (%) über n Minuten**, **Volatilität** (z.B. ATR oder StdDev), **Volumen-Spike**, **Orderbuch-Imbalance**, etc., die auch in der aktuellen Strategie benutzt werden. \- Evtl. neuere Features: **Trendstärke** (z.B. ADX), **Relative Stärke** (RSI), **Buy/Sell-Volume Delta**,  **Liquidität/Microstructure** (Spread, Orderbuch-Gradient). \- Zeitliche Merkmale: z.B. **Stunde des Tages**, um Tageszeiten-Effekte zu berücksichtigen, falls relevant.

Geplant ist ein kurzer **Explorations-Workshop** zum Feature Engineering, auch gestützt auf die Analyse bestehender Open-Source-Bots: Open-Source-Systeme wie *Freqtrade/FreqAI* bieten Tools zur schnellen 10 11
Generierung vieler Features (teils \> 10k, allerdings oft mit PCA-Reduktion) . Davon soll im kleinen Umfang gelernt werden: Wir priorisieren Features, die **intuitiv und erklärbar** sind, statt blind eine riesige Feature-Matrix zu erstellen. Qualität geht vor Quantität – jedes Feature muss potenziell interpretierbar sein, um später im SHAP-Plot oder ähnlichem genutzt zu werden.

Ziel ist es, die **wichtigsten Einflussgrößen** für Handelsentscheidungen zu identifizieren, damit das ML Modell auf ähnlicher Informationsbasis agiert wie die menschlichen Entwickler/Regeln (Stichwort: *Expert Knowledge einbringen*, um Black-Box-Verhalten zu reduzieren). In der Evaluation wird gemessen, welche Features tatsächlich Beiträge zur Modellgenauigkeit liefern (z.B. via Feature Importance oder Ablation

Studien). Unwichtige oder korrelierte Merkmale werden aussortiert, u.U. kommt **Dimensionsreduktion** 11
**(PCA)** zum Einsatz, falls es die Performance steigert .

**4.3 Explainability (Modellerklärbarkeit)**

Da **Nachvollziehbarkeit** eine zwingende Voraussetzung ist, widmet sich dieser Strang den Methoden, mit denen das ML-Modul erklärbar gemacht wird: \- **SHAP (Shapley Additive Explanations):** Zum

5
Berechnen des Beitrags jedes Features zu einer bestimmten Modellentscheidung. Insb. für Baum Modelle sehr effizient (TreeSHAP). Wir planen, für **jedes ML-Signal** die Top-Feature-Beiträge per SHAP zu loggen, um im Nachhinein begründen zu können, *warum* das Modell z.B. einen Kauf empfahl (z.B. "Signal, weil 15min-Momentum \+3%, Volumenanstieg \+50%" o.ä.). \- **LIME:** Als lokal lineares Erklärmodell könnte LIME eingesetzt werden, um einzelne Vorhersagen durch einfache approximative Modelle darzustellen. Praktisch wird LIME evtl. weniger genutzt, da SHAP umfassender ist, aber es bleibt als Option. \- **Integrated Gradients:** Falls ein Deep Learning Modell (LSTM/TCN) zum Einsatz kommt, können wir Integrated Gradients berechnen, um Feature-/Zeitpunktbeiträge zu quantifizieren. Dies ist rechenintensiver, würde aber stichprobenartig gemacht (z.B. bei auffälligen Trades in der Analyse). \- **Modell-Reports:** Zusätzlich zu per-Signal Erklärungen überlegen wir, aggregierte **Modellberichte** zu erstellen: z.B. durchschnittliche Feature-Importance über alle Trades, oder Partial Dependence Plots, um globale Zusammenhänge zu zeigen ("Steigt *Signalconfidence* stark, wenn Momentum \> X% und Volumen \> Y" etc.). Diese dienen der Validierung, ob das Modell plausible Muster lernt oder irgendwelchen Rauschen folgt.

Explainability fließt auch in das **Datenmodell**: Der ML-Advisor soll idealerweise im **reason \-Feld** des

Signals (siehe Eventschema) eine Erklärung mitliefern. Bei regelbasierten Signalen wird dort z.B. ein Text eingetragen ("Momentum-Kaufsignal, Preis \+5%/15min, hohes Volumen" ). Für ML-Signale
12

könnten wir analog einen erklärenden Satz generieren, basierend auf den wichtigsten Faktoren. Kurzfristig kann es auch ein generischer Text sein ("ML-Modell Signal mit 78% Konfidenz aufgrund historischer Muster"), aber perspektivisch sollten hier greifbare Gründe stehen.

Wichtig: Explainability ist nicht nur ein *nice-to-have*, sondern **essenziell für die Akzeptanz**. Intern (für Entwickler, Auditoren) soll jeder Trade nachvollziehbar bleiben, und extern (falls erforderlich für Compliance) muss dokumentiert sein, dass kein unkontrolliertes KI-System "wild" handelt. Daher wird ein Kriterium der Studie sein: **Bewerten, ob die eingesetzten Erklärmethoden ausreichend Info liefern**. Beispiel: Wenn SHAP anzeigt, dass ein Kauf zu 80% vom Feature "Volume spike" getrieben war, passt das zu intuitiven Erwartungen? Oder identifiziert das Modell scheinbar zufällige Faktoren? Dieser Abgleich fließt in die Entscheidungsfindung (Go/No-Go).

**4.4 Risk Governance & Safety Layer**

Dieser Strang adressiert die **Risiko-Governance**: Welche zusätzlichen Regeln und Protokolle müssen eingeführt werden, damit das ML-Modul *nur innerhalb sicherer Grenzen* agiert. Prinzip: **ML-gated, aber rule-bounded** – d.h. das ML darf Vorschläge machen, aber **strenge Regeln begrenzen** deren Einfluss: \- **Integration in Risk-Manager:** Der Risikomanager wird so erweitert, dass er neben klassischen
signal \-Events auch ml\_signal \-Events verarbeiten kann. Standardmäßig gelten *alle bisherigen Limitregeln* (Positionsgröße, Exposition, Drawdown, Stop-Loss, Circuit Breaker) identisch für ML-Signale
13 14
. Ein ML-Signal, das z.B. eine riesige Position vorschlägt, würde vom Risk-Layer automatisch auf 15 16
erlaubte Größe getrimmt oder komplett abgelehnt . Damit ist die **grundlegende Abschirmung** bereits gegeben. \- **Confidence Gating:** Zusätzlich kann definiert werden, dass **nur ML-Signale oberhalb einer bestimmten Konfidenzschwelle** zum Risk-Manager durchgestellt werden (bzw. von diesem akzeptiert werden). Z.B. könnte man verlangen, dass confidence \>= 0.7 sein muss, damit überhaupt eine Order erwogen wird. Niedriger konfidente ML-Hinweise würden ignoriert oder nur als Info im Dashboard erscheinen. Diese Schwelle kann anhand von Backtest-Ergebnissen kalibriert werden (Trade-off zwischen Trefferquote und Anzahl Signale). \- **Outlier Detection & Sanity-Checks:** Inspiriert von FreqAI's *Outlier Removal* Ansatz könnte vor jeder Modell-Inferenz ein Check laufen, ob die
17

Inputdaten innerhalb normaler Range liegen (z.B. keine unmöglichen Ausreißerwerte). Weiterhin könnten die Modelloutputs plausibilisiert werden: Ein Beispiel-Maßnahme wäre, Konfidenzen \> 0.99 hart auf 0.99 zu deckeln, da extreme Überkonfidenz oft Fehlkalibrierung ist. \- **Fallback und Parallel Run:** In der Übergangsphase wird das ML-Modul **nicht allein gelassen**: Entweder läuft es zunächst im

6
**Shadow Mode** (siehe unten) ohne Ausführungswirkung, oder falls es aktiv Trades vorschlägt, könnte es *parallel zur alten Strategie* laufen. Eine denkbare Governance-Policy: Ein Trade wird nur ausgeführt, **wenn sowohl Regel-Signal als auch ML-Signal übereinstimmend** ein "Kauf" anzeigen (Kombination aus beidem für extra Sicherheit). Oder umgekehrt: Der ML-Advisor kann einen Trade *blockieren*, den die Regel-Engine generiert, falls er extreme Bedenken hat – aber nicht eigenständig ausführen. Solche *Vier Augen-Prinzip*\-Ansätze (Regel \+ ML) könnten in einem **Conditional Go** Szenario relevant sein, sofern sie signifikant Nutzen bringen. \- **Überwachung & Logging:** Alle ML-Entscheidungen werden detailliert geloggt: Eingabefeatures, Modellversion, Output (Signal, Konfidenz) und dann die Entscheidung des Risikomanagers (ausgeführt/abgelehnt \+ Grund). Damit entsteht ein Audit-Trail, der später ausgewertet werden kann, um evtl. Fehlverhalten zu erkennen. Zudem sollten **Warnungen/Alerts** definiert werden: z.B. wenn das ML-Modell mehrfach in kurzer Zeit Signale liefert, die vom Risikomanager immer abgelehnt werden (weil riskant), könnte ein Alert *ML-Modul außer Rand und Band?* ausgelöst werden, was menschliches Eingreifen veranlasst.

Im Rahmen der Studie wird eine **Risiko-Matrix** erstellt, die mögliche Fehlerszenarien und Gegenmaßnahmen gegenüberstellt (siehe Tabelle 2). Damit stellen wir sicher, dass für jedes identifizierte ML-Risiko eine Governance-Lösung diskutiert und bewertet wurde.

*Tabelle 2: Mögliche Risiken durch ML-Modul und vorgesehene Gegenmaßnahmen (Auszug)*

| Risiko/Problem (ML) Geplante Gegenmaßnahme / Governance-Ansatz |
| ----- |
| *Risk-Manager-Filter:* Jeder ML-Trade muss durch Risk-Filter. Fehlsignale  **Falsch positive Signale**  werden dort abgefangen (Positionslimit, Expositionslimit etc.).  (ML empfiehlt Trade, der  Zudem Backtesting-Validierung, um ML-Schwellen zu justieren, und  schlecht ist)  ggf. **Confirmation durch Regel-Engine** (Trade nur, wenn beides  positiv). |
| *Confidence Gating:* Signale nur ausführen, wenn Konfidenz innerhalb  **Probabilistischer**  plausibler Range. Extrem abweichende Confidences werden ignoriert  **Ausreißer** (unplausibles  oder capped. Zusätzlich **Outlier Detection** auf Input-Daten (ähnlich  Signal mit extremer  FreqAI-Ansatz) entfernt untypische Datenpunkte vor der Prognose  Confidence)  .  17 |
| *Shadow Tests & Retraining:* Regelmäßiges Retraining mit aktuellen  **Modell-Drift /**  Daten; kontinuierliche Evaluation der Vorhersagegüte. Bei starker  **Performanceabfall** (über  Verschlechterung wird Modell deaktiviert (Fallback auf Regel-Only)  Zeit wird Modell ungenau)  bis Update erfolgt. Monitoring-Komponente misst z.B. *Anteil korrekter  Richtungsprognosen* im letzten Monat. |
| *XAI-Einsatz:* Pflicht, zu jedem ML-Signal die Top-Gründe per SHAP zu  **Black-Box Intransparenz**  loggen. Audit-Logs speichern Modellinput und \-output. Zusätzlich  (Entscheidungen nicht  quartalsweise ML-Modell-Dokumentation (Feature Importances  nachvollziehbar)  global, Beispiel-Erklärungen) für interne Prüfung. Damit ist im Audit  Fall belegbar, warum ein Trade zustande kam. |
| *Strenges Validierungsverfahren:* Daten in Train/Val/Test splitten, Cross  **Overfitting** (Modell passt  Validation für robustere Parameter. Begrenzte Modellkomplexität  auf historische Daten,  (Depth, Neuronen) um Overfitting zu reduzieren. Evtl. Feature  versagt live)  Selektion oder PCA zur Komplexitätsreduktion . Und: erst Shadow  11 Mode, dann schrittweise live – kein "Big Bang".  |

7

| Risiko/Problem (ML) Geplante Gegenmaßnahme / Governance-Ansatz |
| ----- |
| *Architekturoptimierung:* ML-Service läuft **asynchron** neben Strategy  Service. Inferenz \< z.B. 50ms anstreben (Modellkomplexität  **System-Latenz /**  begrenzen). Gegebenenfalls Threads/Async nutzen (vgl. FreqAI  **Performance** (ML  Threading für Training vs. Inference ). Falls nötig, Einsatz von  18 verzögert Reaktionszeit)  schneller Hardware (z.B. GPU oder TPU) – aber nur, wenn wirklich  erforderlich für Meeting der Latenzanforderungen.  |

Die obigen Maßnahmen werden im Verlauf der Studie konzipiert, prototypisch umgesetzt (z.B. Schwellen im Risk-Modul konfiguriert) und in Tests geprüft (z.B. absichtlich einen Ausreißer-Input schicken und verifizieren, dass das System ihn ignoriert). Ziel ist, nachzuweisen, dass **das vorhandene Risk-Management auch mit ML-Schicht robust bleibt** und im Zweifel stets "konservativ 4
entscheidet" .

**4.5 Backtesting & Shadow-Mode Tests**

Bevor irgendein ML-gestützter Trade live geht, müssen umfangreiche **Backtests und Shadow-Mode Runs** die Auswirkungen prüfen. Dieser Strang definiert das Testvorgehen: \- **Historische Backtests:** Aufbauend auf vorhandenen Marktdaten (z.B. BTC/ETH Preis-/Orderbuch-Daten der letzten X Monate) werden **Offline-Simulationen** gefahren. Wir simulieren die Strategie "Regel-basiert vs. ML-basiert vs. Kombination" auf identischen Daten und vergleichen Kennzahlen: Gewinn/Verlust, Sharpe Ratio, Drawdown, Trefferquote der Signale, ggf. Kosten etc. Hierdurch sehen wir, ob das ML-Modell *in der Vergangenheit* einen Mehrwert gebracht hätte. Wichtig ist, die Backtests so realistisch wie möglich zu halten (Slippage, Gebühren, Latenz vernachlässigbar da 1m Intervall). Auch **Walk-Forward**\-Tests können zum Einsatz kommen, um Overfitting zu erkennen (Trainiere Modell bis 2024, teste auf 2025- Daten etc.). \- **Shadow Mode (Paper Trading):** Das ML-Modul wird im **Live-Betrieb parallel** geschaltet, jedoch so, dass seine Signale **nicht** zu echten Orders führen, sondern nur geloggt werden. Konkret: Der ML-Advisor-Service abonniert echte market\_data in Echtzeit und publiziert ml\_signals auf einem separaten Kanal. Der Risikomanager könnte diese zwar empfangen, aber wir konfigurieren ihn (für Testphase) so, dass er ml\_signals entweder ignoriert oder als *virtuell* behandelt (d.h. er protokolliert, ob sie **würden** durchgehen, löst aber keine Order aus). Alternativ läuft ein separater Shadow-Risk Manager instanziert, der nur zum Loggen dient. In diesem Shadow-Betrieb über z.B. 2-4 Wochen sammeln wir **Live-Leistungsdaten** des Modells: Wie oft hätte es getradet? Wie wären die Trades ausgegangen (ggf. mark-to-market Berechnung)? Hätte das Risk-Modul sie erlaubt oder geblockt? Diese Ergebnisse sind äußerst wichtig, da sie zeigen, ob der ML-Advisor in unterschiedlichen Marktphasen (ruhig vs. volatil) stabil funktioniert. \- **Benchmarking gegen Baseline:** Alle Testergebnisse werden gegen die aktuelle deterministische Strategie verglichen (Baseline \= Regel-Engine allein). So können wir quantifizieren: *Steigert ML die Performance?* Z.B. sieht man vielleicht eine höhere Trefferquote, aber evtl. auch mehr Trades (Kostenfrage) oder höhere Maximalverluste (Risiko). Ebenso prüfen wir Mischformen, z.B. "nutze ML nur zur Bestätigung" – verbessert das die Kennzahlen weiter? \- **Spezielle Testszenarien:** Zusätzlich definieren wir Sonderfälle, um die Robustheit zu prüfen. Beispiele: Plötzlicher Marktabsturz – wie reagiert das ML-Modell vs. der Risikomanager (hier sollte der Risk-Circuit-Breaker wie gehabt 19 20
greifen ). Oder: Datenlücke/Feed-Ausfall – stellt das ML-Modul Blödsinn an? (Es sollte im Zweifel nichts tun). Auch Performance unter Stress (z.B. sehr volatile Phase mit vielen Signalen in kurzer Zeit) wird beobachtet.

Das Ergebnis dieses Strangs ist ein umfassender **Testreport** mit Metriken, Grafiken (Equity-Kurven, Konfusionsmatrix der Signale vs. echte Marktbewegungen, etc.) und Erkenntnissen, welche Stärken und Schwächen der ML-Advisor hat. Insbesondere wird daraus hervorgehen, ob die Hypothese quantitativ

8
gestützt wird (z.B. **höherer Gesamtprofit bei vergleichbarem Risiko** mit ML) oder nicht. Diese Test Ergebnisse sind das Herzstück für die Entscheidungsvorlage.

**4.6 Mensch-KI-Schnittstelle (Advisory UI)**

Last but not least beleuchtet ein Strang die **Benutzerinteraktion und Visualisierung** des ML-Advisors. Auch wenn Claire de Binaire primär autonom handelt, ist eine transparente Darstellung für die Betreiber wichtig: \- **Dashboard-Integration:** Das bestehende Dashboard/UI (z.Z. geplant via Streamlit) soll erweitert werden, um ML-Informationen anzuzeigen. Beispielsweise könnten ML-Signale als separate Layer auf Chart-Plots erscheinen (ähnlich wie TradingView-Indicator-Signale). Oder ein Panel listet die letzten ML-Empfehlungen mit Konfidenz und ob sie ausgeführt wurden oder nicht. \- **Erklärungsanzeige:** Für den Nutzer (Trader/Ops-Team) sollte ersichtlich sein, *warum* der ML-Advisor etwas empfiehlt. Denkbar ist ein **Tooltip oder Popup**, wenn man auf ein ML-Signal klickt, der die SHAP Topgründe aufzählt ("Kaufsignal, Hauptgründe: Momentum hoch, Volumenanstieg, RSI überkauft"). Dies erhöht das Vertrauen und ermöglicht menschliche Plausibilitätschecks. \- **Benachrichtigung und Override:** Sollte der ML-Advisor in Zukunft aktiv Trades ausführen dürfen, stellt sich die Frage nach **Benachrichtigungen** und manuellen Overrides. Evtl. möchte man bei ML-basierten Trades ein Flag setzen "AI" und der Nutzer bekommt eine Push-Nachricht "*AI Trade executed*". Im frühen Modus (Shadow/Advisory) könnte man ML-Empfehlungen als **Empfehlung an einen menschlichen Händler** präsentieren, der dann entscheiden kann, ob er manuell eingreift. Z.B. "*ML empfiehlt Verkauf BTC\_USDT, 70% confidence*" – und der Mensch klickt ggf. "Execute" oder verwirft. Das wäre ein halbautomatisches *Advisor-Mode*, falls völlige Autonomie (noch) nicht gewünscht ist. \- **Nutzerakzeptanz:** In diesem Strang werden auch die *weichen Faktoren* betrachtet: Wie erklären wir den Stakeholdern (Team, ggf. Aufsicht), was das ML-Modul tut? Hier fließt Explainability natürlich ein. Geplant ist ein **Workshop/Review Meeting**, in dem die Visualisierungen und Erklärungen getestet werden – etwa ob die Darstellung der SHAP-Werte verständlich ist oder ob weitere Dokumentation nötig ist.

Der Outcome dieses Strangs ist ein Konzept, **wie die ML-unterstützten Signale im System präsentiert und kontrolliert werden**. Für das endgültige Go/No-Go spielt die *Usability* und *Transparenz* ebenfalls eine Rolle: Ein hochprofitabler ML-Bot wäre wenig wert, wenn niemand versteht, was er tut und deshalb aus Sorge deaktiviert bleibt. Durch eine gute Schnittstelle soll daher die Zusammenarbeit Mensch–KI gefördert werden (Stichwort *Augmented Intelligence* statt reine Autonomie).

**5\. Methodik und Vorgehensplan**

Um die oben genannten Fragen und Stränge zu bearbeiten, schlagen wir folgendes gestuftes **Forschungsdesign** vor:

**5.1 Analyse bestehender Lösungen (Research Review)**

Zuerst erfolgt eine **Literatur- und Tool-Analyse**: Wir schauen uns erfolgreiche Open-Source-Projekte an, die ML im Trading einsetzen, um Best Practices abzuleiten: \- **Freqtrade (FreqAI)** – Das Freqtrade 21
Framework hat mit *FreqAI* ein ML-Modul eingeführt, das adaptive Modelle ermöglicht . Wir werden deren Doku studieren, insbesondere wie sie **Datenpipeline**, **Retraining-Strategie** und **Integration ins Tradingsystem** gelöst haben. Wichtige Punkte sind z.B. die Verwendung von *selbstadaptierendem* 10 17
*Training*, Outlier Removal und die Trennung von Strategie/Modell . Auch Freqtrade’s Umgang mit **Hyperparameter-Optimierung** (Hyperopt) und *Thresholding der Modell-Signale* liefert Inspiration
8

für unser Design. \- **OctoBot** – Dieser Bot ist als “AI-ready” bekannt, d.h. durch ein Plugin-System lassen 22
sich TensorFlow/Scikit-learn Modelle integrieren . Wir schauen, wie OctoBot ML und Regel-Strategien kombiniert und welche *AI-Signale* dort existieren (z.B. gibt es Berichte über ChatGPT-Integration für Sentiment). Von Interesse ist die **Architektur**: Hat OctoBot ein separates ML-Modul oder ist KI direkt

9
Teil der Strategiekomponente? Und wie adressieren sie Risiko (hierzu evtl. Community-Erfahrungen recherchieren)? \- **Numerai/Open AI Trading** – Numerai stellt ein Meta-ML-Ansatz dar (Ensemble aus vielen Modelleinsendungen). Zwar nicht 1:1 vergleichbar, aber wir schauen uns an, welche **Feature Kodierungen** dort genutzt werden (Stichwort Metadaten, Erklärbarkeit) und wie die *meta model combination* funktioniert. Auch andere Projekte, wo ML-Signale geteilt werden, können Ideen geben, wie man ML als “Signal Provider” gestaltet. \- **Akademische Quellen** – Parallel sichten wir neuere *Research Papers oder Blogs* zur Anwendung von XAI und ML im Trading. Z.B. Ansätze zu **Erklärbarer KI** 23
**in Finance** oder **Reinforcement Learning mit Risk Controls**. Auch regulatorische Whitepaper (z.B. von CFA Institute über Explainable AI in Finance) könnten herangezogen werden, um sicherzustellen, dass wir regulatorisch konform denken.

**Deliverable dieses Schritts:** Ein internes Memo oder Tabelle mit *Lessons Learned* aus externen Systemen – etwa: *"Freqtrade FreqAI: trennt ML als optionales Modul, nutzt Retraining \+ Outlier-Filter ,*
*17*

*8*
*Integration via threshold triggers ; OctoBot: Plugin-Architektur, ermöglicht schnelles Einbinden beliebiger 22*
*ML-Bibliotheken ; etc."* Diese Erkenntnisse fließen in unseren Architektur- und Methodikplan ein.

**5.2 Prototypische ML-Pipeline (Experimente)**

Auf Basis der Recherche wird eine **kleine ML-Pipeline prototypisch gebaut**. Dies geschieht in der Entwicklungsumgebung (nicht auf dem Live-System) und umfasst: \- **Datenbeschaffung:** Nutzung historischer Marktdaten für BTC\_USDT und ETH\_USDT (die primären Assets im System) – idealerweise aus unserer Persistenz oder via API. Datenfrequenz: 1m Kerzen über z.B. 6-12 Monate, inkl. Indikatoren falls bereits berechnet, oder wir berechnen sie nach. \- **Feature-Aufbereitung:** Berechnung der 5-10 Features pro Zeitstempel, wie im Feature-Strang definiert. Implementierung in einem Notebook oder Skript, Wiederverwendung von vorhandener Indikator-Berechnungslogik der Strategie-Engine wo möglich, um Konsistenz zu wahren. \- **Modellauswahl und \-training:** Wir implementieren zwei Modellvarianten: (a) **XGBoost (Tree Booster)** und (b) **LSTM (Deep Learning)** als Ausgangspunkt. Diese Modelle werden auf einem Trainingsdatensatz trainiert, die Zielvariable könnte z.B. *zukünftige 1h Preisänderung* (Binary: Up/Down oder Regression % change) sein, oder ein direktes Label ob in nächster Zeit ein profitable Trade möglich gewesen wäre. Hier müssen wir definieren, was genau prognostiziert wird – wahrscheinlich ein **Signal/Trade-Entscheidungs-Label** (z.B. "Kauf, wenn der Preis in nächsten N Minuten um \>X% steigt" als positiv). \- XGBoost-Modell: Wir nutzen evtl. xgboost Python-Bibliothek, trainieren auf tabellarischen Features. \- LSTM-Modell: Wir bauen mit TensorFlow/Keras ein kleines

LSTM-Netz, das eine Sequenz vergangener timesteps (z.B. letzte 60 min) als Input nimmt und eine Binärentscheidung oder Wahrscheinlichkeitsausgabe macht. \- **Validierung:** Erste Performance Evaluation auf Testdatensatz (Precision, Recall der Signals etc., evtl. ROC AUC falls probabilistisch). Gegebenenfalls Hyperparameter-Tuning im kleinen Rahmen (Gridsearch auf Baumtiefe, Lernrate oder LSTM-Units, etc.), aber begrenzt, um Overfitting des Prozess zu vermeiden. \- **Integration in Event Kette (Trockenlauf):** Anschließend wird der Prototyp insofern erweitert, dass er **Events verarbeiten kann**. Wir implementieren einen rudimentären **ml\_signal\_service** , der genau wie die Strategie

Engine MarketData-Events subscribt und bei jedem neuen Timestep einen **ML-Signal-Event** publiziert. Dieser Service läuft vorerst isoliert (z.B. in Jupyter Notebook mit Streaming-Simulation oder als separater Thread im Dev-Environment). Wir testen die Kette: market\_data \-\> ml\_signal\_service  \-\> (generiert) ml\_signals \-\> risk\_manager . In Dev können wir den Risk-Manager so konfigurieren, dass er die ml\_signals aus einer Test-Queue liest und z.B. in eine Logdatei oder Test Datenbank schreibt, ohne echte Orders. Damit prüfen wir **end-to-end**: 1\. Marktdaten simulieren (Replay historischer Daten oder künstlicher Feed), 2\. ML-Service reagiert und erzeugt Signal-Events, 3\. Risk Manager empfängt sie und wendet seine Logik an (wir schauen ins Log: wurden ML-Signale genehmigt oder geblockt nach den aktuellen Regeln?).

10
Dies dient auch als Technik-Test: Latenzen messen (Zeit von MarketData bis Signal-Event), Fehlermeldungen (z.B. was passiert, wenn Modell Input unvollständig?), und Sicherstellen, dass keine Crashs passieren. Zudem sammeln wir hier *Live-Daten* für Erklärbarkeit: z.B. lassen wir SHAP Werte für jedes Signal berechnen und mit ausgeben, um das Logging-/Speichervolumen und Geschwindigkeit abzuschätzen.

**Deliverable dieses Schritts:** Ein funktionsfähiger **Experimentier-Prototyp** des ML-Advisors. Dieser ist noch nicht optimiert oder produktionsreif, aber er erlaubt, alle weiteren Untersuchungen (Backtest, Shadow, etc.) durchzuführen. Außerdem entsteht Dokumentation/Code (z.B. Jupyter Notebook), die dem Anhang des Berichts beigelegt werden kann, um Transparenz des Vorgehens zu gewährleisten.

**5.3 Integrationstest & Shadow Deployment**

Nachdem der Prototyp steht, folgt der **Integrationstest im Staging/Shadow Mode**: \- Wir deployen den ML-Service in einer Staging-Umgebung oder auf dem bestehenden Dev-Setup neben den anderen Services. Der ML-Service erhält Zugang zum *echten MarketData-Feed* (z.B. WebSocket der Exchange, oder Proxy davon) analog zur Strategie-Engine. Er publiziert auf einem separaten Topic (z.B. ml\_signals )

6
. \- Der Risk-Manager wird für Testzwecke so modifiziert, dass er **die ML-Signale zwar empfängt,**
**aber nicht an den Execution-Service weiterleitet**. Dies könnte durch Kennzeichnung type \=  ml\_signal erfolgen – wir passen den Code so an, dass if event.type \== "ml\_signal": handle separat (nur loggen) . Somit fließen ML-Signale ins System, werden vom Risk-Modul geprüft und geloggt, aber im Alert/Order-Bereich entweder blockiert oder als *virtuell* behandelt. \- Alternativ können wir den ML-Service so einstellen, dass er statt direkt orders zu publizieren im Erfolgsfall nur einen *Advisory-Eintrag* generiert. Implementation Detail: Evtl. ein neuer Event-Typ "advice" oder wir mischen es nicht in den Bus, sondern schreiben in eine separate Tabelle ml\_advice mit Timestamp, predicted action, confidence. \- Die *Shadow-Phase* läuft dann unter Live-Bedingungen, aber ohne finanzielles Risiko. Wir sammeln z.B. über 1-2 Wochen die ML-Signale parallel zum normalem Bot-Betrieb. Dabei führen wir Buch über die "was wäre wenn"- Trades des ML: \- Wir können offline berechnen: Hätte der ML-Trade Gewinn gebracht? (Vergleich Entry/ Exit mit Marktpreisen) \- Wurden ML-Signale vom Risk-Manager durchgelassen oder hätte er sie wegen Limits gestoppt? (Falls wir Risk-Prüfung aktiv lassen im Code, aber Execution blockieren, können wir aus den Logs sehen, welche Signale **approved** und welche **rejected** worden wären.) \- Verhalten bei besonderen Marktbedingungen: Triggert ML vielleicht in Situationen, wo Regel-Engine aufgrund Vorsicht gar nichts sendet? (Könnte gut oder schlecht sein – entweder entdeckt ML eine Chance, oder es übersieht Gefahr, z.B. in anormaler Volatilität. So was würde der Risk-Manager ggf. als "abnormal 19 24
market" blockieren , was wir ebenfalls testen wollen.) \- Nach dieser Phase werten wir die Logs und Trades gründlich aus (siehe Strang Backtesting & Shadow, was teilweise hiermit verschränkt ist).

Zusätzlich zum technischen Test ist dies auch der Zeitpunkt, **die Organisation einzubinden**: Präsentation an das Team, was das ML-Modul tut, Demo der Live-Visualisierung, Einholen von Feedback. So können wir früh usability-Probleme erkennen oder Bedenken adressieren.

**Deliverable dieses Schritts:** Ein **Erfahrungsbericht aus der Shadow-Phase**, inkl. identifizierter Probleme (z.B. Latenzspitzen, falsche Signale) und ggf. bereits implementierter Bugfixes oder Tuning. Dies fließt ins Kapitel „Integrationserfahrung“ des Berichts ein. Zudem generiert die Phase **Daten für den Evaluations-Teil**: reale Beispiele von ML-Signalen, Performance-Vergleiche etc.

**5.4 Auswertung & Entscheidungsfindung**

Zum Abschluss der Methodik steht die **Auswertung aller Ergebnisse** in Bezug auf die Forschungsfragen: \- Wir konsolidieren die Erkenntnisse aus Backtests, Shadow Runs und Analysen in

11
einer strukturierten Gegenüberstellung *ML vs. No-ML*. Dazu gehören tabellarische Übersichten (z.B. Performance-Metriken), Grafiken (Equity Curve mit/ohne ML, Verteilung der Returns, Confusion Matrix der Signalvorhersagen etc.) und textuelle Interpretation. \- Pro Forschungsfrage (aus Abschnitt 3\) liefern wir eine **begründete Antwort**. Beispiel: \- *"Wie weit darf ein Advisor gehen?"* – Antwort basiert auf unseren Erfahrungen: Wahrscheinlich schlagen wir vor, **zunächst nur beratend bzw. gemeinsam mit Regeln** (Hybrid-Ansatz) einzusetzen, weil vollständige Autonomie zwar möglich war, aber noch Vertrauensaufbau nötig ist. Oder falls ML extrem gut funktioniert und keine neuen Risiken zeigte, könnte man mutiger sein. \- *"Welche Modelle sind realistisch?"* – Hier berichten wir z.B., dass XGBoost in unseren Tests 90% der Performance von LSTM brachte, aber viel schneller und leichter erklärbar war – daher für Realtime eher XGBoost (oder umgekehrt, falls LSTM klar besser war). Vielleicht empfehlen wir auch, TCN mal später zu testen, aber aktuell nicht zwingend. \- *"Schutz des Risk-Layers?"* – Wir dokumentieren, wie unsere Risk-Manager-Änderungen wirkten. Evtl. zeigen wir einen Fall, wo das ML Modell einen zu großen Trade wollte und risk manager korrekt blockte (Beleg für Sicherheit). Wir formulieren Guidelines wie "*der Risk-Layer bedarf keiner fundamentalen Änderung, außer Threshold-Filter für ML-Signale und erweitertes Monitoring.*" \- **Go / No-Go Entscheidungsvorlage:** Basierend auf allem erstellen wir eine klare Empfehlung. Diese wird im Bericht als **Konklusion** stehen, aber zugleich in einer separaten Management-Vorlage (ein zweiseitiges Memo oder PowerPoint-Folie) zusammengefasst. Darin: \- **Go:** Falls Ergebnisse positiv und Risiken beherrschbar \-\> Empfehlung, ML-Advisor in nächster Phase produktiv (vielleicht unter Beobachtung) zu nehmen. \- **Conditional Go:** Falls teils positiv, aber bestimmte Bedingungen müssen erfüllt sein (z.B. "*Go, sobald zusätzliche 3 Monate Shadow Mode und Modell-Audit gemacht sind*", oder "*Go nur für kleine Positionsgrößen, ansonsten No-Go*"). Hier würden wir Parameter definieren, die vor Launch erfüllt sein müssen. \- **No-Go:** Falls ML keinen Mehrwert lieferte oder zu gefährlich erschien \-\> Empfehlung, vorerst nicht zu integrieren, ggf. in 6-12 Monaten neu evaluieren, wenn Technologie gereift.

Der Bericht endet mit dieser Empfehlung, begründet durch die Fakten aus der Forschung. Zusätzlich werden **Folgeschritte** skizziert, z.B. "*Falls Go: Plan für Implementierung in Production und Monitoring definieren*" oder "*Falls No-Go: Alternative Verbesserungsmaßnahmen (andere Indikatoren ausprobieren, etc.)*".

**Methodik-Zusammenfassung (Zeitplan):** Die einzelnen Schritte werden natürlich in einer sinnvollen Reihenfolge und teils parallel ablaufen. Geschätzt: Recherche (Step 5.1) \~1 Woche, Prototyping (5.2) \~2 Wochen, Shadow Phase \+ Backtesting (5.3) \~2-4 Wochen, Auswertung (5.4) \~1 Woche. Insgesamt ca. 4-6 Wochen Projektlaufzeit, was in den Kontext der Roadmap passt (Phase 4 optional).

**6\. Technische Architektur der ML-Integration**

In diesem Kapitel des Berichts (zukünftig) wird die **geplante Architektur** des ML-Advisor-Systems detailliert, einschließlich eines Diagramms der Komponenten und Datenflüsse im Vergleich *vorher/ nachher*. Hier schon vorab die Kernpunkte der Architektur und Integration:

•
**Separater ML-Service:** Wie in Roadmap vorgesehen, wird der ML-Advisor als **losgelöster** 6
**Microservice** umgesetzt . Dieser Service abonniert das bestehende market\_data Topic (wie die Strategie-Engine) und hat optional Zugriff auf weitere Datenquellen (z.B. eigene State History, evtl. News in Zukunft). Bei Erkennung eines Musters generiert er ein Event, vermutlich vom Typ "ml\_signal" (neuer Event-Typ analog zu signal ) mit ähnlichem Schema:

{ type: "ml\_signal", symbol, timestamp, side, confidence, reason, ... } . 6
Dieses Event wird auf ein Topic ml\_signals publiziert .

•
**Erweiterter Event-Bus-Flow:** Das **Sequenzdiagramm** wird angepasst: Bisher:  market\_data \-\> Strategie \-\> signals \-\> Risk \-\> orders \-\> ... . Neu kommt

12
parallel: market\_data \-\> ML-Service \-\> ml\_signals \-\> Risk . Der Risk-Manager würde somit aus zwei Quellen Signale erhalten. In der *Shadow-Phase* konfigurieren wir ihn so, dass er ML-Signale zwar loggt, aber nicht an orders weitergibt. In einem *Go-Szenario* könnte er beide gleich behandeln oder differenziert (z.B. Priorisierungskonflikte regeln, falls gleichzeitig unterschiedliche Signale kommen).

•
**Datenpersistenz:** Die bestehende Datenbank hat bereits eine signals Tabelle für 25
aufgezeichnete Handelssignale . Wir würden entscheiden, ob ML-Signale in eine separate Tabelle ml\_signals geschrieben werden (um sie getrennt auszuwerten) oder mit Flag in derselben Tabelle. Wahrscheinlich getrennt, da Struktur leicht anders (zusätzliche Felder wie Modell-ID, Features?). Ein **Datenmodell-Vorschlag** wird erarbeitet, der in den Deliverables enthalten ist. Dieser definiert z.B. ein JSON-Schema für ml\_signal Events analog zu SignalEvent, mit Ergänzungen:

•
z.B. "type": "ml\_signal" , "model": "LSTM\_v1" , "features": { ... } (optional, evtl. weglassen wegen Größe, lieber nur Top reasons in Text), "confidence": float ,  "side": "BUY/SELL" , "reason": "Top3 Features: Vol+10%, Mom+5%, RSI70" .

•
**Modularität & Schnittstellen:** Der ML-Service wird so entwickelt, dass er austauschbar ist (man

kann verschieden Modelle einhängen). Er kommuniziert nur über den Message-Bus – keine direkten Aufrufe ins Core-System, was Loose Coupling wahrt. Diese Entkopplung erlaubt es auch, den ML-Advisor bei Bedarf auszuschalten oder neuzustarten, ohne dass das Hauptsystem gestört wird (Fehlerisolation).

•
**Ressourcen und Performance:** Architektonisch wird darauf geachtet, dass der ML-Service

ausreichend Ressourcen bekommt (eigenes Docker-Container mit evtl. mehr RAM/CPU, optional GPU-Passthrough falls genutzt). Durch asynchrone Kommunikation hat eine langsamere ML Berechnung nicht direkten Einfluss auf den Risk-Manager – schlimmstenfalls käme das Signal zu spät und würde dann ggf. nicht mehr relevant sein. Dieses Timing-Problem wird im Test evaluiert; bei kurzen Intervallen ist aber Pünktlichkeit wichtig. Falls nötig, könnten wir Mechanismen einbauen wie "*Signal wird nur berücksichtigt, wenn es \< X Sekunden nach Candle Close ankommt*".

•
**Fehlerhandling:** Sollte der ML-Service einen Fehler haben (Crash, Exception), darf das nicht das

Trading stoppen. Hier greift das Microservice-Prinzip: der Service kann neu gestartet werden, und bis dahin laufen die normalen Signale weiter. Logs/Monitoring werden eingerichtet (z.B. 26
Health-Check Endpoint /health analog den anderen Services ), sodass der Ausfall bemerkt wird. Zudem könnte der Risk-Manager bei Abwesenheit des ML-Signals normal weiterarbeiten – im schlimmsten Fall fehlt dann nur die ML-Hilfe, aber es entstehen keine inkonsistenten Halbsituationen.

•
**Versionierung:** Jedes ML-Modell-Deployment wird versioniert (z.B. Modellname mit Versionsnummer). Die Version fließt in Logs und ggf. in Events ein. So ist nachvollziehbar, mit welcher Modellversion ein bestimmter Trade empfohlen wurde – wichtig für spätere Analysen oder falls plötzlich Performance einbricht (dann sieht man "aha, seit Version 1.3 schlechter" etc.). Ein **Modell-Wechselprozess** wird definiert: z.B. neues Modell erst in Shadow Mode testen, dann switchen.

•
**Sicherheit:** Obwohl der ML-Service nichts Kritisches wie API-Keys hält, achten wir auf Security – z.B. gleiche Authentifizierungsmechanismen im Message-Bus nutzen (damit kein Fremdservice sich als ML-Service ausgeben kann). Auch darf der ML-Service keine Trades direkt ausführen, nur über den Risk-Manager gehen – so bleibt eine Schicht der Kontrolle immer dazwischen (kein "direkter Draht" ML-\>Broker, um Fat-Finger-ähnliche KI-Fehler zu vermeiden).

Im Bericht wird dies durch Diagramme veranschaulicht. Insbesondere ein **Architekturdiagramm** (Komponenten und Topics) und ein **Sequenzdiagramm** der erweiterten Event-Flow im Normalfall und im Ausnahmefall (z.B. Risk-Block). Möglicherweise greifen wir auf die vorhandene PlantUML-Skizze zurück und erweitern sie um den ML-Service Kasten und Linien.

13
Durch diese Architektur bleibt Claire de Binaire trotz neuer Intelligenz **deterministisch kontrollierbar**: Der Risk-Manager bildet weiterhin das "Herzstück" der Entscheidungsfindung und fungiert als Gatekeeper, während der ML-Service als *advisory* Komponente fungiert, die potentielle Chancen (oder Warnungen) liefert.

**7\. Evaluationsdesign (Bewertungsrahmen)**

Um die Entscheidungsgrundlage fundiert zu gestalten, legen wir einen **Bewertungsrahmen** mit Kriterien fest. Diese leiten sich aus den Zielen ab (Leistungsverbesserung **und** Sicherheit/Erklärbarkeit). Im Einzelnen fließen in die Bewertung ein:

•
**Handels-Performance-Kennzahlen:** •
*Profitabilität:* z.B. **Netto-Profit** oder **ROI** über Testperiode, **Sharpe Ratio**, **Profit-Faktor** (Gewinn/ Verlust-Verhältnis). Hier vergleichen wir Regel-Only vs. ML-gestützt. Eine Verbesserung um X% wäre ein starkes Pro-Argument, während eine Verschlechterung ein klares No-Go wäre, außer es gibt andere Vorteile.

•
*Trefferquote und Risk-Reward:* Wie hoch ist die **Hit-Rate** der Signale (Prozentsatz profitabler

Trades) und das **Durchschnitts-Risiko-Ertrags-Verhältnis** pro Trade? Ein ML-Modell könnte z.B. weniger Trades machen, aber dafür Trefferquote steigern – das wäre positiv, da es Qualität vor Quantität setzt.

•
*Drawdown/Risiko:* **Maximaler Drawdown** und Anzahl der Verlusttrades am Stück. Wichtig, dass ML nicht zu neuen schlimmsten Verlusten führt. Im Idealfall senkt ML das Risiko (z.B. weil es einige verlustreiche Trades vermeidet). Gleiches oder leicht höheres Risiko wäre akzeptabel nur wenn Gewinn deutlich besser; stark erhöhtes Risiko wäre kritisch.

•
*Ausführungs-KPIs:* Latenz vom Signal bis Order (sollte sich kaum ändern, ggf. \+ ein paar ms durchs ML). Wenn ML-Signale oft zu spät kämen (z.B. Kurs schon weg), wird das in Erfolgsquote sichtbar sein.

•
**Modell-Leistungskennzahlen:** Neben Trading-Outcome betrachten wir die ML-Modelle als Prädiktor:

•
*Vorhersagegüte:* Metriken wie **Accuracy**, **Precision/Recall**, **ROC AUC** (falls klassifikatorisch) auf

Testdaten. Diese zeigen, ob das Modell an sich Informationsgehalt hat. Allerdings zählen letztlich die Trading-Metriken mehr, da wir inklusive Money-Management betrachten. •
*Stabilität:* Hat das Modell gleichmäßige Performance, oder nur in bestimmten Regimen (Bullenmarkt gut, Crash schlecht)? Evtl. aufgeteilt nach Marktphasen analysieren. •
*Erklärungskonsistenz:* Schauen wir qualitativ drauf: Stimmen die SHAP-Interpretationen mit Expertenwissen überein? Wenn das Modell z.B. konstant "Volumenanstieg" als wichtigsten Grund für Käufe nennt, deckt sich das mit der Strategie-Idee und wäre gut. Wenn es kryptische Gründe (Feature X, das menschlich wenig Sinn ergibt) hoch rankt, müssten wir vorsichtig sein (mögliche Overfitting-Indikatoren).

•
**System-Integrationsaspekte:**

•
*Zuverlässigkeit:* Lief der ML-Service stabil, oder gab es Abstürze/Lags? Anzahl der Ausfälle, durchschnittliche CPU/RAM Nutzung, etc., um abzuschätzen, ob das im Dauerbetrieb praktikabel ist.

•
*Skalierbarkeit:* Kann das System mit ML immer noch angedachte Erweiterungen stemmen (Multi Asset-Support, etc.) oder wird ML zum Bottleneck? Falls unser ML z.B. 100% CPU auf 1 Asset braucht, skaliert das nicht auf 10 Assets linear. Das würden wir zumindest überschlagen (ggf. Test mit 2 Assets).

•
*Sicherheit & Audit:* Überprüfung, ob alle vorgesehenen Logs erzeugt wurden (gab es Lücken?), ob Explainability-Daten tatsächlich hilfreich sind. Hier könnten wir z.B. ein Audit-Szenario durchspielen: Wir nehmen einen ML-Trade und folgen dem Audit-Trail – können wir vollständig

14
rekonstruieren, warum er passiert ist und wer ihn "genehmigt" hat? Wenn ja \-\> Auditierbarkeit gegeben.

•
**Ethisch/Regulatorisch:** Subjektivere Bewertung, aber wichtig: •
*Regulatorische Konformität:* Hat sich irgendwas am Setup ergeben, was regulatorisch fragwürdig wäre? (z.B. Modelldokumentation unklar \-\> potenzielles Audit-Problem, oder ML könnte evtl. Muster nutzen, die an *Marktmissbrauch* grenzen – unwahrscheinlich, aber wir bedenken es.) •
*Ethik:* Ist das System für Nutzer verständlich genug, um verantwortbar zu sein? (Stichwort "Kennt der Mensch stets die Konsequenzen?") und verletzt es keine AI-Governance-Prinzipien (Transparenz, etc.). Da Explainability im Fokus steht, erwarten wir hier grüne Haken, aber wir dokumentieren es dennoch.

•
*Organisatorische Akzeptanz:* Feedback vom Team, ob sie dem Modell vertrauen würden. Falls intern große Skepsis bleibt, wäre ein vorsichtiges Vorgehen ratsam (z.B. längere Parallelphase). •
**Aufwand/Nutzen-Relation:** Zuletzt fließt in die Bewertung auch die *Praktikabilität* ein: War der Implementierungs- und Abstimmungsaufwand vertretbar und ist das System künftig gut wartbar? Wenn z.B. die Entwicklung gezeigt hat, dass ML extrem pflegeintensiv ist (Datenaufbereitung, ständiges Retraining), aber nur minimalen Vorteil bringt, ist der Nutzen zweifelhaft. Umgekehrt, wenn es moderate Pflege erfordert und deutliche Vorteile bringt, wäre das positiv. Diesen Aspekt quantifizieren wir schwer, aber wir können z.B. angeben: Zusätzlich \~X Stunden/Monat für Modellpflege nötig – ist die Organisation bereit dazu?

Alle diese Kriterien werden in einer Art **Entscheidungsmatrix** abgebildet. Denkbar ist eine Tabelle, wo für "Status Quo" vs "ML-Integration" verschiedene Kategorien (Performance, Risiko, Erklärbarkeit, Aufwand) qualitativ (✔ Verbesserug / neutral / Verschlechterung) eingetragen sind. Diese visuelle Zusammenfassung hilft Entscheidern schnell zu sehen, ob ML unterm Strich ein Gewinn ist.

Die Gewichtung der Kriterien wird vorher intern besprochen (z.B. Profitabilität ist wichtig, aber nicht um jeden Preis – ein kleiner Gewinnanstieg bei großer Komplexitätszunahme könnte dennoch abgelehnt werden, etc.). Letztlich gibt es jedoch keinen starren Score, sondern die **Expertenabwägung** des Projektteams, die im Empfehlungsteil erläutert wird.

**8\. Erwartete Ergebnisse und Deliverables**

Am Ende des Forschungsvorhabens sollen mehrere **greifbare Ergebnisse** vorliegen:

•
**Abschlussbericht (Deep Research Paper)** – Ein wissenschaftlich-technischer Bericht in Deutsch, ca. 20–25 Seiten (Markdown und als PDF), der alle oben genannten Punkte detailliert ausführt. Gliederung etwa: Executive Summary, Einleitung, Zielsetzung, Methodik, Ergebnisse (Pro Strang: Befunde), Diskussion, Empfehlung. Der Bericht enthält Tabellen (Modellvergleich, Risiko-Matrix, Performance-Übersicht), Diagramme (Systemarchitektur, ggf. ein Flowchart der Shadow-Pipeline und Beispielplots von Backtests) und **Quellenverweise** auf Analysen und externe Inspirationen. Er ist so geschrieben, dass sowohl technische Leser (Entwickler, Data Scientists) als auch Entscheider die relevanten Infos finden. Im Anhang könnten Code-Snippets oder Detailtabellen stehen. **Formatierung** ist bereits festgelegt: das Dokument wird in Markdown verfasst, was eine einfache Konvertierung zu PDF ermöglicht, und entspricht unseren Doku-Standards (eindeutige Kapitelüberschriften, nummerierte Abbildungen/Tabellen, klare Sprache).

•
**Entscheidungsvorlage (Management Summary Slide/Memo)** – Als Extrakt aus dem Bericht
wird eine 1-2 seitige Entscheidungsvorlage erstellt, die die wichtigsten Resultate und die empfohlene Go/No-Go-Entscheidung zusammenfasst. Diese Vorlage ist für das Management bzw. das Projektentscheidungsgremium gedacht. Sie enthält eine Zusammenfassung der Hypothese, einen **Ampel-Bewertungsteil** (z.B. "Performance: grün, Risiko: gelb, Aufwand: gelb")

15
und den konkreten Vorschlag ("Wir empfehlen **Go** unter folgenden Bedingungen..."). Diese Vorlage dient dazu, in der Entscheidungsrunde (die nach Stabilisierung des Risk/Execution Stacks ansteht) klar zu vermitteln, ob und wie man mit dem ML-Advisor fortfahren soll.

**Datenmodell-Vorschlag ml\_signals :** Ein konkreter Vorschlag für die Schemaerweiterung •
wird ausgearbeitet. Wahrscheinlich in Form eines JSON-Schemas ähnlich dem bestehenden SignalEvent , ergänzt um ML-spezifische Felder. Ebenso die DDL für eine neue
27

Datenbanktabelle ml\_signals (falls getrennt) oder Änderung an signals \-Tabelle (z.B. zusätzliche Spalte source \= {strategy, ML} ). Dieses Modell wird im Bericht beschrieben (im Architekturteil) und kann dann von den Entwicklern umgesetzt werden, falls Go. Es stellt sicher, dass alle relevanten Informationen eines ML-Signals (Confidence, Reason, etc.) sauber abgespeichert werden für spätere Analysen und Audits.

**Governance-Leitlinien:** Ein Dokument oder Abschnitt, der **Betriebsrichtlinien** für den ML
•

Advisor festhält. Darin z.B.:

•
Welche **Risikogrenzen** unbedingt einzuhalten sind (auch zukünftig, falls jemand die ML Parameter ändern will – z.B. "Confidence-Schwelle nicht unter 0.6 setzen, ohne neues Ok der Risk-Abteilung").

•
**Logging- & Auditing-Vorschriften:** Was muss geloggt werden (Empfehlung: alle ML Entscheidungen \+ Erklärungen immer loggen, Logs mind. X Monate aufbewahren). Ggf. Bezug

zu Compliance: "Ein KI-Modell muss dokumentiert werden, inkl. Trainingsdatenquelle und Testgüte" etc.

•
**Change-Management:** Wie werden Modell-Updates gehandhabt? (Vorschlag: jedes neue Modell durchläuft erst Backtest+Shadow, Freigabe durch Teamleiter, Versionierung in Repo, etc.).

•
**Fallback-Plan:** Was tun, wenn das ML-Modul Fehlverhalten zeigt? (z.B. Auto-Deaktivierung wenn

3 Fehlversuche in Folge, oder manuelles Abschalten via Dashboard – ein *AI-NOT-AUS* sozusagen).

•
**Explainability/Audit-Kriterien:** z.B. "Für jeden Trade muss ein Grund im Klartext vorliegen –

entweder aus Regel oder ML. Falls ML, muss der Grund auf XAI beruhen."

•
**Verantwortlichkeiten:** Festlegen, wer die ML-Komponente überwacht (neue Rolle Data Scientist oder im Team verteilt?) und wer im Zweifel eingreifen darf.

Diese Leitlinien sollen sicherstellen, dass beim Übergang von Forschungsprototyp zu eventueller Produktion alle organisatorischen Fragen abgedeckt sind. Im Bericht wird ein Kapitel dies umreißen, und ggf. ein separates policy-Dokument als Anhang erstellt.

Zusätzlich zu diesen Kern-Deliverables entstehen **Nebenergebnisse** wie Code (Prototyp, Notebooks), die jedoch primär intern bleiben. Wenn relevant, können Code-Module, die sich als nützlich erwiesen (z.B. eine SHAP-Visualisierungspipeline), im Repository abgelegt und dokumentiert werden. Aber Schwerpunkt sind die oben genannten Dokumente.

**9\. Dokumentationsformat und Abgrenzung**

**Formatierung und Dokumentation:** Wie bereits angedeutet, wird der Abschlussbericht in einer Weise verfasst, dass er sowohl als **Markdown** gelesen als auch in ein **PDF** umgewandelt werden kann. Dies entspricht den internen Standards und erleichtert die Verteilung. Alle wichtigen Ergebnisse werden in übersichtlichen **Tabellen** oder **Grafiken** präsentiert, um die Kernaussagen schnell erfassbar zu machen. Ein Diagramm veranschaulicht die ML-Integration im System (Shadow Mode Pipeline), was insbesondere für das Management hilfreich ist, um die Änderungen im Datenfluss zu verstehen. Der Bericht endet mit einer klar formulierten **Empfehlung** (inklusive eventueller Bedingungen), sodass die Entscheidungsträger eine eindeutige Handlungsoption haben.

16
**Abgrenzung des Vorhabens:** Es ist wichtig zu betonen, was dieses Forschungsprojekt **nicht** ist: \- **Keine direkte Produktiv-Implementierung:** Wir führen eine *Evaluation* durch, nicht die endgültige Implementierung ins Livesystem. Selbst wenn ein Go entschieden wird, käme die eigentliche Implementierungsphase (Härten des Codes, umfassende Testing, Deployment auf Prod) **erst danach**. Bis dahin bleibt der ML-Advisor in Test-/Shadow-Umgebung. Dies soll sicherstellen, dass die aktuellen Trading-Aktivitäten nicht gefährdet werden. \- **Fokus auf Machbarkeit, nicht Perfektion:** Wir werden nicht alle möglichen ML-Modelle bis ins Letzte austesten (z.B. keine wochenlangen Hyperparameter Optimierungen mit gigantischen Feature-Sets). Stattdessen ein **MVP-Ansatz für den ML-Advisor**: einfaches Modell, überschaubare Features, um prinzipiell Nutzen vs. Aufwand abzuwägen. Sollte sich zeigen, dass ML vielversprechend ist, kann man später immer noch tiefer ins Detail gehen (mehr Modelle, längere Trainings). Umgekehrt, wenn schon ein simpler Versuch kaum Mehrwert bringt, kann man wohl fundiert sagen, dass sich komplexere Versuche eher nicht lohnen – zumindest derzeit. \- **Kein Eingriff in Risk/Execution Kernlogik (ohne separate Freigabe):** Wir nehmen uns vor, während der Forschungsphase den **Risk-Layer** nicht fundamental zu ändern. Kleine Anpassungen (Konfiguration, Logging zusätzlicher Infos) ja, aber keine Abschwächung der Sicherheitsregeln zugunsten der ML Signale. Falls wir merken, das ML nur sinnvoll arbeiten kann, wenn man Risk-Limits lockert, wäre das wahrscheinlich ein Dealbreaker und würde auf No-Go hinauslaufen. Erst wenn das ML-Konzept überzeugt **und** wir Mechanismen für gleichwertige Sicherheit haben, würde man über Änderungen am Risk-Modul nachdenken, und das auch nur mit getrenntem Review. \- **Zeitliche Abgrenzung:** Sollte das Projekt feststellen, dass zu einer endgültigen Bewertung noch gewisse Voraussetzungen fehlen (z.B. "*Execution-Service war noch nicht stabil, daher konnten wir im Shadow Mode nicht echte Slippage-Effekte berücksichtigen*"), dann wird das im Bericht vermerkt. Gegebenenfalls wird vorgeschlagen, die ML Integration erst **nach** Erreichen bestimmter Meilensteine weiterzuverfolgen – z.B. "*warten bis Live Trading 1 Monat fehlerfrei lief, dann erneut ML testen*". Das soll verhindern, dass man Entscheidungen auf unsicherer Basis trifft.

Kurz gesagt: Dieses Briefing und das daraus entstehende Research Paper sollen **einen klaren Rahmen** stecken – was wird gemacht und geliefert, was nicht – damit Erwartungsmanagement betrieben wird. Erfolg ist hier nicht, dass am Ende ein fertiger ML-Bot läuft, sondern dass wir **wissen, ob wir einen ML Bot haben wollen** (und was es bräuchte, ihn verantwortungsvoll einzusetzen).

**10\. Fazit und nächste Schritte**

Die Integration eines ML-basierten Signal-Advisors in Claire de Binaire bietet spannende Chancen, aber muss mit Bedacht angegangen werden. Dieses Briefing hat dargelegt, wie wir strukturiert untersuchen, **ob** und **unter welchen Bedingungen** ein solcher Schritt sinnvoll ist. Wir kombinieren modernste technische Analyse (ML-Modelle, XAI-Tools) mit bewährten Prinzipien der Risikokontrolle in unserem deterministischen System.

Die **Erwartung** ist, nach Abschluss der Untersuchung eine fundierte Empfehlung geben zu können. Im Idealfall zeigt sich: *Ja, ein ML-Modul kann Mehrwert bringen, ohne unsere Prinzipien zu verletzen*, und wir schlagen dann ein konkretes Go mit Fahrplan vor (inkl. schrittweiser Aktivierung und Monitoring). Sollte das Ergebnis gemischt sein, werden wir genau benennen, welche **Bedingungen** zu erfüllen wären (z.B. weitere Daten sammeln, Modell verbessern, Team erweitern etc.), damit ein Go verantwortet werden kann. Und falls die ML-Integration sich als nicht lohnend oder zu riskant erweist, werden wir auch das transparent darlegen und begründen – dann bleibt der deterministische Pfad zunächst unsere beste Option.

**Nächste Schritte nach diesem Briefing:** Abstimmung mit allen Stakeholdern, Feinschliff des Forschungsplans (haben alle relevanten Fragen Eingang gefunden? Gibt es zusätzliche Bedenken von

17
Risk/Compliance-Seite, die noch berücksichtigt werden müssen?). Danach Freigabe des Plans und Start der Umsetzung (Datenbeschaffung, Tooling vorbereiten, etc.). Parallel kann schon begonnen werden, das Dokumentengerüst für den Bericht anzulegen, sodass während der Arbeit kontinuierlich Ergebnisse eingepflegt werden können – dies stellt sicher, dass am Ende alle Erkenntnisse lückenlos dokumentiert sind.

Abschließend ist hervorzuheben, dass **diese Evaluation in engem Austausch mit dem Entwickler und Risk-Team erfolgen wird**, um jederzeit sicherzustellen, dass wir auf dem richtigen Weg sind. Das Projekt dient nicht nur der Technikfindung, sondern auch dem *Wissensaufbau im Team* zum Thema KI im Trading. Unabhängig vom Ausgang (Go oder No-Go) wird das Team danach deutlich besser verstehen, wie ML-Modelle ticken und wie sie sich im Kontext unseres Systems verhalten. Dieses gewonnene Know-how ist in jedem Fall wertvoll und kann auch in anderen Bereichen (z.B. bessere Indikatoren, Auswertung von Backtest-Daten) nützlich sein.

Mit diesem Briefing sind die Weichen für eine erfolgreiche Deep Research Phase gestellt. Wir freuen uns darauf, die Hypothese zu prüfen und Claire de Binaire möglicherweise den Weg in Richtung *AI augmented Trading* zu ebnen – jedoch mit der gebotenen Vorsicht und Transparenz, die unser deterministisches Framework auszeichnet.

1 5 12
Service-Kommunikation & Datenflüsse.md

file://file-N2G9yoz33Lgt9YyeF71BV3

2 3 4 13 14 15 16 19 20 24 file://file-95h5nxmre4nE6ohJhuvjfX

Risikomanagement-Logik.md

6 26
ARCHITEKTUR.md

https://github.com/jannekbuengener/Claire-de-Binare/blob/cc202654df47bdcd026c2b40f1e52cffac7edfcb/backoffice/docs/ ARCHITEKTUR.md

7 25
PROJECT\_STATUS.md

https://github.com/jannekbuengener/Claire-de-Binare/blob/cc202654df47bdcd026c2b40f1e52cffac7edfcb/backoffice/ PROJECT\_STATUS.md

8 9 21 22
AI-Integrated Crypto Trading Platforms: A Comparative Analysis of OctoBot, Jesse, Krypto

Trading-Bot (K), Superalgos, and Freqtrade | by Jung-Hua Liu | Medium https://medium.com/@gwrx2005/ai-integrated-crypto-trading-platforms-a-comparative-analysis-of-octobot-jesse b921458d9dd6

10 11 17 18
Introduction \- Freqtrade

https://www.freqtrade.io/en/stable/freqai/

23
Explainable AI in Finance \- CFA Institute Research and Policy Center

https://rpc.cfainstitute.org/research/reports/2025/explainable-ai-in-finance

27
EVENT\_SCHEMA.json

file://file-GQuu1oGr3xKM8oy9VhUq9v

18