---
status: archived
migration_status: resolved
note: "Legacy file-links entfernt, Textreferenzen beibehalten (ADR-027)"
---

## cdb\_redis

Für einen Neuaufbau des **Claire de Binaire** Servers wird zunächst eine geeignete Systemumgebung benötigt. Idealerweise steht ein **aktueller x64-Server oder Rechner** zur Verfügung (getestet wurde z. B. auf Docker Desktop unter Windows) mit installiertem **Docker** und **Docker-Compose**[\[1\]]. Dadurch sind Anforderungen an das Basis-Betriebssystem gering – Linux oder Windows mit Docker-Unterstützung reichen aus. Für den Betrieb sollten ca. 1–2 GB RAM und eine stabile Internetverbindung eingeplant werden, da Marktdaten in Echtzeit von der **MEXC**\-API bezogen werden.

**Software/Services:** Benötigt werden Container-Images für **Redis** (Message-Bus) und **PostgreSQL** (Datenbank), sowie die Python-basierten Microservices des Bots selbst (als Docker-Images). Docker-Compose orchestriert diese Komponenten. Beim Neuaufsetzen zieht Docker-Compose die Basis-Images (z. B. redis:7-alpine und postgres:15-alpine) automatisch aus dem Registry[\[2\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L28-L36)[\[3\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L9-L17).

**Zugriffstokens & Secrets:** In einer konfigurierten **.env**\-Datei sind alle sensiblen Zugangsdaten und Konfigurationswerte abzulegen. Dazu zählen insbesondere:

* **MEXC API Key & Secret:** API-Schlüssel für die Börse (nur Lese-/Handelsrechte, **keine Withdraw-Rechte** gemäß Sicherheitsrichtlinie[\[4\]]). Diese sind in den Env-Vars MEXC\_API\_KEY und MEXC\_API\_SECRET zu hinterlegen[\[5\]]. Ebenso die Basis-URL der API (MEXC\_BASE, default: MEXC Contract-API).

* **Redis-Zugang:** Ein Redis-Instanz wird als Message-Bus genutzt. In der .env müssen REDIS\_PASSWORD (gemäß Compose erforderlich[\[6\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L13-L19)) und ggf. Host/Port stehen. Standardmäßig verbinden die Services auf REDIS\_HOST=redis (Container-Hostname) und Port 6379[\[7\]].

* **PostgreSQL-Zugang:** Die Datenbank-Zugangsdaten POSTGRES\_USER, POSTGRES\_PASSWORD und der Datenbankname POSTGRES\_DB sind anzugeben[\[8\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L32-L40). Im Docker-Setup wird z. B. ein User *cdb\_user* und die DB *claire\_de\_binare* genutzt (siehe unten).

* **Weitere Secrets:** Für Benachrichtigungen via Web-Push sind – falls das Notification-Service genutzt wird – ein VAPID-Schlüsselpaar (WEBPUSH\_VAPID\_PUBLIC\_KEY, WEBPUSH\_VAPID\_PRIVATE\_KEY) sowie ein Kontakt-URL (WEBPUSH\_CONTACT) erforderlich[\[9\]]. Legacy-Optionen wie Telegram-Bot-Token und Chat-ID können entfallen[\[10\]].

**Hardware**: Spezielle Hardware ist nicht erforderlich, da alle Komponenten in Docker-Containern laufen. Eine zuverlässige **Speicherlösung** für Persistenz sollte vorhanden sein (Docker Volumes für Datenbank und ggf. Logs), sowie genug CPU-Ressourcen für die Datenverarbeitung in Echtzeit. Backups (siehe unten **Sicherheit & Recovery**) sollten auf ein separates Medium/Verzeichnis erfolgen.

## 2\. Deployment Stack (Docker, Compose, Python, Redis, PostgreSQL, Flask)

Claire de Binaire setzt auf einen **containerisierten Deployment-Stack** zur einheitlichen Bereitstellung aller Komponenten. Kernbestandteile und ihr Zusammenspiel:

* **Docker & Docker-Compose:** Alle Services laufen in Docker-Containern, definiert durch individuelle Dockerfile\-Rezepte und orchestriert über eine zentrale docker-compose.yml. Docker-Compose startet die Infrastruktur (Redis, Postgres, Monitoring) sowie die Bot-Services in korrekter Reihenfolge. Beispielsweise wird in der Compose-Datei der Redis-Container cdb\_redis definiert (mit persistentem Volume für Daten und Passwortschutz)[\[3\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L9-L17), ebenso der PostgreSQL-Container cdb\_postgres mit Initialisierung des DB-Schemas[\[8\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L32-L40). Die Compose-Datei legt zudem fest, welche Ports nach außen geöffnet werden, und nutzt depends\_on, um Abhängigkeiten und Startreihenfolge auszudrücken (z. B. muss Redis laufen, bevor die Signal-Engine startet[\[11\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L178-L186)).

* **Python-Anwendungen & Requirements:** Die fachliche Logik ist in **Python** implementiert (Version 3.11). Jedes Microservice-Modul hat sein eigenes Verzeichnis mit Code und eine requirements.txt für Dependencies. Wichtige Bibliotheken sind u. a. **Flask** (für HTTP-Endpunkte wie Health-Checks), **redis-py** (für die Pub/Sub-Anbindung), ggf. **ccxt** (für Börsen-API-Zugriff in der Execution) sowie ORMs/DB-Treiber wie SQLAlchemy und Psycopg2 für die Datenbankanbindung[\[12\]]. Die requirements.txt der Services listen nur dienstspezifische Abhängigkeiten (z. B. Flask, redis, dotenv) – dadurch bleiben die Container schlank[\[13\]][\[14\]].

* **Flask Microservices:** Jeder Service ist als eigenständige Flask-Anwendung gestaltet. Flask stellt minimale HTTP-Endpunkte bereit – vor allem /health für Health-Checks, evtl. /status oder /metrics für Statusabfragen[\[15\]]. Die Flask-App läuft innerhalb des Containers auf dem vorgesehenen Port (siehe unten Architektur/Ports) und ermöglicht so Docker-Compose Healthchecks. Im Dockerfile wird dafür der Port exponiert und ein Healthcheck-CMD definiert (z. B. via curl auf /health)[\[16\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/backoffice/services/risk_manager/Dockerfile#L14-L19)[\[17\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/backoffice/services/risk_manager/Dockerfile#L20-L23). Die Flask-Server starten in den jeweiligen service.py\-Mainprogrammen.

* **Redis (Message-Bus):** Redis dient als zentrales **Pub/Sub-Message-Bus** für die lose gekoppelte Kommunikation zwischen den Microservices. Der Redis-Container wird mit Persistenz (AppendOnly Log) konfiguriert und im Compose-File hinterlegt[\[18\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L16-L24). Alle Services verbinden sich über die in .env konfigurierten Host/Port/Passwort auf diesen Bus. Ereignisse wie Marktdaten, Signale etc. werden als JSON-Nachrichten über definierte Channels (Topics) veröffentlicht – Redis verteilt sie an alle abonnierten Dienste (siehe Architekturbeschreibung).

* **PostgreSQL (Persistenz):** Die relationale Datenbank speichert **persistente Daten**: Signale, Trades, Risk-Entscheidungen, Performance-Metriken usw. Beim Initialstart legt der Postgres-Container mittels eingebundenem Schema-SQL-Skript die nötigen Tabellen an[\[19\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L38-L44). Der DB-Zugriff erfolgt aus den Services heraus (z. B. Speichern von Trades nach Ausführung). Wichtig: Vor dem Start müssen die DB-Zugangsdaten in .env stimmen, da die Services diese nutzen, um eine DB-Verbindung aufzubauen. Im Compose ist Postgres durch depends\_on bei der Execution-Komponente berücksichtigt (Execution-Service wartet auf DB-Start)[\[20\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L236-L244).

**Docker-Aufbau (Dockerfiles):** Jedes Microservice-Modul hat ein eigenes Dockerfile, meist basierend auf python:3.11-slim. Darin werden die Abhängigkeiten installiert und der Anwendungscode kopiert[\[21\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/backoffice/services/risk_manager/Dockerfile#L9-L16). Es wird ein eingeschränkter **Non-Root-User** erstellt (Security Best Practice: „least privilege“)[\[22\]][\[16\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/backoffice/services/risk_manager/Dockerfile#L14-L19), und der Standard-Startbefehl führt die Python-Service-Main aus. Beispielhaft zeigt der Dockerfile-Auszug des Risk-Manager-Dienstes die Erstellung eines Users und einen Healthcheck-Befehl:

RUN useradd \-m \-u 1000 riskuser && chown \-R riskuser:riskuser /app    
USER riskuser    
HEALTHCHECK \--interval=30s \--timeout=3s \--retries=3 \\    
    CMD curl \-f http://localhost:8002/health || exit 1    
EXPOSE 8002    
CMD \["python", "-u", "service.py"\]  

*Quelle: Risk-Manager Dockerfile[\[23\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/backoffice/services/risk_manager/Dockerfile#L14-L22).*

**docker-compose.yml:** In der Compose-Datei sind alle Container und deren Konfiguration vermerkt. Zentral ist das **Zusammenspiel der Services**: z. B. startet der bot\_ws (WebSocket-Datenfeed) Container erst nach Redis[\[24\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L112-L119); die signal\_engine (Signal-Engine) startet nach Redis *und* dem Datenfeed[\[11\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L178-L186); der risk\_manager wartet auf Redis und die Signal-Engine[\[25\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L206-L214); die execution\_service hängt von Redis, Risk-Manager *und* Datenbank ab[\[20\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L236-L244). Diese Staffelung stellt sicher, dass bei einem Neustart jeder Dienst seine benötigten Gegenstellen vorfindet. Compose verwaltet auch gemeinsame **Netzwerke** (hier ein Bridge-Netz cdb\_network für internen Traffic[\[26\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L24-L27)[\[27\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L252-L255)) und **Volumes** (für persistente Redis-/Postgres-Daten[\[28\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L16-L19)[\[29\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L36-L40)). Die Ports der Services werden meist 1:1 an den Host gemappt (8000/8001/8002/etc.), während interne Verbindungen über den Service-Namen laufen (z. B. redis:6379).

## 3\. Architekturüberblick (Microservices & Event-Bus)

Claire de Binaire folgt einer **Microservice-Architektur** mit entkoppelten, ereignisgesteuerten Komponenten[\[30\]]. Gemäß *ARCHITEKTUR.md* sind folgende Haupt-Services definiert:

* **Datenfeed / Ingestion-Service:** Bezieht in Echtzeit Marktdaten von MEXC (WebSocket-Streams für Kurse/Orderbuch, REST für periodische Updates), normalisiert die Daten und publiziert sie als **MarketData-Events** auf dem Message-Bus[\[31\]]. (Im aktuellen Setup entspricht dies dem bot\_ws Container, der z. B. Top-5 Märkte streamt.)

* **Strategie-Engine (Signal-Generator):** Subskribiert die Marktdaten und berechnet kontinuierlich definierte **Indikatoren** (Momentum, Volumen-Spikes, Orderbuch-Imbalance etc.). Sobald die Regeln ein Handelssignal auslösen (Kauf/Verkauf inkl. Begründung), wird ein **Signal-Event** auf dem Bus publiziert[\[32\]]. (Beispiel: Wenn Preis in 15 min \>3% steigt *und* Volumen-Kriterium erfüllt ist, generiert die Engine ein BUY-Signal[\[33\]][\[34\]].)

* **Risikomanager:** Empfängt neue Signal-Events als **Safety-Layer** vor jeder Ausführung. Er prüft mehrstufig alle vordefinierten Limits – z. B. maximale Positionsgröße pro Trade, Gesamt-Exposition aller offenen Trades, Tagesverlust-Limit, Stop-Loss-Grenzen sowie Auffälligkeiten im Markt[\[35\]][\[36\]]. Ist das Signal *konform*, publiziert der Risikomanager ein **Order-Event** (Freigabe zur Ausführung) auf dem Bus; überschreitet das Signal ein Limit, wird es **blockiert** und stattdessen ein **Alert-Event** (Warnung) erzeugt[\[37\]]. Außerdem überwacht dieser Service globale **Circuit-Breaker**: Bei z. B. ≥5% Tagesverlust stoppt er den Handel komplett und löst einen Alarm aus[\[38\]][\[39\]].

* **Execution-Service:** Hört auf freigegebene Order-Events und führt die Trades an der Börse aus (über die MEXC-API, z. B. mittels CCXT-Bibliothek)[\[40\]]. Nach Orderplatzierung verarbeitet der Service das Ergebnis – ob Ausführung (Fill) oder Fehler – und publiziert ein **OrderResult-Event** zurück auf den Bus[\[41\]]. Damit werden alle beteiligten Module informiert (für Trade-Buchung, Risikoupdate, Benachrichtigung). Der Execution-Service kümmert sich um robuste Durchführung: z. B. Wiederholungsversuche bei Timeouts und Idempotenz (Vermeidung von Doppelorders durch eindeutige client\_id)[\[41\]].

* **Persistenz-Service (Signal-Writer):** Dieser optionale Service (teils auch in die anderen integriert) sorgt für das **Persistieren wichtiger Ereignisse** in der Datenbank. Er kann relevante Events vom Bus abonnieren (Signals, Orders, Trades, Alerts) und schreibt sie in die entsprechenden Tabellen[\[42\]]. So entsteht ein Audit-Log aller Aktivitäten. In der aktuellen Implementierung werden z. B. alle generierten Signale, ausgeführten Trades und Risk-Entscheidungen gespeichert (siehe Abschnitt *Datenbank*).

* **Benachrichtigungs-Service:** Wartet auf Alert-Events oder wichtige Trade-Events und versendet **Push-Benachrichtigungen** an den Nutzer[\[43\]]. Kritische Meldungen (z. B. Not-Stopp ausgelöst, Order abgelehnt) werden sofort als Push geschickt, weniger dringende Infos nur im Dashboard angezeigt. (Dieser Service ist konzeptionell vorgesehen – derzeit können Alerts z. B. via Web-Push im UI oder logischerweise via Telegram erfolgen, wobei Telegram laut Konzept deprecated ist[\[10\]].)

* **Dashboard / UI-Service:** Stellt eine Web-Oberfläche bereit, um den **Echtzeit-Status** des Bots einzusehen und ggf. Aktionen manuell durchzuführen. Das Dashboard (z. B. Prototyp als Streamlit-App) zeigt offene Positionen, P\&L, letzte Signale/Trades, Risk-Alerts etc. an[\[44\]]. Es abonniert dafür die Bus-Events oder fragt periodisch die Datenbank. Zudem bietet das UI Kontrollfunktionen wie einen **“Not-Aus”**\-Schalter, um alle Handelsaktivitäten sofort zu stoppen[\[45\]]. (Im MVP ist das UI optional und kann später hinzugefügt werden.)

Alle diese Services kommunizieren **asynchron über den Message-Bus** (typischerweise Redis Pub/Sub) nach dem **Publish/Subscribe-Muster**[\[30\]]. Dadurch sind sie lose gekoppelt und unabhängig deploybar – ein Dienstausfall legt nicht das Gesamtsystem lahm, sondern Nachrichten stauen sich höchstens im Bus und der Dienst kann neu starten, ohne Zustandsverlust[\[46\]].

**Event-getriebene Kommunikation:** Die zentrale Rolle spielt der Redis-Bus mit definierten **Topics** (Kanälen). Die wichtigsten Topics und ihre Publisher/Subscriber sind in der folgenden Tabelle dargestellt (vgl. ARCHITEKTUR.md):

| Topic | Publisher | Subscriber | Inhalt (Kurz) |
| :---- | :---- | :---- | :---- |
| market\_data | Datenfeed-Service | Strategie-Engine, UI | Marktdaten (Preis, Volumen, Symbol, etc.) |
| signals | Strategie-Engine | Risikomanager | Handelssignal (Symbol, Richtung, Konfidenz, Grund) |
| orders | Risikomanager (Freigabe) | Execution-Service | Order-Anforderung (Symbol, Side, Menge, ggf. SL/TP) |
| order\_result | Execution-Service | Risikomanager, UI, Notify, Persistenz | Ausführungsergebnis (Order-ID, Status, Preis, Fills, Fehler) |
| alerts | Risk/Execution/Monitoring | Notify-Service, UI, Persistenz | Alarmmeldung (Level, Code, Nachricht, Kontext) |
| health | *alle Dienste* | Monitoring/UI | Health-Status der Dienste (Name, Status, Zeit) |

*Quelle: Topics gemäß Architektur[\[47\]][\[48\]].*

Diese **Message-Bus-Topologie** (hier auf Redis umgesetzt) ermöglicht einen entkoppelten, skalierbaren Event-Flow. Jeder Service hört nur auf die für ihn relevanten Events und ignoriert andere. Neue Komponenten (z. B. ein ML-basiertes Modul) können einfach durch Subscriben/Publizieren zusätzlicher Topics integriert werden, ohne dass bestehende Komponenten geändert werden müssen.

**Start-Reihenfolge der Dienste:** Beim Neustart des gesamten Systems ist die richtige Sequenz wichtig, damit kein Dienst ins Leere läuft. Zuerst müssen die **Infrastruktur-Services** verfügbar sein: **Redis** (Pub/Sub-Bus) und die **PostgreSQL-Datenbank**. Erst danach sollten die anwendungsbezogenen Container hochgefahren werden. Praxisgerecht übernimmt docker-compose dies via Abhängigkeiten: So startet cdb\_signal (Signal-Engine) erst, wenn Redis läuft und der Datenfeed (cdb\_ws) Daten liefert[\[11\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L178-L186). Der Risk-Manager wartet auf die Signal-Engine[\[25\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L206-L214), und der Execution-Service wiederum auf den Risk-Manager *und* die Datenbank[\[20\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L236-L244). Dieses gestaffelte Hochfahren stellt sicher, dass z. B. die Signal-Engine beim Start direkt auf den Redis-Bus verbinden kann und auch bereits Marktdaten-Events vorfindet, oder dass der Execution-Service eine Datenbankverbindung herstellen kann, weil Postgres bereit ist. Sollte ein Dienst dennoch zu früh gestartet sein (etwa Redis Verzögerung), besitzen die Services Wiederholungs- bzw. Backoff-Logik, um die Verbindung erneut zu versuchen[\[49\]][\[50\]] (z. B. reconnect beim WebSocket-Datenfeed). Insgesamt gilt: **Redis und DB zuerst**, dann *Datenfeed → Strategie → Risiko → Execution → optionale UI/Notify*.

## 4\. Datenbank (PostgreSQL Setup & Schema)

Für Persistenz und Nachvollziehbarkeit betreibt Claire de Binaire eine **PostgreSQL**\-Datenbank. Das SQL-Schema ist in der Datei *DATABASE\_SCHEMA.sql* festgelegt und wird beim Neuaufsetzen automatisch angewendet (durch Mounten der SQL-Datei ins Postgres-Container-Initdir[\[19\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L38-L44)). Wichtig: Vor dem ersten Start müssen die in .env definierten DB-Zugangsdaten stimmen, damit der Container die DB erstellen kann (POSTGRES\_USER, POSTGRES\_PASSWORD, POSTGRES\_DB[\[8\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L32-L40)). Der Datenbankname ist standardmäßig **claire\_de\_binare** (ohne Accent)[\[51\]] – dieser muss konsistent verwendet werden.

Nach dem Start enthält die Datenbank das Schema mit allen notwendigen Tabellen und ggf. Basisdaten. Die wichtigsten Tabellen aus *DATABASE\_SCHEMA.sql* sind:

* **signals** – Enthält alle generierten **Trading-Signale** der Strategie-Engine[\[52\]]. Pro Eintrag: fortlaufende ID, Symbol, Side (BUY/SELL), Confidence (Konfidenzwert 0–1), Reason (Begründungstext), Preis zum Signalzeitpunkt, Prozentänderung, Volumen sowie Zeitstempel. Indexe bestehen u.a. auf Symbol und Timestamp für schnelle Abfragen.

* **trades** – Beinhaltet ausgeführte **Trades** (Einstiege/Ausstiege)[\[53\]]. Verknüpft ggf. auf das Signal (signal\_id), enthält Menge, Entry/Exit-Preise, PnL (Profit/Loss absolut und %), Status (OPEN/CLOSED), zugeordnete Order-IDs usw. Hier werden alle abgeschlossenen Trades zu Audit-Zwecken archiviert.

* **risk\_events** – Protokolliert Entscheidungen des **Risikomanagers**[\[54\]]. Zum Beispiel wenn ein Signal geblockt wurde (blocked\_order=true) oder ein Circuit Breaker gegriffen hat. Enthält Feld severity (INFO/WARNING/CRITICAL) und eine Beschreibung des Ereignisses (z. B. *“Tagesverlust-Limit überschritten – Handel gestoppt”*).

* **orders** – Hält die Historie aller **Order-Anfragen** und deren Status[\[55\]] (PENDING, FILLED, PARTIALLY\_FILLED, CANCELLED, REJECTED). Hier werden auch ggf. Exchange-spezifische IDs, Zeitstempel der Orderaufgabe und Ausführung etc. gespeichert. Damit lässt sich jeder Order-Lebenszyklus nachvollziehen.

* **Weitere Tabellen:** positions für aktuell offene Positionen (für die Berechnung der Gesamt-Exposition)[\[56\]], balances für regelmäßige Kapital-Snapshots (Equity, Margin, PnL)[\[57\]], health\_checks für periodische Service-Health-Status[\[58\]], metrics für Performance-Metriken[\[59\]] (z. B. durchschnittliche Signal-Konfidenz, Verarbeitungszeiten) sowie strategy\_params zur Historisierung von Strategie-Parameteränderungen[\[60\]].

Beim erstmaligen Aufsetzen werden durch das Schema-Skript auch einige **Initialdaten** eingetragen – z. B. Standard-Parameter in strategy\_params (Momentum-Schwelle, max. Drawdown etc.)[\[61\]] – sowie Berechtigungen gesetzt. So wird ein DB-Benutzer (z. B. „claire“ bzw. der in POSTGRES\_USER gesetzte User) berechtigt, die Tabellen zu selektieren und zu verändern[\[62\]]. Außerdem wird eine schema\_version Tabelle angelegt, in der die Schema-Version („1.0“) vermerkt ist[\[63\]]. Für zukünftige Änderungen könnten hier Migrationen versioniert werden.

**Migration/Updates:** Sollte das System neu aufgesetzt werden, aber eine bestehende Datenbank mit älteren Daten vorhanden sein, ist darauf zu achten, dass das Schema kompatibel ist. Im Zweifel können Migrationen erforderlich sein, um alte Tabellenversionen an das neue Schema anzupassen (dies würde über Erhöhung der schema\_version und separate Migration-Skripts passieren). Im vorliegenden Schema 1.0 sind jedoch alle oben genannten Tabellen frisch anzulegen, ein Neuaufsetzen mit leerer DB ist daher unkompliziert.

**Persistierte Signale & Events:** Alle wichtigen Events des Bots werden in der DB persistiert, um **Transparenz und Auditierbarkeit** zu gewährleisten. Beim Neuaufsetzen auf einem frischen Server sollten vorhandene historische Daten (Signals, Trades etc.) nach Möglichkeit aus Backups wiederhergestellt werden, um den fortlaufenden Betrieb mit Historie zu ermöglichen. Andernfalls startet das System mit leeren Tabellen – was funktional kein Problem ist (der Bot kann auch ohne historische Daten handeln), aber man verliert die Bezugswerte für z. B. Tages-Drawdown-Berechnung, offene Positionen etc. Im Abschnitt *Sicherheit & Recovery* sind Backup/Recovery-Prozesse erläutert, um persistierte Events zu sichern. Kurz gesagt: **Vor dem Neuaufsetzen immer ein Backup der DB ziehen**, damit keine Signale/Trades verloren gehen.

## 5\. Event-Handling (Event-Bus & Subscriptions)

Die **ereignisgetriebene Kommunikation** erfolgt über den zentralen **Message-Bus (Redis)**. Alle Services sind darauf ausgelegt, bestimmte Topics zu **subscriben** (abonnierten) und darauf Ereignisse zu **publizieren**, gemäß ihrer Rolle. Die Integration ist im Code typischerweise über die Redis-Pub/Sub-API realisiert (z. B. via redis-py Library). Jedes Event wird als JSON-Objekt verschickt, oftmals validiert durch ein gemeinsames Schema (siehe EVENT\_SCHEMA.json). Dieses JSON-Schema definiert die erwarteten Felder und Typen pro Event-Typ, was Konsistenz sicherstellt – z. B. ein Signal-Event muss type \= "signal", ein Symbol, Timestamp, side (BUY/SELL) und confidence 0–1 enthalten[\[64\]]. Solche formalen Schemabeschreibungen können genutzt werden, um Eingaben früh zu prüfen und Fehlformate abzufangen.

Im laufenden Betrieb fungiert Redis als **verteilter Event-Bus**: Ein Publisher schreibt z. B. eine neue Nachricht auf Topic "signals" – Redis leitet diese sofort an alle Services weiter, die "signals" abonniert haben. Unten eine Zusammenfassung, welche Services welche Topics bearbeiten (siehe auch Tabelle in Abschnitt 3):

* **Topic market\_data:** Publiziert vom Datenfeed-Service mit den neuesten Marktdaten (z. B. Preisaktualisierungen). Abonniert von der Strategie-Engine (zur Signalberechnung) und ggf. vom Dashboard (für Charts)[\[65\]].

* **Topic signals:** Publiziert von der Strategie-Engine, sobald ein neues Handelssignal erkannt wurde. Nur der Risikomanager subscribed auf signals, da er als nächstes jeden Signal verarbeitet[\[65\]].

* **Topic orders:** Publiziert vom Risikomanager, wenn ein Signal freigegeben wurde (Order-Anforderung). Nur der Execution-Service abonniert orders und führt diese Order dann aus[\[66\]]. (Nicht freigegebene Signale erzeugen stattdessen einen Alert, siehe dort.)

* **Topic order\_result:** Publiziert vom Execution-Service nach Ausführung einer Order – enthält entweder die Bestätigung eines Trades oder eine Fehlermeldung[\[67\]]. Abonniert vom Risikomanager (zur Kenntnisnahme des Ergebnisses, z. B. für PnL-Berechnung oder Fehlermeldung), vom Benachrichtigungs-Service (um z. B. *Trade ausgeführt* Push zu senden) und vom UI (zur Aktualisierung der Oberfläche)[\[68\]]. Auch ein Persistenz-Service würde hier mitlauschen, um Trades in die DB zu schreiben.

* **Topic alerts:** Publiziert von verschiedenen Stellen, insbesondere dem Risikomanager (wenn er ein Signal blockiert oder einen globalen Stopp auslöst) oder vom Execution-Service (bei kritischen Fehlern). Abonniert vom Notify-Service und UI, die solche Alerts dem Benutzer anzeigen[\[69\]]. Auch hier kann Persistenz die Alerts loggen.

* **Topic health:** Publiziert von *jedem* Service in regelmäßigen Abständen oder auf Anfrage, um den eigenen Gesundheitsstatus zu melden. Abonniert z. B. vom Dashboard oder einem Monitoring-Service, um den Gesamtzustand aller Dienste zu überwachen[\[70\]]. Im Compose-Setup erfolgt Health-Checking allerdings primär durch Docker-Mechanismen (siehe Healthcheck in Dockerfile/Compose).

Die Event-Nachrichten selbst sind JSON-Strukturen mit festgelegten Feldern. Ein **Beispiel**: Ein Signal-Event könnte wie folgt aussehen:

{  
  "type": "signal",  
  "symbol": "BTC\_USDT",  
  "timestamp": 1696789260,  
  "side": "BUY",  
  "confidence": 0.85,  
  "reason": "Momentum-Kaufsignal (+5%/15min, hohes Volumen)"  
}

Hier signalisiert die Strategie-Engine einen Kaufsignal für BTC/USDT mit 85% Confidence und nennt als Grund den Momentum-Anstieg. Der Risikomanager würde dieses Event aus dem Redis-Stream lesen und entsprechend reagieren. Ähnlich standardisiert sind Order-Events (type: "order" mit Symbol, side, quantity, etc.), OrderResult-Events (status: FILLED/ERROR usw.) und Alerts (level: INFO/WARNING/CRITICAL mit Code und Message)[\[71\]].

**Implementierungsdetails:** In jedem Service lädt die Konfigurationsroutine die relevanten Bus-Parameter aus den Environment-Variablen (z. B. REDIS\_HOST, REDIS\_PORT, REDIS\_PASSWORD) – im Standard sind Host "redis" und Port 6379 gesetzt[\[7\]], Passwort muss aus .env kommen. Die Services stellen beim Start die Verbindung zu Redis her. Gelingt das nicht (Redis noch nicht bereit), wird meist in Intervallen ein Retry unternommen, wie oben erwähnt. Sobald verbunden, führen die Services ein **Subscribe** auf ihre Topics durch (bspw. Strategie abonniert market\_data, Risk abonniert signals usw.) und lauschen in separaten Threads oder Async-Callbacks auf neue Events. Beim Eintreffen eines Events wird dieses deserialisiert (JSON \-\> Objekt) und der jeweilige **Event-Handler** im Service greift die Daten auf (z. B. Risiko prüft Limits bei Signal, Execution führt Order bei Order-Event aus). Publizieren wiederum erfolgt nach Bearbeitung analog: der Service serialisiert das Event-Objekt zu JSON und pusht es auf den Redis-Kanal.

Durch diese Architektur sind die Services entkoppelt: Die Kommunikation ist **asynchron** und erfolgt in **Echtzeit**. Sollte ein Service ausfallen, puffert Redis die Nachrichten nicht (Pub/Sub verteilt nur live), aber dank der kurzen Abfolgen (Marktdaten alle Sekunde, Signale alle paar Minuten) ist ein Wiederverbinden unproblematisch – verpasste Events sind entweder nicht kritisch oder können durch erneute Marktdaten schnell nachgeliefert werden. Für wichtige Events könnte man Redis Streams oder eine Message-Queue mit Persistenz einsetzen (in Zukunft evtl. NATS, RabbitMQ, Kafka), aber im aktuellen Setup genügt der Redis Pub/Sub (MVP-Ansatz)[\[30\]][\[49\]].

Zusammengefasst: **Der Event-Bus nach dem Pub/Sub-Prinzip ist das Rückgrat der Systemkommunikation.** Das EVENT\_SCHEMA.json stellt sicher, dass alle Services dieselbe Sprache sprechen, und in ARCHITEKTUR.md bzw. obiger Tabelle ist klar dokumentiert, welcher Dienst welche Events produziert oder konsumiert – ein essenzielles Nachschlagewerk beim Neuaufsetzen, um nichts zu vergessen.

## 6\. Servicespezifikationen (Beispiele: Strategy, Risk, Signal-Writer, Execution)

In diesem Abschnitt werden exemplarisch einige zentrale Services im Detail beschrieben – inklusive Konfiguration, Ablauf und wie sie dem allgemeinen Service-Template entsprechen. Jeder Service folgt dem gleichen Grundaufbau (siehe *SERVICE\_TEMPLATE.md*): ein eigenes Verzeichnis mit service.py (Hauptlogik), config.py (Konfigurationsladen von ENV), optionalen Hilfsmodulen (models.py für Datenklassen, etc.) und einem README[\[72\]]. Alle Services implementieren bestimmte Pflichtfunktionen: einen **HTTP-Healthcheck** (/health Endpoint), **strukturiertes Logging** (JSON-Format Logs), **Graceful Shutdown** via Signal-Handler und **Konfigurationsvalidierung** beim Start[\[73\]]. Dadurch verhalten sich die Services konsistent und sind im Betrieb leicht zu überwachen.

**Strategie-Engine (Signal-Generator):** Dieser Service verantwortet die **Handelsstrategie**. Er liest kontinuierlich Marktdaten vom market\_data Topic (abonniert z.B. auf Kurse von BTC/USDT, ETH/USDT etc.) und berechnet definierte Regeln/Indikatoren. In der aktuellen Implementierung handelt es sich um eine einfache **Momentum-Strategie**: Es wird z. B. geprüft, ob der Preis eines Coins in den letzten *LOOKBACK\_MIN* Minuten um mehr als einen Schwellwert X% gestiegen/gesunken ist und ob das Volumen über einem Minimum liegt. Ist die Bedingung erfüllt, generiert die Strategie ein entsprechendes Kauf- oder Verkaufssignal. Standardmäßig ist die **Schwelle 3%** Preisänderung bei mindestens **100k Volumen**, was dann eine Confidence-Berechnung triggert[\[33\]][\[74\]]. Die Strategie-Engine erstellt ein Signal-Objekt (siehe Event oben) und veröffentlicht es auf dem signals Kanal.

Konfigurierbar ist das Verhalten über ENV-Variablen: z. B. SIGNAL\_THRESHOLD\_PCT (Momentum-Schwelle, Default 3.0) und SIGNAL\_MIN\_VOLUME (Mindestvolumen)[\[74\]]. Diese können in der .env angepasst werden, um die Empfindlichkeit der Strategie zu steuern. Die Engine loggt ihre Aktionen, z.B. *“Subscribed to Topic: market\_data”* und bei Start die gesetzten Parameter[\[75\]]. Sie bietet zudem HTTP-Endpoints: /health (einfacher Ok-Check), /status (Status/Statistik der Signals, z. B. Anzahl generierter Signale, letztes Signal)[\[76\]], /metrics (Prometheus-Metriken, falls integriert). Dies hilft beim Monitoring und Testing. Die Signal-Engine läuft kontinuierlich, d.h. es gibt eine Schleife oder einen Redis-Listener, der auf neue Marktdaten reagiert, und zwischenzeitlich berechnet sie Indikatoren (z. B. alle 1 Minute).

**Risikomanager:** Der Risk-Service implementiert die **mehrlagige Risikokontrolle** des Systems. Er empfängt jedes Signal vom signals Topic und prüft nacheinander alle hinterlegten Regeln, bevor eine Order zum Exchange durchgewunken wird. Die konfigurierbaren **Schwellenwerte** sind in ENV definiert (teils mit Default): MAX\_POSITION\_PCT (max. Positionsgröße pro Trade, default 10% des Kapitals)[\[77\]], MAX\_EXPOSURE\_PCT (max. Gesamt-Exposition, default 50%)[\[78\]], STOP\_LOSS\_PCT (Stop-Loss pro Trade, default 2%)[\[79\]], MAX\_DAILY\_DRAWDOWN\_PCT (max. Tagesverlust, default 5%)[\[79\]]. Diese Werte sollte man vor Inbetriebnahme gemäß Risikoprofil setzen. Beim Eintreffen eines Signals durchläuft der Risikomanager folgende Logik (Pseudocode gekürzt aus *Risikomanagement-Logik.md*): zuerst globale Abbruchkriterien, dann trade-spezifische Limits[\[80\]][\[81\]]. In vereinfachter Form:

1. **Tagesverlust-Limit überschritten?** Wenn ja, **alle Trades stoppen** für den Tag (Circuit Breaker) – Signal wird verworfen, bestehende Positionen geschlossen, Alert *“Tagesverlust-Limit überschritten – Handel gestoppt”* wird publiziert[\[82\]][\[83\]].

2. **Anormale Marktbedingungen?** (z. B. Exchange nicht erreichbar, extreme Volatilität \>10% in 5min) – dann **Handel pausieren**, Signal verwerfen, Alert *“Trading ausgesetzt wegen Marktanomalie”*[\[84\]].

3. **Expositions-/Positionsanzahl-Limit?** Wenn bereits zu viele offene Positionen oder zu viel Kapital im Markt, wird das neue Signal **abgelehnt** und ein entsprechender Alert geloggt[\[85\]].

4. **Positionsgröße \> Max?** Wenn die vorgeschlagene Order größer als erlaubt, wird sie **beschnitten** auf das erlaubte Maximum[\[86\]]. D.h. der Risikomanager ändert die Quantity auf z. B. 10% des Kapitals und lässt das angepasste Signal passieren (optional mit Warn-Alert *“Signalgröße angepasst”*).

5. **Sonst:** Wenn all diese Checks bestanden sind, wird das Signal **freigegeben**[\[87\]]. Der Risikomanager erzeugt dann ein **Order-Event** auf dem Bus, das alle relevanten Orderdaten enthält (Symbol, Side, Größe, evtl. Stop-Loss).

Zusätzlich überwacht der Risikomanager laufend geöffnete Trades: sollte z. B. im Verlauf ein Trade einen Verlust \> Stop-Loss-PCT erreichen, wird ein Close-Event initiiert (Position sofort schließen)[\[83\]]. Ebenso, wenn der kumulative Tagesverlust über das Limit steigt, greift der Circuit Breaker jederzeit – nicht nur bei neuen Signalen[\[88\]]. Die Regeln sind hierarchisch priorisiert (Tagesverlust und extreme Bedingungen ganz oben)[\[89\]], sodass immer die gravierendste Schutzmaßnahme zuerst greift.

Der Risikomanager loggt alle Entscheidungen. Blockierte Signale resultieren in risk\_events\-DB-Einträgen (mit Beschreibung, z.B. *“Expositions-Limit erreicht – Signal verworfen”*) und Alerts. Freigegebene Signale sieht man indirekt durch die nachfolgenden Trades. Auch dieser Service bietet HTTP-Status (z. B. Anzahl erhaltene Signale, genehmigte vs. abgelehnte Orders)[\[90\]] und Health-Check. Beim Start loggt er die gesetzten Limits (*“Max Position: 10.0%”* etc.)[\[91\]], damit klar ist, mit welchen Parametern er arbeitet.

**Execution-Service:** Diese Komponente führt die **Orderausführung** aus. Sie wartet auf orders Events, die vom Risikomanager kommen. Bei Eintreffen entpackt sie die Orderdaten und interagiert mit der **MEXC-Börsen API**, typischerweise über eine Bibliothek wie *CCXT*, welche gängige Methoden bereitstellt (z. B. create\_order(...)). In der aktuellen Phase war die Execution in Entwicklung; konzipiert ist, dass der Service sowohl Market-Orders als auch Limit/Stop je nach Bedarf platzieren kann. Wichtig: Die **API-Keys** müssen korrekt konfiguriert sein (MEXC\_API\_KEY/SECRET), und es sollte das **Testnet** oder ein beschränktes Konto verwendet werden, um Risiken zu minimieren.

Nach Absetzen der Order wartet der Execution-Service auf die Bestätigung von der Börse (bzw. erhält über WebSocket oder API-Rückmeldung den Orderstatus). Daraus generiert er dann ein **order\_result** Event: im Erfolgsfall mit Status "FILLED" und Details (gefüllte Menge, Preis)[\[92\]], im Fehlerfall mit Status "ERROR"/"REJECTED" und einer Fehlermeldung. Dieses Event publiziert er auf dem Bus, damit alle anderen Module es verarbeiten. Beispielsweise erkennt der Risikomanager daran, dass eine Position nun offen ist oder dass ein Trade fehlgeschlagen ist und loggt ggf. einen Risk-Event. Das UI würde den neuen Trade anzeigen oder eine Fehlermeldung visualisieren.

Der Execution-Service muss robust sein gegenüber **Netzwerkausfällen oder API-Errors**. Implementiert ist vorgesehen: falls keine Antwort innerhalb eines Timeouts kommt, Wiederholungsversuche (mit Backoff) zu senden[\[93\]]. Dabei hilft Idempotenz: jedem Order-Event wird vorab ein eindeutiger client\_id mitgegeben[\[94\]], sodass die Execution erkennen kann, ob ein Retry dieselbe Order betrifft und nicht doppelt ausgeführt werden darf. Die Execution-Komponente schreibt erfolgreiche Trades in die Datenbank (Tabelle trades) und aktualisiert ggf. positions und balances. In Compose ist sie so konfiguriert, dass sie auf Postgres wartet[\[20\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L236-L244), damit die DB-Verbindung steht. Logs des Execution-Services enthalten u.a. Order-Requests, Rückmeldungen der Börse und etwaige Exception-Traces bei Fehlern. Auch hier gibt es einen /health Endpoint.

**Signal-Writer / Persistenz:** In der aktuellen Architektur gibt es (noch) keinen separaten Persistenz-Container; stattdessen übernehmen die bestehenden Services die Aufgabe, relevante Daten in die DB zu schreiben. So kann z. B. der Signal-Generator jeden generierten Signal in die signals\-Tabelle einfügen, und der Execution-Service jeden ausgeführten Trade in trades. Der Risk-Manager könnte alle Alerts/Risk-Events in risk\_events loggen. Dieser Ansatz wurde wahrscheinlich für das MVP gewählt, um Komplexität zu sparen (kein separater Service nötig). Perspektivisch ist aber ein **dedizierter Persistenz-Service** sinnvoll, wie in der Architektur vorgesehen[\[42\]]. Dieser würde sich auf Topics wie signals, order\_result, alerts subscriben und alle Ereignisse parallel in der DB abspeichern (als Audit-Trail). Beim Neuaufsetzen ist es wichtig zu wissen: **Datenpersistenz läuft über die DB** – es gibt keine andere Statefulness in den Services selbst. Wenn also die DB intakt aus einem Backup wiederhergestellt wird und die Services neu starten, haben sie den vollen Verlauf (z. B. offene Positionen können aus positions gelesen werden). Falls die DB verloren ginge, startet der Bot “frisch” – was man nur in Ausnahmefällen möchte.

Alle Services orientieren sich am gemeinsamen **Service-Template** (einheitlicher Aufbau und Grundfunktionen)[\[73\]], was den Betrieb vereinfacht: z. B. reagiert jeder Dienst auf SIGTERM mit einem sauberen Shutdown (Connection Close, Thread Stop) gemäß implementiertem Signal-Handler, und jeder Dienst nutzt strukturiertes Logging über die Python logging Bibliothek (Format im JSON-Stil). Dadurch sind Logs zentral auswertbar. Ebenso prüfen die Services bei Start die wichtigsten ENV-Variablen – z. B. ob Redis-Host gesetzt, Port gültig, Limits sinnvoll – und werfen Fehler, falls Konfigurationsfehler vorliegen[\[95\]][\[96\]]. Dies verhindert häufige Fehlkonfigurationen beim Deployment.

## 7\. Tests und Debugging (End-to-End Tests & Diagnose)

Nach dem Aufsetzen des Systems sollte ein **End-to-End-Test** durchgeführt werden, um sicherzustellen, dass alle Komponenten ordnungsgemäß funktionieren. Hierfür liegt die Anleitung *END\_TO\_END\_TEST\_GUIDE.md* vor, die Schritt für Schritt das Vorgehen beschreibt. Wichtige Punkte daraus:

* **Container-Start prüfen:** Zunächst wird via docker-compose up \-d das Gesamtsystem gestartet. Erwartet wird, dass alle definierten Container hochfahren und den Status "healthy" erreichen[\[97\]]. Konkret sollten mindestens Redis, PostgreSQL, Signal-Engine und Risk-Manager laufen (im Entwicklungsstand ggf. plus der Datenfeed cdb\_ws). In Docker Desktop kann man dies visuell kontrollieren; alternativ per docker ps.

* **Logs beobachten:** Für jeden Service sollten die Logs keine Fehler anzeigen. Die Test-Anleitung empfiehlt, in Docker Desktop oder via docker logs \<container\> die Ausgaben zu verfolgen[\[98\]]. Typische Meldungen für einen erfolgreichen Start sind z. B.:

* *Signal-Engine:* „Redis verbunden: redis:6379“, „Subscribed zu Topic: market\_data“, „🚀 Signal-Engine gestartet (Schwelle: 3.0%)“[\[75\]].

* *Risk-Manager:* „Redis verbunden: redis:6379“, „Subscribed zu Topic: signals“, „🚀 Risk-Manager gestartet (Max Position: 10.0% ...)“[\[91\]].

* Datenfeed (cdb\_ws): Meldet Verbindung zur Börse und dass MarketData-Events publiziert werden (z. B. Top Movers alle X Sekunden).  
  Fehlermeldungen (ERROR im Log) dürfen **nicht** auftauchen[\[99\]]. Falls doch, müssen sie untersucht werden (z. B. Redis-Verbindung fehlgeschlagen, weil falsches Passwort).

* **Health-Checks:** Als Nächstes ruft man die Health-URLs der Services ab (z. B. http://localhost:8001/health für Signal, 8002/health für Risk) – entweder im Browser, via Curl oder wie im Guide gezeigt mit PowerShells Invoke-WebRequest[\[100\]]. Erwartet wird jeweils ein JSON {"status":"ok", ...} mit HTTP 200[\[101\]]. Ein ausbleibendes OK deutet auf ein Service-Problem hin (dann Logs checken).

* **Redis-Events überprüfen:** Man kann in den Redis-Container reinschauen: docker exec \-it cdb\_redis redis-cli und dort MONITOR eingeben[\[102\]]. Damit sieht man alle Pub/Sub-Aktivitäten live. Im erfolgreichen Betrieb sollte im Sekundentakt ein PUBLISH "market\_data" ... auftauchen[\[103\]] (der Datenfeed sendet kontinuierlich Marktdaten). Zudem spätestens nach einigen Momenten erste PUBLISH "signals" ... und ggf. orders wenn Signale freigegeben wurden. Das zeigt, dass die gesamte Pipeline vom Datenfeed über Strategie zu Risk funktioniert. Anschließend CTRL+C in Redis CLI, um den Monitor zu verlassen.

* **Datenbankinhalte prüfen:** Mit docker exec \-it cdb\_postgres psql \-U \<USER\> \-d claire\_de\_binare kann man sich auf die DB schalten[\[104\]]. Dort lassen sich Abfragen durchführen, um zu sehen, ob Daten ankommen. Beispielsweise die Anzahl der Signals: SELECT COUNT(\*) FROM signals; – nach ein paar Minuten Laufzeit sollte \>0 herauskommen[\[105\]]. Oder man schaut die letzten Einträge an (SELECT \* FROM signals ORDER BY timestamp DESC LIMIT 5;). Die Anleitung gibt hier konkrete SQL-Beispiele, etwa um die letzten 5 Signale mit Zeitstempel anzuzeigen[\[106\]], oder Risk-Events und eine Zusammenfassung aller Kernzahlen (Anzahl Signale, Risk-Events, offene Trades, Gesamtorders)[\[107\]]. Diese Queries sollten Ergebnissen liefern (z. B. einige Signale und ggf. Risk-Events, falls Limits gerissen wurden). Stimmen die Zahlen nicht (z. B. 0 Signale trotz Marktdaten), stimmt etwas im vorherigen Schritt nicht.

* **Service-Metriken:** Die Guide schlägt ferner vor, die /status Endpoints abzufragen (sofern implementiert)[\[108\]][\[90\]]. Dort sieht man z. B. wie viele Signale generiert und wie viele Orders genehmigt/blockiert wurden – ein direkter Indikator, ob die Strategie und der Risikomanager sinnvoll arbeiten. Beispielsweise könnte signals\_generated bei der Signal-Engine \>0 sein und orders\_approved beim Risk-Manager ebenfalls \>0 nach einiger Laufzeit[\[109\]].

Am Ende definiert der End-to-End-Test eine **Checkliste von Erfolgskriterien** (7/7 müssen erfüllt sein)[\[110\]]:  
1\. Alle Container laufen und sind *healthy*.  
2\. Health-Checks der Services antworten mit 200 OK.  
3\. Redis antwortet auf PING (Verbindung okay).  
4\. PostgreSQL: notwendige Rollen/Benutzer vorhanden (Setup korrekt).  
5\. PostgreSQL: Verbindung aus Container erfolgreich.  
6\. Signal-Engine: Keine Errors, Health ok.  
7\. Risk-Manager: Keine Errors, Health ok.

Wenn all das erfüllt ist, gilt der Test als bestanden[\[111\]] – das System ist dann **vollständig einsatzbereit** (in der Doku beispielhaft am 21.10.2025 so vermerkt).

**Troubleshooting & Debugging:** Tritt irgendwo ein Problem auf, gibt es in den Dokumenten Hilfestellungen:

* Zuallererst sollte man die Container-Logs prüfen (docker logs \<name\>), da hier meist bereits ersichtlich ist, wo es hakt (z. B. Exception wegen fehlender Umgebungsvariable oder Verbindungsfehler).

* In *CODE\_CLEANUP\_AUDIT.md* und *TROUBLESHOOTING.md* finden sich Checklisten: z. B. ob die .env\-Datei korrekt ist (keine Duplikate, alle Passwörter konsistent)[\[112\]]. Ein docker-compose config Befehl kann Syntaxfehler in der Compose oder fehlende ENV anzeigen[\[113\]].

* Häufige Probleme beim Start: **Redis nicht erreichbar** – dann den Redis-Container (neu) starten[\[114\]]; **Port-Kollision** – wenn z. B. noch ein alter Prozess auf 8001 läuft, muss dieser beendet oder der Port geändert werden[\[114\]]; **fehlende ENV-Variablen** – dann .env überprüfen und korrekt befüllen[\[114\]].

* **Keine Marktdaten/Signale:** Prüfen, ob der Datenfeed läuft (docker logs cdb\_ws) und ob dieser erfolgreich auf Redis publiziert (siehe Redis MONITOR). Gegebenenfalls sicherstellen, dass die API-Keys gültig sind und das Netzwerk Zugriff auf MEXC hat.

* **Keine DB-Einträge:** Prüfen, ob die Services DB-Verbindungsdaten haben (docker exec cdb\_signal env | grep POSTGRES beispielsweise)[\[115\]]. Fehlt hier etwas, dann .env falsch oder der Service wurde ohne DB-Anbindung gebaut. Testhalber kann man auch manuell ein Signal in Redis stellen, um die Verarbeitungskette zu stimulieren (siehe Guide: mit redis-cli ein Test-Event auf market\_data publizieren)[\[116\]].

* **Performance/Delay:** Wenn z. B. Signale generiert werden, aber Execution spät reagiert, könnte die Bottleneck der Exchange API sein – hier sind ggf. Ratenlimits zu beachten. Logs mit Timestamp helfen, solche Lags zu identifizieren.

Generell sollte man im Fehlerfall zunächst die spezifischen Komponenten prüfen (oft ist es ein kleines Config-Detail). Die umfangreichen Dokumentationen (ARCHITEKTUR.md, End-to-End Guide, etc.) sind so gestaltet, dass sie für jedes Symptom mögliche Ursachen bereitstellen.

## 8\. Sicherheit und Recovery (Risiken, Secrets, Backup, Rollback)

Beim Neuaufsetzen des Servers sind einige **Sicherheitsaspekte** und **Wiederanlauf-Strategien** zu beachten, um einen sicheren, nahtlosen Betrieb zu gewährleisten:

**Risiken beim Neuaufsetzen:**  
\- *Konfigurationsfehler:* Ein großes Risiko ist, dass ENV-Secrets falsch eingegeben werden (z. B. vertippter API-Key, falsches DB-Passwort). Dies kann dazu führen, dass der Bot zwar startet, aber keine Trades ausführt oder keine Daten empfängt. Lösung: penible Überprüfung der .env gegen die Doku.  
\- *Datenverlust:* Wird der Server neu aufgesetzt ohne vorheriges Backup, können alle **persistierten Signale, Trades und Parameter** verloren gehen. Dadurch gehen wichtige Referenzen für Risikometriken (z. B. bisheriger Tagesverlust) verloren. Außerdem wären Audit-Logs weg, was **Transparenz** und Nachvollziehbarkeit beeinträchtigt. Daher immer **vor dem Neuaufsetzen Backups ziehen** (siehe unten).  
\- *Secrets-Leaks:* Während des Neuaufsetzens ist darauf zu achten, dass **Schlüssel und Passwörter** nicht in falsche Hände geraten. .env-Dateien sollen z. B. mittels restriktiver Dateirechte geschützt sein[\[4\]]. Im Idealfall liegen Secrets in einem Vault und werden zur Deployzeit injected. Kein Secret sollte im Klartext in ein Repository committet werden.  
\- *Unbeabsichtigte Withdrawals:* Sicherheitsprinzip ist „Sicherheit vor Profit“ – d.h. selbst wenn der Server kompromittiert würde, dürfen API-Keys keine Auszahlung erlauben[\[117\]]. Beim Neuaufsetzen stets API-Schlüssel ohne Withdraw-Rechte verwenden[\[4\]] und ggf. IP-Whitelist bei der Börse aktivieren. So minimiert man das finanzielle Risiko.  
\- *Ausfallrisiko:* Während der Neuinstallation steht der Bot ggf. kurz still. Wenn dies während volatiler Marktphasen passiert, könnten Chancen verpasst werden – das ist jedoch bewusst in Kauf zu nehmen gegenüber einem unsauberen Live-Wechsel. Wichtig ist eher, dass nach Wiederanlauf **alle Komponenten synchron** laufen, um Fehlentscheidungen zu vermeiden (z. B. Risk-Manager denkt, es gibt keine offenen Positionen, obwohl an der Börse noch welche offen sind). Hier muss man ggf. manuell verifizieren, dass beim Neustart die internen Daten (Datenbank) mit dem tatsächlichen Börsenstatus konsistent sind.

**Umgang mit Secrets:** Wie oben erwähnt, sollten Secrets (API Keys, Passwörter) **ausschließlich über Environment-Variablen** oder ein Secret-Management-Tool eingespeist werden[\[4\]]. In Docker-Compose können .env-Dateien benutzt werden, was bereits implementiert ist (env\_file: .env in allen relevanten Services[\[118\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L106-L114)[\[119\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L202-L210)). Nach dem Neuaufsetzen ist zu prüfen, dass die .env-Datei korrekt vorliegt. Sie sollte **nicht** Teil von Backups in Klartext sein (laut Backup-Anleitung wird .env explizit ausgenommen[\[120\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L44-L48)). Beim Recovery also daran denken, die .env manuell zu sichern/verifizieren.

Alle Container laufen mit reduzierten Rechten (non-root) und zusätzlichen Sicherheitsoptionen (z. B. no-new-privileges, read\_only Dateisystem in Compose)[\[121\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L216-L224)[\[122\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L246-L254). Diese Hardening-Maßnahmen reduzieren die Angriffsfläche. Trotzdem sollte das System nur in vertrauenswürdigen Netzwerken laufen und Firewalls die offenen Ports (8000-8003, 5432, 6379 etc.) absichern, vor allem wenn auf einem Cloud-Server.

**Backup-Strategie:** Für Betriebssicherheit und schnelle Wiederherstellung ist ein regelmäßiges Backup unverzichtbar. Im Projekt gibt es eine ausführliche *BACKUP\_ANLEITUNG.md*, die ein tägliches Vollbackup vorsieht. Zusammengefasst werden **jeden Tag um 3:00 Uhr** folgende Komponenten gesichert[\[123\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L30-L38)[\[124\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L50-L58):

1. *PostgreSQL-Datenbank:* Komplettes Dump aller Tabellen (Signals, Trades, Orders, Positions, Balances, Risk-Events, Metrics, Health-Checks, Strategy-Params)[\[125\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L32-L40) – so geht keine historische Trading-Information verloren.

2. *Redis-Snapshot:* Der aktuelle Redis-In-Memory-Store (der die momentanen Topics/Zustände hält) wird gesichert[\[126\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L38-L41). Dies ist zwar weniger kritisch (da nach Neustart Redis leer startet und das System trotzdem funktioniert), aber für Debugging oder Replay von zuletzt publizierten Events hilfreich.

3. *Projektverzeichnis:* Der gesamte Code und die Dokumentation (alles unter dem Repository, inkl. Dockerfiles, Compose, Skripte) werden archiviert[\[127\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L42-L48). Ausgenommen sind temporäre/vertrauliche Dinge wie Logs, \_\_pycache\_\_, node\_modules, .git und .env[\[120\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L44-L48). Damit ist gewährleistet, dass bei einem Serververlust der exakt gleiche Code wiederhergestellt werden kann – wichtig, falls lokale Änderungen vorgenommen wurden.

4. *Docker-Volumes:* Alle persistente Volumes der Container (Postgres-Datenfiles, Redis Dump, Prometheus TSDB, Grafana config) werden wegsichert[\[124\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L50-L58). Dies erlaubt notfalls auch eine punktgenaue Wiederherstellung des Zustands (z. B. DB-Files direkt zurückspielen statt nur SQL-Import).

5. *Logs:* Alle vorhandenen Logfiles werden als ZIP archiviert[\[128\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L56-L58), um im Nachhinein Fehlerursachen analysieren zu können oder ein Reporting der Aktivitäten zu haben.

Die Backup-Anleitung beschreibt, wo diese Backups liegen (z. B. unter C:\\Backups\\claire\_de\_binare\\ mit Ordnern pro Datum)[\[129\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L70-L78). Beim Neuaufsetzen **nach einem Crash** sollte man zunächst das letzte Vollbackup einspielen:

**Recovery/Restore:** Die Schritte zur Wiederherstellung sind im Backup-Dokument skizziert[\[130\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L94-L100): *(1)* alle laufenden Container stoppen, *(2)* den Postgres-Dump (.sql) zurück in die DB importieren, *(3)* den Redis RDB-Snapshot ins neue Redis-Verzeichnis legen (optional), *(4)* die Docker-Volumes (sofern im Backup als Tar/Zip) wiederherstellen, *(5)* die Container erneut starten, und *(6)* das System ausgiebig testen. Oft reicht es aber, einfach die DB mit dem Dump zu füllen, da darin alle wichtigen historischen Daten stecken. Redis-Inhalt kann man meist weglassen (der füllt sich wieder). Wichtig ist, dass nach dem Recovery die **Datenkonsistenz** geprüft wird – z. B. ob offene Trades in der DB zu real existierenden Positionen an der Börse passen. Gegebenenfalls muss man hier manuell nachjustieren (im Extremfall einen Trade schließen, falls die Software ihn als offen führt, die Börse aber nicht – oder umgekehrt).

**Rollback:** Falls ein Neuaufsetzen (z. B. mit einer neuen Version des Bots) fehlschlägt oder Probleme bereitet, sollte man vorbereitet sein, auf den vorherigen Stand zurückzurollen. Dazu bewährt es sich, **vor dem Upgrade** ein Backup zu haben (siehe oben). Ein Rollback bestünde dann darin, die alte Code-Version wieder zu deployen und die vor dem Upgrade gesicherten Daten zurückzuspielen. Dank Docker kann man auch versionierte Images nutzen: z. B. das alte Docker-Compose oder Tagged-Images der Services. Im Zweifel lässt sich auch nur die Datenbank rückspielen, falls das Code-Update unproblematisch war, aber z. B. falsche Berechnungen machte – so hat man den Stand vor dem Fehler wieder.

**Zusätzliche Sicherheitsmaßnahmen:** Gemäß Manifest legt Claire de Binaire mehr Wert auf Sicherheit als auf maximale Profitjagd[\[131\]]. Daher sind im Betrieb einige Mechanismen aktiv, die auch beim Neuaufsetzen zu berücksichtigen sind:

* Ein **Circuit-Breaker/Not-Aus** ist integraler Bestandteil – im UI gibt es einen Knopf, aber auch automatisch greift der Risk-Manager bei gefährlichen Situationen[\[132\]][\[133\]]. Nach einem Neustart sollte dieser Mechanismus unverändert aktiv sein (d.h. keine Neustart durchführen, um einen Crash-Loop nach Circuit-Breaker zu umgehen, ohne das Grundproblem zu lösen). Wenn z. B. Tagesverlust überschritten war und der Bot gestoppt wurde, sollte man bis zum nächsten Tag warten oder die Tagesverlust-Tracking zurücksetzen, bevor man neu startet.

* **Logs & Monitoring:** Die Sicherheit umfasst auch, dass Anomalien schnell erkannt werden. Nach Neuaufsetzen unbedingt die Logs beobachten (mindestens in den ersten Stunden Live-Betrieb) und sicherstellen, dass Monitoring-Tools wie Prometheus/Grafana laufen (im Compose enthalten)[\[134\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L53-L61)[\[135\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L73-L81). Grafana kann Alerts definieren, die bei bestimmten Events Alarm schlagen.

* **Benutzerzugriff:** Sofern das Dashboard/UI mit Authentifizierung ausgestattet ist (z. B. 2FA, wie geplant[\[136\]]), muss beim Neuaufsetzen die User-Config übernommen werden. Falls es keinen persistierten Userstore gibt (UI evtl. readonly mit Single-User), ist das weniger Thema.

Alles in allem ist ein Neuaufsetzen mit diesem Dokument und den vorhandenen Scripts gut machbar. Wichtig ist ein **sorgfältiges Vorgehen** – erst die Basisdienste, dann die Bot-Services starten; vorab Secrets kontrollieren; nachher Tests ausführen. Die vorhandenen Backup- und Sicherheitsrichtlinien sorgen dafür, dass auch im Fehlerfall kein großer Schaden entsteht (Daten und Geld bleiben sicher).

## 9\. Besonderheiten (ML-Modul, Shadow-Mode, essentielle Deliverables)

Zum Abschluss noch einige projektspezifische Besonderheiten, die beim Neuaufsetzen oder Betrieb bedacht werden sollten:

**ML-Modul im “Shadow-Mode”:** Claire de Binaire ist bislang strikt regelbasiert-deterministisch, hat aber perspektivisch ein Machine-Learning-Modul als Erweiterung vorgesehen. Dieses ML-Modul (ein *ML-basierter Signal-Advisor*) soll zunächst in einem **Shadow Mode** laufen – d.h. **parallel** zum eigentlichen Signalsystem, ohne direkt Trades auszulösen. Konkret bedeutet das: Der ML-Service (ggf. eigener Microservice) würde die gleichen Marktdaten bekommen und eigene **ML-Signale** generieren, diese aber auf einen separaten Topic, z. B. ml\_signals, publizieren[\[137\]]. Der Risk-Manager oder ein übergeordnetes Modul könnte diese ML-Signale zwar auswerten, aber nicht direkt ausführen, sondern höchstens zur Bestätigung oder Alarmierung nutzen. So kann man die Leistung des ML-Modells beobachten, ohne das deterministische Kernsystem zu gefährden.

Beim Neuaufsetzen muss man beachten, dass ein ML-Modul (falls bereits integriert) **zusätzliche Ressourcen** erfordert – z. B. ein geladenes ML-Modell, möglicherweise eine GPU oder spezielle Python-Dependencies (TensorFlow/PyTorch etc.). Diese müssen im Deployment-Stack berücksichtigt sein (Docker-Image mit ML-Library, evtl. größeres Memory). Im aktuellen Projektstadium ist das ML-Modul laut Roadmap optional und nicht aktiv im Trading-Prozess[\[137\]]. Sollte es zum Einsatz kommen, sind auch hier Transparenz und Nachvollziehbarkeit Pflicht: Entscheidungen des ML müssen geloggt und erklärbar sein. “Shadow-Mode” bedeutet auch, dass man **Metriken erhebt**, wie oft das ML-Modell zustimmt oder abweicht von der Regel-Engine, und diese Ergebnisse in Berichten dokumentiert. Es liegt ein Konzeptpapier vor, das genau diese Integration beleuchtet und Deliverables definiert (z. B. einen ausführlichen Bericht mit Entscheidungsgrundlagen, Modellvergleich etc.). Für den operativen Betrieb heißt das: Das ML-Modul darf **keine automatische Trade-Befugnis** haben, bevor nicht in solchen Berichten nachgewiesen wurde, dass es sicher und vorteilhaft ist – es bleibt im read-only Modus in der Produktion, bis ein Go entschieden wird. Dies entspricht dem Leitprinzip, dass die deterministische Nachvollziehbarkeit gewahrt bleiben muss, egal wie “smart” das ML-Modell ist[\[138\]][\[139\]].

**Essenzielle Deliverables für Betriebssicherheit & Transparenz:** Über die reine Codebasis hinaus lebt Claire de Binaire von umfangreicher Dokumentation und Auditierbarkeit. Einige Artefakte, die für einen sicheren, transparenten Betrieb und eine schnelle Wiederinbetriebnahme essenziell sind:

* **ARCHITEKTUR.md:** Das Architektur-Doc ist die *Single Source of Truth* für das Systemdesign[\[140\]]. Beim Neuaufsetzen dient es als Referenz für alle Komponenten, Schnittstellen, Env-Variablen und Healthchecks. Jede Änderung am System sollte hier nachvollzogen werden. Es gewährleistet, dass alle Teammitglieder und auch zukünftige Maintainer schnell verstehen, wie die Teile zusammenspielen.

* **EVENT\_SCHEMA.json:** Das formale JSON-Schema der Events stellt sicher, dass Produzenten und Konsumenten dieselben Datenformate nutzen. Es erhöht die Transparenz, weil es quasi die “Verträge” zwischen den Services dokumentiert. Beim Debugging kann man damit valide von invalide Events unterscheiden. Zudem unterstützt es die Auditierbarkeit: Man könnte eingehende und ausgehende Events gegen das Schema prüfen, um Fehler früh zu erkennen.

* **Risikomanagement-Dokumentation:** Eine klare Beschreibung aller Risikoregeln (wie in *Risikomanagement-Logik.md* und ARCHITEKTUR.md) ist für die **Betriebssicherheit** fundamental. So ist für jeden Eingriff des Bots definiert, warum er erfolgt. Diese Dokumente dienen intern als Referenz und extern ggf. als Nachweis gegenüber Dritten, dass kontrolliert und konservativ gehandelt wird. Änderungen an Risikoparametern sollten hier dokumentiert werden, um Transparenz zu wahren.

* **Logging & Audit-Trails:** Das System ist so gebaut, dass **jede Entscheidung erklärbar** ist – nicht nur durch Code, sondern durch Logs[\[141\]]. Die strukturierte Speicherung von Signalen, Entscheidungen und Trades in der DB ermöglicht es, im Nachhinein jeden Trade zu begründen („wegen Signal X mit Grund Y, geprüft gegen Limit Z“). Diese Audit-Trails sind ein deliverable in dem Sinne, dass sie jederzeit vorgezeigt werden können, um das Verhalten des Bots zu prüfen. Im Betrieb sollten regelmäßige Auswertungen der Logs/DB (z. B. wöchentliche Reports der Performance und Regel-Compliance) erfolgen, um frühzeitig Auffälligkeiten zu erkennen.

* **Backup- und Recovery-Prozesse:** Die oben erwähnten Backup-Skripte und Anleitungen sind ein essenzieller Bestandteil der Betriebsdokumentation. Sie stellen sicher, dass ein **Wiederanlauf** nach Ausfällen möglich ist, ohne Datenverlust. Das Vorhandensein getesteter Backup-Dateien und einer klaren Recovery-Doku (Schritt-für-Schritt) ist entscheidend, um im Ernstfall schnell reagieren zu können. Diese müssen gepflegt und aktuell gehalten werden (z. B. Anpassung falls neue Volumes/Services hinzukommen).

* **Testdokumentation (End-to-End Guide):** Ein weiterer wichtiger deliverable ist der vollständige End-to-End-Testplan. Er gewährleistet, dass nach jeder Neuinstallation oder Änderung das System auf Herz und Nieren geprüft wird. Für Betriebssicherheit ist es unerlässlich, einen solchen Validierungsprozess zu haben – er verhindert, dass ein fehlerhaft konfiguriertes System live geht.

* **Entscheidungs- und Änderungsprotokolle:** Im Projekt werden Architektur-Entscheidungen (ADR) und Änderungen dokumentiert (z. B. DECISION\_LOG.md, CHANGELOGs). Diese erhöhen die Transparenz für alle Beteiligten: Man kann nachvollziehen, warum z. B. von SQLite auf PostgreSQL gewechselt wurde, warum Telegram entfernt wurde (ADR-003) etc. Beim Neuaufsetzen kann man hier nachlesen, was aktuell gelten sollte.

Abschließend lässt sich sagen, dass Claire de Binaire großen Wert auf **technische Eleganz, Integrität und Nachvollziehbarkeit** legt – wie im Manifest festgehalten[\[142\]]. Beim Neuaufsetzen profitiert man davon: Eine gute Dokumentation, klar strukturierte Services und ein robustes Deployment-Setup sorgen dafür, dass der Bot schnell wieder zum Laufen gebracht werden kann. Indem man den oben beschriebenen Leitfäden folgt, stellt man sicher, dass der **Betrieb sicher** (durch strenge Risk-Limits, keine Leaks), **transparent** (durch Dokumentation und Logging) und **wiederanlauf-fähig** (durch Backups und klare Prozesse) bleibt – selbst wenn der Server mal komplett neu aufgesetzt werden muss.

---

[\[1\]] [\[51\]] [\[75\]] [\[76\]] [\[90\]] [\[91\]] [\[97\]] [\[98\]] [\[99\]] [\[100\]] [\[101\]] [\[102\]] [\[103\]] [\[104\]] [\[105\]] [\[106\]] [\[107\]] [\[108\]] [\[109\]] [\[110\]] [\[111\]] [\[115\]] [\[116\]] END\_TO\_END\_TEST\_GUIDE.md

\1

[\[2\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L28-L36) [\[3\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L9-L17) [\[6\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L13-L19) [\[8\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L32-L40) [\[11\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L178-L186) [\[18\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L16-L24) [\[19\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L38-L44) [\[20\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L236-L244) [\[24\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L112-L119) [\[25\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L206-L214) [\[26\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L24-L27) [\[27\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L252-L255) [\[28\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L16-L19) [\[29\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L36-L40) [\[118\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L106-L114) [\[119\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L202-L210) [\[121\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L216-L224) [\[122\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L246-L254) [\[134\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L53-L61) [\[135\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml#L73-L81) docker-compose.yml

[https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/docker-compose.yml)

[\[4\]] [\[5\]] [\[9\]] [\[10\]] [\[22\]] [\[31\]] [\[47\]] [\[48\]] [\[70\]] [\[94\]] [\[136\]] [\[137\]] ARCHITEKTUR.md

\1

[\[7\]] [\[15\]] [\[33\]] [\[34\]] [\[74\]] [\[114\]] SIGNAL\_ENGINE\_COMPLETE.md

\1

[\[12\]] [\[13\]] [\[14\]] [\[95\]] [\[96\]] [\[112\]] [\[113\]] CODE\_CLEANUP\_AUDIT.md

\1

[\[16\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/backoffice/services/risk_manager/Dockerfile#L14-L19) [\[17\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/backoffice/services/risk_manager/Dockerfile#L20-L23) [\[21\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/backoffice/services/risk_manager/Dockerfile#L9-L16) [\[23\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/backoffice/services/risk_manager/Dockerfile#L14-L22) Dockerfile

[https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/backoffice/services/risk\_manager/Dockerfile](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/backoffice/services/risk_manager/Dockerfile)

[\[30\]] [\[32\]] [\[35\]] [\[37\]] [\[40\]] [\[41\]] [\[42\]] [\[43\]] [\[44\]] [\[45\]] [\[46\]] [\[49\]] [\[50\]] [\[65\]] [\[66\]] [\[67\]] [\[68\]] [\[69\]] [\[92\]] [\[93\]] Service-Kommunikation & Datenflüsse.md

\1

[\[36\]] [\[38\]] [\[39\]] [\[77\]] [\[78\]] [\[79\]] [\[80\]] [\[81\]] [\[82\]] [\[83\]] [\[84\]] [\[85\]] [\[86\]] [\[87\]] [\[88\]] [\[89\]] [\[132\]] [\[133\]] Risikomanagement-Logik.md

\1

[\[52\]] [\[53\]] [\[54\]] [\[55\]] [\[56\]] [\[57\]] [\[58\]] [\[59\]] [\[60\]] [\[61\]] [\[62\]] [\[63\]] DATABASE\_SCHEMA.sql

\1

[\[64\]] [\[71\]] EVENT\_SCHEMA.json

\1

[\[72\]] [\[73\]] SERVICE\_TEMPLATE.md

\1

[\[117\]] [\[131\]] [\[140\]] [\[141\]] [\[142\]] MANIFEST.md

\1

[\[120\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L44-L48) [\[123\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L30-L38) [\[124\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L50-L58) [\[125\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L32-L40) [\[126\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L38-L41) [\[127\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L42-L48) [\[128\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L56-L58) [\[129\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L70-L78) [\[130\]](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md#L94-L100) BACKUP\_ANLEITUNG.md

[https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP\_ANLEITUNG.md](https://github.com/jannekbuengener/Claire-de-Binare/blob/4ccbfbb4d2b69d8d0bdef6128dcf5c0df701a955/BACKUP_ANLEITUNG.md)

[\[138\]] [\[139\]] Briefing\_ ML-basierter Signal-Advisor im deterministischen Handelssystem \_Claire de Binaire\_.pdf

\1