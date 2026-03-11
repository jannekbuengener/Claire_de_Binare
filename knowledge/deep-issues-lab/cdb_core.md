# IST-ZUSTAND: cdb_core

**ID:** `cdb_core`
**Typ:** Interne Bibliothek (Shared Library)
**Technologie:** Python

---

## 1. Kurzbeschreibung

`cdb_core` ist keine eigenständig lauffähige Anwendung, sondern eine zentrale Python-Bibliothek, die von allen anderen Services innerhalb des `Claire_de_Binare`-Projekts als Abhängigkeit genutzt wird. Sie bündelt Code, der systemweit geteilt wird, insbesondere Domänenmodelle, Event-Strukturen und grundlegende Utility-Funktionen. Ihr Ziel ist es, Code-Duplizierung zu vermeiden und eine kanonische, einheitliche Definition der wichtigsten Datenstrukturen und Konzepte sicherzustellen.

## 2. Kernfunktionen & Verantwortlichkeiten

- **Kanonische Datenmodelle (`core.domain.models`):** Definiert die `dataclass`-basierten Standard-Strukturen für `Signal`, `Position`, `Order` und `OrderResult`. Dies stellt sicher, dass alle Services die gleiche "Sprache" sprechen, wenn sie Daten austauschen.
- **Event-Sourcing-Grundlage (`core.domain.event`):** Stellt eine `Event`-Basisklasse bereit, die für das Event-Sourcing-Muster im System unerlässlich ist. Sie erzwingt wichtige Governance-Regeln wie Unveränderlichkeit und deterministische Replay-Fähigkeit durch Hash-Validierung.
- **Zentrales Secret Management (`core.domain.secrets`):** Bietet eine `get_secret`-Funktion, die den Zugriff auf Docker Secrets (mit Fallback auf Umgebungsvariablen) standardisiert. Dadurch wird die Handhabung von sensiblen Daten in allen Services vereinheitlicht.
- **Abstraktion für Determinismus (`core.utils`):**
    - `clock.py`: Stellt Uhren-Klassen (`Clock`, `FixedClock`) zur Verfügung, die es ermöglichen, die Zeit in Tests und Simulationen zu kontrollieren.
    - `uuid_gen.py`: Ermöglicht die Erzeugung von deterministischen UUIDs, was für das Replay von Event-Strömen kritisch ist.
    - `seed.py`: Stellt einen `SeedManager` bereit, um die Zufallszahlengenerierung für Tests und Simulationen reproduzierbar zu machen.

## 3. Architektur & Integration

- **Integration als Abhängigkeit:** `cdb_core` wird nicht als eigener Service im Docker-Stack ausgeführt. Stattdessen wird der `core`-Ordner direkt in die Docker-Images der anderen Services (z.B. `cdb_db_writer`, `cdb_execution`) kopiert (`COPY core /app/core`). Dies macht die Funktionalität von `core` als lokales Python-Modul für diese Services verfügbar.
- **Struktur:**
    - `core/domain`: Enthält den "Business-Kern" – die Definitionen von Daten, Events und die Logik zum Umgang mit Secrets.
    - `core/utils`: Beinhaltet technische Hilfsfunktionen, die für die Umsetzung der übergeordneten Architekturprinzipien (v.a. Determinismus) erforderlich sind.
    - `core/config`: Derzeit leer, aber wahrscheinlich für zukünftige, systemweit geteilte Konfigurationen vorgesehen.
- **Governance-Bezug:** Die Module in `core` (insbesondere `event.py`, `clock.py`, `uuid_gen.py`) sind die direkte technische Umsetzung der in `CDB_PSM_POLICY.md` festgelegten Architekturprinzipien für Event-Sourcing und deterministische Replay-Fähigkeit.

## 4. Status & Bewertung

- **Zustand:** Gut strukturiert und fundamental für die Architektur des Gesamtsystems.
- **Stärken:**
    - **Single Source of Truth:** `cdb_core` ist die alleinige Wahrheitsquelle für die wichtigsten Datenstrukturen. Änderungen an einem `Order`-Objekt müssen nur hier vorgenommen werden.
    - **Fördert Konsistenz:** Erzwingt eine konsistente Implementierung von Kernfunktionen wie Secret Management und Event-Erstellung über alle Services hinweg.
    - **Testbarkeit:** Die Utilities in `core.utils` sind entscheidend, um das System testbar und deterministisch zu machen, was für einen Trading-Bot von höchster Wichtigkeit ist.
- **Potenzielle Risiken/Schwächen:**
    - **Kopplung:** Da alle Services von `core` abhängen, kann eine Änderung in `core` potenziell Updates in allen Services erfordern. Dies ist jedoch ein bewusster Trade-off für die gewonnene Konsistenz.
    - **Distribution:** Die aktuelle Methode, den `core`-Ordner per `COPY` in andere Images zu kopieren, ist einfach, aber nicht sehr elegant. In einem größeren System könnte `core` als eigenständiges, versioniertes Python-Paket in einer privaten Registry (z.B. PyPI Server, GitLab Package Registry) veröffentlicht werden. Dies würde die Verwaltung von Versionen und Abhängigkeiten formalisieren.

**Fazit:** `cdb_core` ist das Rückgrat der Anwendungsarchitektur. Es setzt zentrale Governance-Richtlinien technisch um und stellt die Konsistenz und Testbarkeit des gesamten Systems sicher. Die aktuelle Distributionsmethode ist pragmatisch, könnte aber in Zukunft durch ein formales Paketmanagement ersetzt werden.

