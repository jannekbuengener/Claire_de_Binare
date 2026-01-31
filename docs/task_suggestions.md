# Task-Vorschläge (Codebasis-Review)

1. **Tippfehler beheben:** In `cdb_agent_sdk/README.md` steht die Überschrift "Programmatisch mit Options". Korrektur auf "Programmatisch mit Optionen".
2. **Programmierfehler beheben:** In `core/domain/models.py` und `services/risk/models.py` setzt `Signal.__post_init__` `side = direction`, wodurch bei `direction="LONG"` ein ungültiger `side`-Wert entsteht. Korrigieren durch Normalisierung/Mapping auf `BUY`/`SELL` oder keine Übernahme.
3. **Kommentar/Dokumentation konsistent machen:** `PROJECT_STATUS.md` beschreibt den Market Service als "PRODUCTION-READY", während `services/market/service.py` als STUB/TEMPLATE markiert ist. Status aktualisieren oder Implementation nachziehen.
4. **Test verbessern:** `tests/unit/market/test_service.py` enthält ausschließlich `@pytest.mark.skip`-Platzhalter. Task: Implementiere mindestens einen echten Unit-Test (z. B. Health-Endpoint oder Konfig-Validierung).
