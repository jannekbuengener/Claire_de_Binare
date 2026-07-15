# Kubernetes Budget Decision

Status: PARKED / NO ACTIVE IMPLEMENTATION

Decision anchor: GitHub issue #293 (closed 2025-12-28)

Reconciled: 2026-07-15

## Decision

Docker Compose remains the canonical deployment/runtime surface under
`infrastructure/compose/`. Kubernetes is not approved, budgeted, or used by an
active workflow, test, or deployment path.

The former root `k8s/` directory was removed during the root information-
architecture cleanup because it was only an incomplete placeholder:

- placeholder registry image (`your-registry/...`),
- signal-service port `8001`, inconsistent with the canonical runtime port,
- no production overlays, secrets integration, health contract, CI validation,
  rollout, or rollback path,
- no active source, workflow, or test consumer.

Keeping that scaffold implied a deployment capability that did not exist and
contradicted the original decision to add Kubernetes assets only after a GO.

## Rationale

| Consideration | Current assessment |
|---|---|
| Workload topology | Compose satisfies the current single-host BLUE/RED model |
| Scaling need | No approved multi-region or cluster autoscaling requirement |
| Operational cost | Cluster, Helm/Kustomize, secrets, observability, CI/CD and rollback overhead is not justified |
| Safety | A partial scaffold is more misleading than having no deploy surface |
| Team capacity / budget | No current Kubernetes budget or implementation allocation |

## Re-evaluation triggers

Re-evaluate only when at least one concrete requirement exists, for example:

- approved multi-host or multi-region deployment,
- measured load that cannot be handled by the Compose topology,
- explicit availability/SLO requirements needing orchestration,
- approved budget and named operational ownership.

Re-evaluation requires a new scoped issue, an architecture/security review, and
explicit Human-GO. If approved, executable assets belong under
`infrastructure/k8s/`—not at repository root and not under `knowledge/`.

## Minimum acceptance criteria for any future implementation

- images and registries are real, pinned, and supply-chain checked,
- service ports, health checks and dependencies match the canonical topology,
- secrets are externalized and never committed,
- dev/prod overlays and resource limits are defined,
- CI validates rendered manifests,
- deployment, observability, rollback and disaster-recovery runbooks exist,
- Compose-to-Kubernetes parity is demonstrated before any cutover.

This parked decision grants no Live-Go, deployment GO, or real-money authority.
