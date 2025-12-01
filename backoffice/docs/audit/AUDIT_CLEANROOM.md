# Audit – Claire_de_Binare Claire de Binare

Dieses Dokument definiert das Audit-Verhalten für das Projekt **Claire_de_Binare** (interne Schreibweise) bzw. **„Claire de Binare“** (externe Schreibweise) und beschreibt, was bei dem Kommando **„audit“** passiert.

Es kombiniert:
- ein maschinenlesbares Schema (YAML), das von Claude als Referenz genutzt werden kann, und
- eine klare Beschreibung des Audit-Ablaufs im Fließtext – inklusive Regeln gegen „Dokumüll“ und unsauberes Archivieren.

---

## 1. Projektname und Naming-Policy

### 1.1 Kanonische Schreibweise

- **Intern (Repos, Ordner, IDs):** `Claire_de_Binare`  
- **Extern (Texte, Überschriften):** „Claire de Binare“

Alle Schreibweisen mit **„Binaire“** sind **falsch** bzw. **Legacy** und werden vom Audit als Finding markiert.

Beispiele für **ungültige Varianten** (historisch/Legacy):
- Claire de Binare
- Claire_de_Binaire
- Claire-de-Binare
- claire de binaire  

Der Audit sorgt dafür, dass:
- im Code, in Dateinamen und in internen Referenzen **nur** `Claire_de_Binare` verwendet wird und
- in externen Texten (z. B. Beschreibungen, Overviews) die Formulierung **„Claire de Binare“** genutzt wird.

---

## 2. Ordnerstruktur (relevant für Audits)

Der Audit geht davon aus, dass das Repo in etwa so strukturiert ist:

```text
Claire_de_Binare/
├── backoffice/
│   ├── docs/
│   │   ├── architecture/        # N1_ARCHITEKTUR, System-Diagramme
│   │   ├── knowledge/           # input.md, output.md, scratch/Brain-Dumps
│   │   ├── provenance/          # PROVENANCE, audit_log.md, CANONICAL_SOURCES.yaml
│   │   ├── schema/              # audit_schema.yaml, canonical_schema.yaml
│   │   ├── services/            # Service-Beschreibungen (execution, risk, signal, ...)
│   │   ├── security/            # Security-Guidelines, Hardening
│   │   ├── runbooks/            # Betriebsanweisungen
│   │   ├── infra/               # ENV-Index, Infra-Beschreibung
│   │   └── audit/               # AUDIT_PLAN.md, Projektstatus
│   ├── services/
│   │   ├── execution_service/
│   │   ├── risk_manager/
│   │   └── signal_engine/
│   └── templates/
│       ├── .env.template
│       └── infra_templates/
├── scripts/
├── tests/
├── logs/
├── docker-compose.yml
└── Dockerfile
```

Wichtige Annahme:
- Es gibt **einen klaren Dokumenten-Kanon**, der über `CANONICAL_SOURCES.yaml` gesteuert wird.
- Archivierte Stände liegen unter `backoffice/docs/archive/`.
- Temporäre Brain-Dumps liegen ausschließlich in dedizierten Scratch-Bereichen.

---

## 3. Audit-Schema (YAML)

Dieses Schema kann 1:1 als Datei verwendet werden, z. B.:

`backoffice/docs/schema/audit_schema.yaml`

