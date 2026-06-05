# Replay tests (`tests/replay/`)

Tests für deterministische Replay-, Envelope- und Report-Pfade unter [`core/replay/`](../../core/replay/).

## Marker

- Kein separates pytest-Marker `replay` in allen Dateien; Ordner ist die Konvention.
- CI: Teil von `make test` / `make test-unit` je nach Datei-Markern.

## Commands

```bash
pytest -v tests/replay/
pytest -v tests/unit -k "replay"
```

## Container

| Modus | Stack |
|---|---|
| Unit/Replay (default) | Kein Stack |
| E2E mit Replay-Pfad | `make docker-up` + `@pytest.mark.e2e` |

## Related

- [`core/replay/README.md`](../../core/replay/README.md)
- [`tests/integration/README.md`](../integration/README.md)
