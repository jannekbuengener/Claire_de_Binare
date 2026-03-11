**Audit‑Roadmap: Repo‑Hygiene und Governance für Claire de Binare** 

**Einleitung** 

Das Projekt **Claire de Binare (CDB)** besteht aus einem **Working Repo** für den ausführbaren Code und einem **Docs Hub** für Governance‑, Knowledge‑ und Agentendokumente. Laut Verfassung und Policy‑Stack ist diese Trennung fest definiert – der Arbeits‑Code bleibt bereinigbar und deterministisch, während kanonische Dokumente im Docs Hub versioniert werden. Ziel dieser Audit‑Roadmap ist es, den aktuellen Zustand des Working Repos zu analysieren, Abweichungen von den Governance‑Richtlinien zu identifizieren und konkrete Maßnahmen für eine robuste Repo‑Hygiene und Governance‑Überarbeitung zu planen. 

**Grundlagen & Policies** 

**Verfassung und Policy‑Stack** 

•    
**CDB Constitution (v1.1)** – höchste Instanz: sie definiert das deterministische, event‑getriebene Trading‑System und legt die Rangordnung fest (Verfassung → Governance → Policies → 1   
Implementierung) . Sie garantiert Souveränität des Users, Dezentralisierung, Transparenz 2   
und Auditierbarkeit . Governance‑Entscheidungen folgen dem 

3   
Proposal‑Review‑Approval‑Merge‑Prozess . 

•    
**CDB Governance (v1.1)** – operationalisiert die Verfassung. Das Dokument regelt Rollen, Rechte, Zonen und Change Control; es ist als Systemvertrag zu sehen und trennt Ausführung, Autonomie und Sicherheit (Zeilen 13–31 des Dokuments) und ist bindend für alle Beteiligten. •    
**CDB Policy Stack Mini** – definiert den kanonischen Dokumentensatz (Constitution, Governance, 4   
Agent Policy, Infra Policy, RL‑Safety Policy, Tresor Policy, PSM Policy und das Delivery Gate) . Änderungen an diesen Dokumenten sind nur via Proposal → Review → explizite User‑Freigabe → 5   
versioniertem Merge zulässig . 

•    
**Agent Policy** – legt die Handlungszonen der KI‑Agenten fest. In Zone A dürfen Agenten im Rahmen des Mandats autonom agieren, in Zone C dürfen sie nur Vorschläge unterbreiten und 6 7   
Zone D ist strikt verboten (z.B. Tresor‑Zugriff, Änderung von Hard Limits) . Persistente Schreibrechte sind auf den Knowledge‑Bereich beschränkt; Schreibzugriffe in den 8   
Working‑Repo‑Code oder in knowledge/governance sind untersagt . 

• 9 10   
**Infra Policy** – fordert Infrastructure as Code und GitOps als Single Source of Truth . Services müssen kubernetes‑ready sein (stateless, Konfiguration über ENV/Secrets, Health/ 11   
Liveness‑Probes) . Secrets dürfen nicht im Repo liegen und werden ausschließlich über 12   
Secret‑Manager bereitgestellt . 

•    
**RL‑Safety Policy** – definiert deterministische Guardrails für reinforcement learning. RL‑Aktionen 

werden durch einen Risk‑Layer maskiert; ein Kill‑Switch mit abgestuften Stufen (Reduce Only, 13   
Hard Stop, Emergency) ist vorgeschrieben . RL darf niemals Hard Limits ändern, Keys 14   
anfassen oder Governance verändern . 

•    
**Tresor Policy** – sichert kryptografische Assets, Hard Limits und Governance‑Dateien in einer Tresor‑Zone außerhalb des Repos. Kein autonomer Zugang ist erlaubt; alle Änderungen sind 

1  
15 16   
human‑only und nachvollziehbar . Secrets und Keys dürfen niemals im Repository liegen 

17   
. 

•    
**Repo‑Guidelines & Repo‑Structure** – beschreiben die erlaubten Verzeichnisse und 

Cleanroom‑Regeln für das Working Repo. Erlaubt sind /core , /services , / 18 19   
infrastructure , /tests , /tools , /scripts , Compose‑Dateien und Makefile . 20   
Verboten sind /knowledge , /governance , /agents und Logs im Working Repo . Das 21   
Working Repo soll jederzeit löschbar und neu aufbaubar sein . Commit‑ und PR‑Nachrichten 22   
müssen konventionell strukturiert sein und die Änderungen, Tests und Risiken beschreiben . Diese Grundlagen bilden den Maßstab für das Audit. 

