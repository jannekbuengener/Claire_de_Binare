# Hermes app.HERMES live mint + canary evidence (#4289)

Status date: 2026-08-04
LR: NO-GO
Target status: DONE_HERMES_GITHUB_APP_CANARY_PR_OPEN

## GitHub App Identity

- App-Name: `app.HERMES`
- App-ID: `4480891`
- Current App Slug (live): `app-hermes`
- Owner: `jannekbuengener`
- PEM SHA256 (file fingerprint only): `C13B2271470792F2C2C8EF7B1F7D50A72916574898F3A255E72A02B049C2CA11`

## Installation and Permissions

- Installation-ID: `151136371`
- Repository selection: `all` (prefer narrow to Claire_de_Binare later)
- Claire_de_Binare access: PASS
- Live permission map (names only):
  - contents: write
  - pull_requests: write
  - issues: write
  - metadata: read
  - checks: read
  - actions: read
  - administration: read (not write)
- Forbidden critical writes absent: checks/statuses/administration/secrets/actions write = PASS

## Credential Transfer / Host Isolation

- Host: `cdb-hermes-01`
- PEM host path: `/etc/hermes/secrets/cdb-hermes-engineer.pem` (root:root 0600)
- Host PEM SHA256 matches local fingerprint: PASS
- Env: `/etc/hermes/cdb-engineer.env` (root:hermes-cdb-engineer 0640) with `HERMES_GH_APP_*` only
- Bundle: `/opt/cdb-hermes-bundle` (token broker + ci publisher libs)
- Cross-profile PEM read deny (assistant + engineer UIDs): PASS (exit 1)
- sshd was disabled post-reboot; re-enabled during controlled Rescue hop
- Temporary public /32 SSH FW rules used only during Rescue; cleared to deny-inbound afterward

## Token Broker / Live Mint

- Unit: `hermes-github-token.service`
- Expected App-ID: 4480891
- Hard-reject App-ID 4410232: PASS (`AuthenticationError: App 4410232 ... forbidden`)
- Host mint journal: `ok: true`, permissions contents/issues/pull_requests write, metadata read, token `[REDACTED]`, token_file `/run/hermes/cdb-engineer/token` mode 0600
- Note: oneshot `ExecStopPost` removes token when unit deactivates; `RemainAfterExit` restgap documented below
- Canary GitHub writes use a short-lived installation token minted with App-ID 4480891 + same PEM (never logged)

## Negative App-ID 4410232 Test

- `resolve_hermes_app_id` with `HERMES_GH_APP_ID=4410232` → REJECT_OK

## Canary Validation

- Branch: `hermes/canary-4289-github-app`
- Base: current `origin/main`
- Change: this redacted evidence file only
- Non-goals: no merge, no issue close, no cdb-local-ci publish, no trading, no secrets in tree

## Restunsicherheiten

- `repository_selection=all` broader than preferred `Only select repositories`
- Host oneshot token lifetime vs `ExecStopPost` without `RemainAfterExit=yes`
- Host bundle initially incomplete (`ci.lib` / `ci.__init__`); repaired under Rescue
- Commit bot email derived from live slug (not a separate repo SSOT)

## Safety Boundaries

- LR remains NO-GO
- App 4480891 is not Live/Echtgeld/merge-bypass/CI publisher
- App 4410232 remains cdb-local-ci only
