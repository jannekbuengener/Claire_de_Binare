# Wissensbasis des Claire de Binare Systems

## Übersicht

Die Wissensbasis ist das zentrale Repository für systemweites Wissen, Entscheidungen und Erkenntnisse im Claire de Binare (CDB) System.

## Zweck

Diese Wissensbasis dient als:
- **Langzeit-Memory**: Persistentes Wissen über das System
- **Entscheidungsarchiv**: Dokumentation wichtiger Entscheidungen
- **Kontext-Quelle**: Hintergrund für Governance und Entwicklung
- **Lernbasis**: Erkenntnisse und Best Practices

## Struktur

### `/knowledge`
Hauptverzeichnis der Wissensbasis

### `/knowledge/decisions/`
Architektur- und Governance-Entscheidungen (Architecture Decision Records)

#### ADR-Format
Entscheidungen folgen dem ADR-Format:
- Dateiname: `ADR-NNN-titel.md` (z.B. `ADR-001-repository-structure.md`)
- Nummerierung: Fortlaufend, beginnt bei 001
- Status: Proposed | Accepted | Deprecated | Superseded

#### ADR-Template
```markdown
# ADR-NNN: Titel der Entscheidung

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

## Kontext
Was ist die Situation, die eine Entscheidung erfordert?

## Entscheidung
Was haben wir entschieden?

## Konsequenzen
Was sind die Folgen dieser Entscheidung?

## Alternativen
Welche Alternativen wurden in Betracht gezogen?

## Datum
YYYY-MM-DD
```

### `/knowledge/index.yaml`
Strukturierter Index aller Wissenseinträge für programmatischen Zugriff

## Wissenskategorien

### 1. Architektur-Entscheidungen
Strukturelle und fundamentale Entscheidungen über das System
- Speicherort: `decisions/ADR-*-*.md`
- Format: Architecture Decision Record

### 2. Governance-Entscheidungen
Entscheidungen über Regeln, Prozesse und Governance
- Speicherort: `decisions/GDR-*-*.md` (Governance Decision Record)
- Format: Ähnlich ADR

### 3. Best Practices
Bewährte Praktiken und Richtlinien
- Speicherort: `best-practices/*.md`
- Format: Strukturierte Dokumentation

### 4. Lessons Learned
Erkenntnisse aus Projekten und Erfahrungen
- Speicherort: `lessons-learned/*.md`
- Format: Narrative Dokumentation

## Wissen hinzufügen

### Neue Entscheidung dokumentieren

1. **Nächste Nummer finden**
   ```bash
   # Letzte ADR finden
   ls -1 knowledge/decisions/ADR-*.md | sort -V | tail -1
   ```

2. **ADR erstellen**
   - Verwende Template
   - Benenne: `ADR-NNN-kurzer-titel.md`
   - Fülle alle Sektionen aus

3. **Index aktualisieren**
   - Update `knowledge/index.yaml`
   - Füge Metadaten hinzu

4. **Pull Request erstellen**
   - Folge Contribution Rules
   - Tag: `knowledge`

### Wissen kuratieren

#### Wissens-Maintainer
Verantwortlich für:
- Struktur und Organisation
- Aktualität der Einträge
- Index-Pflege
- Qualitätssicherung

#### Review-Prozess
1. Inhaltliche Korrektheit
2. Strukturelle Konsistenz
3. Vollständigkeit
4. Verlinkung und Referenzen

## Index-Verwendung

Der `index.yaml` ermöglicht:
- Programmatischen Zugriff auf Wissen
- Suche nach Kategorien/Tags
- Zeitliche Navigation
- Dependency-Tracking

## Wissens-Governance

### Änderungen an Entscheidungen
Entscheidungen sollten normalerweise **nicht geändert** werden:
- **Neue Entscheidung**: Erstelle neuen ADR
- **Supersede**: Markiere alten ADR als "Superseded by ADR-XXX"
- **Deprecate**: Markiere als "Deprecated" wenn nicht mehr relevant

### Ausnahmen
Korrektur von Tippfehlern oder Klarstellungen:
- Klare Kennzeichnung der Änderung
- Update des Datums
- Kurze Begründung

## Suche und Navigation

### Nach Kategorie
```bash
grep -l "Kategorie: Architektur" knowledge/decisions/*.md
```

### Nach Status
```bash
grep -l "Status: Accepted" knowledge/decisions/*.md
```

### Im Index
```yaml
# knowledge/index.yaml
decisions:
  - id: "ADR-001"
    status: "accepted"
    category: "architecture"
```

## Qualitätsstandards

### Entscheidungen müssen:
- ✅ Klaren Kontext bieten
- ✅ Begründung enthalten
- ✅ Konsequenzen aufzeigen
- ✅ Alternativen diskutieren
- ✅ Datum haben

### Dokumentation muss:
- ✅ Klar und präzise sein
- ✅ Strukturiert und navigierbar
- ✅ Aktuell und relevant
- ✅ Referenzen enthalten

## Langzeit-Strategie

Die Wissensbasis ist für **langfristige Nutzung** konzipiert:
- Entscheidungen bleiben erhalten (historische Referenz)
- Kontinuierliche Erweiterung
- Regelmäßige Kuratierung
- Index-Pflege

---
**Version**: 1.0.0  
**Letzte Änderung**: 2025-12-16
---
relations:
  role: doc
  domain: knowledge
  upstream: []
  downstream:
    - knowledge/CDB_KNOWLEDGE_HUB.md
    - knowledge/SHARED.WORKING.MEMORY.md
    - knowledge/reviews/
---
# Knowledge base and shared agent memory.

## Where to write / Where not to write
*   **Write here:** Session summaries, decision logs, agent handoffs, review reports, operating rules.
*   **Do NOT write here:** Canonical governance policies (use `knowledge/governance/`), active code, ephemeral logs (use `knowledge/logs/`).

## Key entrypoints
*   [CDB Knowledge Hub (knowledge/CDB_KNOWLEDGE_HUB.md)](knowledge/CDB_KNOWLEDGE_HUB.md)
*   [Shared Working Memory (knowledge/SHARED.WORKING.MEMORY.md)](knowledge/SHARED.WORKING.MEMORY.md)
*   [Review Reports (knowledge/reviews/)](knowledge/reviews/)

# /knowledge — Working Knowledge & Session Context (NON-CANONICAL)

## Zweck

Der Ordner `/knowledge` ist der **zentrale Arbeits- und Denkraum**
für Mensch und KI-Agenten im Projekt *Claire de Binare*.

Er dient als:
- temporärer Denkraum
- Übergabe- und Koordinationsfläche
- Ablage für Reviews, Logs und Session-Kontext

**Wichtig:**  
Inhalte in `/knowledge` besitzen **keine kanonische Autorität** und
setzen **keine systemweiten Regeln**.

---

## Grundprinzip (verbindlich)

> `/knowledge` ist **Arbeitsgedächtnis**, nicht Gesetz.  
> Denken ist erlaubt. Autorität ist es nicht.

---

## Was gehört HIERHER