```yaml
schema_id: "claire_de_binare_audit_schema"
version: "1.2.0"

triggers:
  - type: "keyword"
    pattern: "(?i)^audit$"
    mode: "command"

project:
  canonical_name:
    internal: "Claire_de_Binare"
    external: "Claire de Binare"
  naming_rules:
    enforce_canonical_project_name: true
    invalid_variants:
      - "Claire de Binare"
      - "Claire_de_Binaire"
      - "Claire-de-Binare"
      - "claire de binaire"
      - "claire_de_binare"
    normalization_rules:
      - pattern: "(?i)claire[ _-]?de[ _-]?binaire"
        replace_with_internal: "Claire_de_Binare"
        replace_with_external: "Claire de Binare"
      - pattern: "(?i)claire[ _-]?de[ _-]?bin[aä]re"
        replace_with_internal: "Claire_de_Binare"
        replace_with_external: "Claire de Binare"
    on_violation:
      action: "report_and_autofix"
      severity: "high"
      finding_code: "NAMING-PROJECT-001"

  repo_root: "Claire_de_Binare"
  base_path_windows: "C:\\Users\\janne\\Documents\\GitHub\\Workspaces\\Claire_de_Binare"

folders:
  root: "Claire_de_Binare"
  structure:
    backoffice:
      docs:
        architecture: "backoffice/docs/architecture/"
        knowledge: "backoffice/docs/knowledge/"
        provenance: "backoffice/docs/provenance/"
        schema: "backoffice/docs/schema/"
        services: "backoffice/docs/services/"
        security: "backoffice/docs/security/"
        runbooks: "backoffice/docs/runbooks/"
        infra: "backoffice/docs/infra/"
        audit: "backoffice/docs/audit/"
        archive: "backoffice/docs/archive/"
      services:
        execution_service: "backoffice/services/execution_service/"
        risk_manager: "backoffice/services/risk_manager/"
        signal_engine: "backoffice/services/signal_engine/"
      templates:
        env_template: "backoffice/templates/.env.template"
        infra_templates: "backoffice/templates/infra_templates/"
    scripts: "scripts/"
    tests: "tests/"
    logs: "logs/"
    docker_compose: "docker-compose.yml"
    dockerfile: "Dockerfile"
    claude_doc: "CLAUDE.md"

agents:
  - id: "claire-architect"
    responsibility:
      - "Systemarchitektur, Service-Abhängigkeiten, Datenflüsse"
  - id: "software-jochen"
    responsibility:
      - "Produktiver Code, Service-Struktur, Dockerfile-Konsistenz"
  - id: "agata-van-data"
    responsibility:
      - "Datenflüsse, Tests, Metriken, Monitoring-Readiness"
  - id: "devops-infrastructure-architect"
    responsibility:
      - "Infra, docker-compose, Netzwerke, Volumes, Security-Hardening"
  - id: "claire-risk-engine-guardian"
    responsibility:
      - "Risk-Engine, Limits, Fallbacks, Guard-Logik"

audit_areas:
  - id: "architecture"
    name: "Architektur"
    paths:
      - "backoffice/docs/architecture/"
    checks:
      - "Service-Abhängigkeiten konsistent zu N1_ARCHITEKTUR.md"
      - "Datenflüsse konsistent zum Systemflussdiagramm"
      - "Services in backoffice/services/* entsprechen der Doku"

  - id: "env_config"
    name: "ENV/Config"
    paths:
      - "backoffice/templates/.env.template"
      - "backoffice/docs/infra/env_index.md"
    checks:
      - "Naming-Konventionen (UPPER_SNAKE_CASE) eingehalten"
      - "Dezimal-Konvention bei *_PCT (z. B. 0.05 = 5%)"
      - "Pflicht/Optional markiert"

  - id: "risk_engine"
    name: "Risk-Engine"
    paths:
      - "backoffice/services/risk_manager/"
      - "backoffice/docs/services/risk/"
    checks:
      - "Alle Risk-Parameter mit Min/Max/Default dokumentiert"
      - "Fallbacks bei fehlenden Werten implementiert"
      - "Circuit-Breaker-Logik (Drawdown, Exposure) vorhanden"

  - id: "security"
    name: "Security"
    paths:
      - "backoffice/docs/security/"
      - ".env"
    checks:
      - "Keine Real-Secrets im Repo"
      - ".env und .env.template strukturell konsistent"
      - "Hardening-Empfehlungen dokumentiert"

  - id: "service_code"
    name: "Service-Code"
    paths:
      - "backoffice/services/*/"
    checks:
      - "Config-Usage im Code konsistent zur Doku"
      - "Dependencies konsistent zu docker-compose.yml"
      - "Legacy-Services aus docker-compose entfernt"

  - id: "provenance"
    name: "Provenance"
    paths:
      - "backoffice/docs/provenance/"
    checks:
      - "audit_log.md gepflegt"
      - "CANONICAL_SOURCES.yaml vorhanden"
      - "DECISION_LOG.md referenziert"

  - id: "tests"
    name: "Tests"
    paths:
      - "tests/"
      - "backoffice/docs/tests/"
    checks:
      - "Unit-Tests für Kern-Services"
      - "Smoke-Tests für docker-compose Up/Down"
      - "Risk-Engine mit Grenzfall-Tests"

  - id: "infra"
    name: "Infra"
    paths:
      - "docker-compose.yml"
      - "Dockerfile"
      - "backoffice/docs/infra/"
    checks:
      - "Services starten in sinnvoller Reihenfolge"
      - "Netzwerke/Volumes konsistent"
      - "Monitoring (Prometheus/Grafana) vorbereitet"

audit_types:
  - id: "security_scan"
    priority: 1
    description: "Secrets, Hardening, Config-Konflikte prüfen"
  - id: "env_canonization"
    priority: 2
    description: "ENV-Werte und Konventionen standardisieren"
  - id: "risk_parameter_validation"
    priority: 3
    description: "Risk-Limits, Fallbacks und Guard-Checks prüfen"
  - id: "service_architecture_check"
    priority: 4
    description: "Code vs. Doku-Abgleich auf Service-Ebene"
  - id: "document_consolidation"
    priority: 5
    description: "Redundanz eliminieren, Kanon-Quellen definieren, Archiv bereinigen"
  - id: "pre_migration_audit"
    priority: 6
    description: "Finale Claire de Binare-Bereitschaft vor Migration"

audit_flow:
  stop_on_uncertainty: true
  behavior_on_uncertainty: "pause_and_ask"
  phases:
    - order: 1
      id: "security_scan"
      title: "Schritt 1 – Security-Scan (kritisch)"
      rationale: "Secrets im Repo = höchstes Risiko"
      tasks:
        - "Secret-Leaks via Pattern-Suche prüfen"
        - ".env vs. .env.template vergleichen"
        - "Hardening-Status evaluieren"
      required_outputs:
        - "Security-Findings im audit_log.md"
        - "Empfohlene Hardening-Maßnahmen"

    - order: 2
      id: "env_canonization"
      title: "Schritt 2 – ENV-Kanonisierung"
      rationale: "Grundlage für alle Services (Stabilität)"
      tasks:
        - "Dezimal-Konvention für *_PCT validieren"
        - "Pflicht/Optional pro ENV-Key markieren"
        - "Konflikte dokumentieren"
      required_outputs:
        - "Aktualisierte env_index.md"
        - "Liste kritischer ENV-Konflikte"

    - order: 3
      id: "risk_parameter_validation"
      title: "Schritt 3 – Risk-Parameter-Validierung"
      rationale: "Schutz vor Over-Exposure und Runaway-Trades"
      tasks:
        - "Alle Limits und Defaults aufnehmen"
        - "Edge-Cases (API down, stale data) definieren"
      required_outputs:
        - "Risk-Parameter-Tabelle in docs/services/risk/"
        - "Liste von Edge-Cases"

    - order: 4
      id: "service_architecture_check"
      title: "Schritt 4 – Service-Architektur-Check"
      rationale: "Doku und Code müssen übereinstimmen"
      tasks:
        - "backoffice/services/* vs. docs/services/* abgleichen"
        - "Events/Topics vs. N1_ARCHITEKTUR prüfen"
      required_outputs:
        - "Diff-Liste Doku vs. Code"
        - "Vorschlag für Bereinigung"

    - order: 5
      id: "document_consolidation"
      title: "Schritt 5 – Dokumenten-Konsolidierung & Archiv-Disziplin"
      rationale: "Klarer Kanon statt Doku-Schatten und Archiv-Müll"
      tasks:
        - "Duplikate und Parallel-Dokumente zu einem Thema identifizieren"
        - "Für jedes Thema genau ein kanonisches Dokument in CANONICAL_SOURCES.yaml festlegen"
        - "Relevante Inhalte aus scratch/Brain-Dumps in das kanonische Dokument übernehmen"
        - "Erst danach stabile Stände ins Archive verschieben (backoffice/docs/archive/)"
        - "Sicherstellen, dass im Archive keine WIP-/TODO-/Brain-Dump-Dokumente liegen"
      required_outputs:
        - "Aktualisierte CANONICAL_SOURCES.yaml"
        - "Liste bereinigter bzw. zusammengeführter Dokumente"
        - "Review-Eintrag in backoffice/docs/provenance/audit_log.md zum Archiv-Zustand"

    - order: 6
      id: "pre_migration_audit"
      title: "Schritt 6 – Pre-Migration-Audit"
      rationale: "Letzte Ampel vor produktiver Nutzung"
      tasks:
        - "Offene Findings der Phasen 1–5 prüfen"
        - "Claire de Binare-Struktur final validieren"
      required_outputs:
        - "Abgenommener AUDIT_PLAN.md"
        - "Status-Update in PROJECT_STATUS.md"

security_rules:
  write_access:
    allowed_paths:
      - "backoffice/docs/knowledge/"
      - "backoffice/docs/audit/"
      - "backoffice/docs/provenance/audit_log.md"
    policy: "read_only_outside_allowed_paths"
  read_access:
    denied_patterns:
      - "/**/.*"
  secrets:
    allow_real_secrets: false
    policy: "only_placeholders"
  notstop_keyword: "NOTSTOP"
  safety:
    stop_on_uncertainty: true
    behavior: "Bei Unklarheit Audit pausieren und explizit nachfragen"

document_hygiene:
  no_trash_policy: true
  scratch_paths:
    - "backoffice/docs/knowledge/_scratch/"
  archive_root: "backoffice/docs/archive/"
  rules:
    - "Zwischenstände, Brain-Dumps und Skizzen liegen nur in scratch_paths."
    - "Vor Archivierung werden relevante Inhalte in das jeweils kanonische Dokument übernommen."
    - "Archive enthält nur freigegebene, stabile Stände und keine WIP-/Brain-Dump-Dateien."
  allowed_temp_markers:
    - "TODO(Jannek):"
    - "OPEN:"
  disallow_in_archive:
    - "TODO"
    - "WIP"
    - "DRAFT"
    - "???"
  enforcement:
    on_violation:
      action: "report"
      severity: "medium"
      finding_code: "DOC-HYGIENE-001"

provenance_policy:
  canonical_sources_file: "backoffice/docs/provenance/CANONICAL_SOURCES.yaml"
  archive:
    root: "backoffice/docs/archive/"
    require_canonical_mapping: true
    prohibit_raw_brain_dumps: true
    required_metadata:
      - "version"
      - "date"
      - "source_doc"
      - "reason_for_archiving"
    disallow_markers:
      - "WIP"
      - "TODO"
      - "DRAFT"

text_validation:
  enforce_canonical_terms: true
  languages:
    - "de"
    - "en"
  spelling_policy: "flag_and_suggest"
  spellcheck_scope:
    - "Dateinamen"
    - "Ordnernamen"
    - "Markdown-Überschriften"
    - "ENV-Kommentare"
    - "Prompts und Hilfetexte"
  canonical_terms:
    - canonical: "Claire_de_Binare"
      variants:
        - "Claire de Binare"
        - "Claire_de_Binaire"
        - "Claire-de-Binare"
        - "Claire de Binare"
        - "claire de binaire"
      action: "auto_fix"
      severity: "high"

    - canonical: "execution_service"
      variants: ["ExecutionService", "execution-service", "Execution Service"]
      action: "auto_fix"

    - canonical: "risk_manager"
      variants: ["Risk-Manager", "risk-manager", "Risk Manager"]
      action: "auto_fix"

    - canonical: "signal_engine"
      variants: ["Signal-Engine", "signal-engine", "Signal Engine"]
      action: "auto_fix"

    - canonical: "N1_ARCHITEKTUR.md"
      variants: ["N1_Architektur.md", "N1-ARCHITEKTUR.md"]
      action: "flag"

    - canonical: "ARCHITEKTUR.md"
      variants: ["Architektur.md"]
      action: "flag"

    - canonical: "DECISION_LOG.md"
      variants: ["Decision_Log.md", "DecisionLog.md"]
      action: "auto_fix"

  legacy_terms:
    - pattern: "(?i)binaire"
      message: "Legacy-Schreibweise, nach Binare migrieren"
      severity: "medium"

reporting:
  output_files:
    - "backoffice/docs/provenance/audit_log.md"
    - "backoffice/docs/audit/AUDIT_PLAN.md"
    - "backoffice/PROJECT_STATUS.md"
  required_sections:
    - "Summary"
    - "Findings"
    - "Risks"
    - "Recommendations"
    - "Next Steps"
  templates:
    audit_log:
      format: "markdown"
      sections:
        - "## Summary"
        - "## Findings"
        - "## Risks"
        - "## Recommendations"
        - "## Next Steps"
    audit_plan:
      format: "markdown"
      sections:
        - "## Scope"
        - "## Phases"
        - "## Responsibilities"
        - "## Timeline"

progress_model:
  example_status:
    migration_progress: 95
    label: "Claire de Binare-Migration"
    phases:
      - "Struktur aufgebaut"
      - "Audit-Plan erstellt"
      - "Security-Scan gestartet"
      - "ENV-Standards ausstehend"
      - "Service-Tests ausstehend"
      - "Deployment ausstehend"
```

