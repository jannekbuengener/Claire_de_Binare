# Repository-Richtlinien

## Zweck

Dieses Dokument definiert die strikten Richtlinien für das `Claire_de_Binare_Docs` Repository.

## Grundprinzip: Dokumentation und Governance Ausschließlich

### Was dieses Repository IST
✅ **Ein Dokumentations- und Governance-Hub für:**
- Systemweite Governance-Richtlinien
- Agenten-Charter und Rollenbeschreibungen
- Wissens- und Entscheidungsarchiv
- Dokumentationsstrukturen und -indizes
- Langzeit-Memory für das CDB-System

### Was dieses Repository NICHT IST
❌ **Kein Platz für:**
- Anwendungscode oder Implementierungen
- Services, APIs oder Microservices
- Infrastruktur-Code (Terraform, CloudFormation, etc.)
- CI/CD-Pipelines mit Ausführungslogik
- Build-Tools oder Package-Dependencies
- Binärdateien oder kompilierte Artefakte
- Datenbanken oder Daten-Stores
- Test-Frameworks mit ausführbarem Code

## Erlaubte Dateitypen

### Primär erlaubt
- **`.md`** (Markdown): Für alle Dokumentation
- **`.yaml` / `.yml`**: Für strukturierte Governance-Daten

### Ergänzend erlaubt
- **`.gitignore`**: Für Git-Konfiguration
- **`CODEOWNERS`**: Für Governance-Kontrolle
- **`LICENSE`**: Für Lizenzinformationen

### Verboten
Alle anderen Dateitypen sind grundsätzlich verboten, insbesondere:
- `.js`, `.ts`, `.py`, `.go`, `.java`, `.rb`, etc.
- `.sh`, `.bash`, `.ps1`, `.bat`
- `.tf`, Infrastruktur-`.yaml` (für Kubernetes/Terraform)
- `.json` (außer in Dokumentationsbeispielen)
- Binärdateien jeglicher Art

## Verzeichnisstruktur

### Obligatorische Struktur
```
/
├── README.md                    # Repository-Übersicht
├── knowledge/governance/                  # Governance-Dokumente
│   ├── CONSTITUTION.md         # System-Verfassung
│   ├── REPOSITORY_POLICY.md    # Diese Datei
│   └── CONTRIBUTION_RULES.md   # Beitragsregeln
├── agents/                      # Agenten-Governance
│   ├── README.md               # Agenten-Übersicht
│   ├── charter-template.yaml   # Charter-Vorlage
│   └── roles.yaml              # Rollendefinitionen
├── knowledge/                   # Wissensbasis
│   ├── README.md               # Wissens-Übersicht
│   ├── index.yaml              # Wissens-Index
│   └── decisions/              # Entscheidungsaufzeichnungen
└── docs/                        # Dokumentation
    ├── INDEX.md                # Dokumentations-Index
    └── templates/              # Vorlagen
```

## Änderungsprozess

### 1. Änderungen initiieren
- Nur über Pull Requests
- Klare Beschreibung der Änderung
- Referenz zu relevanter Governance

### 2. Review-Prozess
- Mindestens ein Governance-Review erforderlich
- Prüfung auf Einhaltung der Repository-Policy
- Prüfung auf Konsistenz mit bestehender Governance

### 3. Merge-Kriterien
- ✅ Nur Markdown oder YAML
- ✅ Passt in definierte Struktur
- ✅ Respektiert Agenten-Governance
- ✅ Keine Code- oder Infrastruktur-Inhalte
- ✅ Dokumentation ist klar und vollständig

### 4. Automatische Prüfungen
`.gitignore` sollte nicht-erlaubte Dateitypen ausschließen.

## Durchsetzung

### Bei Verstößen
1. **Automatisch**: `.gitignore` verhindert Commit vieler verbotener Dateien
2. **Review**: Manuelle Prüfung bei Pull Requests
3. **Ablehnung**: PRs mit verbotenen Inhalten werden abgelehnt
4. **Bereinigung**: Versehentlich eingefügte Inhalte werden entfernt

### Ausnahmen
Es gibt **keine Ausnahmen** von dieser Policy. Wenn ausführbarer Code benötigt wird, muss er in einem separaten Repository existieren.

## Verantwortlichkeit

Alle Beitragenden sind verantwortlich für:
- Kenntnis dieser Richtlinien
- Einhaltung der Dokumentations-only Policy
- Respektierung der Governance-Strukturen

---
**Version**: 1.0.0  
**Status**: Bindend  
**Letzte Änderung**: 2025-12-16
