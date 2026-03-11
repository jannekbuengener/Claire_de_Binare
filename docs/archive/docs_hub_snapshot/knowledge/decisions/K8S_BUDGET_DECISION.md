# K8s Budget Decision (Issue #293)

## Status: 🟡 PENDING

Entscheidung über Kubernetes-Migration steht aus bis Gate-Kriterien erfüllt.

## Executive Summary

| Aspekt | Status |
|--------|--------|
| E2E Test Coverage | 🟡 In Progress |
| Critical CVEs | 🟡 Some Open |
| Rollback Runbook | ✅ Done |
| Budget Approval | ⏳ Pending |

## Decision Criteria

### Go/No-Go Checklist

| Kriterium | Erforderlich | Aktuell | Status |
|-----------|--------------|---------|--------|
| E2E Pass Rate | ≥95% | TBD | 🟡 |
| Critical CVEs | 0 | TBD | 🟡 |
| Rollback Runbook | Vorhanden | ✅ | ✅ |
| Compose Docs | Vollständig | ✅ | ✅ |
| Team Capacity | Verfügbar | TBD | 🟡 |
| Budget | Genehmigt | Pending | ⏳ |

### Gate-Abhängigkeiten

```
A-05 (E2E Critical Path) ──┐
A-06 (Risk Guards)      ──┼── Gate: K8s Go/No-Go
B-01 (Postgres CVE)     ──┤
B-02 (Redis CVE)        ──┘
```

## Cost-Benefit Analyse

### Kosten (K8s Migration)

| Kategorie | Einmalig | Monatlich |
|-----------|----------|-----------|
| Cluster Setup | 8-16h | - |
| Helm/Kustomize | 16-24h | - |
| CI/CD Anpassung | 8-16h | - |
| Managed K8s (AKS/EKS/GKE) | - | ~$100-300 |
| Team Training | 8-16h | - |
| **Total** | **40-72h** | **$100-300** |

### Benefits (K8s)

| Benefit | Wert |
|---------|------|
| Auto-Scaling | Nur bei Traffic-Peaks relevant |
| Self-Healing | Docker Compose hat restart:always |
| Multi-Region | Nicht geplant (Single Server OK) |
| Rolling Updates | Bereits via Compose möglich |

### Empfehlung

**NO-GO für 2025-Q1**

Begründung:
1. Docker Compose erfüllt aktuelle Anforderungen
2. Single-Server-Deployment ausreichend
3. K8s-Overhead rechtfertigt nicht den Nutzen
4. Team-Kapazität für E2E-Stabilisierung benötigt

### Re-Evaluation

K8s erneut evaluieren wenn:
- Multi-Region Deployment benötigt
- Auto-Scaling erforderlich (hohe Last)
- >5 Trading-Pairs gleichzeitig

## K8s Scaffold (Vorbereitet)

Falls GO-Entscheidung:

```
k8s/
├── README.md           # Diese Datei
├── kustomize/          # Kustomize-basiert (empfohlen)
│   ├── base/
│   │   ├── kustomization.yaml
│   │   └── namespace.yaml
│   └── overlays/
│       ├── dev/
│       └── prod/
└── helm/               # Alternative: Helm Charts
    └── claire/
        ├── Chart.yaml
        ├── values.yaml
        └── templates/
```

## Appendix

### Managed K8s Optionen

| Provider | Service | Kosten/Monat |
|----------|---------|--------------|
| Azure | AKS | ~$100 (Free Control Plane) |
| AWS | EKS | ~$150 ($0.10/h Control Plane) |
| GCP | GKE | ~$100 (Free Autopilot Tier) |
| DigitalOcean | DOKS | ~$60 |

### Timeline (falls GO)

| Phase | Dauer | Inhalt |
|-------|-------|--------|
| 1 | 2 Wochen | Helm/Kustomize Setup |
| 2 | 2 Wochen | CI/CD Integration |
| 3 | 1 Woche | Testing + Rollback |
| 4 | 1 Woche | Production Cutover |
