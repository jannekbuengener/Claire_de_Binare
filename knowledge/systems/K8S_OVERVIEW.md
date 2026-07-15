# Kubernetes Overview

Status: PARKED — no active Kubernetes deploy surface

Claire de Binare currently uses Docker Compose as its canonical runtime and
deployment model. The old root `k8s/` placeholder was removed on 2026-07-15
because it had no active consumers and did not constitute a deployable system.

Authoritative decision and re-evaluation criteria:
[`knowledge/decisions/K8S_BUDGET_DECISION.md`](../decisions/K8S_BUDGET_DECISION.md).

If Kubernetes is approved in the future, executable manifests belong under
`infrastructure/k8s/` after a new scoped issue and explicit Human-GO. This page is
documentation only and grants no runtime or Live-Go authorization.
