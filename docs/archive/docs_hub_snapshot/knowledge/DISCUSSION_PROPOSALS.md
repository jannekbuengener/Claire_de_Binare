# Deep Issues - Diskussionsvorschläge

Dieses Dokument sammelt Themen, Widersprüche und ungelöste Fragen aus der Deep Research-Bibliothek, um sie in handfeste Entwicklungsziele zu überführen.

---

## Vorschlag 1: Vereinheitlichung des CDB Master Safety Frameworks

**Problem:**
Mehrere Deep-Research-Dokumente (`RL-Safety Framework`, `Tresor-Regel`, `APE-Architektur`, `Hard Constraints`, `Action Masking`) beschreiben sich überschneidende Sicherheits- und Risikomodelle. Eine explizite, kanonische Integration in einen einzigen Gesamtrahmen fehlt, was zu Redundanzen, potenziellen Konflikten und unklarer Verantwortlichkeit führen kann.

**Ziel:**
-   Definition eines vereinheitlichten **"CDB Master Safety Frameworks"**, das alle bestehenden und vorgeschlagenen Sicherheitskonzepte integriert.
-   Klärung der Hierarchie, Verantwortlichkeiten und Interaktionsmechanismen der verschiedenen Sicherheits-Layer (z.B. APE Policy Stack, RL-Safety-Modell, Tresor-Regel).
-   Erstellung einer finalen, kohärenten Architektur-Skizze, die alle Sicherheitskomponenten und deren Fluss abbildet.

**Nicht-Ziele:**
-   Neuentwicklung individueller Sicherheitsmechanismen.
-   Detaillierte Implementierungspezifikationen einzelner Komponenten.

**Risiken / Nebeneffekte:**
-   **Over-Engineering:** Ein zu komplexes, allumfassendes Framework könnte schwer umsetzbar, wartbar und schwerfällig werden.
-   **Performance-Implikationen:** Eine Kaskade von Sicherheitsprüfungen könnte die Latenz der Trading-Pipeline signifikant erhöhen.
-   **Definitions-Konflikte:** Inkonsistente Terminologie oder sich widersprechende Regelwerke könnten die Systemintegrität gefährden.

**Quellen:**
- `CDB-DR-TR: Die Tresor-Regel: Sicherheitsarchitektur`
- `CDB-DR-004: CDB RL-Safety Framework`
- `CDB-DR-006: Architektur der Autonomen Policy Engine (APE)`
- `CDB-DR-H1: Spezifikation für Harte Constraints nach Risikoprofil`
- `CDB-DR-C4: Action Masking in Reinforcement Learning`

```json
{
  "title": "Diskussion: Vereinheitlichung des CDB Master Safety Frameworks",
  "type": "Research",
  "scope": "risk-modeling",
  "prio": "P1",
  "akzeptanzkriterien": [
    "Ein kanonisches Master Safety Framework ist definiert und dokumentiert.",
    "Alle bestehenden und vorgeschlagenen Sicherheitskonzepte sind eindeutig darin verortet.",
    "Eine klare Hierarchie und Interaktionsmechanismen der Sicherheits-Layer sind festgelegt."
  ],
  "stopregeln": [
    "Wenn ein Entwurf des Master Safety Frameworks vorliegt, der alle Kernanforderungen (Regulierung, Operative Sicherheit) abdeckt.",
    "Wenn die Hauptakteure (Risikomanager, Architekten, RL-Experten) Konsens über die Struktur erzielt haben."
  ],
  "sources": [
    "CDB-DR-TR: Die Tresor-Regel: Sicherheitsarchitektur",
    "CDB-DR-004: CDB RL-Safety Framework",
    "CDB-DR-006: Architektur der Autonomen Policy Engine (APE)",
    "CDB-DR-H1: Spezifikation für Harte Constraints nach Risikoprofil",
    "CDB-DR-C4: Action Masking in Reinforcement Learning"
  ]
}
```

---

## Vorschlag 2: Optimierung der Signalqualität durch Martingal-Deviation und Auto-Feature-Ranking

**Problem:**
Die Dokumente `CDB-DR-003 Handelsfrequenz & Signalqualität` und `CDB-DR-A1 Martingal-Deviation Modelle` schlagen Filtermechanismen zur Verbesserung der Signalqualität vor. `CDB-DR-A4 Auto-Feature-Ranking` bietet Methoden zur Bewertung der Relevanz von Features. Es ist unklar, wie diese Konzepte optimal kombiniert werden können, um die Balance zwischen Handelsfrequenz und Win-Rate zu optimieren und gleichzeitig Transparenz in die Signalgenerierung zu bringen. Es besteht das Risiko, zu viele oder ineffektive Filter zu implementieren.

