# GOVERNANCE_QUICKREF - Governance-Regeln Kurzreferenz

**Version:** 1.0
**Erstellt:** 2025-12-28
**Status:** Kanonisch
**Pruefintervall:** Bei jedem Session-Start

---

## 1. Hierarchie (nicht verhandelbar)

| Rang | Dokument | Zweck |
|------|----------|-------|
| 1 | **User (Jannek)** | Oberste Autoritaet, ueberschreibt alles |
| 2 | CDB_CONSTITUTION.md | Systemverfassung |
| 3 | CDB_GOVERNANCE.md | Governance-Regeln |
| 4 | CDB_AGENT_POLICY.md | Agenten-Verhalten |
| 5 | Spezifische Policies | CDB_*_POLICY.md |
| 6 | AGENTS.md | Agenten-Registry |
| 7 | Agent-Rollendateien | CLAUDE.md, GEMINI.md, etc. |
| 8 | Implementierung | Code, Config, IaC |

---

## 2. Delivery Gate (absolut)

**Regel:** Kein Live-Deployment ohne explizites Gate.

**Datei:** `governance/DELIVERY_APPROVED.yaml`

```yaml
# Nur wenn approved: true
approved: true
approved_by: "Jannek"
approved_at: "2025-12-XX"
mode: "paper"  # oder "live"
```

**Pruefung:**
- CI-Workflow `delivery-gate.yml` prueft dieses Gate
- Paper Trading ist Default (MOCK_TRADING=true)
- Live Trading erfordert: approved: true UND mode: live

---

## 3. Agenten-Verhalten (Kurzform)

### MUSS
- User-Entscheidungen respektieren
- Bei Unklarheit: STOP und fragen
- Context Core bei Session-Start laden
- GitHub Issues am Session-Ende pflegen

### DARF NICHT
- Autonome Entscheidungen gegen User
- Governance ohne Freigabe aendern
- Secrets committen
- Delivery Gate ohne User aendern

---

## 4. Schreibrechte

### Docs Repo (Claire_de_Binare_Docs)
| Pfad | Rechte | Bedingung |
|------|--------|-----------|
| knowledge/** | Read + Write | Fuer operative Doku |
| agents/** | Read + Write | Fuer Rollendefinitionen |
| governance/** | Read Only | Nur mit expliziter Freigabe |

### Working Repo (Claire_de_Binare)
| Pfad | Rechte | Bedingung |
|------|--------|-----------|
| services/*, core/* | Read + Write | Nach CDB_AGENT_POLICY |
| governance/* | Read Only | Canon-Dokumente |
| .cdb_local/** | Read + Write | Lokale Konfiguration |

---

## 5. Absolute NO-GOs (nicht verhandelbar)

1. **NIEMALS** Secrets committen
   - Secrets gehoeren in `~/.secrets/.cdb/`
   - Niemals in `.env`, niemals in Git

2. **NIEMALS** Delivery Gate ohne User aendern
   - DELIVERY_APPROVED.yaml ist human-only

3. **NIEMALS** autonome Kapitalbewegungen
   - Paper Trading ist Default
   - Live Trading erfordert explizites Gate

4. **NIEMALS** Canon-Dateien im Working Repo erstellen
   - Canon liegt im Docs Repo
   - Working Repo = Code + Runtime

5. **NIEMALS** ohne Context Core arbeiten
   - Erst laden, dann handeln

---

## 6. Konfliktaufloesung

Bei Widerspruechen:
1. Hoeherer Rang gewinnt (siehe Hierarchie)
2. User-Entscheidung ueberschreibt alles
3. Bei Unklarheit: **STOP & FRAG JANNEK**

---

## 7. Session-Ende Pflichten

Keine Session ist abgeschlossen ohne:
- [ ] CURRENT_STATUS.md aktualisiert
- [ ] Mindestens ein GitHub Issue erstellt/aktualisiert
- [ ] Blocker explizit benannt oder geloest
- [ ] Session-Log in knowledge/logs/sessions/

---

## Changelog

| Datum | Aenderung | Durch |
|-------|-----------|-------|
| 2025-12-28 | Initiale Erstellung via Context Core Build Sprint | Claude (Orchestrator) |
