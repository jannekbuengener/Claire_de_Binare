# Verfassung des Claire de Binare Systems

## Präambel

Dieses Dokument definiert die grundlegenden Prinzipien und Strukturen des Claire de Binare (CDB) Systems.

## Artikel I: Zweck und Geltungsbereich

### §1 Systemidentität
Das Claire de Binare System ist ein agentengesteuertes Governance- und Wissensmanagementsystem.

### §2 Repository-Zweck
Dieses Repository (`Claire_de_Binare_Docs`) dient ausschließlich als:
- Zentraler Governance-Hub
- Wissens- und Entscheidungsdokumentation
- Agentensteuerungs- und Koordinationszentrale
- Langzeit-Memory für systemweites Wissen

### §3 Strikte Trennung
**Absolutes Verbot**: Dieses Repository darf KEINEN der folgenden Inhalte enthalten:
- Anwendungscode (außer Beispiele in Dokumentation)
- Ausführbare Services oder Skripte
- Infrastruktur-Definitionen (außer Dokumentation darüber)
- Build-Artefakte oder Dependencies
- Binärdateien oder kompilierter Code

## Artikel II: Erlaubte Inhalte

### §1 Dokumentationstypen
Folgende Inhalte sind ausschließlich erlaubt:
- **Markdown-Dateien (.md)**: Für alle textuelle Dokumentation
- **YAML-Dateien (.yaml, .yml)**: Für strukturierte Governance-Daten

### §2 Inhaltskategorien
Erlaubte Dokumentationskategorien:
1. **Governance-Richtlinien**: Regeln, Prozesse, Entscheidungsrahmen
2. **Agenten-Charter**: Rollendefinitionen, Verantwortlichkeiten, Befugnisse
3. **Wissensstrukturen**: Entscheidungsaufzeichnungen, Architekturwissen
4. **Dokumentations-Indizes**: Strukturierung und Navigation

## Artikel III: Governance-Struktur

Zusatz: Agenten-Autonomie wird über ein Trust-Score-System gesteuert (auditierbar).
Referenz: `CDB_TRUST_SCORE_POLICY.md`, Ledger: `knowledge/agent_trust/ledger/`.

### §1 Hierarchie
```
knowledge/governance/          - Verfassung und Grundregeln
agents/             - Agenten-Charter und Rollen
knowledge/          - Wissensbasis und Entscheidungen
docs/               - Dokumentationsindex und Templates
```

### §2 Änderungskontrolle
Alle Änderungen unterliegen der Agenten-Governance mit strikten:
- Schreibrechten
- Review-Prozessen
- Freigaberegeln

## Artikel IV: Gültigkeit

Diese Verfassung ist bindend für alle Interaktionen mit diesem Repository.

---
**Version**: 1.0.0  
**Status**: Gültig  
**Letzte Änderung**: 2025-12-16