**Aktueller Zustand des Working Repos** 

**Struktur & Verzeichnisse** 

•    
Die Verzeichnisstruktur entspricht weitgehend den Richtlinien: Es gibt core/ , services/ ,  infrastructure/ , tests/ , tools/ und scripts/ . Ein knowledge ‑ oder  governance ‑Verzeichnis existiert nicht, was der Trennung zwischen Working Repo und Docs 19 20   
Hub entspricht . 

•    
Für Dokumentation wurde eine Datei DOCS\_MOVED\_TO\_DOCS\_HUB.md hinterlegt, die erklärt, 

dass alle Dokumente in das Docs Hub migriert wurden und das Working Repo nur Code enthält 

23 24   
. Dies entspricht der Clean‑Repo‑Philosophie. 

•    
Es existiert keine LICENSE ‑Datei und kein CODE\_OF\_CONDUCT.md . Die repo‑Guidelines 

verlangen zwar keine konkreten Lizenzen, aber für Open‑Source‑Transparenz und klare Nutzungsrechte sollte eine Lizenz definiert werden. 

**README & Projektstatus** 

•    
Das Root‑ README.md beschreibt das Projekt, listet die Microservices, Infrastruktur und 

Governance‑Dokumente auf und enthält einen aktuellen Fortschritts‑Bericht (Issues/Services/ 25 26   
Tests/Monitoring) . Der Bericht ist sehr umfangreich, aber auf deutsche Nutzer\*innen ausgerichtet; eine englische Zusammenfassung könnte die Zugänglichkeit erhöhen. 

•    
Der README‑Statusblock zeigt 65 % Projekt‑Reife mit 1607 Python‑Dateien, 140+ Commits und 27   
247 Tests . Diese Informationen sind hilfreich für neue Mitarbeitende. **CI/CD, GitHub Hygiene & Milestones** 

•    
Laut MILESTONES.md wurde die Phase M1 („GitHub & CI Baseline“) als abgeschlossen markiert. 28   
Sie zielte auf Repository‑Hygiene, aktives CI/CD, strukturierte Labels und Automatisierungen . In dieser Phase wurden ein Stale Bot, Auto‑Labeler und ein Label‑System eingeführt – das legt eine solide Basis für das Issue‑Management. 

•    
Die nächsten Meilensteine (M2 bis M9) sind geplant oder in Arbeit; u. a. 

„Infra & Security Hardening“, „Observability“, „Persistenz“, „Testnet“, „Security Review“ und 29 30   
„Release 1.0“ . Diese Roadmap sollte mit den hier vorgeschlagenen Audit‑Maßnahmen abgeglichen werden. 

**Sicherheitslage & Legacy** 

•    
Das SECURITY\_BASELINE.md dokumentiert, dass bekannte CVEs (u. a. pip CVE‑2025‑8869) 31   
behoben wurden und alle Python‑Services auf pip 25.3 aktualisiert wurden . Darüber hinaus wurden Sicherheitsmaßnahmen wie non‑root‑Images, Read‑only‑Dateisysteme und 32   
wöchentliche Scans umgesetzt . 

2  
•    
Es wird ein **Accept‑Risk** für embedded gosu‑Binaries (kritische CVEs in den Redis/ Postgres‑Images) beschrieben. Die Attack‑Surface‑Analyse bewertet das Risiko als niedrig und 33   
definiert eine Mitigation mit Pinning, CI‑Gates und Monitoring . 

•    
Das LEGACY\_FILES.md listet zahlreiche veraltete Compose‑Dateien ( docker-compose.yml ,  docker-compose.base.yml , docker-compose.dev.yml ) sowie unsichere Praktiken wie 

plaintext‑Passwort‑Variablen und lokale .secrets ‑Verzeichnisse. Es beschreibt Migrationspfade zu den neuen Dateien unter infrastructure/compose und zur Nutzung 34 35 36   
von Docker‑Secrets . Die Entfernung der Legacy‑Dateien ist für Phase 3 geplant . **Hinweise zu Commit‑Hooks & Secret‑Scanning** 

•    
Unter tools/ gibt es Skripte wie install-git-hooks.ps1 und enforce-root 

baseline.ps1 . Dies deutet auf eine vorbereitete Infrastruktur für Git‑Hooks zur Durchsetzung von Commit‑Standards und Root‑Baseline‑Checks. Eine Prüfung der installierten Hooks und deren Wirksamkeit sollte Teil des Audits sein. 

•    
Es existiert eine .gitleaksignore ‑Datei, die offenkundig für das Secret‑Scanning mit  

