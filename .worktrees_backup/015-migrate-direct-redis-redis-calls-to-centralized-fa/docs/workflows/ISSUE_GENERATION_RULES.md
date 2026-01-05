# Issue Generation Rules (Issue #245)

Regelwerk für die automatisierte Generierung von Issues aus Roadmap-Elementen.

## Roadmap-Format

Jedes Roadmap-Item sollte folgendes Format haben:

```markdown
| ID | Title | Gate/Dependency | Priority |
|---|---|---|---|
| A-01 | Test inventory & baseline | G0 | P0 |
```

## Issue-Generierung

### Automatische Felder

| Roadmap-Feld | Issue-Feld |
|--------------|------------|
| ID | Title-Prefix (z.B. "A-01: ...") |
| Title | Issue Title |
| Priority | Label (prio:must/should/nice) |
| Gate/Dependency | "Blocked by #..." im Body |

### Label-Mapping

| Priority | Label |
|----------|-------|
| P0 | prio:must |
| P1 | prio:should |
| P2 | prio:nice |

### Template

```markdown
---
agent: claude
scope: [SCOPE]
phase: [PHASE]
related_issues: [DEPENDENCIES]
---

Kurzbeschreibung:
[TITLE]

Context:
Roadmap Item [ID] aus [ROADMAP_FILE]

Aufgabenliste:
- [ ] [Generated from roadmap description]

Akzeptanzkriterien:
- [ ] [Generated from roadmap "Missing Work" column]

Verweise:
- Roadmap: [ROADMAP_FILE]
- Gate: [DEPENDENCY]
```

## Prozess

1. **Roadmap-Update**: Neues Item in `Roadmap_*.md` hinzufügen
2. **Map-Update**: `ROADMAP_ISSUE_MAP.md` aktualisieren (Coverage=None)
3. **Issue erstellen**: Mit obigem Template
4. **Map-Update**: Issue-Link in Map eintragen, Coverage=Full/Partial

## CLI-Befehl

```bash
gh issue create \
  --title "[ID]: [TITLE]" \
  --label "agent:claude,prio:[PRIORITY]" \
  --body-file /tmp/issue_body.md
```

## Kompatibilität

- Bestehende Issues werden nicht überschrieben
- ROADMAP_ISSUE_MAP.md ist Single Source of Truth für Mapping
- Manuelle Issues sind erlaubt (Coverage=Manual)
