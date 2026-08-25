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

`hermes-runs-tailnet-transport.service` is the separate root-owned private
transport contract. It reads the same protected `API_SERVER_PORT`, requires the
gateway and `tailscaled` to be active, removes any persisted raw TCP mapping for
that port, and configures Tailscale Serve HTTPS/TLS on the private Tailnet
frontend with the exact `http://127.0.0.1:${API_SERVER_PORT}` backend. Raw
`--tcp` is not a canonical Runs API transport. `tailscale funnel` is absent from
the unit and from operator sudo rights. The mapping is persistent through Serve
background mode; stopping the fixed service removes only that HTTPS Serve port.
`TimeoutStartSec=120` bounds oneshot activation so a hung `tailscale serve --bg
--https=...` cannot remain `activating` forever. The shared `hermes` operator
may control the exact systemd unit but never receives generic Tailscale CLI
authority.

Tailnet control-plane prerequisite (not a host unit defect): private HTTPS Serve
requires the Tailnet admin setting that enables Serve / HTTPS certificates.
On Tailscale CLI v1.98.x, `tailscale serve --https ...` calls
`enableFeatureInteractive("serve", CapabilityHTTPS)` **before** `SetServeConfig`.
If the node lacks the `https` capability, the CLI queries control (`QueryFeature`)
and, when `ShouldWait=true`, blocks on the IPN bus until an admin enables the
feature. `--yes` only skips local overwrite prompts; it does **not** skip that
control-plane wait. Until Serve/HTTPS is enabled in the Tailscale admin console,
the transport oneshot can time out with an empty Serve config even when the
unit bytes, gateway loopback backend, and Funnel-absent contract are correct.
Do not restart-loop the transport unit while that Tailnet prerequisite is missing.
See Claire_de_Binare#4498.
