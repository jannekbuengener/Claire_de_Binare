# GitHub Projects Board Setup

## ⚠️ Auth-Scope Issue

Die `gh project create` Befehle benötigen erweiterte Scopes:
```bash
gh auth refresh -s project,read:project --hostname github.com
```

Da dies interaktiv ist, folge dieser **manuellen Anleitung**:

---

## 🎯 Manual Setup (5 Min)

### Schritt 1: Project erstellen

1. Gehe zu: https://github.com/users/jannekbuengener/projects
2. Klicke **"New project"**
3. Wähle **"Table"** Template
4. Name: **"Claire de Binare - N1 Roadmap"**
5. Description: **"N1 Paper-Test Phase - Milestone & Issue Tracking"**

### Schritt 2: Views konfigurieren

#### View 1: "Roadmap" (Board)
- Layout: **Board**
- Group by: **Milestone**
- Sort by: **Priority**
- Filter: `is:open`

#### View 2: "Status" (Table)
- Layout: **Table**
- Columns: Title, Status, Milestone, Labels, Assignees
- Group by: **Status**

#### View 3: "N1-Phase" (Filtered)
- Layout: **Board**
- Filter: `label:n1-phase is:open`
- Group by: **Milestone**

### Schritt 3: Issues hinzufügen

**Automatisch alle Issues importieren**:
1. Im Project → **"+ Add items"**
2. Dropdown: **"Add items from repository"**
3. Repo wählen: `jannekbuengener/Claire_de_Binare_Cleanroom`
4. Alle Issues auswählen (20 Issues)
5. **"Add selected items"**

### Schritt 4: Custom Fields (optional)

Zusätzliche Felder für besseres Tracking:

| Field Name | Type | Options |
|-----------|------|---------|
| **Priority** | Single Select | 🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low |
| **Phase** | Single Select | N1-Prep, N1-Test, Post-N1, Production |
| **Effort** | Number | 1-5 (Story Points) |
| **Blocked By** | Text | Issue-Numbers (#25, #26) |

**Hinzufügen**:
1. Project → **Settings** (⚙️)
2. **"+ New field"**
3. Felder wie oben definieren

### Schritt 5: Automation einrichten

**Auto-Status bei Close**:
1. Settings → **Workflows**
2. Enable: **"Auto-close items"**
3. Enable: **"Auto-archive items"**

**Custom Workflow**:
```
Trigger: Issue labeled "critical"
Action: Set Priority to "🔴 Critical"
```

---

## 📊 Erwartetes Ergebnis

Nach Setup:

### Board-Ansicht (Roadmap):
```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│  M1 - Foundation    │  M3 - Risk-Layer    │  M5 - Persistenz    │
├─────────────────────┼─────────────────────┼─────────────────────┤
│  #25 ENV Validation │  #21 pytest Setup   │  #23 Portfolio Mgr  │
│  #37 ✅ KODEX       │  #22 Risk Tests     │  #24 Analytics      │
│                     │                     │  #31 Grafana        │
│                     │                     │  #32 Backup         │
│                     │                     │  #38 ✅ DB Schema   │
└─────────────────────┴─────────────────────┴─────────────────────┘

┌─────────────────────┬─────────────────────┬─────────────────────┐
│  M6 - Docker        │  M7 - Live-Test     │  M8 - Hardening     │
├─────────────────────┼─────────────────────┼─────────────────────┤
│  #26 Systemcheck    │  #27 Exec Simulator │  #29 Infra Security │
│  #36 ✅ Docker Stack│  #28 E2E Test       │  #30 CI/CD          │
│                     │                     │  #34 ✅ Security 95%│
│                     │                     │  #40 ✅ MEXC Safety │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

### Milestones Progress:
```
M1 - Foundation:         [████████░░] 66% (2/3 closed)
M2 - Architektur:        [██████████] 100% (1/1 closed)
M3 - Risk-Layer:         [░░░░░░░░░░] 0% (0/2 closed)
M4 - Event-Driven:       [██████████] 100% (1/1 closed)
M5 - Persistenz:         [███░░░░░░░] 20% (1/5 closed)
M6 - Docker:             [█████░░░░░] 50% (1/2 closed)
M7 - Live-Test:          [░░░░░░░░░░] 0% (0/2 closed)
M8 - Hardening:          [█████░░░░░] 50% (2/4 closed)
M9 - Release 1.0:        [░░░░░░░░░░] 0% (0/0 closed)
```

---

## 🔗 Quick Links

Nach Setup verfügbar:

- **Project Board**: https://github.com/users/jannekbuengener/projects/[PROJECT_NUMBER]
- **Milestones**: https://github.com/jannekbuengener/Claire_de_Binare_Cleanroom/milestones
- **Issues**: https://github.com/jannekbuengener/Claire_de_Binare_Cleanroom/issues

---

## ✅ Verifizierung

Nach Setup prüfen:

```bash
# Issues mit Project verknüpft?
gh issue list --json number,projectItems --jq '.[] | select(.projectItems | length > 0) | .number'

# Erwartung: 20 Issues
```

---

## 🛠️ CLI-Alternative (nach Auth-Refresh)

Falls `gh auth refresh -s project` funktioniert:

```bash
# 1. Project erstellen
PROJECT_ID=$(gh project create \
  --owner @me \
  --title "Claire de Binare - N1 Roadmap" \
  --format json | jq -r '.id')

# 2. Alle Issues hinzufügen
gh issue list --limit 100 --json url | jq -r '.[] | .url' | while read url; do
  gh project item-add $PROJECT_ID --owner @me --url "$url"
done

# 3. View konfigurieren (via Web-UI)
```

---

**Erstellt**: 2025-11-20
**Projekt**: Claire de Binare
**Phase**: N1 - Paper-Test
