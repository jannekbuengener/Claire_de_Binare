# Konsistenzbericht: Agent Policies

**Datum:** 2025-12-12
**Analysierte Dateien:** `AGENTS.md`, `CDB_*_POLICY.md`

| Datei | Befund | Schweregrad | Empfohlene Lösung |
| :--- | :--- | :--- | :--- |
| `CDB_AGENT_POLICY.md` | Version ist `0.2.0`. `CDB_POLICY_STACK_MINI.md` (Abschnitt 2) verlangt jedoch Version `≥ 1.0.0` für kanonische Dateien. Zudem fehlt das Feld `Status: Canonical` im Header. | 🟥 Kritisch | Version auf `1.0.0` anheben und `Status: Canonical` im Header ergänzen. |
| `CDB_POLICY_STACK_MINI.md` | Listet `CDB_AGENT_POLICY.md` als kanonischen Bestandteil (Punkt 3), obwohl diese die definierten Kriterien (v1.0.0) aktuell nicht erfüllt. | 🟥 Kritisch | Inkonsistenz durch Update von `CDB_AGENT_POLICY.md` beheben. |
| `AGENTS.md` | Datei ist nicht Teil des kanonischen Stacks (`CDB_POLICY_STACK_MINI.md`). Formatierung weicht stark ab. Inhalt (z.B. Rollenbeispiele) ist wertvoll, aber strukturell isoliert. | 🟧 Moderat | Relevante Inhalte (Beispielrollen) in `CDB_AGENT_POLICY.md` integrieren und `AGENTS.md` archivieren oder als "deprecated" markieren. |
| `CDB_AGENT_POLICY.md` | Header-Format weicht leicht von anderen Policies ab (fehlender Status). | 🟨 Geringfügig | Header an Standard (`Version • Date • Status`) anpassen. |

## Handlungsvorschlag

Ich kann die kritischen Inkonsistenzen **sofort beheben**:

1.  **Update `CDB_AGENT_POLICY.md`**:
    *   Version auf `1.0.0` setzen.
    *   Status `Canonical` hinzufügen.
    *   Abschnitt "Beispielrollen" aus `AGENTS.md` integrieren (unter "2. Rollenlogik").
2.  **Cleanup**:
    *   `AGENTS.md` löschen (da Inhalt migriert).

Soll ich diese Änderungen durchführen?