**gitleaks** genutzt wird. Es sollte überprüft werden, ob gitleaks in der CI‑Pipeline aktiviert ist und ob das gitleaks.toml ‑Konfigurationsfile existiert. 

**Fehlende oder verbesserungswürdige Punkte** 

1\.    
**Lizenz & Rechtliches:** Es fehlt eine Lizenzdatei, sodass unklar ist, unter welchen Bedingungen 

der Code genutzt werden darf. Eine OS‑Lizenz wie MIT, Apache 2.0 oder GPL sollte gewählt und implementiert werden. Ebenfalls fehlt ein CODE\_OF\_CONDUCT.md und ein CONTRIBUTING.md , die für die Community‑Governance hilfreich sind. 

2\.    
**Test‑Abdeckung & Qualitätsmetriken:** Laut README existieren 247 Testfunktionen bei 27   
1607 Python‑Dateien . Eine Coverage‑Analyse (z.B. mittels pytest-cov ) ist nicht dokumentiert; hierfür sollten Metriken definiert und CI‑Gates gesetzt werden. 3\.    
**Secret‑Management:** Obwohl die Legacy‑Files einen Umzug zu Workspace‑Secrets und den 37   
Verzicht auf .env propagieren , sollte überprüft werden, ob wirklich keine .env ‑Dateien im Repo verbleiben und ob secrets nicht versehentlich in den Code gelangen. Der Infra‑Policy 12   
zufolge sind Secrets im Repo strikt verboten . 

4\.    
**Ergänzende Governance‑Checks:** Der Policy‑Stack legt strenge Regeln für Änderungen fest. Eine Prüfung der vorhandenen Pull‑Requests sollte sicherstellen, dass sie stets den Proposal‑Review‑Approval‑Flow durchlaufen und dass Delivery‑Gate‑Checks 

( DELIVERY\_APPROVED.yaml ) eingehalten werden. 

5\.    
**Code‑Qualität & Style:** Das Repo‑Guideline verlangt konventionelle Commit‑Nachrichten und 22 38   
deterministischen Python‑Code . Die Einrichtung von Pre‑Commit‑Hooks (flake8, black, mypy) könnte die Einhaltung automatisiert absichern. 

6\.    
**Dokumentation:** Das README ist umfangreich, jedoch könnte eine englische Version die 

internationale Zusammenarbeit verbessern. Zudem fehlen Hinweise zur lokalen Einrichtung 39   
(Requirements, Virtualenv) und zur Nutzung von Make‑Targets aus den Repo‑Guidelines . **Roadmap zur Repo‑Hygiene & Governance** 

Die folgenden Schritte bauen aufeinander auf und orientieren sich an den Milestones M2–M8. Sie sind in kurz‑, mittel‑ und langfristige Maßnahmen gegliedert. 

3  
**Phase 1: Sofortmaßnahmen (nächste 2 Wochen)** 

| Maßnahme Beschreibung Begründung und Quelle |
| ----- |
| Wähle eine Open‑Source‑Lizenz (z.B. MIT  Aktuell fehlt eine Lizenz;  oder Apache 2.0) passend zum  **Lizenz auswählen**  ohne klare Lizenz ist die  Projektziel; lege sie als LICENSE ins  **und hinzufügen**  Nutzung unklar. Root und verweise im README darauf.  |
| Erstelle CODE\_OF\_CONDUCT.md und   Fördert Community‑Hygiene  **CODE\_OF\_CONDUCT**  CONTRIBUTING.md mit Verweis auf  und definiert Beiträge;  **& CONTRIBUTING**  aktuell nicht vorhanden. Rollen und Prozesse aus der Governance.  |
| Entferne docker-compose.yml ,   docker-compose.base.yml ,   docker-compose.dev.yml und  Die Migration ist in Phase 3  **Legacy‑Dateien**  geplant; Entfernen  andere als **deprecated** markierte  **entfernen**  verhindert Verwechslungen  Dateien, nachdem das Team umgestellt  und „Repo‑Verschmutzung“.  hat . Füge .gitignore ‑Einträge  36 hinzu, um Wiedereinchecken zu  verhindern.  |
| Prüfe, ob gitleaks in der CI‑Pipeline läuft;  richte gitleaks.toml mit den  Die Tresor‑ und Infra‑Policies  **Secret‑Scanning**  aktuellen Secrets‑Regeln ein und  untersagen Secrets im Repo  **konfigurieren**  12 17 verifiziere .gitleaksignore . Ergänze  .  GitHub‑Secret‑Scanning.  |
| Nutze die vorhandenen Skripte  ( install-git-hooks.ps1 ) zur  Unterstützt  Installation von Hooks für  **Pre‑Commit‑Hooks**  deterministischen  Code‑Formatierung, Linting (flake8/  **etablieren**  Coding‑Style .  black) und Commit‑Message‑Linting  38 (Conventional Commits). Dokumentiere  die Verwendung im README.  |
| Integriere Test‑Coverage‑Checks (z.B.   pytest-cov ) und Linting‑Jobs in  Derzeit sind nur Test‑ und  **CI‑Pipeline ergänzen**  Lint‑Jobs erwähnt; Coverage  GitHub Actions. Definiere  fehlt. Schwellenwerte (z.B. \>80 % Coverage)  und mache sie zu Merge‑Blockern.  |

