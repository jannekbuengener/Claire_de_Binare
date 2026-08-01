# Hermes on Hetzner (repo surface)

Issue: [#4289](https://github.com/jannekbuengener/Claire_de_Binare/issues/4289)  <!-- pragma: allowlist secret -->

Declarative, fail-closed bootstrap surface for a single Ubuntu LTS Hermes host.
This directory never contains secrets, personal memory, sessions, or tokens.

## Layout

| Path | Purpose |
|---|---|
| `VERSION_PIN.yaml` | Bound Hermes version/commit before install |
| `hetzner/` | CLI/API provision, firewall, cloud-init, bootstrap/destroy |
| `systemd/` | Hardened `hermes serve` units (loopback bind) |
| `windows/` | Dedicated workspace + kill-switch scripts |

## Profiles (repo distributions)

Versioned under `config/hermes/profiles/`:

- `jannek-assistant` — personal lane, no Windows shell, no GitHub write
- `cdb-engineer` — CDB workspace + scoped GitHub App tokens
- `validation-chief` — disabled until #4270 contract is ready

## Ops entrypoint

```bash
python -m tools.hermes_ops validate-profiles
python -m tools.hermes_ops secret-scan
python -m tools.hermes_ops policy-check
```

Live Hetzner/Windows mutation requires operator credentials and Human-GO.
LR remains **NO-GO**. No live/echtgeld authority.
