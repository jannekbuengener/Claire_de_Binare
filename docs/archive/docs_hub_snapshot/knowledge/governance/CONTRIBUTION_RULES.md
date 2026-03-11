# Beitragsregeln für Claire de Binare Docs

## Übersicht

Dieses Dokument definiert die Regeln für Beiträge zum `Claire_de_Binare_Docs` Repository.

## Grundsätze

### 1. Dokumentation und Governance ausschließlich
- **Erlaubt**: Markdown (.md) und YAML (.yaml, .yml) Dateien
- **Verboten**: Jeglicher ausführbarer Code, Infrastruktur, Services

### 2. Respekt der Governance
Alle Änderungen müssen:
- Die bestehende Governance-Struktur respektieren
- Mit der System-Verfassung übereinstimmen
- Den Repository-Richtlinien entsprechen

### 3. Agenten-Kontrolle
Änderungen an kritischen Governance-Bereichen erfordern:
- Explizite Agenten-Genehmigung
- Dokumentierte Begründung
- Review durch Governance-Verantwortliche

## Beitragsprozess

### Schritt 1: Issue erstellen (optional, aber empfohlen)
- Beschreibe die geplante Änderung
- Erkläre die Motivation
- Referenziere relevante Governance-Dokumente

### Schritt 2: Branch erstellen
```bash
git checkout -b <typ>/<beschreibung>
```

Branch-Typen:
- `knowledge/governance/` - Governance-Änderungen
- `agents/` - Agenten-bezogene Änderungen
- `knowledge/` - Wissensstrukturen
- `docs/` - Dokumentation

### Schritt 3: Änderungen durchführen

#### Erlaubte Änderungen
✅ Neue Markdown-Dokumentation hinzufügen  
✅ Bestehende Dokumentation aktualisieren  
✅ YAML-Strukturen für Governance erstellen/ändern  
✅ Wissenseinträge hinzufügen  
✅ Entscheidungen dokumentieren  
✅ Templates und Vorlagen erstellen  

#### Verbotene Änderungen
❌ Code-Dateien hinzufügen  
❌ Skripte erstellen (außer Dokumentationsbeispiele)  
❌ Infrastruktur-Definitionen  
❌ CI/CD mit Ausführungslogik  
❌ Binärdateien oder Artefakte  
❌ Package-Dependencies  

### Schritt 4: Commit Guidelines

#### Commit-Message Format
```
<typ>: <kurze Beschreibung>

<detaillierte Beschreibung>

<Governance-Referenz>
```

**Typen:**
- `governance:` - Governance-Dokumente
- `agents:` - Agenten-Charter
- `knowledge:` - Wissensbasis
- `docs:` - Dokumentation
- `structure:` - Verzeichnisstruktur

**Beispiel:**
```
governance: Update contribution rules

Fügt Klarstellungen zu erlaubten Dateitypen hinzu
und definiert den Review-Prozess genauer.

Ref: knowledge/governance/CONSTITUTION.md, Artikel II
```

### Schritt 5: Pull Request erstellen

#### PR-Titel Format
```
[<Typ>] <Kurzbeschreibung>
```

Beispiele:
- `[Governance] Aktualisierung der Verfassung`
- `[Agents] Neue Agenten-Rolle für Dokumentation`
- `[Knowledge] Entscheidungsaufzeichnung ADR-001`

#### PR-Beschreibung muss enthalten
1. **Zusammenfassung**: Was wird geändert?
2. **Motivation**: Warum ist diese Änderung notwendig?
3. **Governance-Konformität**: Welche Governance-Regeln werden erfüllt?
4. **Checklist**:
   - [ ] Nur Markdown/YAML Dateien
   - [ ] Kein ausführbarer Code
   - [ ] Konsistent mit bestehender Struktur
   - [ ] Governance-Regeln befolgt
   - [ ] Dokumentation ist klar und vollständig

### Schritt 6: Review-Prozess

#### Review-Kriterien
Reviewer prüfen:
1. **Policy-Konformität**: Entspricht der Repository-Policy?
2. **Governance-Konformität**: Folgt der System-Verfassung?
3. **Struktur**: Passt in die definierte Verzeichnisstruktur?
4. **Qualität**: Ist die Dokumentation klar und vollständig?
5. **Konsistenz**: Ist sie konsistent mit bestehenden Dokumenten?

#### Review-Rollen
- **Governance-Reviewer**: Prüft Governance-Konformität
- **Agenten-Reviewer**: Prüft Agenten-bezogene Änderungen
- **Dokumentations-Reviewer**: Prüft Qualität und Klarheit

#### Erforderliche Approvals
- Governance-Änderungen: Mindestens 1 Governance-Reviewer
- Agenten-Änderungen: Mindestens 1 Agenten-Reviewer
- Andere Dokumentation: Mindestens 1 beliebiger Reviewer

### Schritt 7: Merge
Nach erfolgreicher Review wird der PR gemerged.

## Spezielle Beitragstypen

### Neue Agenten-Charter
1. Verwende Template: `agents/charter-template.yaml`
2. Fülle alle erforderlichen Felder aus
3. Platziere in: `agents/<agent-name>.yaml`
4. Erstelle begleitende Dokumentation: `agents/<agent-name>.md`

### Entscheidungsaufzeichnungen (ADR)
1. Verwende nummerierten Namen: `knowledge/decisions/ADR-NNN-titel.md`
2. Folge ADR-Format (siehe Template)
3. Update `knowledge/index.yaml`

### Governance-Updates
1. Hohe Sorgfalt erforderlich
2. Klare Begründung notwendig
3. Explizite Governance-Approval erforderlich

## Verantwortlichkeiten

### Contributor
- Kenntnis und Einhaltung dieser Regeln
- Qualitativ hochwertige Beiträge
- Responsive bei Review-Feedback

### Reviewer
- Zeitnahe Reviews
- Konstruktives Feedback
- Sicherstellung der Policy-Einhaltung

### Maintainer
- Governance-Konsistenz wahren
- Struktur-Integrität sicherstellen
- Konfliktlösung

## Enforcement

### Bei Regelverstoß
1. **Automatisch**: `.gitignore` blockiert viele verbotene Dateien
2. **Review**: Manuelles Feedback bei Policy-Verstößen
3. **Ablehnung**: PRs mit Verstößen werden abgelehnt
4. **Anleitung**: Hilfe zur Korrektur wird gegeben

### Bei wiederholten Verstößen
- Zusätzliche Schulung zu Governance
- Engere Review-Prozesse
- Im Extremfall: Einschränkung der Beitragsrechte

## Hilfe und Fragen

Bei Unklarheiten:
1. Lies die Governance-Dokumente: `knowledge/governance/`
2. Prüfe bestehende Beispiele im Repository
3. Erstelle ein Issue mit Fragen
4. Kontaktiere Governance-Verantwortliche

---
**Version**: 1.0.0  
**Status**: Bindend  
**Letzte Änderung**: 2025-12-16
