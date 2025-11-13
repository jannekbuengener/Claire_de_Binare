# Sicherheitsrisikobericht

| ID | Titel | Schweregrad | Fundstelle | Impact | Exploitability | Fix | Nachweis |
|----|-------|-------------|------------|--------|----------------|-----|----------|
| SR-001 | Redis ohne Auth & Host-Expose | 🔴 | docker-compose.yml:12-31, .env:30-37 | Vollständiger Zugriff auf Message-Bus; Manipulation von `orders`/`signals` möglich | Hoch – Port 6380 offen, kein Passwort erforderlich | `--requirepass` mit verpflichtendem Secret, Port auf Loopback gebunden | `rg -n "redis-server" docker-compose.yml` |
| SR-002 | Postgres Passwort-Fallback | 🔴 | docker-compose.yml:30-40, .env:56-63 | DB-Komplettübernahme, Manipulation von Trades/Orders, Datenabfluss | Hoch – bekannter Default `cdb_secure_password_2025` verwendbar | Fallback entfernt, Secret über `.env` verpflichtend | `rg -n "POSTGRES_PASSWORD" docker-compose.yml .env` |
| SR-003 | Grafana Admin-Standardpasswort | 🟠 | docker-compose.yml:78-86, .env:36-44 | Admin-Übernahme, Dashboard-Manipulation, Credential-Leak | Hoch – Default `admin123` bekannt, Login ohne Rate-Limit | Secret zwingend via `.env`, Operator muss starkes Passwort setzen | `rg -n "GF_SECURITY_ADMIN_PASSWORD" docker-compose.yml` |
| SR-004 | Execution-Service läuft als Root ohne Hardening | 🟠 | backoffice/services/execution_service/Dockerfile:1-40, docker-compose.yml:176-205 | Container-Escape-Risiko via Python/psycopg2 Exploit, Dateisystem-Manipulation | Mittel – Service exponiert Flask-Endpunkte, mehrere Third-Party-Module | Non-Root-User, Cap-Drop, `no-new-privileges`, Read-Only Root-FS | `rg -n "no-new-privileges" docker-compose.yml` |

## STRIDE-Zuordnung

- SR-001: Tampering, Spoofing, Denial of Service
- SR-002: Tampering, Information Disclosure, Elevation of Privilege
- SR-003: Information Disclosure, Tampering
- SR-004: Elevation of Privilege, Tampering, Repudiation

## Status 2025-10-25

Alle oben genannten Risiken wurden mit den beigefügten Patches mitigiert; Rest-Risiko besteht nur bei nicht rotierten Secrets.
