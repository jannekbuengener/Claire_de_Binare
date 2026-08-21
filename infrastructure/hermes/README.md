# Hermes on Hetzner (repo surface)

Issue: [#4289](https://github.com/jannekbuengener/Claire_de_Binare/issues/4289)  <!-- pragma: allowlist secret -->

Declarative, fail-closed bootstrap surface for a single Ubuntu LTS Hermes host.
This directory never contains secrets, personal memory, sessions, or tokens.

## Layout

| Path | Purpose |
|---|---|
| `VERSION_PIN.yaml` | Bound Hermes version/commit before install |
| `hetzner/` | CLI/API provision, firewall, cloud-init, bootstrap/destroy |
| `systemd/` | Hardened dashboard and cdb-engineer Runs API gateway units |
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
python -m tools.hermes_ops pin-check --require-pinned
```

Live Hetzner/Windows mutation requires operator credentials and Human-GO.
LR remains **NO-GO**. No live/echtgeld authority.

## Runs API gateway

`hermes-gateway-cdb-engineer.service` runs the official pinned `hermes gateway`
command alongside the existing dashboard. It is dedicated to the existing
`cdb-engineer` Unix identity and profile home, binds the API server to loopback,
and gets the required API port and key only from the protected profile
environment file. The service intentionally contains no endpoint, port value,
or secret material. The root bootstrap installs the unit itself; the shared
`hermes` operator may only enable/restart/status/is-active that exact root-owned
service. It cannot sudo-install a caller-writable unit or run daemon-reload.
The loopback host is enforced at `ExecStart` after `EnvironmentFile` loading, and
the protected API key is never expanded into process argv. The gateway must not
be exposed through a public listener or Funnel.
