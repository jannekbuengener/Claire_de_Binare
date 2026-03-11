---
relations:
  role: working_memory
  domain: knowledge
  upstream:
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_GOVERNANCE.md
    - knowledge/governance/CDB_AGENT_POLICY.md
  downstream: []
  status: active
  tags: [working_memory, agent_collaboration, temporary]
---
# SHARED.WORKING.MEMORY
**CDB – Shared Working Memory Layer**

Version: 1.2  
Status: Non-Canonical / Agent-Writable  
Charakter: Flüchtig, explorativ, nicht bindend

---

## 0. Rangordnung & Systemeinordnung

Diese Datei ist **nicht-kanonisch** und unterliegt strikt der Rangordnung:

1. `governance/CDB_CONSTITUTION.md`  
2. `governance/CDB_GOVERNANCE.md`  
3. `governance/CDB_AGENT_POLICY.md`

Sie ist ausdrücklich:
- ❌ keine Governance
- ❌ kein kanonisches Wissen
- ❌ kein Entscheidungsartefakt
- ❌ kein Audit- oder Logbuch

**Merksatz:** Eintrag ≠ Wahrheit ≠ Entscheidung.

---

## 1. Zweck

`SHARED.WORKING.MEMORY.md` ist der **gemeinsame Denk- und Arbeitsraum** für Agenten/Modelle, um:

- Zwischenstände festzuhalten (Skizzen, Hypothesen, Notizen)
- Abhängigkeiten sichtbar zu machen
- Parallel-Work zu synchronisieren
- Entscheidungen vorzubereiten (nicht zu treffen)

> Hier darf gedacht werden. Behalten wird woanders.

---

## 2. Was diese Datei IST

Diese Datei ist:
- ein temporärer **kognitiver Synchronisationsraum**
- ein **Arbeitskontext**, kein Wissensspeicher
- ein Ort für unfertige Gedanken und verworfene Optionen

**Stabilität ist nicht das Ziel.**

---

## 3. Was diese Datei NICHT ist

Diese Datei ist nicht:
- System- oder Langzeitgedächtnis → `governance/NEXUS.MEMORY.yaml`
- Entscheidungslog / Change-Proposal → `knowledge/CDB_KNOWLEDGE_HUB.md`
- Dokumentation (How-To / Architektur)
- Status-Übersicht (Current Status / Roadmap)
- Taskliste als Quelle der Wahrheit
- Secrets-/Key-Ablage

Alles, was bestätigt, stabil oder bindend ist, gehört **nicht** hierher.

---

## 4. Zugriffsrechte

### 4.1 Lesen
- alle Agenten / Modelle
- Session Lead
- User

### 4.2 Schreiben
- ✅ alle Agenten (parallel, ohne Vorab-Freigabe)
- ✅ auch im Analysis Mode

### 4.3 Einschränkungen (hart)
- ❌ kein automatischer Transfer nach `NEXUS.MEMORY`
- ❌ kein „Persistenz-Upgrade“ durch Copy/Paste in andere Kanäle
- ❌ keine implizite Autorität („steht da, also gilt das“)

---

## 5. Semantische Regeln (verbindlich)

Einträge dürfen:
- widersprüchlich sein
- unfertig sein
- überschrieben oder verworfen werden

**Wahrheit ist optional. Nützlichkeit ist Pflicht.**

---

## 6. Beitragsformat (empfohlen)

```md
### [Agent/Modell | YYYY-MM-DD HH:MM]
- Kontext:
- Beobachtung:
- Hypothese / Idee:
- Auswirkungen (Impact):
- Risiken / Unsicherheiten:
- Nächster Schritt (konkret):
- Links/Artefakte:
```

---

## 7. Beziehung zu anderen Ebenen

| Ebene | Zweck | Schreibrechte | Charakter |
|---|---|---|---|
| `knowledge/SHARED.WORKING.MEMORY.md` | Denken & Synchronisieren | Agenten | flüchtig |
| `knowledge/CDB_KNOWLEDGE_HUB.md` | Entscheiden & Beauftragen | Session Lead | versioniert |
| `governance/NEXUS.MEMORY.yaml` | Erinnern (stabilisiertes Wissen) | User + Lead | langfristig |

**Regel:** Kein Übergang erfolgt automatisch. Jeder Transfer ist bewusst und manuell.

---

## 8. Löschung & Vergessen

Vergessen ist erwünscht.

Einträge dürfen jederzeit:
- gelöscht
- zusammengefasst
- ersetzt
- verworfen

---

## 9. Sicherheitsprinzip

Diese Datei darf das System **klüger**, aber niemals **mächtiger** machen.

Kein Eintrag darf:
- Execution auslösen
- Policies verändern
- Limits umgehen
- Secrets enthalten oder indirekt reproduzierbar machen

---

## 10. Abschlussregel

Wenn etwas:
- stabil ist
- bewiesen ist
- systemweit gelten soll

→ **raus aus dieser Datei** (in Knowledge Hub / NEXUS / Governance – je nach Rang).

Dies ist ein Denkraum. Kein Gedächtnis. Kein Gesetz.