---

## 4. Was im Audit passiert (Fließtext)

Wenn du das Kommando **„audit“** verwendest, passiert aus Sicht der Logik oben Folgendes:

1. **Projekt- und Naming-Check**  
   Zuerst wird geprüft, ob der Projektname überall konsistent ist:
   - Intern wird nur `Claire_de_Binare` akzeptiert.
   - Externe Beschreibungen können „Claire de Binare“ nutzen.
   - Jede Form mit „Binaire“ wird als Legacy bzw. Fehler gewertet und als Finding im `audit_log.md` dokumentiert.
   Zusätzlich werden die wichtigsten Service- und Dokument-Namen geprüft (z. B. `execution_service`, `risk_manager`, `N1_ARCHITEKTUR.md`, `DECISION_LOG.md`).

2. **Security-Scan (Schritt 1)**  
   Der Audit startet mit Sicherheit:
   - Pattern-Scans suchen nach möglichen Secrets (Passwörter, API-Keys, Tokens).
   - `.env` wird gegen `.env.template` geprüft: gleiche Struktur, aber keine echten Secrets im Repo.
   - Security-/Hardening-Dokumente werden darauf geprüft, ob sie zu dem passen, was in `docker-compose.yml` und `Dockerfile` steht.  
   Ergebnis: Eine Liste von Security-Findings mit Priorisierung (Severity) im `audit_log.md`.

