backoffice/docs/ – Single Source of Truth

Struktur (vereinfachte Übersicht):

backoffice/docs/KODEX – Claire de Binare.md
Rahmenwerk, Prinzipien, Zielarchitektur

backoffice/docs/DECISION_LOG.md
ADRs / technische Entscheidungen (inkl. ADR-039 Nullpunkt)

backoffice/docs/architecture/

N1_ARCHITEKTUR.md – Architektur der N1-Paper-Test-Phase

SYSTEM_FLUSSDIAGRAMM.md – Flussdiagramm / Systemübersicht

backoffice/docs/provenance/
Pipeline-Historie, Quellen, Nullpunkt-Dokumente, Audit- und Migrationsprotokolle

backoffice/docs/runbooks/
Historisierte Migrations-Runbooks, operative Checklisten

backoffice/docs/services/
Service-Beschreibungen (cdb_*, Risk-Logic, Data-Flows)

backoffice/docs/schema/
Canonical Schema, Readiness-Reports, Modell-Übersichten

backoffice/docs/audit/
Claire de Binare-Audits, Audit-Plan, Audit-Schema

backoffice/docs/infra/
Infra-Wissen, Env-Index, Repo-Map, Strukturpläne (inkl. dieses Dokuments)

backoffice/docs/knowledge/
Extrahiertes Wissen, Konfliktlisten, historische Knowledge-Artefakte

backoffice/docs/security/
Hardening, Konflikte, Sicherheitsregeln

backoffice/docs/tests/
Test-Dokumentation (nicht Test-Code)

2.2 backoffice/services/ – Services

execution_service/ – Order-Ausführung / Execution-Simulation

risk_manager/ – Risikoregeln, Limits, Positionsgrößen

signal_engine/ – Signal- und Strategielogik

Weitere Services können nach dem Pattern cdb_<funktion> ergänzt werden.

Jeder Service folgt idealerweise demselben Setup:

service.py – Entry-Point

config.py – Konfiguration

models.py – zentrale Datentypen

Dockerfile, requirements.txt – Containerisierung / Dependencies

README.md – Service-spezifische Dokumentation

3. Priorisierte Einstiegsdokumente

Für neue Personen oder KI-Agents empfiehlt sich die folgende Lesereihenfolge:

backoffice/docs/KODEX – Claire de Binare.md
– Projektprinzipien, Zielbild, Namenskonventionen, Guardrails

backoffice/docs/provenance/EXECUTIVE_SUMMARY.md
– Überblick über die Canonicalization und den Claire de Binare-Kontext

backoffice/docs/provenance/Claire de Binare_BASELINE_SUMMARY.md
– Kurzfassung der Nullpunkt-Definition

backoffice/docs/provenance/NULLPUNKT_DEFINITION_REPORT.md
– Details zur Umstellung von „Migration geplant“ auf „Migration abgeschlossen“

backoffice/docs/architecture/N1_ARCHITEKTUR.md
– Technisches Zielbild der N1-Paper-Test-Phase

backoffice/PROJECT_STATUS.md
– Aktueller Projektstatus und N1-Backlog auf hoher Ebene

backoffice/docs/DECISION_LOG.md
– ADRs (insbesondere ADR-039 zum Claire de Binare-Nullpunkt)

Danach lohnt der Blick in:

backoffice/docs/services/*.md – Dienste im Detail

backoffice/docs/schema/*.yaml / .md – Datenmodell und Schema

backoffice/docs/audit/AUDIT_Claire de Binare.md – Audit-Sicht auf die Struktur

4. Arbeitsregeln in diesem Repository

Doku-first

Architekturänderungen, Service-Schnittstellen, neue Risiken oder Infrastrukturanpassungen werden zuerst in backoffice/docs/ beschrieben.

DECISION_LOG als Gate

Relevante Struktur- oder Technologieentscheidungen werden als ADR in DECISION_LOG.md dokumentiert.

Code-Änderungen ohne ADR bei größeren Themen (z. B. neue Services, geänderte Datenwege) sind zu vermeiden.

Claire de Binare ist Kanon

Historische Repositories, Sandboxen und Backups sind nur noch Referenz/Historie.

Neue Arbeit findet ausschließlich in Claire_de_Binare statt.

Trennung von Doku und Code

Test-Code liegt unter tests/.

Test-Dokumentation liegt unter backoffice/docs/tests/.

archive/ enthält nur historische Artefakte, keine aktiv gepflegten Dokumente.

Namenskonvention „Claire de Binare“

Die Schreibweise „Claire de Binare“ gilt als historisch/ungültig (Ausnahme: explizite Audit- oder Historien-Referenzen).

5. Onboarding-Flow (Menschen)

Empfohlener Ablauf für neue Teammitglieder:

30 Minuten Überblick

README im Repo-Root lesen.

Dieses Dokument (Claire de Binare ONBOARDING & REPO NAVIGATION) überfliegen.

KODEX & Executive Summary

KODEX komplett lesen.

EXECUTIVE_SUMMARY + Claire de Binare_BASELINE_SUMMARY lesen.

Architektur verstehen

N1_ARCHITEKTUR.md und SYSTEM_FLUSSDIAGRAMM.md durcharbeiten.

Eigener Fokusbereich

Backend / Services: Service-Dokus unter backoffice/docs/services/ lesen.

Data / Schema: canonical_schema.yaml + canonical_model_overview.md.

Infra / Ops: infra_knowledge.md, repo_map.md, env_index.md.

Erstes Ticket / Task

Mit dem Maintainer einen konkreten, kleinen Task aus dem aktuellen Backlog (siehe PROJECT_STATUS) auswählen.

6. Onboarding-Flow (KI-Agents wie Claude / ChatGPT)

KI-Agents, die mit Repo-Zugriff arbeiten, sollten folgendes Vorgehen nutzen:

Zu Beginn einer Session prüfen:

backoffice/docs/DECISION_LOG.md (letzte ADRs)

backoffice/docs/provenance/NULLPUNKT_DEFINITION_REPORT.md

Bei Architektur- oder Strukturfragen:

backoffice/docs/KODEX – Claire de Binare.md

backoffice/docs/architecture/N1_ARCHITEKTUR.md

Bei Änderungen am Wissensstand oder an der Struktur:

Zuerst in backoffice/docs/ neue Inhalte/Änderungsvorschläge formulieren.

Danach erst Code- oder Config-Anpassungen vorschlagen.

Archivdateien nur als Historie behandeln:

archive/ und alte Knowledge-Dumps NICHT als aktuelle Quelle verwenden.