**Ziel:**
-   Entwicklung einer integrierten Strategie zur Verbesserung der Signalqualität unter Berücksichtigung von Handelsfrequenz-Zielen.
-   Definition, wie Martingal-Deviation-Filter und Auto-Feature-Ranking-Ergebnisse in der Signal-Pipeline interagieren sollen (z.B. Vorfilter, Score-Anreicherung, dynamische Schwellen).
-   Sicherstellung der Erklärbarkeit der Signalgenerierung durch die Integration von Feature-Wichtigkeiten.

**Nicht-Ziele:**
-   Neuentwicklung individueller Martingal-Deviation-Modelle oder Feature-Ranking-Algorithmen.
-   Fokus auf die Optimierung einzelner Handelsstrategien.

**Risiken / Nebeneffekte:**
-   **Over-Filtering:** Zu viele Filter könnten zu einem Verlust valider Handelssignale führen.
-   **Latenz:** Komplexe Filter- und Ranking-Prozesse könnten die End-to-End-Latenz der Signalgenerierung erhöhen.
-   **Overfitting:** Kalibrierung der Filter auf historische Daten könnte zu schlechter Out-of-Sample-Performance führen.

**Quellen:**
- `CDB-DR-003: Optimierung von Handelsfrequenz und Signalqualität`
- `CDB-DR-A1: Analyse von Martingal-Abweichungen im algorithmischen Handel`
- `CDB-DR-A4: Auto-Feature-Ranking (KI-Light)`

```json
{
  "title": "Diskussion: Optimierung der Signalqualität durch Martingal-Deviation und Auto-Feature-Ranking",
  "type": "Research",
  "scope": "signal-processing",
  "prio": "P2",
  "akzeptanzkriterien": [
    "Eine integrierte Strategie zur Signalqualitätsverbesserung ist konzeptionell definiert.",
    "Interaktionspunkte zwischen Martingal-Deviation und Auto-Feature-Ranking in der Signal-Pipeline sind festgelegt.",
    "Metriken zur Messung des Trade-offs zwischen Handelsfrequenz und Win-Rate sind identifiziert."
  ],
  "stopregeln": [
    "Wenn ein konsolidierter Vorschlag für die Integration der Filter vorliegt.",
    "Wenn potenzielle Performance-Auswirkungen durch erste Schätzungen bewertet wurden."
  ],
  "sources": [
    "CDB-DR-003: Optimierung von Handelsfrequenz und Signalqualität",
    "CDB-DR-A1: Analyse von Martingal-Abweichungen im algorithmischen Handel",
    "CDB-DR-A4: Auto-Feature-Ranking (KI-Light)"
  ]
}
```

---

## Vorschlag 3: Adaptives Risikomanagement durch Volatilitätsregime und Drawdown-Prognose

**Problem:**
Die Dokumente `CDB-DR-B1 Lokale Volatilitätsmodelle` und `CDB-DR-B2 Volatilitätsregime und Drawdown-Prognose` beschreiben verschiedene Methoden zur Volatilitätsschätzung und zur Erkennung von Marktphasen sowie zur Drawdown-Vorhersage. `CDB-DR-C1 Adaptive Risk Intelligence` geht auf dynamische Risikomodelle ein. Es ist notwendig, diese Konzepte zu einem kohärenten, adaptiven Risikomanagement-System zu synthetisieren, das das Risikoprofil des Bots dynamisch an die Marktbedingungen anpasst. Die Herausforderung besteht darin, robuste Indikatoren für Regime-Wechsel zu definieren und diese effektiv in Positionsgrößen, Stop-Loss-Strategien und Circuit Breaker zu übersetzen.

**Ziel:**
-   Entwicklung eines adaptiven Risikomanagement-Konzepts, das Volatilitätsregime und Drawdown-Prognosen nutzt.
-   Definition von klaren Regeln, wie Regime-Wechsel (z.B. von "ruhig" zu "panisch") die Risikoparameter des Bots beeinflussen (z.B. Positionsgrößen-Anpassung, Trade-Frequenz-Reduzierung).
-   Spezifikation der Integration eines `cdb_risk_regime` Microservice und dessen Interaktion mit dem Risk Manager.

