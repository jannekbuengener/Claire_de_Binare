# Evidence — Hermes Hetzner (#4289)

Status: REPO_CI_FIXED + LIVE_BLOCKED_WRONG_CREDENTIAL_PRODUCT
Date: 2026-08-02
PR: [#4290](https://github.com/jannekbuengener/Claire_de_Binare/pull/4290)    <!-- pragma: allowlist secret -->
Head (start): `00db85d22e05075da2f07ccca4246fd51c7f860f`
LR: NO-GO

## Scope of this evidence

Repository CI/format fixes, credential-product classification, and redacted
preflight. Live Hetzner / Windows / GitHub write drills remain blocked.
Sensitive host inventory stays outside the repository.

## Pin (verified)

Authoritative live pin is `infrastructure/hermes/VERSION_PIN.yaml` (refreshed
[#4327](https://github.com/jannekbuengener/Claire_de_Binare/issues/4327) after
floating CDN drift blocked [#4289](https://github.com/jannekbuengener/Claire_de_Binare/issues/4289)
Phase A). Historical 2026-08-02 floating-CDN values below are superseded.

| Field | Value |
|---|---|
| git_ref | `v2026.7.30` |
| git_commit | `cc4cab2f592e60a197e796506de9168f74baf3ea` |
| release | Hermes Agent v0.19.1 |
| install.sh sha256 | `ab3e6ae1a1bda828941df8911ae44ed5de68412805124f338f157aa0360eb660` |
| install URL | commit-bound `…/cc4cab2f…/scripts/install.sh` (floating `hermes-agent.nousresearch.com/install.sh` forbidden for `--require-pinned`) |
| dashboard entrypoint | `hermes dashboard --host 127.0.0.1 --port <N> --no-open --isolated` |
| cost estimate | 14.89 EUR/mo (CPX21 + IPv4 + backups); live provision default CX23≈9.03 EUR/mo |

## Session 2026-08-02 — CI root cause

Hosted run `30741978587` on head `00db85d2`: `overall_status=FAIL` in stage **lint**.
Cause: `black --check` would reformat 5 Hermes files under `tools/hermes_ops/` and
`tests/unit/hermes_ops/`. Classification: **scope-conform**. Fixed by applying Black
and making the executable-bit contract check **git index mode `100755`** (Windows
NTFS local `stat` is not authoritative).

## Credential / SSH preflight (redacted)

| Check | Result |
|---|---|
| `HETZNER_ACCESS_KEY.txt` exists (len=20) | PASS (file present) |
| `HETZNER_SECRET_KEY.txt` exists (len=40) | PASS (file present) |
| Access/Secret as `HCLOUD_TOKEN` | FAIL_UNAUTHORIZED |
| Object Storage S3 ListBuckets (fsn1/nbg1/hel1) | PASS (HTTP 200) |
| Active `hcloud` context `traumtaenzer` | FAIL_UNAUTHORIZED (stale/invalid) |
| SSH pubkey fingerprint | PASS `SHA256:1KHxOlbvep+HTwWC5YtZ+CIPrBHCQQ8m2F8xgRlqDD0` |
| SSH private key present | PASS (basename only) |
| Tailscale CLI | MISSING |
| `D:\Dev\HermesWorkspace\Claire_de_Binare` | MISSING |
| Product classification | **Object Storage keys ≠ Hetzner Cloud API** |

## Commands (PASS this session)

```bash
python -m black --config pyproject.toml --check tools/hermes_ops tests/unit/hermes_ops
python -m tools.hermes_ops validate-profiles
python -m tools.hermes_ops secret-scan
python -m tools.hermes_ops pin-check --require-pinned
pytest -q tests/unit/hermes_ops   # 28 passed
ruff check tools/hermes_ops tests/unit/hermes_ops
git diff --check
```

Required merge gate `cdb-local-ci` not published (out of scope).

## Live drill matrix (session 2026-08-02)

| Drill | Result |
|---|---|
| Bootstrap on empty VM | BLOCKED (`POST /servers` HTTP 403 forbidden; firewall OK) |
| Idempotent second bootstrap | BLOCKED |
| VM reboot + auto start | NOT_RUN |
| Port/firewall external | NOT_RUN |
| Unauthorized access denied | NOT_RUN |
| Profile identity/skills/memory isolation | NOT_RUN |
| Memory/sessions survive restart | NOT_RUN |
| Cross-profile secret/memory deny | NOT_RUN |
| Windows ACL allow/deny | NOT_RUN (workspace + Tailscale missing; UAC likely) |
| Kill-switch | NOT_RUN |
| Backup + restore | NOT_RUN |
| Update + rollback | NOT_RUN (script contracts PASS; live NOT_RUN) |
| Token rotation/revoke | NOT_RUN (no dedicated Hermes GitHub App) |
| Secret/PII scan of redacted evidence | PASS (repo secret-scan) |

## Session 2026-08-02b — HCLOUD_TOKEN follow-up

| Check | Result |
|---|---|
| `HCLOUD_TOKEN.txt` present (len=64) | PASS |
| `hcloud server list` | PASS (0 servers) |
| SSH key `cdb-hermes-hetzner` registered + fingerprint match | PASS |
| Firewall `cdb-hermes-deny-inbound` create + temp SSH rule | PASS |
| `POST /servers` (cx23/cpx22/…) | **HTTP 403 forbidden** |
| `POST /volumes` | **HTTP 403 forbidden** |
| Default type under ≤15 EUR | `cx23` @ `fsn1` estimate **9.03 EUR/mo** (`cpx21` unorderable) |


## Session 2026-08-02c — post-repro permission matrix

Live python -m tools.hermes_ops hcloud-preflight → SERVER_CREATE_FORBIDDEN.

| Probe | HTTP |
|---|---|
| GET /servers | 200 |
| POST /firewalls | 201 (deleted) |
| POST /networks | 201 (earlier matrix) |
| POST /primary_ips | 201 (earlier matrix) |
| POST /servers | **403 forbidden** |
| POST /volumes | **403** |
| POST /floating_ips | **403** |
| POST /load_balancers | **403** |

Classification: token is **not** read-only; server/volume create specifically denied.

## Holds (exact Human action — single primary blocker)

1. **PRIMARY:** Hetzner Cloud project/token can authenticate and manage firewalls,
   but **server/volume create returns HTTP 403 `forbidden`**. In Hetzner Console
   verify: API token is **Read & Write**, payment method active, project role
   allows server create, no account lock. Then re-run
   `HERMES_SSH_KEY_NAME=cdb-hermes-hetzner HERMES_BOOTSTRAP_ADMIN_CIDR=<ip>/32
   bash infrastructure/hermes/hetzner/provision.sh`.
2. Dedicated Hermes GitHub App (do **not** expand App `4410232`).
3. Install/auth Tailscale; elevated Windows session for `hermes-win` + ACL/kill-switch.
4. After Tailscale: remove temp firewall rule `hermes-bootstrap-ssh-temp` and UFW OpenSSH.

## Probe issues

- #4287 / #4288 already CLOSED with “Permission-Probe, superseded by #4289.”
  Verified live; no re-open.
