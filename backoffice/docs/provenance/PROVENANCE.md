# PROVENANCE.md -- Kompakte Provenance-Matrix für KI

Dieses Dokument beschreibt die minimale, maschinenrelevante
Provenance-Struktur des Claire de Binare-Systems. Alle menschlichen
Prozessberichte wurden entfernt. Es bleiben ausschließlich
deterministische, KI-relevante Herkunftsangaben.

------------------------------------------------------------------------

## 📌 Canonical Sources

Die Datei **CANONICAL_SOURCES.yaml** definiert weiterhin die
autoritativen Ursprungsquellen. Diese Datei dient ausschließlich als
Hash- und Mapping-Ergänzung.

------------------------------------------------------------------------

## 📁 Kern-Provenance-Einträge

### 1. ARCHITEKTUR.md

-   source: `docs/ARCHITEKTUR.md`
-   target: `docs/architecture/ARCHITEKTUR.md`
-   sha256:
    `9eb3e13ac7487f31b2eb7c92e640162649bddb7e8ed533bdeb235cc297e23540`
-   status: identical

### 2. RISK_LOGIC.md

-   source: `docs/Risikomanagement-Logik.md`
-   target: `docs/security/RISK_LOGIC.md`
-   sha256:
    `faf05cec5332dbfc63d6ec89c54181d236990d12b096278c25a9db634313f0f7`
-   status: identical

### 3. RUNBOOK_DOCKER_OPERATIONS.md (entfernt)

-   source: `docs/ops/RUNBOOK_DOCKER_OPERATIONS.md`
-   target: removed
-   sha256:
    `25f850ad3740169c188b3fdc995c94f5917e88ec017cd632c217ef6e7b8aa3b4`
-   status: removed (irrelevant)

------------------------------------------------------------------------

## 🔄 Provenance-Status

-   Validiert am: 2025-11-13
-   Hash-Konsistenz: 100 %
-   Abweichungen: keine
-   Nicht-KI-relevante Provenance-Reports: entfernt

------------------------------------------------------------------------

## 🎯 Zweck

Ermöglicht der KI: - Herkunft zu verifizieren - Hash-basierte Konsistenz
sicherzustellen - autoritative Dokumentquellen zu priorisieren

Dies ist die einzige notwendige Provenance-Datei zusätzlich zu
`CANONICAL_SOURCES.yaml`.
