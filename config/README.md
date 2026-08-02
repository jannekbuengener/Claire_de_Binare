# Repository Configuration

Versionierte, bereichsübergreifende Konfiguration, die weder Tool-native
`.github`-Konfiguration noch ausführbare Infrastruktur ist.

| Path | Purpose |
|---|---|
| [`agent-control/`](agent-control/README.md) | Declarative Agent Registry Desired State + profiles (`#4252`); CLI `python -m tools.agent_control` |
| [`arvp/`](arvp/README.md) | ARVP campaign manifests and Compose overrides |
| [`hermes/`](hermes/README.md) | Hermes profile/config surfaces (Hetzner ops; no Live-Go) |
| [`live-readiness/`](live-readiness/README.md) | Machine-readable readiness configuration; no Live-Go implication |
| [`parameter-control/`](parameter-control/v1/README.md) | Parameter-control v1 manifests |
| [`repository/`](repository/README.md) | Repository structure and hygiene policy |
| `governance/` | Config-adjacent governance inputs (no local README; see [`knowledge/governance/README.md`](../knowledge/governance/README.md)) |

Secrets do not belong here. Runtime secrets remain outside the repository as
defined by the security and operator documentation.