3. **ENV-Kanonisierung (Schritt 2)**  
   Danach wird das ENV-/Config-Fundament ausgerichtet:
   - Alle ENV-Variablen aus `.env.template` und `env_index.md` werden abgeglichen.
   - Namenskonventionen (UPPER_SNAKE_CASE) werden konsistent enforced.
   - Prozent-Parameter (z. B. mit `_PCT`) werden auf einheitliche Dezimal-Logik geprüft.
   - Pro ENV-Key wird geklärt: Pflicht vs. Optional, inklusive Default-Strategie.  
   Ziel: Konfigurations-Chaos abbauen und eine belastbare, dokumentierte ENV-Basis schaffen.

4. **Risk-Parameter-Validierung (Schritt 3)**  
   Anschließend wird die Risk-Engine geprüft:
   - Alle relevanten Risk-Parameter (Limits, Schwellen, Faktoren) werden mit Min/Max/Default erfasst.
   - Es wird geprüft, ob Fallbacks für fehlende, invalide oder veraltete Werte existieren.
   - Circuit-Breaker, Drawdown- und Exposure-Logik werden gegen die Dokumentation gespiegelt.  
   Ergebnis: Eine klar dokumentierte Risk-Landschaft, die im Fehlerfall definiert reagiert – statt unkontrolliert zu laufen.

