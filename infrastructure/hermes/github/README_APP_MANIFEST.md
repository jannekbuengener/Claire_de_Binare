# Create GitHub App from Manifest (Owner one-click) — #4289 B2.1

Do **not** reuse App `4410232` (`cdb-local-ci`).

## Manifest

File: `infrastructure/hermes/github/cdb-hermes-engineer.manifest.json`

Permissions (only):
- `metadata:read`
- `contents:write`
- `pull_requests:write`
- `issues:write`

Forbidden: admin, actions, checks, statuses, secrets, workflows, administration.
Webhooks: inactive / unused URL (GitHub requires a URL field).

## Owner steps (once)

1. Open GitHub → Settings → Developer settings → GitHub Apps → **New GitHub App**
   or use the Manifest POST flow with the JSON above.
2. Confirm the app name `cdb-hermes-engineer`.
3. Generate a **private key** once; store outside the repo at the operator secrets path
   (never commit; never paste into issues/PRs/chat).
4. Install the app **only** on `jannekbuengener/Claire_de_Binare`.
5. Record App ID + Installation ID into host `/etc/hermes/cdb-engineer.env` as
   `HERMES_GH_APP_ID` / `HERMES_GH_APP_INSTALLATION_ID` (not `CDB_GH_APP_*`).
6. Place PEM on host as `/etc/hermes/secrets/cdb-hermes-engineer.pem`
   (`root:root` `0600`) via a controlled root path — not through dashboards.

## Agent note

OAuth `gh` scopes (`repo`/`workflow`) cannot create GitHub Apps. Manifest/UI
confirmation is an Owner capability gate, not a missing Plan-GO.
