# Repository Configuration

Versionierte, bereichsübergreifende Konfiguration, die weder Tool-native
`.github`-Konfiguration noch ausführbare Infrastruktur ist.

| Path | Purpose |
|---|---|
| [`agent-control/`](agent-control/) | Declarative Agent Registry Desired State + profiles (`#4252`); CLI `python -m tools.agent_control` |
| [`arvp/`](arvp/) | ARVP campaign manifests and Compose overrides |
| [`live-readiness/`](live-readiness/) | Machine-readable readiness configuration; no Live-Go implication |
| [`repository/`](repository/) | Repository structure and hygiene policy |

Secrets do not belong here. Runtime secrets remain outside the repository as
defined by the security and operator documentation.
