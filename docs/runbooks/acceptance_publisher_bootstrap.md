# Acceptance evidence publisher bootstrap — operator steps (#4505)

Status: Pre-merge wiring (repo-owned)  
Related: [`final_head_approval_eligibility.md`](final_head_approval_eligibility.md)

## Purpose

Bind trusted PR-comment publishing for acceptance envelopes to the **repo-canonical**
GitHub App `cdb-local-ci` (`app_id=4410232`, same credential lineage as
`ci.publisher` / `#4170`).

Chain:

`validate (canon schema)` → `publish (GitHub App comment)` →
`performed_via_github_app` → `producer_actor_trusted()` → `acceptance_provenance`

## One-time operator permission (required before live publish)

The `cdb-local-ci` App currently has Check Run permissions only. Issue comments
require **`Issues: Read and write`** on the GitHub App settings page:

1. GitHub → Settings → Developer settings → GitHub Apps → **CDB Local CI**
2. Permissions → Repository permissions → **Issues: Read and write**
3. Save → accept installation permission upgrade for `jannekbuengener/Claire_de_Binare`

Without this, `python -m tools.agent_control approval publish` fails closed with
`APPROVAL_PUBLISH_APP_PERMISSION_DENIED`.

## Self-governance bootstrap

- Bootstrap manifest pins `publisher.github_app_id: 4410232` (SSOT on `main` in
  `docs/ci/local-status-publisher.md`).
- Publisher validates envelopes against schema loaded from `origin/main`.
- Trust allowlists may only contain the live publisher app slug (`cdb-local-ci`).
- PRs must not add alternate slugs without a separate governance path.

## CLI

```bash
# Publish completeness envelope (stdin or file)
python -m tools.agent_control approval publish \
  --pr 4530 \
  --producer cdb-pr-completeness-review \
  --envelope-file /path/to/envelope.json
```

Credentials: `CDB_GH_APP_ID`, `CDB_GH_APP_INSTALLATION_ID`, `CDB_GH_APP_PRIVATE_KEY(_PATH)`
(same as local-ci publisher).

## Verify trust after publish

```bash
gh api repos/jannekbuengener/Claire_de_Binare/issues/comments/<ID> \
  --jq '{user:.user,type:.user.type,app:.performed_via_github_app.slug}'

python -m tools.agent_control approval snapshot --pr 4530
```

Snapshot must recognize the completeness envelope as trusted (no
`UNTRUSTED_HANDOFF` solely due to missing completeness evidence).

## Out of scope here

- Plaketten-Ingo / Cursor provider automation binding (closes #4505 post-merge)
- Final-Head Conductor / `cdb-local-ci` Check Run publish
- Merge / APPROVE