4  
**Phase 2: Mittelfristige Maßnahmen (Q1 2026)** 

| Maßnahme Beschreibung Begründung und Quelle |
| ----- |
| Implementiere den im Legacy‑Guide  beschriebenen Weg: Secrets nur über  Docker Secrets  ( ../.cdb\_local/.secrets ),  Vermeidet Leaks und  **Secrets‑Management**  Nutzung eines Secret‑Managers  sorgt für künftige  **konsolidieren**  (Vault / Sealed Secrets) gemäß  Kubernetes‑Readiness.  12 37 Infra‑Policy . Entferne  .env ‑Files und dokumentiere den  lokalen Setup‑Prozess.  |
| Migriere alle Compose‑Dateien in   infrastructure/compose und  arbeite mit stack\_up.ps1 laut  **Infrastruktur Hardening**  Erfüllt Infra‑Policy (IaC,  Legacy‑Guide . Implementiere  349 12 **(Milestone M2)**  GitOps, Secrets) .  Secrets, Health‑Checks und network  isolation. Ergänze TLS/SSL für externe  Verbindungen.  |
| Überprüfe, ob der Delivery‑Gate  ( DELIVERY\_APPROVED.yaml )  Verhindert  korrekt gesetzt ist; CI/Jira sollten  **Governance‑Gate**  unautorisierte  Blockieren, wenn   **Enforcement**  Mutationen im Working  delivery.approved: false .  4 Repo.  Automatisiere die Prüfung in der  Pipeline.  |
| Entwickle Replay‑fähige  Policies verlangen  End‑to‑End‑Tests, Performance‑Tests  **Testnetz & Persistenz**  deterministische  und Persistenz‑Integration. Ergänze  **(Milestones M5 & M7)**  Replays und  Tools zur deterministischen  Auditierbarkeit .  40 Replay‑Funktion.  |
| Ergänze das README um eine  englische Version und extrahiere den  Verbessert Lesbarkeit  **Internationalisierung der**  Fortschritts‑Block in ein automatisch  für internationale  **Dokumentation**  generiertes Dashboard. Verweise auf  Stakeholder. das Docs Hub für vertiefte  Informationen.  |
| Definiere eine wöchentliche  Die Governance  Governance‑Review  verlangt regelmäßige  **Community‑Kommunikation**  (Policy‑Stack Review) und  Reviews und klare  protokolliere sie im Docs Hub.  Rollenverteilung .  3 |

5  
**Phase 3: Langfristige Maßnahmen (Q2 2026 → Release 1.0)** 

| Maßnahme Beschreibung Begründung |
| ----- |
| Packe alle Services in stateless  Containers mit ConfigMaps/Secrets,  Erfüllt die Infra‑Policy  **Kubernetes‑Readiness**  definiere Resource‑Limits und  11  (Kubernetes‑Readiness ,  **& GitOps**  Liveness‑Probes. Implementiere  GitOps ).  10 FluxCD oder ähnliches für  GitOps‑Reconcile.  |
| Migriere von Redis als temporärem  Transport zu JetStream/Kafka;  Erhöht Persistenz,  **Event‑Driven**  implementiere Dual‑Write und  Reproduzierbarkeit und  **Backbone**  Replay‑Vergleich wie in der Infra‑Policy  Auditierbarkeit.  beschrieben .  41 |
| Implementiere den Risk‑Layer mit  deterministischen Guardrails und  Action‑Masking. Richte das  Erfordert strikte Einhaltung  **RL‑Safety & Kill‑Switch**  Kill‑Switch‑System ein und  der RL‑Safety‑Policy.  dokumentiere Tests zur Verifikation  42 13 .  |
| Beauftrage ein externes Security‑Team  (Milestone M8). Prüfe OWASP Top 10,  **Penetration Testing &**  Container‑Scanning,  Erfüllt Milestone M8 und  **Compliance**  Netzwerk‑Isolation und  stärkt Sicherheit. Secrets‑Management. Schließe offene  CVEs.  |
| Technische Trennung der Tresor‑Zone  **Tresor‑Zone**  (Keys, Limits, Governance‑Docs) vom  Schutz vor Verlusten und  **Implementieren**  Trading‑System. Stelle offline‑Access  Missbrauch.  43 16 und Auditing sicher .  |
| Erstelle einen  Finalisiert die  **Release‑Prozess &**  Release‑1.0‑Checklisten‑Prozess  Governance‑Überarbeitung  **Incident‑Response**  (Milestone M9) mit Security‑Sign‑off,  und bereitet Go‑Live vor. Monitoring, SLAs und Rollback‑Plan.  |