**Nicht-Ziele:**
-   Detaillierte Implementierung spezifischer Volatilitätsmodelle.
-   Fokus auf reine Performance-Optimierung ohne Risikobetrachtung.

**Risiken / Nebeneffekte:**
-   **Fehlklassifikation von Regimen:** Falsch erkannte Marktphasen könnten zu suboptimalen oder erhöhten Risiken führen.
-   **Lag in der Reaktion:** Verzögerungen bei der Erkennung von Regime-Wechseln könnten den Bot zu spät reagieren lassen.
-   **Over-Reaction:** Das System könnte auf kurzfristige Volatilitätsspitzen überreagieren und profitable Gelegenheiten verpassen.

**Quellen:**
- `CDB-DR-B1: Analyse lokaler Volatilitätsmodelle`
- `CDB-DR-B2: Volatilitätsregime und Drawdown-Prognose`
- `CDB-DR-C1: Adaptive Risk Intelligence`
- `CDB-DR-002: Analyse von Marktregimen mit HMM`
- `CDB-DR-A2: Analyse Stochastischer Marktregime`

```json
{
  "title": "Diskussion: Adaptives Risikomanagement durch Volatilitätsregime und Drawdown-Prognose",
  "type": "Research",
  "scope": "risk-management",
  "prio": "P1",
  "akzeptanzkriterien": [
    "Ein kohärentes Konzept für adaptives Risikomanagement ist definiert.",
    "Regeln für die Anpassung von Risikoparametern bei Regimewechsel sind spezifiziert.",
    "Die Architektur des `cdb_risk_regime` Microservice ist klar."
  ],
  "stopregeln": [
    "Wenn ein konsolidierter Vorschlag für das adaptive Risikomanagement vorliegt.",
    "Wenn eine erste Bewertung der Auswirkungen auf Positionsgrößen und Handelsfrequenz erfolgt ist."
  ],
  "sources": [
    "CDB-DR-B1: Analyse lokaler Volatilitätsmodelle",
    "CDB-DR-B2: Volatilitätsregime und Drawdown-Prognose",
    "CDB-DR-C1: Adaptive Risk Intelligence",
    "CDB-DR-002: Analyse von Marktregimen mit HMM",
    "CDB-DR-A2: Analyse Stochastischer Marktregime"
  ]
}
```

---

## Vorschlag 4: Strategie für den Übergang von Redis Pub/Sub zu Kafka/NATS JetStream

**Problem:**
Das Dokument `CDB-DR-C1 Adaptive Risk Intelligence` hebt die Limitierungen von Redis Pub/Sub für hochperformante, Event-Sourcing-basierte Architekturen hervor und schlägt den Übergang zu Apache Kafka oder NATS JetStream vor. Das bestehende System von *Claire de Binare* nutzt jedoch Redis Pub/Sub als zentrale Infrastruktur. Ein detaillierter Migrationspfad ist erforderlich, um einen reibungslosen Übergang zu gewährleisten, ohne die Live-Operationen zu beeinträchtigen. Dies beinhaltet die Koexistenz beider Systeme während der Übergangsphase und die Definition klarer Kriterien für die Wahl zwischen Kafka und NATS JetStream für verschiedene Anwendungsfälle.

**Ziel:**
-   Entwicklung einer Migrationsstrategie von Redis Pub/Sub zu einer resilienteren Event-Streaming-Plattform (Kafka/NATS).
-   Definition von Anwendungsfällen und Kriterien für die Auswahl zwischen Kafka und NATS JetStream (z.B. Latenz, Durchsatz, Persistenzanforderungen).
-   Spezifikation einer Architektur, die eine Koexistenz und schrittweise Migration ermöglicht, um Betriebsunterbrechungen zu minimieren.

**Nicht-Ziele:**
-   Implementierung einer neuen Messaging-Plattform von Grund auf.
-   Vollständige Neugestaltung der Microservice-Kommunikation in einem Schritt.

**Risiken / Nebeneffekte:**
-   **Datenverlust:** Unzureichende Handhabung der Datenreplikation während der Migration könnte zu Datenverlust führen.
-   **Komplexität:** Die Koexistenz und der Betrieb zweier Messaging-Systeme während der Übergangsphase erhöhen die operative Komplexität.
-   **Latenz:** Unerwartete Performance-Engpässe oder erhöhte Latenzen während der Übergangsphase oder bei der Integration neuer Komponenten.

**Quellen:**
- `CDB-DR-C1: Adaptive Risk Intelligence`
- `CDB-DR-E1-4: Policy Engine und Begleitmodule`

