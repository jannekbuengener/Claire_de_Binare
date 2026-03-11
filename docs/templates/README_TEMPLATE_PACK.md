# Issue Template Pack (CDB)

Enthält GitHub Issue Templates für euren Standard-Flow:

- `.github/ISSUE_TEMPLATE/standard.md`
- `.github/ISSUE_TEMPLATE/meta_cluster.md`
- `.github/ISSUE_TEMPLATE/meta_phase.md`
- `.github/ISSUE_TEMPLATE/meta_governance.md`
- `.github/ISSUE_TEMPLATE/meta_tracking.md`

Hinweis:
- Kein Soak/Shadow-Sonderregime enthalten (absichtlich).
- Ledger-Gate ist im Standard-Template und in Meta-Templates vorgesehen.

## Usage Guide (Which template when?)

### standard.md
Nutzen fuer normale Tasks/Painpoints.
- Erwartet: Context, Scope, Relations, Analysis-Comment, READY, Ledger, PRs, DoD.

### meta_cluster.md
Nutzen als Sammel-Issue fuer ein Themenpaket (z.B. PAINPOINTS-Cluster).
- Child-Issues als Checkliste
- Status-Overview Tabelle optional

### meta_phase.md
Nutzen fuer Phase-Gates (analysis / implementation / governance).
- Eingangskriterien -> GO/NO-GO -> DoD

### meta_governance.md
Nutzen fuer Policies/Prozessregeln/Doku-Normen.
- Analyse durch Agent
- READY FOR ADOPTION
- Ledger + Doku-Update

### meta_tracking.md
Nutzen fuer Koordination ohne tiefe Inhalte.
- Nur Checkliste + Fortschritt/Notes

## Conventions
- "Relates to" + Dependencies sauber pflegen.
- READY immer als klare Decision Line.
- Ledger-Eintrag bei Statuswechsel/Adoption.
- Umsetzung nur via PRs (Issue referenziert im PR).