**Abschluss und Ausblick** 

Das Working Repo von Claire de Binare zeigt bereits eine starke Trennung von Code und Wissen, eine aktive CI‑Pipeline und einen klaren Milestone‑Plan. Die Governance‑Dokumente im Docs Hub bilden eine robuste Grundlage, die deterministische Abläufe und strikte Sicherheitsgarantien vorschreibt. Fehlende Elemente wie Lizenz, Verhaltens‑ und Beitragsrichtlinien, vollständiges Secret‑Management und die Entfernung von Legacy‑Dateien sollten kurzfristig behoben werden.  

Die vorgeschlagene Audit‑Roadmap orientiert sich an den bestehenden Policies und Milestones und ergänzt sie um konkrete Maßnahmen zur Repo‑Hygiene, Sicherheits‑Härtung und Governance‑Compliance. Durch regelmäßige Reviews, automatisierte Prüfungen und eine klare Rollentrennung wird gewährleistet, dass das Projekt deterministisch, auditierbar und sicher bleibt. 

6  
1 2 3 40   
CDB\_CONSTITUTION.md 

https://github.com/jannekbuengener/Claire\_de\_Binare\_Docs/blob/main/knowledge/governance/CDB\_CONSTITUTION.md 

4 5   
CDB\_POLICY\_STACK\_MINI.md 

https://github.com/jannekbuengener/Claire\_de\_Binare\_Docs/blob/main/knowledge/governance/ CDB\_POLICY\_STACK\_MINI.md 

6 7 8   
CDB\_AGENT\_POLICY.md 

https://github.com/jannekbuengener/Claire\_de\_Binare\_Docs/blob/main/knowledge/governance/CDB\_AGENT\_POLICY.md 

9 10 11 12 41   
CDB\_INFRA\_POLICY.md 

https://github.com/jannekbuengener/Claire\_de\_Binare\_Docs/blob/main/knowledge/governance/CDB\_INFRA\_POLICY.md 

13 14 42   
CDB\_RL\_SAFETY\_POLICY.md 

https://github.com/jannekbuengener/Claire\_de\_Binare\_Docs/blob/main/knowledge/governance/CDB\_RL\_SAFETY\_POLICY.md 

15 16 17 43   
CDB\_TRESOR\_POLICY.md 

https://github.com/jannekbuengener/Claire\_de\_Binare\_Docs/blob/main/knowledge/governance/CDB\_TRESOR\_POLICY.md 

18 22 38 39   
CDB\_REPO\_GUIDELINES.md 

https://github.com/jannekbuengener/Claire\_de\_Binare\_Docs/blob/main/knowledge/governance/CDB\_REPO\_GUIDELINES.md 

19 20 21   
CDB\_REPO\_STRUCTURE.md 

https://github.com/jannekbuengener/Claire\_de\_Binare\_Docs/blob/main/knowledge/governance/CDB\_REPO\_STRUCTURE.md 

23 24   
DOCS\_MOVED\_TO\_DOCS\_HUB.md 

https://github.com/jannekbuengener/Claire\_de\_Binare/blob/main/DOCS\_MOVED\_TO\_DOCS\_HUB.md 

25 26 27   
README.md 

https://github.com/jannekbuengener/Claire\_de\_Binare/blob/main/README.md 

28 29 30   
MILESTONES.md 

https://github.com/jannekbuengener/Claire\_de\_Binare/blob/main/.github/MILESTONES.md 

31 32 33   
SECURITY\_BASELINE.md 

https://github.com/jannekbuengener/Claire\_de\_Binare/blob/main/docs/security/SECURITY\_BASELINE.md 

34 35 36 37   
LEGACY\_FILES.md 

https://github.com/jannekbuengener/Claire\_de\_Binare/blob/main/LEGACY\_FILES.md 7