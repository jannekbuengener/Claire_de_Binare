# CDB_INFRA_POLICY
**IaC / GitOps / Runtime / K8s-Readiness (Mini-Stack)**  
Version: 1.0.0 • Date: 2025-12-12 • Status: Canonical

---

## 1. Ziel & Verbindlichkeit

Dieses Dokument definiert **verbindliche, technisch durchgesetzte Infrastrukturregeln** für CDB.
Es operationalisiert `CDB_CONSTITUTION.md` und `CDB_GOVERNANCE.md` für den Infrastruktur-Stack.

Optionale Regeln sind **nicht zulässig**. Jede Regel ist erzwingbar und auditierbar.

---

## 2. IaC & GitOps (HARD REQUIREMENTS)

### 2.1 Infrastructure as Code (IaC)

**Prinzip**
- Jede Infrastrukturressource ist als Code definiert.
- Keine manuelle Erstellung persistenter Infrastruktur.

**Durchsetzung**
- CI blockiert Änderungen ohne IaC-Artefakte.
- Drift-Checks vergleichen Runtime-Zustand mit Git-Definition.

---

### 2.2 Git als Single Source of Truth

**Prinzip**
- Git ist die **einzige** autoritative Quelle.

**Durchsetzung**
- Keine direkten Schreibrechte auf Runtime-Systeme.
- Änderungen außerhalb von Git werden bei Reconcile überschrieben.
- Audit-Log aller Merges ist Pflicht.

---

### 2.3 Drift-Erkennung & -Korrektur (VERPFLICHTEND)

**Mechanismus**
- GitOps-Reconcile ist **immer aktiv**.
- Tooling: FluxCD oder funktional gleichwertiges OSS.
- Reconcile-Intervall: ≤ 5 Minuten.

**Audit**
- Drift-Events werden geloggt.
- Jede Korrektur ist nachvollziehbar.

---

### 2.4 Manuelle Änderungen (AUSNAHMEFALL)

**Zulässig nur bei**
- Incident-Response
- Sicherheitsnotfällen

**Technische Regeln**
- Änderung erzeugt Pflicht-Ticket.
- Änderung wird **sofort** nachträglich als IaC codiert.
- Reconcile erzwingt Rückführung in Soll-Zustand.

**Audit**
- Zeit, Grund, Verantwortlicher sind verpflichtend zu dokumentieren.

---

## 3. OSS-Referenz-Stack (bindend, austauschbar)

- Provisioning: Terraform oder OpenTofu
- GitOps: FluxCD (oder gleichwertig)
- Config: Ansible (optional, deklarativ)
- Observability: Prometheus, Grafana, Loki, OpenTelemetry
- Secrets: Vault oder Sealed-Secrets
- Storage: MinIO (S3-kompatibel)
- Messaging: NATS JetStream (primär), Kafka (sekundär)

---

## 4. Event-Driven Backbone (MIGRATION VERANKERT)

### 4.1 Übergangsphase (JETZT)

- Redis **nur** als temporärer Transport.
- Keine Redis-Abhängigkeit für Persistenz oder Audit.

### 4.2 Zielzustand (VERPFLICHTEND)

- Persistenter Event-Bus (NATS JetStream oder Kafka).
- Replay-fähig, versionierte Schemas.

### 4.3 Migrationsregel

- Dual-Write-Phase: Redis + Persistenter Bus.
- Abnahme durch Replay-Vergleich.
- Redis-Only-Betrieb ist zeitlich begrenzt und dokumentiert.

---

## 5. K8s-Readiness (TECHNISCH GEPRÜFT)

**Regeln**
- Stateless Services
- Config nur via ENV/ConfigMaps/Secrets
- Health-, Readiness-, Liveness-Endpunkte
- Resource Requests & Limits
- Keine lokalen Pfadabhängigkeiten

**Durchsetzung**
- CI prüft Container-Images auf diese Kriterien.
- Nicht-konforme Services sind nicht mergefähig.

---

## 6. Secrets & Tresor-Integration (HART)

**Regeln**
- Keine Secrets im Repo (Scan + CI-Block).
- Secrets nur via Secret-Manager.
- Tresor-Zone ist nicht mountbar.

**KI-Enforcement**
- KI-Container ohne Secret-Zugriff.
- Kein Netzwerkpfad zum Tresor.

---

## 7. Change Control (INFRA)

**Delivery Mode zwingend**
1. Plan (IaC-Diff)
2. PR
3. Automatisierte Tests
4. Reconcile-Rollout
5. Post-Check

**Durchsetzung**
- Branch-Protection
- CI-Gates
- Kein Auto-Merge

---

## 8. Gültigkeit

Diese Infrastruktur-Policy ist **kanonisch**.  
Abweichungen gelten als Governance-Bruch.

Keine Ausnahmen.