5. **Service-Architektur-Check (Schritt 4)**  
   Jetzt wird sichergestellt, dass Code und Dokumentation zusammenpassen:
   - Die Services in `backoffice/services/*` werden mit den Beschreibungen in `backoffice/docs/services/*` abgeglichen.
   - Events, Topics und Datenflüsse werden mit N1_ARCHITEKTUR.md und weiteren Architektur-Dokumenten abgeglichen.
   - Legacy-Services oder veraltete Pfade werden identifiziert.  
   Das Ergebnis ist eine Diff-Liste, aus der klar hervorgeht:
   - Wo beschreibt die Dokumentation mehr als es gibt?
   - Wo läuft im Code etwas, das in der Dokumentation nicht (mehr) existiert?

6. **Dokumenten-Konsolidierung & Archiv-Disziplin (Schritt 5)**  
   Hier greift die Anti-„Dokumüll“-Logik:
   - Der Audit identifiziert doppelte oder konkurrierende Dokumente pro Thema (z. B. mehrere Risk-Docs, mehrere ENV-Übersichten).
   - Über `CANONICAL_SOURCES.yaml` wird für jedes Thema genau **ein** Kanon-Dokument festgelegt.
   - Inhalte aus Scratch-/Brain-Dump-Dateien (z. B. `backoffice/docs/knowledge/_scratch/`) werden gesichtet:
     - Relevante Inhalte werden in die jeweiligen Kanon-Dokumente übernommen.
     - Nicht relevante oder überholte Notizen bleiben im Scratch-Bereich oder werden explizit verworfen – **sie wandern nicht ins Archiv**.
   - Das Archiv (`backoffice/docs/archive/`) wird nur mit **stabilen, freigegebenen Ständen** befüllt:
     - Jedes Archiv-Dokument erhält Meta-Informationen (Version, Datum, Ursprung, Grund für Archivierung).
     - Dateien mit „WIP“, „TODO“, „DRAFT“ oder rohen Brain-Dumps sind im Archiv explizit untersagt.  
   Ziel: Keine Doku-Schattenwelten, kein wildes Archiv voller halbfertiger Texte, sondern klare Kanon-Dokumente plus ein aufgeräumtes, nachvollziehbares Archiv.