```json
{
  "title": "Diskussion: Strategie für den Übergang von Redis Pub/Sub zu Kafka/NATS JetStream",
  "type": "RFC",
  "scope": "infra",
  "prio": "P2",
  "akzeptanzkriterien": [
    "Eine klare Migrationsstrategie ist definiert und dokumentiert.",
    "Kriterien für die Auswahl zwischen Kafka und NATS JetStream pro Anwendungsfall sind festgelegt.",
    "Ein architektonisches Konzept für die Koexistenz und schrittweise Migration liegt vor."
  ],
  "stopregeln": [
    "Wenn ein Entwurf der Migrationsstrategie vorliegt.",
    "Wenn eine Kosten-Nutzen-Analyse der Plattformen durchgeführt wurde."
  ],
  "sources": [
    "CDB-DR-C1: Adaptive Risk Intelligence",
    "CDB-DR-E1-4: Policy Engine und Begleitmodule"
  ]
}
```

---

## Vorschlag 5: Standardisierung der Datenmodelle und Metadaten über alle Services

**Problem:**
Viele Dokumente (`CDB-DR-A4 Auto-Feature-Ranking`, `CDB-DR-F1 Feature Store`, `CDB-DR-H2 Performance Review via Policy Logs`, `CDB-DR-E1-4 Policy Engine und Begleitmodule`) beschreiben interne Datenstrukturen, Event-Formate und Metadaten (z.B. für Features, Policy-Entscheidungen, KPIs). Es besteht die Gefahr, dass sich diese Definitionen im Laufe der Entwicklung divergent entwickeln oder nicht optimal aufeinander abgestimmt sind. Eine fehlende Standardisierung erschwert die Interoperabilität, Analyse und Wartung des Systems.

**Ziel:**
-   Definition eines kanonischen Datenmodells und standardisierter Schemata (z.B. JSON Schema, Avro) für alle wichtigen Entitäten und Events im System (Features, Signale, Orders, Policy-Entscheidungen, KPIs).
-   Spezifikation eines Metadaten-Managements für Features und Modelle (z.B. Feature Store Metadatenblätter) zur Verbesserung der Erklärbarkeit und Auditierbarkeit.
-   Entwicklung eines Prozesses zur Versionierung und Evolution dieser Schemata.

**Nicht-Ziele:**
-   Direkte Implementierung eines Schema Registry.
-   Komplette Neugestaltung bestehender Datenbanktabellen.

**Risiken / Nebeneffekte:**
-   **Implementierungsaufwand:** Die Migration bestehender Datenstrukturen und die Anpassung von Services an neue Schemata kann aufwändig sein.
-   **Widerstand:** Potenzielle Herausforderungen bei der Durchsetzung der Standardisierung in dezentralen Teams oder bei bestehenden Services.
-   **Überdimensionierung:** Ein zu komplexes oder rigides Schema könnte die Agilität und Erweiterbarkeit des Systems einschränken.

**Quellen:**
- `CDB-DR-A4: Auto-Feature-Ranking (KI-Light)`
- `CDB-DR-F1: Feature Store Spezifikation`
- `CDB-DR-F3: Risiko-KPIs als Systemweite Metriken`
- `CDB-DR-H2: Performance Review via Policy Logs`
- `CDB-DR-E1-4: Policy Engine und Begleitmodule`

```json
{
  "title": "Diskussion: Standardisierung der Datenmodelle und Metadaten über alle Services",
  "type": "RFC",
  "scope": "architecture",
  "prio": "P2",
  "akzeptanzkriterien": [
    "Ein Vorschlag für ein kanonisches Datenmodell liegt vor.",
    "Standardisierte Schemata für Kern-Entitäten und Events sind definiert.",
    "Ein Konzept für das Metadaten-Management von Features und Modellen ist erstellt."
  ],
  "stopregeln": [
    "Wenn ein Entwurf für ein systemweites Datenmodell und Metadaten-Standard vorliegt.",
    "Wenn eine Strategie für die Versionierung und Evolution der Schemata erarbeitet wurde."
  ],
  "sources": [
    "CDB-DR-A4: Auto-Feature-Ranking (KI-Light)",
    "CDB-DR-F1: Feature Store Spezifikation",
    "CDB-DR-F3: Risiko-KPIs als Systemweite Metriken",
    "CDB-DR-H2: Performance Review via Policy Logs",
    "CDB-DR-E1-4: Policy Engine und Begleitmodule"
  ]
}
```
