# CDB Context Intelligence - Ingestion Scope and File Classification Rules

**Status**: Draft (Issue #1986 replacement slice)
**Authority**: Issue #1986 / Parent #1985 / Epic #1976
**Scope**: Docs-only (no runtime change, no production ingestion, no SurrealDB activation)
**Guardrail**: Live-Readiness remains NO-GO. Board stage `trade-capable` is not a Live-Readiness-Go.

---

## 1. Zweck

Dieses Dokument definiert den kanonischen Ingestion-Scope fuer das CDB Context Intelligence System (CIS).

Es legt fest:

- welche Repo-Bereiche fuer Context-Ingestion zulaessig sind
- welche Bereiche nur bedingt zulaessig sind
- welche Bereiche ausgeschlossen sind
- welche Dateitypen verarbeitet werden duerfen
- welche Sensitivity Class pro Artefakt anzuwenden ist
- welche Guardrails vor jeder spaeteren Ingestion-Implementierung verbindlich gelten

Dieses Dokument ist eine Scope- und Klassifikationsspezifikation. Es ist keine Implementierung, kein Enable-Plan und keine Freigabe fuer produktive SurrealDB-Nutzung.

---

## 2. Nicht-Ziele

- Keine produktive Ingestion.
- Kein produktives SurrealDB-Enable.
- Keine Runtime-Aenderung.
- Kein Trading-State-Modell.
- Keine Secrets-Aufnahme.
- Kein Live- oder Echtgeld-Go.
- Keine Freigabe fuer Wave-8-Implementierung als Nebeneffekt.

---

## 3. Authority Boundary

- Git und GitHub bleiben die Source of Truth fuer Code, Doku, Issues und PR-Wahrheit.
- CIS ist ein read-only Mirror fuer spaeteres Retrieval und Verknuepfung.
- Dieses Dokument definiert nur, was fuer einen spaeteren read-only Mirror ueberhaupt in Betracht kommt.
- Dieses Dokument autorisiert keine Ingestion gegen produktive Systeme.
- Dieses Dokument autorisiert keine Aenderung an Trading-Runtime, Broker-Integrationen, Live-Risk oder operativem Systemzustand.

---

## 4. In-Scope Roots

Die folgenden Root-Bereiche sind grundsaetzlich fuer Context-Ingestion zulaessig, sofern die Regeln in den folgenden Abschnitten eingehalten werden.

| Root | Status | Zweck |
|------|--------|-------|
| `docs/` | allowed | Architektur, Runbooks, Governance-nahe Fachdoku, SurrealDB- und Systemdokumentation |
| `knowledge/` | allowed | Kanonische Knowledge-, Governance- und Operating-Dokumente |
| `agents/` | allowed | Agenten-Registry, Rollen, Boot- und Arbeitsanweisungen |
| `infrastructure/surrealdb/` | allowed | Schema-Drafts, Mirror- und Context-Intelligence-Artefakte |
| `infrastructure/config/surrealdb/` | allowed | SurrealDB-bezogene Konfigurationsartefakte, sofern nicht secret-haltig |
| `tools/surrealdb/` | allowed | Read-only Tooling- und Hilfsoberflaechen fuer SurrealDB/CIS |
| `README.md` | allowed | Repo- oder modulspezifische Einstiegstexte mit dokumentarischem Kontext |

---

## 5. Conditional Roots

Die folgenden Bereiche sind nur bedingt zulaessig. Aufnahme ist nur erlaubt, wenn das Artefakt unmittelbar zum statischen Verstaendnis des Systems, seiner Contracts oder seiner dokumentierten Abhaengigkeiten beitragt.

| Root | Status | Bedingung |
|------|--------|-----------|
| `core/` | conditional | Nur statische Symbole, Interfaces, Typen, Konstanten oder dokumentierende Kommentare; kein Runtime-State |
| `services/` | conditional | Nur servicebezogene statische Struktur, Contracts und Ownership-Hinweise; kein Live-State |
| `tests/` | conditional | Nur als Evidenz fuer Contracts, Beispiele, Fixtures oder dokumentierte Verifikation |
| `infrastructure/compose/` | conditional | Nur Compose- und Stack-Struktur als statischer Betriebs- und Architekturkontext |

Conditional bedeutet:

- Aufnahme nur mit belegbarem Kontextnutzen.
- Aufnahme nur in read-only Form.
- Kein Schluss von Compose-, Test- oder Code-Artefakten auf Live-Readiness-Go.

---

## 6. Excluded Roots and Classes

Die folgenden Bereiche und Datenklassen sind ausgeschlossen.

| Path / Class | Status | Grund |
|--------------|--------|-------|
| `.git/` | excluded | interne Git-Daten, kein kanonischer Ingestion-Scope |
| `.venv/` | excluded | Build-/Tool-Artefakte |
| `.worktrees/` | excluded | lokale Arbeitsflaechen, nicht kanonisch |
| `logs/` | excluded | potenziell sensitive Laufzeitdaten |
| `artifacts/` | excluded | generierte Outputs, kein dauerhafter Canon |
| `docs/archive/` | excluded by default | historischer Rueckgriff, nur bei expliziter Referenz zulaessig |
| Secrets aller Art | excluded | nie ingestieren |
| Trading-Runtime-State | excluded | nie ingestieren |
| Live-Risk-State | excluded | nie ingestieren |
| Credentials / Tokens / Keys | excluded | nie ingestieren |
| Personenbezogene Daten ausser oeffentlichen Repo-Metadaten | excluded | Datenschutz- und Minimalitaetsprinzip |

Explizit verboten sind insbesondere:

- API-Keys
- Private Keys
- Passwoerter
- Broker-Credentials
- Wallet-Secrets
- Session-Secrets
- Balance-, Order-, Fill-, Position- oder Exposure-Zustaende
- produktive Betriebszustandsdaten aus Redis, Postgres oder externen Diensten

---

## 7. Allowed File Types

Die folgenden Dateitypen sind fuer Ingestion zulaessig, sofern sie innerhalb eines erlaubten oder bedingt erlaubten Roots liegen und keine Ausschlussdaten enthalten.

| File type | Beispiele | Normalfall |
|-----------|-----------|------------|
| Markdown | `.md` | bevorzugter Dokumentationsinput |
| YAML | `.yaml`, `.yml` | Ontologien, Config, strukturierte Spezifikation |
| JSON | `.json` | strukturierte Contracts, Metadaten, Schemas |
| Python | `.py` | statische Symbol- und Contract-Extraktion |
| TOML | `.toml` | Tooling- und Projektkonfiguration |
| SurrealQL | `.surql` | statische SurrealDB-Schema-Drafts und Query-/Schema-Artefakte, keine produktive Apply-Freigabe |
| Shell | `.sh` | statische Tooling- und Runbook-Unterstuetzung |
| PowerShell | `.ps1` | Windows-Tooling und Operator-Helfer |
| Compose YAML | `compose*.yml`, `compose*.yaml` | Stack-Struktur, keine Runtime-Freigabe |

Nicht automatisch erlaubt sind Binardateien, Datenbank-Dumps, Medien, Notebook-Ausgaben und generierte Artefakte.

---

## 8. Mandatory Sensitivity Classes

Jedes ingestierbare Artefakt MUSS genau einer der folgenden Klassen zugeordnet werden.

| Class | Bedeutung | Erlaubte Nutzung |
|-------|-----------|------------------|
| `public_context` | oeffentlich teilbarer Repo-Kontext ohne sensible Betriebsmetadaten | normale read-only Ingestion |
| `internal_context` | interner Repo- oder Architekturkontext ohne Secrets, aber nicht fuer beliebige externe Weitergabe gedacht | read-only Ingestion mit interner Kontextbindung |
| `sensitive_metadata` | sensible Metadaten ohne Secret-Inhalt, z. B. Pfad-/Struktur-/Kontrollinformationen, die nur minimiert verarbeitet werden duerfen | nur minimierte read-only Ingestion |
| `forbidden` | nicht ingestierbar | niemals ingestieren |

Diese vier Klassen sind vollstaendig. Es duerfen keine alternativen oder zusaetzlichen Sensitivity Classes fuer diesen Scope eingefuehrt werden.

---

## 9. Deterministic Classification Rules

Die Klassifikation MUSS deterministisch, fail-closed und reproduzierbar sein.

### 9.1 `public_context`

Nutze `public_context`, wenn alle folgenden Kriterien erfuellt sind:

- Artefakt liegt in einem erlaubten Root.
- Inhalt beschreibt Architektur, Doku, Ontologie, Roadmap, Runbook, statische Schnittstellen oder oeffentliche Repo-Metadaten.
- Inhalt enthaelt keine Secrets.
- Inhalt enthaelt keinen Trading-State.
- Inhalt enthaelt keine sensitiven Runtime- oder Zugangsdaten.

Typische Beispiele:

- `docs/surrealdb/*.md`
- `docs/db/index.md`
- repo-weite `README.md`
- dokumentierende YAML-/JSON-Artefakte ohne sensitive Inhalte

### 9.2 `internal_context`

Nutze `internal_context`, wenn alle folgenden Kriterien erfuellt sind:

- Artefakt liegt in einem erlaubten oder conditional Root.
- Artefakt ist fuer Systemverstaendnis relevant.
- Inhalt ist intern oder betrieblich einzuordnen, aber nicht secret-haltig.
- Inhalt enthaelt keine live-operativen Zustandsdaten.

Typische Beispiele:

- Agentenrollen und Arbeitsregeln in `agents/`
- interne Operating-Dokumente in `knowledge/`
- statische Code- und Service-Strukturen in `core/` oder `services/`, sofern sie nur zur Symbol- oder Contract-Extraktion genutzt werden

### 9.3 `sensitive_metadata`

Nutze `sensitive_metadata`, wenn das Artefakt selbst kein Secret enthaelt, aber seine Metadaten oder Struktur nur minimiert verarbeitet werden duerfen.

Typische Indikatoren:

- Pfad- oder Topologieinformationen mit sicherheitsrelevanter Aussagekraft
- Konfigurationsdateien ohne Secret-Inhalt, die sensitive Betriebsgrenzen oder interne Infrastrukturbeziehungen offenlegen
- Test- oder Compose-Artefakte, deren Vollinhalt nicht breit repliziert werden soll, deren Existenz und statische Metadaten aber als Kontext relevant sind

Regel fuer `sensitive_metadata`:

- nur minimal notwendige Felder erfassen
- kein Volltext, wenn Metadaten ausreichen
- keine Ausweitung auf faktische Secret-Naehe

### 9.4 `forbidden`

Nutze `forbidden`, wenn mindestens eines der folgenden Kriterien zutrifft:

- Secret, Credential, Key, Token oder Passwort enthalten
- Trading-State, Live-Risk-State oder produktiver Betriebszustand enthalten
- generiertes Log-, Dump- oder Artefaktmaterial enthalten
- nur lokale, temporale oder nicht-kanonische Arbeitsdaten enthalten
- Archivmaterial ohne explizite Referenz darstellen

Wenn Unsicherheit besteht, MUSS fail-closed auf `forbidden` entschieden werden, bis ein belegter Ausnahmeentscheid vorliegt.

---

## 10. Evidence for Inclusion

Eine Ingestion-Zulassung ist nur dann belegt, wenn mindestens einer der folgenden Punkte zutrifft:

- das Artefakt ist in einem kanonischen Dokument als Referenz oder Abhaengigkeit benannt
- das Artefakt ist fuer Architektur-, Governance-, Contract- oder Validierungsverstaendnis unmittelbar erforderlich
- das Artefakt stuetzt eine spaetere read-only Query-, Impact- oder Evidence-Funktion des CIS
- das Artefakt belegt eine statische Beziehung zwischen Repo-Komponenten, Dokumenten, Issues oder PRs

Nicht ausreichend fuer Inclusion sind:

- technische Neugier ohne dokumentierten Kontextnutzen
- Bequemlichkeit fuer spaetere breite Volltextaufnahme
- implizite Annahmen ueber moegliche kuenftige Nutzung

Regel:

- No evidence for inclusion, no inclusion.

---

## 11. Root-Specific Rules

### 11.1 `docs/`

- Normalfall `public_context`.
- Interne Betriebsdokumente koennen `internal_context` sein.
- Archive unter `docs/archive/` bleiben ausgeschlossen, sofern sie nicht explizit referenziert und separat freigegeben werden.

### 11.2 `knowledge/`

- Normalfall `internal_context`.
- Governance-nahe Kerndokumente koennen ingestiert werden, aber nie als Ersatz fuer Git/GitHub-SSOT.
- Historische Snapshots sind nur zulaessig, wenn sie als solche markiert und fuer Vergleichszwecke explizit benoetigt werden.

### 11.3 `agents/`

- Normalfall `internal_context`.
- Agentenregeln sind Kontext fuer Arbeitsgrenzen und Rollenverstaendnis, nicht fuer Live-Systemsteuerung.

### 11.4 `infrastructure/surrealdb/`

- Schema-Drafts und statische CIS-Artefakte sind im Regelfall `public_context` oder `internal_context`.
- Keine produktiven Apply- oder Aktivierungsdaten.

### 11.5 `infrastructure/config/surrealdb/`

- Normalfall `internal_context` oder `sensitive_metadata`.
- Jede Datei mit Secret-, Credential- oder Produktivzugangsinhalten ist `forbidden`.

### 11.6 `tools/surrealdb/`

- Read-only Tooling-Kontext ist zulaessig.
- Keine Tool-Artefakte mit eingebetteten Secrets oder produktiver Schaltwirkung.

### 11.7 `core/`, `services/`, `tests/`, `infrastructure/compose/`

- nur statisch und selektiv
- keine Vollaufnahme ohne belegten Zweck
- keine Ableitung von Runtime-Wahrheit aus Test- oder Compose-Strukturen

---

## 12. Guardrails for Any Future Ingestion

Vor jeder spaeteren Implementierung oder Dry-run-Ingestion MUESSEN die folgenden Guardrails gelten:

- Kein produktives SurrealDB-Enable.
- Keine produktive Ingestion.
- Keine Runtime-Aenderung.
- Kein Trading-State im Scope.
- Keine Secrets im Scope.
- Kein Live-Readiness-Upgrade.
- Kein Echtgeld-Go.
- Kein Schluss von Board stage `trade-capable` auf operatives Go.
- Git/GitHub bleibt die alleinige Wahrheitsquelle.
- CIS bleibt read-only Mirror.

Wenn einer dieser Guardrails verletzt wird, ist die Ingestion zu stoppen und in einen neuen, explizit gegateten Arbeitsstrang aufzuteilen.

---

## 13. Change Control

Jede Erweiterung dieses Scopes MUSS:

- ueber eine explizite Issue oder kanonische Governance-Referenz belegt sein
- die Sensitivity Class je Root und Dateityp neu pruefen
- fail-closed fuer unklare Bereiche bleiben
- Archive, Secrets und Trading-State weiterhin ausgeschlossen halten
- keine implizite Produktions- oder Live-Freigabe erzeugen

Nicht zulaessig sind Scope-Erweiterungen, die nur aus Implementierungsbequemlichkeit vorgenommen werden.

---

## 14. Downstream Dependency Notes

Dieses Dokument schafft nur die Scope-Grundlage.

- `#1987` darf auf diesem Scope aufbauen, aber keine neuen Scope-Klassen erfinden.
- `#1988` darf auf diesem Scope aufbauen, aber keine ausgeschlossenen Bereiche implizit wieder einfuehren.
- `#1989` ist bereits geschlossen und darf nicht als offener Folge-Slice dargestellt werden.
- `#2045` und `#2046` duerfen diese Scope-Regeln nur konsumieren oder weiter absichern, nicht stillschweigend aufweichen.

Downstream-Arbeit bleibt blockiert fuer:

- produktive SurrealDB-Aktivierung
- produktive Ingestion
- Wave-8-Implementierung ohne separaten, explizit gegateten Schritt

---

## 15. Explicit No-Go Statements

- Live-Readiness bleibt `NO-GO`.
- Dieses Dokument ist keine Freigabe fuer produktive SurrealDB-Aktivierung.
- Dieses Dokument ist keine Freigabe fuer produktive Context-Ingestion.
- Dieses Dokument ist keine Freigabe fuer Wave-8-Implementierung.
- Dieses Dokument ist keine Freigabe fuer Echtgeld-Trading.

---

## 16. Validation Checklist for This Document

- [ ] Erlaubte Roots sind explizit benannt.
- [ ] Conditional Roots sind explizit benannt.
- [ ] Excluded Roots und Datenklassen sind explizit benannt.
- [ ] Dateitypen sind explizit benannt.
- [ ] `public_context`, `internal_context`, `sensitive_metadata`, `forbidden` sind exakt enthalten.
- [ ] Deterministische Klassifikationsregeln sind definiert.
- [ ] Secrets und Trading-State sind explizit ausgeschlossen.
- [ ] Live-Readiness-NO-GO ist explizit wiederholt.
- [ ] Keine produktive SurrealDB-Aktivierung oder Ingestion wird freigegeben.
- [ ] `#1989` wird nicht als offen dargestellt.

---

## Provenance / Quellen

- Epic `#1976`
- Issue `#1985`
- Issue `#1986`
- `docs/surrealdb/context-intelligence-system.md`
- `docs/surrealdb/context-intelligence-validation.md`
- `docs/surrealdb/context-pr-slicing-plan.md`
- `docs/surrealdb/context-wave7-completion-gates.md`
- `docs/db/index.md`
