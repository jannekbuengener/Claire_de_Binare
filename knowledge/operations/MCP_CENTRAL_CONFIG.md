# MCP Zentral-Konfiguration (Team)

**Location:** `D:\Dev\Config\MCP\`
**Purpose:** Gemeinsame MCP Server-Konfiguration für alle Agenten

---

## Architektur

```
D:\Dev\Config\MCP\
├── README.md
├── claire-de-binare.mcp.json (Master Config)
├── sync-to-repos.ps1 (Sync-Script)
└── [future configs]

D:\Dev\Workspaces\Repos\Claire_de_Binare\
└── .mcp.json (Kopie, kein Symlink - Windows-kompatibel)
```

**Update-Prozess:**
```powershell
# Nach Änderungen an D:\Dev\Config\MCP\claire-de-binare.mcp.json
pwsh -File D:\Dev\Config\MCP\sync-to-repos.ps1
```

---

## Verfügbare MCP Server

| Server | Package | Purpose |
|--------|---------|---------|
| **Grafana** | @leval/mcp-grafana | Dashboard/Datasource Management |
| **Postgres** | @modelcontextprotocol/server-postgres | Database Queries |
| **Time** | mcp-server-time | Timezone Operations |
| **Desktop Commander** | @wonderwhy-er/desktop-commander | File System Operations |

---

## Agent Zugriff

**Alle Agenten nutzen die zentrale Config:**
- Claude Code (Session Lead)
- Gemini (Research)
- Codex (Testing)
- Copilot (DevOps)

**Zugriff via Kopie (kein Symlink):**
```powershell
# Repos haben normale .mcp.json Dateien (kopiert vom Master)
# Update via Sync-Script nach Änderungen
D:\Dev\Workspaces\Repos\Claire_de_Binare\.mcp.json
```

**Warum keine Symlinks?**
- Symlinks auf Windows fehleranfällig (Admin-Rechte, Git-Handling)
- Normale Dateien + Sync-Script = einfacher und zuverlässiger

---

## Maintenance

### Token Rotation

**Grafana Service Account:**
```powershell
# 1. Reset admin password
docker exec cdb_grafana grafana-cli admin reset-admin-password admin

# 2. Create new service account
curl -X POST http://localhost:3000/api/serviceaccounts -H "Authorization: Bearer <grafana-admin-token>" -H "Content-Type: application/json" -d '{"name": "mcp-server", "role": "Admin"}'

# 3. Create token
curl -X POST http://localhost:3000/api/serviceaccounts/2/tokens -H "Authorization: Bearer <grafana-admin-token>" -H "Content-Type: application/json" -d '{"name": "mcp-token"}'

# 4. Update D:\Dev\Config\MCP\claire-de-binare.mcp.json
# 5. Restart alle Agenten
```

**Postgres Password:**
- Stored in Docker secrets: `D:\Dev\Documents\.secrets\.cdb\POSTGRES_PASSWORD`
- Update both secrets file and MCP config on rotation

---

## Desktop Commander Allowed Paths

**Current Configuration:**
```json
{
  "allowedDirectories": [
    "D:\\Dev\\Workspaces\\Repos\\Claire_de_Binare",
    "D:\\Dev\\Config\\MCP"
  ]
}
```

**To Update:**
```bash
# Via MCP tool
mcp__desktop-commander__set_config_value(
  key="allowedDirectories",
  value=["D:\\New\\Path", "D:\\Dev\\Config\\MCP"]
)
```

---

## Troubleshooting

### MCP Server nicht verfügbar
```bash
# 1. Verify config file exists
Test-Path D:\Dev\Config\MCP\claire-de-binare.mcp.json

# 2. Verify symlink intact
Get-Item D:\Dev\Workspaces\Repos\Claire_de_Binare\.mcp.json | Select-Object LinkType, Target

# 3. Test server
python -m mcp_server_time  # Time server
npx -y @leval/mcp-grafana  # Grafana server
```

### Grafana 401 Unauthorized
- Token expired → Regenerate using procedure above
- Service account deleted → Recreate SA + token
- Grafana container restarted → Tokens persist in SQLite DB

### Postgres Connection Failed
- Verify container running: `docker ps | grep cdb_postgres`
- Check password in MCP config matches secrets
- Test connection: `docker exec cdb_postgres psql -U claire_user -d claire_de_binare -c "SELECT version();"`

---

## Fail-closed rule for Postgres discovery

For Agent-side Postgres discovery, `claire_user` is **not** an acceptable
readonly identity. Postgres MCP must use a dedicated readonly login, preferably
`cdb_readonly`, or an explicitly approved equivalent readonly principal.

Minimum checks before any later `#1905` DB discovery:

```sql
SELECT current_database(), current_user, session_user;
```

Expected:

- `session_user = cdb_readonly`, or an explicitly approved equivalent readonly login
- `current_user = session_user` for the discovery session, unless an explicitly documented readonly role-switch pattern is approved
- effective `SELECT` on `public.correlation_ledger`
- no effective `INSERT`, `UPDATE`, or `DELETE` on `public.correlation_ledger`

`current_user` alone is not sufficient for Agent/MCP discovery acceptance,
because role switching can change it inside a session. The login identity must
also be readonly via `session_user`.

If any of these checks fail, the discovery path is **fail-closed** and no DB
discovery should proceed.

The repo-backed readonly-login canon lives in:

- `docs/runbooks/postgres_least_privilege_rls.md`
- `infrastructure/database/operator_create_readonly_login.sql`
- `infrastructure/database/verify_privileges.sql`

---

## Git Handling

**.mcp.json in .gitignore:**
```gitignore
# MCP Config (managed centrally, copied to repos)
.mcp.json
```

**Reason:**
- Tokens/Secrets in Config (Grafana, Postgres)
- Zentrale Pflege verhindert Drift zwischen Repos
- Bei Token-Rotation: 1x ändern, sync-to-repos.ps1 ausführen

---

## Security

**Secrets Management:**
- Grafana Token: In MCP config (rotierbar)
- Postgres Password: Hardcoded in MCP config (matches Docker secrets)
- Redis Password: Nur Docker, nicht in MCP config

**Access Control:**
- Desktop Commander: `allowedDirectories` schützt File System
- Postgres: Agent discovery must use a dedicated readonly login, not `claire_user`
- Grafana: Admin role nötig für Dashboard-Änderungen

---

**Last Updated:** 2026-01-01
**Maintained by:** Session Lead (Claude)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