7. **Pre-Migration-Audit (Schritt 6)**  
   Zum Schluss wird geprüft, ob der Claire de Binare wirklich „bereit“ ist:
   - Offene Findings aus allen Phasen werden gesammelt, priorisiert und entweder geschlossen oder bewusst akzeptiert (mit Begründung).
   - `AUDIT_PLAN.md` und `PROJECT_STATUS.md` werden aktualisiert, damit klar ist:
     - Wie weit die Migration/Modernisierung ist.
     - Welche Risiken verbleiben.
     - Welche nächsten Schritte anstehen (z. B. Tests, Deployment, Monitoring-Finalisierung).  
   Damit funktioniert der Audit als letzte Ampel vor dem nächsten technischen Schritt (z. B. MCP-Integration, produktive Nutzung).

8. **NOTSTOP und Umgang mit Unsicherheit**  
   Der Audit bricht nicht „still“ ab, sondern:
   - Wenn essenzielle Informationen fehlen oder widersprüchlich sind, greift `stop_on_uncertainty: true`.
   - Das System pausiert an dieser Stelle, markiert die Unklarheit und fordert explizit Klärung an, statt auf Basis von Vermutungen weiterzuarbeiten.

9. **Zusammenfassung der Dokumenthygiene**

Konkret stellt der Audit sicher, dass:
- **kein dauerhafter Dokumüll** entsteht – Brain-Dumps bleiben in eigenen Scratch-Bereichen.
- **Archiv-Dateien nur stabile Stände** enthalten, mit sauberer Herkunfts-Referenz und klarer Begründung.
- **wichtige Begriffe und Namen (insbesondere „Claire_de_Binare“) konsistent** und korrekt verwendet werden.
- **relevante Inhalte immer zuerst in die richtigen Kanon-Dokumente einfließen**, bevor irgendetwas ins Archiv verschoben wird.

Damit bleibt das Projekt sowohl technisch als auch dokumentarisch sauber, auditierbar und langfristig wartbar.
