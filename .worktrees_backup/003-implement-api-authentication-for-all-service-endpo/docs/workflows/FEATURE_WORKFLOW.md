# Canonical Feature Workflow (Issue #246)

Standard-Workflow für Feature-Entwicklung in Claire de Binare.

## Workflow-Übersicht

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   ISSUE     │────▶│   BRANCH    │────▶│    DEV      │────▶│   REVIEW    │
│   Created   │     │   Created   │     │   + Tests   │     │   + CI      │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐            │
│   CLOSED    │◀────│   MERGED    │◀────│  APPROVED   │◀───────────┘
│   + Docs    │     │   to main   │     │   PR        │
└─────────────┘     └─────────────┘     └─────────────┘
```

## 1. Issue-Phase

### Anforderungen
- [ ] Issue aus Roadmap oder neuer Anforderung erstellt
- [ ] Labels gesetzt: `agent:*`, `scope:*`, `prio:*`, `type:*`
- [ ] Kurzbeschreibung + Akzeptanzkriterien definiert
- [ ] Dependencies geprüft (blocked by?)

### Template
```markdown
Kurzbeschreibung:
[Was soll erreicht werden?]

Akzeptanzkriterien:
- [ ] [Messbare Erfolgskriterien]

Verweise:
- Related Issues: #xxx
- Related Files: [betroffene Dateien]
```

## 2. Branch-Phase

### Namenskonvention
```
<type>/<issue-number>-<kurzbeschreibung>

Beispiele:
feat/246-feature-workflow
fix/303-hardcoded-secrets
docs/245-issue-generator
```

### Types
- `feat/` - Neue Features
- `fix/` - Bugfixes
- `docs/` - Dokumentation
- `refactor/` - Code-Umstrukturierung
- `test/` - Tests
- `chore/` - Maintenance

## 3. Development-Phase

### Checkliste
- [ ] Code geschrieben
- [ ] Tests hinzugefügt/aktualisiert
- [ ] `pytest -m unit` lokal grün
- [ ] Keine neuen Linter-Warnungen
- [ ] Commit-Messages folgen Convention

### Commit-Convention
```
<type>: <kurzbeschreibung> (Issue #xxx)

[optionaler Body mit Details]

🤖 Generated with Claude Code
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

## 4. Review-Phase

### PR-Template
```markdown
## Summary
- [1-3 Bullet Points]

## Test plan
- [ ] Unit Tests
- [ ] Integration Tests (falls relevant)
- [ ] E2E Tests (falls relevant)

## Checklist
- [ ] Tests pass
- [ ] No new warnings
- [ ] Docs updated

Closes #xxx
```

### CI-Gates
- [ ] `pytest -m unit` ✅
- [ ] Linting ✅
- [ ] Security Scan ✅ (keine neuen Critical/High)

## 5. Merge-Phase

### Anforderungen
- [ ] Mindestens 1 Approval (oder Self-Merge bei Solo)
- [ ] Alle CI-Checks grün
- [ ] Keine Merge-Konflikte

### Merge-Strategie
- **Squash Merge** für Feature-Branches (clean history)
- **Merge Commit** für Release-Branches

## 6. Post-Merge

### Checkliste
- [ ] Issue geschlossen mit Kommentar
- [ ] Dokumentation aktualisiert (falls nötig)
- [ ] ROADMAP_ISSUE_MAP.md aktualisiert (Coverage)

## Agenten-Zuständigkeiten

| Agent | Rolle |
|-------|-------|
| Claude | Primary Developer, Code + Tests |
| Gemini | Review, Architecture Feedback |
| Copilot | Docs, Code Completion |

## Ausnahmen

### Hotfixes
Bei kritischen Bugs:
1. Branch direkt von `main`: `hotfix/xxx`
2. Minimaler Fix
3. Fast-Track Review
4. Sofort Merge + Deploy

### Documentation-Only
Für reine Docs-Änderungen:
1. Self-Approve erlaubt
2. Kein CI-Gate für Tests
