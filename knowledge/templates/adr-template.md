# ADR-NNN: Titel der Entscheidung

> **Hinweis**: Ersetze "NNN" mit der nächsten fortlaufenden Nummer.
> Finde die letzte Nummer mit: `ls -1 knowledge/decisions/ADR-*.md | sort -V | tail -1`

## Status

**[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]**

- Proposed: Entscheidung ist vorgeschlagen, noch in Diskussion
- Accepted: Entscheidung ist akzeptiert und wird umgesetzt
- Deprecated: Entscheidung ist nicht mehr relevant
- Superseded: Entscheidung wurde durch ADR-XXX ersetzt

## Kontext

Beschreibe die Situation, die diese Entscheidung erforderlich macht:
- Was ist das Problem oder die Herausforderung?
- Welche Faktoren beeinflussen die Entscheidung?
- Welche Constraints existieren?
- Warum ist jetzt der richtige Zeitpunkt für diese Entscheidung?

## Entscheidung

Beschreibe klar und präzise die getroffene Entscheidung:
- Was haben wir entschieden zu tun?
- Welchen Ansatz werden wir verfolgen?
- Was sind die Kernpunkte der Entscheidung?

## Konsequenzen

### Positive Konsequenzen
Liste die Vorteile dieser Entscheidung:
- Welche Probleme werden gelöst?
- Welche Verbesserungen ergeben sich?
- Welche neuen Möglichkeiten eröffnen sich?

### Negative Konsequenzen
Liste die Nachteile oder Trade-offs:
- Welche Einschränkungen entstehen?
- Welche Probleme könnten auftreten?
- Was müssen wir in Kauf nehmen?

### Neutrale Konsequenzen
Liste sonstige Auswirkungen:
- Was ändert sich sonst noch?
- Welche Bereiche sind betroffen?

## Alternativen

Beschreibe die erwogenen Alternativen und warum sie nicht gewählt wurden:

### Alternative 1: [Name]
- Beschreibung der Alternative
- Vorteile
- Nachteile
- Grund für Ablehnung

### Alternative 2: [Name]
- Beschreibung der Alternative
- Vorteile
- Nachteile
- Grund für Ablehnung

### Option "Nichts tun"
- Was würde passieren, wenn wir keine Entscheidung treffen?
- Warum ist dies keine Option?

## Implementierung

Optional: Beschreibe wie diese Entscheidung umgesetzt wird:
- Welche Schritte sind notwendig?
- Wer ist verantwortlich?
- Welcher Zeitrahmen?

## Referenzen

Liste relevante Dokumente, Diskussionen oder Ressourcen:
- Links zu verwandten ADRs
- Governance-Dokumente
- Externe Quellen
- Issue- oder PR-Links

## Metadaten

- **Autor**: [Name oder Agent]
- **Datum**: YYYY-MM-DD
- **Reviewer**: [Name(n)]
- **Kategorie**: [architecture | governance | documentation | etc.]
- **Tags**: #tag1 #tag2 #tag3

---

**Nach dem Erstellen nicht vergessen**:
1. Datei benennen: `ADR-NNN-kurzer-titel.md`
2. In `knowledge/decisions/` speichern
3. `knowledge/index.yaml` aktualisieren
4. Pull Request erstellen mit Tag `knowledge`
