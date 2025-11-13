---
applyTo:
  - "docker/**/*.yml"
## - "docker-compose.yml"

# Docker-/Compose-Richtlinien

## Struktur
- Services alphabetisch sortieren; abhängige Services mit `depends_on` + Healthchecks versehen.
- Ports dokumentieren und Konsistenz zu `README.md` prüfen.
- Environment-Variablen als Referenz (`${VAR}`) verwenden, keine Klartextwerte.

## Sicherheit & Compliance
- Keine Secrets in Klartext. Sensible Variablen über `.env` oder Secret-Manager.
- Healthchecks müssen `CMD-SHELL` oder `CMD` nutzen und harte Timeouts haben.
- Ressourcenlimits (`cpus`, `mem_limit`) für produktionsnahe Services setzen.

## Validierung
- Vor Merge `docker compose config` ausführen und Ergebnis dokumentieren.
- Änderungen mit Docker MCP validieren (Graph + Healthchecks).
- Für neue Services README/Monitoring aktualisieren (`Prometheus`, `Grafana`).
