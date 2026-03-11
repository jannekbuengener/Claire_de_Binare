# ADR-001: Documentation-Only Repository

## Status

**Accepted**

## Kontext

Das Claire de Binare (CDB) System benötigt ein zentrales Repository für Governance, Wissen und Dokumentation. Es besteht die Gefahr, dass dieses Repository im Laufe der Zeit mit Code, Infrastruktur und anderen ausführbaren Artefakten vermischt wird, was die Klarheit und Wartbarkeit beeinträchtigen würde.

Folgende Faktoren beeinflussen diese Entscheidung:
- Klare Trennung von knowledge/governance/Dokumentation und ausführbarem Code
- Langfristige Wartbarkeit der Wissensbasis
- Einfacher Zugriff für alle Stakeholder (auch nicht-technische)
- Versionskontrolle von Governance-Entscheidungen
- Vermeidung von Build- und Deployment-Komplexität

## Entscheidung

Das `Claire_de_Binare_Docs` Repository wird als **reines Dokumentations- und Governance-Repository** definiert. Es darf ausschließlich folgende Inhalte enthalten:

1. **Markdown-Dateien (.md)** für:
   - Governance-Dokumente
   - Agenten-Charter-Beschreibungen
   - Wissensdokumentation
   - Entscheidungsaufzeichnungen (ADRs)

2. **YAML-Dateien (.yaml, .yml)** für:
   - Strukturierte Governance-Daten
   - Agenten-Charter-Definitionen
   - Wissens-Indizes

3. **Repository-Meta-Dateien**:
   - `.gitignore` (für Enforcement)
   - `CODEOWNERS` (für Governance-Kontrolle)
   - `LICENSE` (falls erforderlich)

**Absolut verboten** sind:
- Jeglicher ausführbarer Code (JS, Python, Go, etc.)
- Infrastruktur-Definitionen (Terraform, Kubernetes, etc.)
- Services oder APIs
- Build-Tools und Package-Dependencies
- Binärdateien oder kompilierte Artefakte

## Konsequenzen

### Positive Konsequenzen

1. **Klarheit**: Jeder weiß sofort, dass dies ein Dokumentations-Repository ist
2. **Einfachheit**: Kein Build-Prozess, keine Dependencies, keine Deployment-Pipeline notwendig
3. **Zugänglichkeit**: Alle können Dokumentation lesen und verstehen, ohne technisches Setup
4. **Fokus**: Das Team konzentriert sich auf Governance und Wissen, nicht auf Code
5. **Langlebigkeit**: Markdown und YAML sind langlebige, zukunftssichere Formate
6. **Versionskontrolle**: Git ist ideal für Dokumentations-Versioning
7. **Governance**: Klare Kontrolle über kritische Governance-Dokumente via CODEOWNERS

### Negative Konsequenzen

1. **Einschränkung**: Keine Möglichkeit, Governance-Tools oder Validierungs-Skripte direkt im Repository zu haben
2. **Manuelle Prozesse**: Einige Prozesse können nicht automatisiert werden (müssen in anderen Repos leben)
3. **Zusätzliche Repos**: Für Tools und Code sind separate Repositories erforderlich
4. **Enforcement-Abhängigkeit**: Einhaltung hängt von .gitignore und Reviews ab (keine automatischen technischen Barrieren)

### Neutrale Konsequenzen

1. **Strukturierung**: Erfordert klare Dokumentationsstruktur (aber das ist eh notwendig)
2. **Governance-Overhead**: Governance-Reviews für alle Änderungen (aber das ist gewollt)

## Alternativen

### Alternative 1: Monorepo mit Code und Dokumentation
- **Beschreibung**: Governance und Code im gleichen Repository
- **Vorteile**: Alles an einem Ort, einfacher zu finden
- **Nachteile**: 
  - Vermischung von Concerns
  - Build-Komplexität
  - Schwerer für nicht-technische Stakeholder
  - Governance-Dokumente könnten in Code-Änderungen untergehen
- **Grund für Ablehnung**: Verletzung der Separation of Concerns

### Alternative 2: Wiki oder externes System
- **Beschreibung**: Verwendung von GitHub Wiki, Confluence, oder ähnlichem
- **Vorteile**: 
  - Spezialisierte Tools für Dokumentation
  - Oft bessere Such- und Navigationsfunktionen
- **Nachteile**:
  - Keine richtige Versionskontrolle
  - Schwieriger zu reviewen (kein PR-Prozess)
  - Keine CODEOWNERS-Unterstützung
  - Vendor-Lock-in
  - Migrations-Risiko
- **Grund für Ablehnung**: Unzureichende Governance-Kontrolle

### Alternative 3: Separate Repos für jeden Dokumentationstyp
- **Beschreibung**: Ein Repo für Governance, eins für Agenten, eins für Wissen
- **Vorteile**: Maximale Trennung
- **Nachteile**:
  - Fragmentierung
  - Schwierige Navigation
  - Overhead bei Repository-Management
  - Cross-referencing wird kompliziert
- **Grund für Ablehnung**: Unnötige Komplexität

## Implementierung

Diese Entscheidung wird umgesetzt durch:

1. **Verzeichnisstruktur** erstellen:
   - `knowledge/governance/` - Governance-Dokumente
   - `agents/` - Agenten-Charter
   - `knowledge/` - Wissensbasis
   - `docs/` - Dokumentation

2. **Enforcement-Mechanismen**:
   - `.gitignore` konfigurieren, um nicht-erlaubte Dateitypen auszuschließen
   - `CODEOWNERS` definieren für Governance-Kontrolle

3. **Dokumentation**:
   - CONSTITUTION.md erstellen mit grundlegenden Prinzipien
   - REPOSITORY_POLICY.md mit detaillierten Regeln
   - CONTRIBUTION_RULES.md für Beitragende

4. **Templates**:
   - ADR-Template für Entscheidungen
   - Charter-Template für Agenten
   - Governance-Template für neue Richtlinien

## Referenzen

- [CONSTITUTION.md](../../knowledge/governance/CONSTITUTION.md) - Systemverfassung
- [REPOSITORY_POLICY.md](../../knowledge/governance/REPOSITORY_POLICY.md) - Repository-Richtlinien
- [Architecture Decision Records Pattern](https://adr.github.io/) - ADR-Methodik

## Metadaten

- **Autor**: System Bootstrap
- **Datum**: 2025-12-16
- **Reviewer**: Governance Board
- **Kategorie**: architecture
- **Tags**: #repository #governance #structure #documentation

---

**Diese Entscheidung ist akzeptiert und bindend für alle zukünftigen Beiträge zum Repository.**
