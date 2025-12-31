# Kubernetes Scaffold

**Status: 🟡 PENDING - Awaiting Go/No-Go Decision**

Siehe [K8s Budget Decision](../docs/decisions/K8S_BUDGET_DECISION.md) für Details.

## Struktur (falls GO)

```
k8s/
├── README.md
├── kustomize/
│   ├── base/
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   ├── redis/
│   │   ├── postgres/
│   │   └── services/
│   └── overlays/
│       ├── dev/
│       └── prod/
└── helm/  (Alternative)
```

## Kustomize vs Helm

| Aspekt | Kustomize | Helm |
|--------|-----------|------|
| Komplexität | Niedriger | Höher |
| Templating | Patches | Go Templates |
| Learning Curve | Flach | Steil |
| Community | Kubernetes-Native | Größer |

**Empfehlung**: Kustomize (einfacher, keine zusätzliche Tooling-Dependency)

## Go/No-Go Checklist

Vor K8s-Migration müssen erfüllt sein:

- [ ] E2E Pass Rate ≥95%
- [ ] 0 Critical CVEs
- [ ] Rollback Runbook getestet
- [ ] Compose Architecture dokumentiert
- [ ] Budget genehmigt
- [ ] Team Capacity verfügbar

## Nächste Schritte (falls GO)

1. `kustomize/base/` mit Namespace + ConfigMaps
2. Service-Manifeste aus Compose konvertieren
3. Secrets Management (Sealed Secrets / External Secrets)
4. CI/CD Pipeline anpassen
