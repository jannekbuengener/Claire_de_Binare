# Hermes profile distributions (repo)

Issue: [#4289](https://github.com/jannekbuengener/Claire_de_Binare/issues/4289)  <!-- pragma: allowlist secret -->

Versioned, non-secret Hermes profile distributions for Hetzner install.

## Rules

- `SOUL.md` = personality only
- `AGENTS.md` / project context = CDB instructions
- `skills/` = reusable procedures
- `config.yaml` = non-secret settings (`security.redact_secrets: true`)
- `.env.EXAMPLE` = secret *names* only; real `.env` never committed
- Memory/sessions/state stay on the host under `/var/lib/hermes/profiles/<name>/`

## Profiles

| Profile | Windows | GitHub write | Live/Risk/Merge |
|---|---|---|---|
| `jannek-assistant` | no | no | no |
| `cdb-engineer` | dedicated workspace only | scoped App token | no |
| `validation-chief` | no (disabled) | no | no |

Omnipotent combined profiles are forbidden.
