**Paper-Trading-Testsystem (N1-Phase) – Technische Dokumentation** 

**Übersicht der Testumgebung** 

Das **Paper-Trading-Testsystem** (Phase N1) dient dazu, Handelsstrategien in einer simulierten 1   
Umgebung zu prüfen, ohne mit einer echten Börse verbunden zu sein . Es verarbeitet historische oder künstliche Marktdaten und durchläuft den gesamten Handels-Workflow – von Signalgenerierung bis Order-Ausführung – rein virtuell. Ziel ist ein **vollständiger End-to-End-Test** der Strategie-, Risiko und Ausführungskomponenten unter realistischen Bedingungen, jedoch **ohne** tatsächliche Geld- oder 1   
Börsentransaktionen .  

**Scope & Ziele:** Die N1-Umgebung soll klar modulare Services bereitstellen, definierte Events und Datenflüsse nutzen und Strategy-, Risk- und Execution-Layer konsistent verknüpfen . Dadurch   
2 

2   
können alle Schritte eines Trades im Nachhinein nachvollzogen und ausgewertet werden .  

**Abgrenzung zu Produktionsumgebungen:** In der Paper-Test-Phase werden produktionsnahe Aspekte bewusst ausgeklammert . Es erfolgt **keine Anbindung an echte Exchanges** (z.B. keine Live   
3 

Integration der MEXC-Börse) und kein vollumfängliches Infrastructure/Deployment-Setup (Docker Container, Kubernetes, Monitoring etc.) . Performance-Optimierungen, Skalierungsfragen oder   
3 

4   
detaillierte physische Datenbankschemata sind in N1 nachrangig . Stattdessen genügt eine einfache 5   
Laufzeitumgebung (ggf. sogar ein Single-Process-Skript) für den Paper-Test . Die Ergebnisse des Paper-Tradings dienen als Vorstufe, um die Logik zu validieren, bevor in späteren Phasen eine produktionsnahe Implementierung mit echten Services, Containern und Live-Daten erfolgt.  

**Modulübersicht** 

Das System ist in **logische Module** unterteilt, die jeweils spezifische Aufgaben im Paper-Trading-Prozess übernehmen . Die folgende Tabelle gibt einen Überblick über alle Komponenten sowie deren   
6 

Verantwortlichkeiten und Schnittstellen: 

| Modul (Kürzel) Aufgabe und Schnittstellen (Inputs/Outputs) |
| ----- |
| **Market Data**  Quelle für Marktdaten-Events. Liest historische oder Mock-Marktdaten und gibt **Ingestion**  7 8 sie sequenziell als market\_data Events an die Strategie-Engine weiter . **(MDI)**  |
| Empfängt Marktdaten vom MDI und generiert daraus Handels-Signale  ( StrategySignal ) nach vordefinierten Regeln. Publiziert Signale auf dem  **Strategy**  9 8 **Engine (SE)**  Topic signals für die Risk Engine . Die SE kennt keine Kontostände  oder Limits – sie verarbeitet ausschließlich Marktdaten und Strategieparameter.  |

1

