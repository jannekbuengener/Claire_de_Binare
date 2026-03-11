---
relations:
  role: policy
  domain: governance
  upstream:
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_GOVERNANCE.md
    - knowledge/governance/CDB_POLICY_STACK_MINI.md
  downstream:
    - knowledge/governance/DELIVERY_APPROVED.yaml
  status: canonical
  tags: [infrastructure, policy, iac, gitops, kubernetes]
---
# CDB_INFRA_POLICY
**Infrastructure, IaC, GitOps & Runtime Policy (Canonical)**

Version: 1.1  
Status: Canonical

---

## 1. Zweck & Verbindlichkeit

Diese Policy definiert die **verbindlichen, technisch durchgesetzten Regeln**
für Infrastruktur, Deployment und Runtime im Projekt *Claire de Binare (CDB)*.

Sie operationalisiert:
- `CDB_CONSTITUTION.md`
- `CDB_GOVERNANCE.md`
- den kanonischen Mini-Policy-Stack

**Alle Regeln sind erzwingbar.**  
Optionale Infrastruktur existiert nicht.

---

## 2. Infrastructure as Code (HARD REQUIREMENT)

### 2.1 Grundprinzip

- Jede persistente Infrastruktur ist **als Code** definiert.
- Manuelle Erstellung produktiver Ressourcen ist verboten.

### 2.2 Durchsetzung

- CI blockiert Änderungen ohne IaC-Diff.
- Drift-Checks vergleichen Soll (Git) vs. Ist (Runtime).
- Abweichungen erzeugen Audit-Events.

---

## 3. GitOps – Single Source of Truth

### 3.1 Prinzip

- Git ist die **einzige autoritative Quelle** für Infrastrukturzustand.
- Runtime-Systeme sind rein exekutiv.

### 3.2 Reconcile (immer aktiv)

- GitOps-Reconcile läuft permanent.
- Reconcile-Intervall: **≤ 5 Minuten**
- Tooling: FluxCD oder funktional gleichwertig (OSS).

### 3.3 Drift-Verhalten

- Drift wird automatisch korrigiert.
- Jeder Drift-Fix ist:
  - geloggt
  - versioniert
  - auditierbar

---

## 4. Manuelle Änderungen (AUSNAHME)

Manuelle Änderungen sind **nur** zulässig bei:
- Security Incidents
- Produktionsstörungen

Pflichtregeln:
- sofortiges Incident-Log
- nachträgliche IaC-Abbildung
- Reconcile erzwingt Rückführung in Soll-Zustand

Manuelle Änderungen ohne Nachcodierung gelten als Governance-Bruch.

---

## 5. Referenz-Stack (bindend, austauschbar)

Der konkrete Stack ist austauschbar, **die Eigenschaften nicht**.

- Provisioning: Terraform / OpenTofu
- GitOps: FluxCD
- Observability: Prometheus, Grafana, Loki, OpenTelemetry
- Messaging: NATS JetStream (primär), Kafka (sekundär)
- Storage: S3-kompatibel (z. B. MinIO)
- Secrets: Vault oder Sealed-Secrets

---

## 6. Event-Driven Backbone (verpflichtend)

### 6.1 Übergang (jetzt)

- Redis darf **nur temporär** als Transport dienen.
- Redis ist **keine** Persistenz- oder Audit-Schicht.

### 6.2 Zielzustand

- Persistenter Event-Bus (JetStream / Kafka)
- Replay-fähig
- versionierte Event-Schemas

### 6.3 Migration

- Dual-Write (Redis + Persistenter Bus)
- Replay-Vergleich als Abnahmekriterium
- Redis-Only-Betrieb ist zeitlich begrenzt und dokumentationspflichtig

---

## 7. Kubernetes-Readiness (erzwingbar)

Alle Services müssen:

- stateless sein
- Konfiguration ausschließlich via ENV / ConfigMaps / Secrets beziehen
- Health-, Readiness- und Liveness-Probes bereitstellen
- Resource Requests & Limits definieren
- ohne lokale Pfadabhängigkeiten laufen

CI prüft diese Kriterien.  
Nicht-konforme Services sind **nicht mergefähig**.

---

## 8. Secrets & Tresor-Zone (hart)

- Keine Secrets im Repo (Scan + CI-Block).
- Secrets ausschließlich über Secret-Manager.
- Tresor-Zone:
  - nicht mountbar
  - kein Netzwerkpfad
  - human-only

KI-Container:
- kein Secret-Zugriff
- kein Tresor-Zugriff
- kein Bypass

---

## 9. Change Control (Infrastructure)

Infrastrukturänderungen sind **nur** im Delivery Mode erlaubt.

Voraussetzungen:
- `knowledge/governance/DELIVERY_APPROVED.yaml`
  - `delivery.approved: true`

Ablauf:
1. IaC-Plan / Diff
2. PR
3. CI-Checks
4. GitOps-Reconcile
5. Post-Deployment-Checks

Ohne Delivery-Gate:
→ **Analysis Mode**
→ **keine Mutationen**

---

## 10. Gültigkeit

Diese Infrastruktur-Policy ist **kanonisch**.

Abweichungen gelten als:
- Governance-Bruch
- CI-Fehler
- Systeminkonsistenz

Keine Ausnahmen.