| Modul (Kürzel) Aufgabe und Schnittstellen (Inputs/Outputs) |
| ----- |
| Konsumiert Signale von der SE und führt mehrstufige Risikoprüfungen durch  (siehe unten). Nutzt aktuelle Portfolio- und Risiko-State-Daten vom PSM, sowie konfigurierbare Limits. Produziert als Ergebnis eine RiskDecision (Order  **Risk Engine**  10  Freigabe oder \-Blockade mit Begründung/Größe) . Publiziert genehmigte  **(RE)**  Orders auf orders für den Execution Simulator und versendet ggf. Alerts auf  11 12 alerts (z.B. bei Limitverletzungen) .  |
| Empfängt freigegebene **Order-Events** von der RE (Topic orders ) und simuliert die Ausführung. Erzeugt dazu eine SimulatedOrder sowie nach definierten 13  Regeln einen SimulatedTrade (z.B. Fill zum nächsten Candle-Preis) . Das  **Execution  Simulator (XS)**  Ergebnis der Simulation (Order-Resultat) wird als Event auf order\_results an 13 12 PSM, LA (und UI) geschickt . Bei Ausführungsbesonderheiten kann XS  auch Alerts (z.B. bei Slippage) auf alerts publizieren.  |
| Konsolidiert alle Trades und Positionsänderungen. Aktualisiert den Portfolio  Zustand nach jedem order\_result (Positionsgrößen, verfügbares Kapital,   **Portfolio &**  14  **State  PortfolioSnapshot** mit Equity, Cash, Drawdown, Exposure) . Führt zudem pro **Manager**  Symbol einen **PositionState** und einen globalen **RiskState** (z.B. Flags für  **(PSM)**  Drawdown überschritten, Pausen, etc.) . Diese aggregierten Zustände stellt 15 PSM der Risk Engine (für Berechnungen) und dem UI zur Verfügung.  |
| 16  Protokolliert *sämtliche* Events und Zustände zentral für die spätere Analyse . Bezieht passiv alle oben genannten Event-Themen und persistiert die Daten (z.B. 17  in einer Datenbank) . Dient als Grundlage für Performance-Auswertungen:  **Logging &**  Equity-Kurven, Drawdown-Analysen, Trade-Statistiken etc. . (Technisch  18 **Analytics (LA)**  subscribt LA alle Topics market\_data , signals , orders ,   order\_results , alerts und schreibt die eingehenden Payloads  unverändert in das Analysesystem.)  |
| Bietet eine einfache Visualisierung der Ergebnisse. Greift auf die von PSM/LA  **Dashboard /**  bereitgestellten Daten (Snapshots, Events, Alerts) zu und zeigt wichtige  **Reporting UI**  Kennzahlen wie Equity-Verlauf, Drawdowns, Trade-Historie und Alerts in Echtzeit 19 20 **(UI)**  an . In N1 dient das UI primär zu Auswertungszwecken und muss noch keine vollproduktiven Anforderungen erfüllen.  |

*Anmerkung:* Ein **Monitoring-Service (MON)** für Health-Checks ist in obiger Aufstellung optional 21   
enthalten , spielt aber für den reinen Paper-Test keine zentrale Rolle. 

**Event-Logik** 

**Event-Typen und Topics** 

Die Module kommunizieren **asynchron über Events** auf definierten Topics. Folgende logische Event 12   
Channels sind im Paper-Trading-Test relevant : 

| TopicPublisher  Subscriber  (Empfänger) Inhalt / Zweck (Sender)  |
| ----- |
| market\_data MDI SEMarktdaten-Events (Preis-Ticks, Candles) |

2

| TopicPublisher  Subscriber  (Empfänger) Inhalt / Zweck (Sender)  |
| ----- |
| signals SE REHandels-Signale der Strategie (z.B. BUY/SELL) |
| orders RE XSGenehmigte **Orders** (logisch, mit Größe) |
| order\_results XS PSM, LA, UIErgebnisse der simulierten Ausführung (Trades/Fills) |
| alerts RE / XS UI, LAWarnungen (Risiko- oder System Alerts) |

**Hinweis:** Ob diese Events in N1 intern nur in-memory weitergereicht oder über einen Message-Bus (z.B. Redis Pub/Sub) realisiert werden, ist flexibel – entscheidend ist das logische Protokoll der Topics und 22   
Payloads . 

**Event-Beispiele (JSON)** 

Nachfolgend sind exemplarische Payloads der verschiedenen Event-Typen im JSON-Format dargestellt 

23 24   
: 

// market\_data 

{ 

 "type": "market\_data", 

 "symbol": "BTC\_USDT", 

 "timestamp": 1730443200000, 

 "open": 35210.0, 

 "high": 35280.5, 

 "low": 35190.0, 

 "close": 35250.5, 

 "volume": 184.12, 

 "interval": "1m" 

} 

// signal 

{ 

 "type": "signal", 

 "symbol": "BTC\_USDT", 

 "direction": "BUY", 

 "strength": 0.82, 

 "reason": "MOMENTUM\_BREAKOUT",  "timestamp": 1730443260000, 

 "strategy\_id": "momentum\_v1" } 

// risk\_decision 

{ 

 "type": "risk\_decision", 

 "symbol": "BTC\_USDT", 

3  
 "requested\_direction": "BUY", 

 "approved": true, 

 "approved\_size": 0.05, 

 "reason\_code": "OK", 

 "timestamp": 1730443270000 

} 

// order\_result 

{ 

 "type": "order\_result", 

 "order\_id": "SIM\_123456", 

 "status": "FILLED", 

 "symbol": "BTC\_USDT", 

 "filled\_quantity": 0.05, 

 "price": 35260.1, 

 "timestamp": 1730443280000 

} 

// alert 

{ 

 "type": "alert", 

 "level": "CRITICAL", 

 "code": "DRAWDOWN\_LIMIT\_HIT", 

 "message": "Maximaler Drawdown erreicht. Trading gestoppt.",  "timestamp": 1730443300000 

} 

*(Beispielerläuterung:* Ein market\_data Event enthält hier z.B. 1-Minuten-Kerzen für BTC/USDT. Die signal \-Message zeigt ein **Kaufsignal** der Momentum-Strategie. Die Risk Engine gibt eine risk\_decision zurück – in diesem Fall **Freigabe** von 0,05 BTC. Der Execution Simulator bestätigt im order\_result den Fill (0,05 BTC zu Preis \~35260). Schließlich erzeugt ein Alert vom Typ CRITICAL 

den Hinweis, dass ein Drawdown-Limit erreicht und der Handel gestoppt wurde.) 

**Datenfluss (logische Reihenfolge)** 

Der End-to-End-Ablauf im Paper-Test verläuft in folgender **sequenzieller Event-Kette**: 

1\.    
**Marktdaten-Input:** Das MDI-Modul liest die nächste Marktdaten-Einheit (z.B. Candle) und 25   
publiziert ein market\_data Event auf den Bus .  

2\.    
**Signalberechnung:** Die Strategy Engine empfängt das Market-Event und berechnet daraus – abhängig von der Strategie – ein neues Handelssignal. Falls ein Signal entsteht, wird ein  26   
signal Event auf dem Topic signals gesendet (inkl. Richtung, Stärke, Begründung) .  

3\.    
**Risikoprüfung:** Die Risk Engine konsumiert das eingehende Signal und überprüft es gegen alle 

definierten Risikoregeln. Dafür lädt sie den aktuellen **RiskState** und **PortfolioSnapshot** vom 27   
PSM sowie die konfigurierten Grenzwerte (RiskConfig) . Basierend darauf entscheidet RE, ob die Order zugelassen wird und in welcher Größe. Das Resultat ist ein RiskDecision Event (mit approved=true/false , size und einem Reason-Code).  

4\.    
**Order-Routing:** Ist eine Order **freigegeben** ( approved=true ), erzeugt die Risk Engine einen 28   
Order-Event auf dem Topic orders , den der Execution Simulator abonniert hat . (Bei  approved=false wird an dieser Stelle der Trade verworfen; ggf. wurde ein Alert ausgegeben.)  

4  
5\.    
**Simulation der Ausführung:** Der Execution Simulator (XS) empfängt die freigegebene Order und erstellt eine korrespondierende **SimulatedOrder**. Anhand des definierten Ausführungsmodells in N1 (z.B. *Fill zum nächsten Candle-Open*) simuliert XS den Trade-Abschluss 29   
und generiert ein **SimulatedTrade**\-Resultat . Dieses Ergebnis wird als order\_results Event publiziert, welches den Trade-Status (z.B. FILLED) und Ausführungsdetails enthält.  

6\.    
**Portfolio-Update:** Der Portfolio & State Manager (PSM) liest das neue order\_results Event 

und aktualisiert daraufhin den internen Zustand. Konkret werden Positionsgrößen angepasst, das verfügbare Cash und der Portfolio-Gesamtwert neu berechnet sowie **Drawdown**\- und  30   
**Exposure-Werte** im RiskState upgedatet . Diese aktualisierten **PortfolioSnapshot**\- und  **RiskState**\-Daten stehen nun für weitere Risikoprüfungen (Schritt 3 bei Folgesignalen) und zur Visualisierung bereit.  

7\.    
**Logging:** Das Logging/Analytics-Modul protokolliert alle oben genannten Events und neuen 17   
Zustände in der Reihenfolge ihres Auftretens mit . Dadurch entsteht ein lückenloses Protokoll des Testlaufs, das für die spätere **Analyse** (Performance-Metriken, Statistiken) verwendet werden kann.  

8\.    
**Reporting:** Die UI-Komponente kann die eingespielten Daten fortlaufend auswerten. Sie bezieht 

z.B. regelmäßige **PortfolioSnapshots** vom PSM oder aggregiert die in der Datenbank gespeicherten Events aus LA, um Kennzahlen wie die Equity-Kurve, aktuellen Drawdown oder 20   
Signal-Trefferquote anzuzeigen .  

Das folgende Mermaid-Diagramm veranschaulicht den Datenfluss zwischen den Komponenten und den wichtigsten Datenobjekten: 

flowchart LR 

 MD\["�� MarketDataEvent"\] 

 SIG\[" StrategySignal"\] 

 RD\["�� RiskDecision"\] 

 OR\[" SimulatedOrder"\]   
 TRD\[" SimulatedTrade"\]   
 PS\[" PortfolioSnapshot"\] 

 RS\["⚠ RiskState"\] 

 MD \--\>|"Strategy Engine"| SIG 

 SIG \--\>|"Risk Engine"| RD 

 RD \--\>|"Execution Simulator"| OR 

 OR \--\>|"simulierte Ausführung"| TRD 

 TRD \--\>|"Update"| PS 

 TRD \--\>|"Update"| RS 

 %% Logging & Analytics beobachtet alle Pfeile passiv (nicht explizit  dargestellt) 

*(Legende:* MD \= Marktdaten-Event; SIG \= generiertes Signal; RD \= Risk-Decision; OR \= simulierte Order; TRD \= Trade/Fill-Ergebnis; PS \= Portfolio-Snapshot; RS \= Risk-State. Die gestrichelte Beziehung zum LA Modul ist im Diagramm textuell angemerkt und bedeutet, dass LA alle Transfers mithört und speichert.) 

5  
**Risk-Engine-Verhalten** 

Die Risk Engine implementiert **mehrlagige Schutzmechanismen** für das Trading. Jedes eingehende Signal durchläuft sequentiell eine Reihe von Risikoprüfungen, die in **Prioritätsstufen** organisiert sind   
31 

1\.    
: 

**Daily Drawdown (Tagesverlust-Limit):** Bricht den Handel ab, wenn der kumulative Verlust 

eines Tages einen vordefinierten Prozentsatz überschreitet. In diesem Fall werden **sofort alle** 31   
**Trades gestoppt**, offene Positionen geschlossen und ein kritischer Alert erzeugt .  2\.    
**Abnormale Marktbedingungen:** Erkennen von anomalen Marktverhältnissen, z.B. **übermäßige** 32   
**Slippage (\>1%)** oder extrem hoher **Spread (\>5× normal)** . Löst einen *Circuit Breaker* aus – d.h. ein Alert vom Typ CIRCUIT\_BREAKER wird gesendet und der Handelsalgorithmus **pausiert** 32   
**vorübergehend** .  

3\.    
**Daten-Stille:** Überwachung, ob Marktdaten ausbleiben. Wenn länger als X Sekunden (z.B. \>30s) 

keine neuen Preise empfangen wurden, wird ein DATA\_STALE \-Alarm ausgegeben und der  32   
**Handelsloop angehalten**, um auf frische Daten zu warten .  

4\.    
**Portfolio Exposure Limit:** Begrenzung des Gesamt-Exposure. Überschreitet die Summe aller 

offenen Positionen einen bestimmten Anteil des Kapitals, werden **neue Orders blockiert** (nicht ausgeführt). Ein entsprechender Hinweis ( RISK\_LIMIT Alert auf INFO-Level) kann protokolliert 33 34   
werden . Bestehende Positionen bleiben unverändert offen.  

5\.    
**Maximale Positionsgröße:** Begrenzung der Größe einzelner Trades. Ist das Volumen eines 

neuen Signals größer als der erlaubte Anteil des Portfolios, nimmt die Risk Engine ein **Order** 35   
**Trimming** vor . D.h., anstatt die Order komplett zu verwerfen, wird die **Größe auf das** 36 37   
**zulässige Maximum reduziert** und dann genehmigt . Falls Trimming nicht möglich (z.B. Mindestordergröße überschritten), würde der Trade abgelehnt.  

6\.    
**Stop-Loss je Position:** Überwachung offener Positionen auf Einzelverlust. Erreicht der  *unrealisierte Verlust* einer Position einen vorgegebenen Schwellenwert (z.B. 2% des Kapitals), 35 38   
initiiert die Execution-Komponente einen **automatischen Exit** für diese Position . Ein Alert (Level WARNING) mit RISK\_LIMIT Code wird dazu generiert.  

**Verarbeitung bei Regelverstößen:** Die oben genannten Checks werden in fester Reihenfolge ausgeführt – die höher priorisierten Regeln (1 ist höchst) können den Tradeflow frühzeitig abbrechen   
31   
. Konkret: 

\- Tritt ein **kritischer Verstoß** ein (Daily Drawdown oder schwerwiegende Marktanomalie), so wird das Signal **komplett abgelehnt** ( Reject ) und sofort ein entsprechender Alert gesendet . Im   
39 

Drawdown-Fall stoppt das System den Handel komplett; bei Marktanomalie geht es in eine Pause über 

40   
. 

\- Schlägt lediglich ein Limit wie Exposure oder Positionsgröße an, verfährt die Engine weniger drastisch: Bei **Exposure-Limit** wird das Signal verworfen (keine neuen Orders) und ein Info-Alert kann geloggt 34   
werden . Bei **Positionslimit** wird – wie erwähnt – die Order **auf erlaubte Größe getrimmt** und dann 41 37   
in reduzierter Form genehmigt (dieser Vorgang wird ebenfalls als regelkonformer Durchgriff protokolliert). 

\- Ein ausgelöster **Stop-Loss** auf einer bestehenden Position führt nicht zu einem eingehenden Signal, sondern zu einer direkten Order (Exit) im Execution-Service, der Verlust wird realisiert und die Position 38   
geschlossen . Auch dies erzeugt einen Alert.  

Jede Regelverletzung kann einen **Alert** auslösen, der auf dem Topic alerts veröffentlicht wird. Alerts 41   
sind in **Schweregrade** unterteilt : 

\- *INFO:* Hinweis auf weiche Grenzen (z.B. Exposure-Limit erreicht, Order blockiert). \- *WARNING:* Warnung bei temporären oder teilweisen Eingriffen (z.B. Order wurde getrimmt, Stop-Loss 42   
ausgelöst, Datenstille erkannt) . 

6  
\- *CRITICAL:* Kritische Alarmierung bei harten Stops (z.B. Drawdown-Limit überschritten, Trading 43   
gestoppt) .  

Jeder Alert enthält einen Code ( code wie z.B. RISK\_LIMIT , CIRCUIT\_BREAKER oder 24   
DATA\_STALE ), eine Beschreibung/Meldung und einen Timestamp . Die UI bzw. das Monitoring kann diese Alerts nutzen, um z.B. Ampel-Indikatoren (grün/orange/rot) anzuzeigen oder Metriken 44   
(Counter) zu erhöhen . 

**Wiederanlaufstrategien:** Für pausierte oder gestoppte Handelsaktivitäten definiert das System folgende Recovery-Ansätze:   
\- Bei einem **Daily Drawdown Stopp** wird das Trading für den Rest des Tages ausgesetzt. Ein Reset erfolgt typischerweise um **00:00 UTC** des nächsten Tages, und es ist ein manueller Neustart/freigabe 45   
durch einen Admin erforderlich, um den Handel wieder aufzunehmen . 

\- Ein durch **Marktanomalien** ausgelöster *Circuit-Breaker* führt zu einer temporären Pause. Das System kann automatisch in Intervallen (z.B. alle 60 Sekunden, maximal 10 Versuche) prüfen, ob sich die 45   
Marktbedingungen normalisiert haben . Sobald die Parameter wieder im grünen Bereich liegen, wird der Handel automatisch fortgesetzt. Andernfalls bleibt der Zustand bestehen, bis ein manueller Eingriff erfolgt.   
\- Bei **Datenstille** (keine Marktdaten) wartet das System automatisch, bis wieder ein neues 45   
market\_data Event eintrifft . Sobald Daten fließen, wird der Handelsloop ohne manuellen Eingriff fortgesetzt. 

\- Limits wie **Exposure** oder **Positionsgröße** erfordern keinen besonderen Neustartmechanismus – hier genügt es, dass sich die Werte wieder unter die Schwellen bewegen (etwa durch Positionsschließungen oder Gewinnanstiege), damit neue Signale wieder normal durchgehen. Diese Limits wirken also eher restriktiv im Moment des Eintreffens eines Signals und heben sich automatisch auf, wenn die Bedingungen es zulassen.  

**Persistenz- und Analysearchitektur** 

Im Paper-Trading-System N1 steht ein **logisches Datenmodell** im Vordergrund . Alle wichtigen   
46 

Ereignisse und Zustände werden als strukturierte Objekte repräsentiert und zur Analyse gespeichert. Die Haupt-Entitäten sind:  

•    
**MarketDataEvent:** Marktdateneinheit (z.B. Candle oder Tick) mit Zeitstempel, Kursen, Volumen 47   
usw. – repräsentiert eingehende Marktdaten im Test .  

•    
**StrategySignal:** Vom Strategie-Modul abgeleitetes Handelssignal (z.B. *BUY* oder *SELL* für ein 47   
Symbol, inkl. Stärke und Grund) .  

•    
**RiskState:** Aggregierter Risikozustand des Systems. Enthält laufende Kennzahlen wie aktuellen 15   
Drawdown, gesamtes Exposure, etwaige *Cooldown*\-Flags oder Pausen-Indikatoren etc. . Der RiskState wird vom PSM gepflegt und von der RE gelesen, um kontextbezogene Entscheidungen 

zu treffen.  

• 48   
**RiskDecision:** Ergebnis der Risiko-Entscheidung zu einem Signal . Besteht aus dem ursprünglichen Signal (Symbol, gewünschte Richtung), einem approved Flag, einer ggf.  **adjustierten Größe** ( approved\_size ) sowie einem **Reason-Code** (z.B. “OK” für freigegeben, 49   
oder ein Kürzel der verhinderten Regel) . Dieses Objekt wird von der RE erzeugt und auf  orders gesendet, sodass XS entsprechend handelt.    
• 50   
**SimulatedOrder:** Repräsentiert eine virtuell erteilte Order im Paper-Test . Enthält u.a. eine Order-ID, das Symbol, die Ordergröße und ggf. Ordertyp. XS erstellt dieses Objekt, sobald eine RiskDecision auf *approved* steht.  

7  
•    
**SimulatedTrade:** Stellt das Ergebnis der Auftragsausführung dar – also einen ausgeführten Trade. Enthält z.B. ausgeführte Menge, Preis, Zeitpunkt und Status ( FILLED , REJECTED , etc.)   
51   
. Der Execution Simulator generiert dieses Objekt gemäß dem simplen Ausführungsmodell 

von N1.  

• 15   
**PositionState:** Laufender Status einer einzelnen Position pro Symbol . Beinhaltet z.B. aktuelle Positionsgröße, durchschnittlicher Einstandspreis, unrealisiertes P\&L und ggf. 

positionsbezogene Flags (z.B. ob Stop-Loss erreicht wurde). PSM führt für jedes gehandelte Symbol einen eigenen PositionState.    
• 52   
**PortfolioSnapshot:** Gesamtsicht auf das Portfolio zu einem bestimmten Zeitpunkt . Umfasst Kennzahlen wie Gesamt-Equity (Kapital \+ unreal. P\&L), verfügbarer Kassenbestand, aktueller Drawdown-Prozentsatz, Gesamt-Exposure und ähnliche aggregierte Daten. PSM erstellt bei jeder Änderung (Trade) einen neuen Snapshot und stellt ihn Risk Engine und UI bereit.  • 53   
**BacktestRunMetadata:** Metadaten zum Testlauf selbst . Z.B. eine ID oder Timestamp des Runs, verwendete Strategiekonfiguration, Dauer des Tests, ggf. Metriken-Übersicht. Dient der Nachverfolgbarkeit verschiedener Paper-Trading-Durchläufe und der Vergleichbarkeit von Strategieänderungen.  

Alle oben genannten Entitäten – von MarketDataEvent bis BacktestRunMetadata – werden vom 16   
**Logging & Analytics (LA)** Modul dauerhaft gespeichert . Die Persistierung erfolgt in einer zentralen **Datenbank** (für strukturierte Abfragen) und/oder als Logfiles. In der N1-Umgebung ist PostgreSQL als 54 55   
relationaler Speicher vorgesehen . Hier werden z.B. Orders, Trades, Signals und Risk-Events in Tabellen abgelegt, um später ausgewertet zu werden. Kurzlebige Daten (Queues/Cache wie aktuelle 55   
Market-Events oder Zwischensignale) können in Redis gehalten werden , obwohl im reinen Paper Test der Bedarf dafür gering ist. 

Die **Logging-Strategie** des LA-Moduls besteht darin, sämtliche Events **unverändert und lückenlos** mit 17   
Zeitstempel abzulegen . So entsteht ein Audit-Trail, der für Analysen und Debugging genutzt werden kann. Das LA-Modul ist dabei *passiv*: Es greift nicht in den Ablauf ein, sondern **“belauscht”** die Kommunikation zwischen den Services (z.B. indem es bei allen relevanten Topics als zusätzlicher 17   
Subscriber registriert ist) . Die gespeicherten Daten ermöglichen im Nachgang vielfältige **Analysen**: Von der Berechnung der Performance-Kennzahlen (siehe unten) über das Debuggen einzelner Trades bis hin zum Tuning von Strategieparametern anhand der aufgezeichneten Signale und Risk 18   
Entscheidungen . 

**Testmetriken und Validierungsansätze** 

Um den Erfolg eines Paper-Trading-Durchlaufs bewerten zu können, werden verschiedene **Metriken** erhoben und anschließend analysiert: 

• 20   
**Equity Curve (Kapitalverlauf):** Entwicklung des Portfoliowerts über die Zeit . Eine steigende Equity-Kurve zeigt Gewinne, Einbrüche markieren Verluste. Die Equity-Kurve wird typischerweise als Zeitreihendiagramm dargestellt und erlaubt visuell zu prüfen, wie stabil und profitabel die Strategie arbeitet. Wichtig sind Kennzahlen wie **Gesamtrendite** und **Volatilität des Kurvenverlaufs**.    
• 20   
**Drawdown:** Messgröße für Verluste vom letzten Höchststand (Peak) des Portfolios . Der  **maximale Drawdown** gibt den größten zwischenzeitlichen Kapitalrückgang (%) im Testzeitraum an – ein Indikator für das Risikoprofil der Strategie. Auch **Tages-Drawdowns** werden betrachtet, insbesondere im Hinblick auf das in der Risk Engine gesetzte Tageslimit. Erwartungsgemäß sollte der maximale Drawdown im Paper-Test das gesetzte Limit (z.B. 5%) nicht überschreiten, andernfalls hätte die Risk Engine ja eingegriffen (was entsprechend im Alert-Log sichtbar wäre).  

8  
•    
**Signal Accuracy (Trefferquote der Signale):** Gibt an, wie oft die generierten Handelssignale  *richtig* lagen. Dies kann definiert werden als Anteil der **profitablen Trades** an allen ausgeführten Trades oder als statistische Kennzahl pro Signaltyp. Eine hohe Trefferquote (z.B. \> 50-60%) zusammen mit einem günstigen **Profit-Faktor** (Summe Gewinne zu Summe Verluste) spricht für eine effektive Strategie. Diese Metrik wird aus den Trade-Daten abgeleitet – z.B. indem geprüft wird, ob die Equity nach einem Signal-Trade gestiegen oder gefallen ist.  

Weitere Kennzahlen können je nach Strategie einbezogen werden, etwa **Sharpe Ratio** (Rendite/Risiko Verhältnis), **Trade-Win/Loss-Verteilung**, durchschnittliche Haltedauer von Trades, **Drawdown-Dauer**, usw. Viele dieser Werte lassen sich aus den von LA gespeicherten Trades und Snapshots berechnen. 

**Validierungsansätze:** Die im Paper-Test erzielten Kennzahlen werden typischerweise mit Erwartungswerten oder Benchmarks verglichen. Zum Beispiel kann man prüfen, ob die Equity-Kurve der Strategie einen bekannten **Buy-and-Hold**\-Vergleichsindex schlägt, oder ob die Drawdowns innerhalb akzeptabler Grenzen blieben. Auch wird kontrolliert, ob die Risk Engine korrekt reagiert hat – etwa indem man sicherstellt, dass *kein* Trade einen Verlust größer als den definierten Stop-Loss oder Tagesdrawdown verursachen konnte (was durch Alerts/Logs verifiziert wird).  

Ein weiterer Validierungsaspekt ist die **Reproduzierbarkeit**: Mehrfache Läufe mit dem gleichen Datenset und Parametern sollten konsistente Ergebnisse liefern (Deterministik des Backtests). Die Testumgebung ermöglicht zudem Komponententests: Jedes Service-Modul (Signal, Risk, Execution) kann isoliert mit spezifischen Szenarien getestet werden (z.B. Risk-Regeln mit konstruierten 56   
Signalinputs), um sicherzustellen, dass Grenzfälle korrekt gehandhabt werden . Automatisierte Tests (z.B. via PyTest) und das Überprüfen der Logs (Audit-Trail) gehören ebenfalls zu den empfohlenen 56   
Praktiken, um die Korrektheit der Abläufe zu validieren . 

**Auswertungsformate:** Die Ergebnisse des Paper-Tradings werden häufig in **grafischer und tabellarischer Form** präsentiert. Beispielsweise: \- **Equity- und Drawdown-Kurven** als Liniendiagramme (oft übereinander gelegt zur Veranschaulichung). \- **Metriken-Report** in Tabellenform (Kennzahlen wie Gesamtrendite, max. Drawdown, \#Trades, Trefferquote, avg. Gewinn/Verlust pro Trade etc.). \- **Trade-Liste** oder Trade-Analytics-Dashboard, das jede Position und deren Ergebnis auflistet. \- **Alert-Log** Übersicht, um zu sehen, wann welche Risk-Limits gegriffen haben (wichtig für die Interpretation der Performance unter Risikogesichtspunkten).  

Im Claire-de-Binare-Projekt liefert das Dashboard bereits einige dieser Visualisierungen in Echtzeit 20   
(Equity, Drawdown, Alerts) . Für tiefere Analysen können die in der Datenbank persistierten Daten exportiert und z.B. in Jupyter-Notebooks oder BI-Tools ausgewertet werden. Die **Erwartung** an den Paper-Test ist, dass er ausreichende Daten liefert, um die Strategie bewerten und calibraten zu können, bevor echtes Kapital riskiert wird. 

**ENV-Konventionen und Startbedingungen** 

**Environment Variablen:** Die Testumgebung verwendet eine .env Konfigurationsdatei, welche alle relevanten Parameter enthält. Dazu gehören Verbindungsdaten für Infrastruktur, konfigurierbare Limits 57   
und Zugangsdaten (für eventuelle externe APIs, in späteren Phasen) . Wichtige Kategorien von ENV Variablen sind:  

•    
**Datenbank:** z.B. POSTGRES\_DB (Name der Postgres-Datenbank, Standard  claire\_de\_binare ), POSTGRES\_USER (DB-Benutzer, z.B. claire ), POSTGRES\_PASSWORD 57   
(Passwort) . Diese dienen dem LA-Modul zum Persistieren der Testergebnisse.  9  
•    
**Message-Bus (Redis):** REDIS\_HOST (Host, meist Container-Name cdb\_redis ),  REDIS\_PORT (Standard 6379 ), REDIS\_PASSWORD (auth-Passwort) – falls ein Redis-Pub/Sub 58   
für Events genutzt wird . In N1 kann es aber auch sein, dass statt Redis einfache In-Memory Queues genutzt werden, abhängig vom Implementierungsmodus.  

•    
**Service-Ports:** Falls die Module als Microservices laufen, werden Ports per ENV gesetzt. Standardmäßig gelten: WS\_PORT=8000 (Market Data Websocket/Screener),  59 60   
SIGNAL\_PORT=8001 , RISK\_PORT=8002 , EXEC\_PORT=8003 . (Weitere Ports:  PROM\_PORT=9090 für Prometheus, GRAFANA\_PORT=3000 , DB\_PORT=5432 , siehe Infrastruktur.) Diese Werte sind im Docker-Compose so festgelegt, können aber im Container 61   
Inneren via ENV auch verwendet werden .  

•    
**Risikoparameter:** Die in der Risk Engine genutzten Grenzwerte werden ebenfalls über ENV 

gesteuert. Beispiele: MAX\_POSITION\_PCT (max. Positionsgröße, z.B. 0.10 für 10% des Kapitals) 

62   
, MAX\_EXPOSURE\_PCT (max. Gesamt-Exposure, z.B. 0.50), MAX\_DAILY\_DRAWDOWN\_PCT 63   
(z.B. 0.05), STOP\_LOSS\_PCT (z.B. 0.02) . Durch diese Variablen kann man Risikoszenarien im Test flexibel justieren.  

•    
**Startkapital und Sonstiges:** Oft wird ein INITIAL\_CAPITAL in der ENV definiert (z.B. 64   
Startportfolio 1000 USDT) , um die Berechnungen von P\&L und Prozentwerten zu initialisieren. Weitere ENV-Flags können z.B. Feature-Toggles sein oder API-Keys (etwa  MEXC\_API\_KEY/SECRET für Live-Betrieb, im Paper-Test nicht genutzt aber vorgesehen).  

*Konvention:* Sensible Daten wie Passwörter oder API-Keys sind **niemals hardcodiert** im Code, sondern 65   
ausschließlich in der .env hinterlegt (und in Versionskontrolle ausgeschlossen) . Die .env wird beim Start geladen, sodass alle Services ihre Konfiguration daraus beziehen.  

**Startup-Bedingungen:** Vor dem Start eines Paper-Test-Laufs sind folgende Voraussetzungen sicherzustellen:  

•    
**Infrastruktur bereit:** Falls die Komponenten verteilt laufen, müssen unterstützende Dienste laufen: z.B. die PostgreSQL-Datenbank (auf dem definierten Port, Standard 5432\) und evtl. der 60   
Redis-Broker (Port 6379\) . In N1 kann alternativ alles in einem Prozess ablaufen, aber bei Container-Betrieb sollten diese zuerst via Docker Compose hochgefahren werden.  •    
**Initialisierung:** Das System sollte mit einem *sauberen Zustand* starten. D.h. die Datenbank ist leer oder enthält einen neuen Schema-Stand, es gibt keine offenen Positionen im PSM (Initial PortfolioSnapshot gesetzt mit Startkapital, alle PositionsStates leer), und RiskState ist auf neutral (z.B. Drawdown-Zähler auf 0, keine Pausen aktiv). Die ENV-Variable INITIAL\_CAPITAL sollte vorab entsprechend gesetzt sein, damit PSM und RE korrekt rechnen.  

•    
**Start der Services:** In der einfachsten Form kann ein **Paper-Trading-Runner-Skript** alle Module der Reihe nach aufrufen (MDI \-\> SE \-\> RE \-\> XS \-\> PSM/LA). In einer Microservice-Architektur startet man jeden Service separat (z.B. per docker compose up die Dienste  66   
cdb\_signal\_gen , cdb\_risk\_manager , cdb\_execution , etc.) . Wichtig ist, dass MDI/ SE zuerst Marktdaten liefern, während RE/XS/PSM bereits horchen. Oftmals ist die Startreihenfolge: **Datenquelle hochfahren**, dann **Strategie-Engine**, dann **Risk Manager**, dann  **Execution Simulator**, und zuletzt **Dashboard**, um sicherzustellen, dass keine Events ins Leere laufen. Health-Checks (z.B. GET /health an Port 8002 für Risk Manager) können genutzt 67   
werden, um die Betriebsbereitschaft der Services zu prüfen .  

•    
**Konfiguration prüfen:** Vor dem Lauf sollte man die geladenen ENV-Parameter verifizieren (z.B. Log-Ausgabe beim Start, oder /status \-Endpoints der Services, die die aktiven Limits anzeigen   
68   
). Damit stellt man sicher, dass die beabsichtigten Schwellenwerte im Risk Manager aktiv sind 

und z.B. der *Circuit-Breaker* wirklich auf den gewünschten Werten basiert.  10  
**Shutdown und Reset:** Nach Abschluss des Paper-Trading-Durchlaufs (z.B. wenn das historische Datenset durchgelaufen ist) können die Services angehalten werden. Hierbei sollte das LA-Modul ggf. letzte Puffereinträge in die Datenbank schreiben (idempotent, da Ereignisse sequentiell verarbeitet wurden). Für einen weiteren Testlauf empfiehlt es sich, die Datenbank zu leeren oder einen neuen Run zu kennzeichnen (via BacktestRunMetadata). Falls Alerts auf einen Trading-Stopp hingedeutet haben (Drawdown überschritten), muss vor einem Neustart entschieden werden, ob man die Umgebung manuell zurücksetzt (z.B. RiskState/Cooldown zurücksetzen). In der N1-Definition sind keine komplizierten Shutdown-Prozeduren vorgeschrieben – ein einfaches Stoppen der Prozesse/Container ist ausreichend, da *Stateful* Daten bereits in der DB persistiert sind und die Services selbst zustandslos neu 69   
gestartet werden können . Wichtig: Es wird erwartet, dass eine gültige .env im Projektroot vorliegt 70   
und benutzt wird , andernfalls könnten Services mit Defaultwerten oder gar nicht starten. 

Zusammenfassend bietet die N1-Paper-Trading-Umgebung ein **klar definiertes, modulares Testfeld** für KI-Agenten oder Entwickler, um Handelslogiken unter sicheren Bedingungen zu erproben. Alle Komponenten, vom Market Data Feed bis zur Risk Engine, arbeiten eventgetrieben zusammen und schaffen so einen reichhaltigen Datensatz, den ein intelligentes Auswertungs-System aufnehmen kann. Diese Dokumentation soll sicherstellen, dass ein KI-basierter Systemteilnehmer die Struktur und 

Abläufe versteht und korrekt mit den definierten Schnittstellen interagiert.    
1 22 

1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 

30 46 47 48 49 50 51 52 53 54 55 57 60 69 70 

N1\_ARCHITEKTUR.md 

https://github.com/jannekbuengener/Claire\_de\_Binare\_Cleanroom/blob/238cdaea1f9c505d83e04387138e9e431ff034b1/ backoffice/docs/architecture/N1\_ARCHITEKTUR.md 

31 32 33 34 35 37 38 39 40 44 56 

RISK\_LOGIC.md 

https://github.com/jannekbuengener/Claire\_de\_Binare\_Cleanroom/blob/238cdaea1f9c505d83e04387138e9e431ff034b1/ backoffice/docs/services/risk/RISK\_LOGIC.md 

36 41 62 63 66 67 68 

README.md 

https://github.com/jannekbuengener/Claire\_de\_Binare\_Cleanroom/blob/238cdaea1f9c505d83e04387138e9e431ff034b1/ backoffice/services/risk\_manager/README.md 

42 43 45 

output.md 

https://github.com/jannekbuengener/Claire\_de\_Binare\_Cleanroom/blob/238cdaea1f9c505d83e04387138e9e431ff034b1/ backoffice/docs/knowledge/output.md 

58 59 61 64 65 

env\_index.md 

https://github.com/jannekbuengener/Claire\_de\_Binare\_Cleanroom/blob/238cdaea1f9c505d83e04387138e9e431ff034b1/ backoffice/docs/infra/env\_index.md 

11