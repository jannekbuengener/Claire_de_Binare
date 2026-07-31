# Trivy Alert Cluster Triage — Issue #1651

**Export-Basis:** 2015 offene Trivy-Alerts (Code Scanning, Stand: 2026-07)
**Branch:** `epic-code` | **Runbook:** `docs/security/TRIAGE_RUNBOOK.md §5`
**Issue:** [#1651](https://github.com/jannekbuengener/Claire_de_Binare/issues/1651)

---

## §1 Kurzdiagnose

| Metrik | Wert |
|--------|------|
| Gesamt offene Trivy-Alerts | **2015** |
| Severity ERROR (CRITICAL) | 263 |
| Severity WARNING (HIGH) | 668 |
| Severity NOTE (MEDIUM/LOW) | 1084 |
| Bestätigte Dismiss-Kandidaten | **~1157** |
| Rest-Backlog nach Dismiss | **~858** |

**Root Cause für die Masse:**
Die beiden Scan-Workflows (`trivy.yml` FS-Scan, `security-scan.yml` Image-Scan) haben in früheren Läufen **NOTE-Severity-Findings** hochgeladen, bevor beide auf `severity: CRITICAL,HIGH` beschränkt wurden. GitHub Code Scanning schließt diese Alerts **nicht automatisch**, wenn eine neue SARIF-Datei eine Regel komplett weglässt (anstatt sie als „nicht mehr gefunden" zu melden). Diese 1084 NOTE-Alerts sind damit permanente historische Artefakte, die manuell dismissed werden müssen.

Zweiter Multiplikator: Dieselben OS-CVEs erscheinen in **8 separaten Service-Images** (`cdb_allocation`, `cdb_db_writer`, `cdb_execution`, `cdb_market`, `cdb_regime`, `cdb_risk`, `cdb_signal`, `cdb_ws`), weil alle das gleiche Debian-Bookworm-Python-Base-Image verwenden. 53 CVEs sind identisch in allen 8 Services → 53 × 8 = 424 Duplikate allein aus diesem Muster.

---

## §2 Cluster-Tabelle

| Cluster | Alerts | Severity | Fix? | Pfad/Scope | Paket | Klasse | Empfehlung |
|---------|--------|----------|------|-----------|-------|--------|-----------|
| **cdb-base-NOTE** | 964 | NOTE | nein/trixie | `library/cdb_*` | libc6, tar, passwd, util-linux, coreutils u.a. | `historic noise` | Dismiss (Batch A+B) |
| **gosu-startup-binary** | 89 | MIX | ja (Go) | `usr/local/bin/gosu` | stdlib (Go) | `false positive` | Dismiss (Test-Batch) |
| **grafana-image-NOTE** | 69 | NOTE | nein | `grafana/grafana` | libssl3, curl, openssl | `historic noise` | Dismiss (Batch B) |
| **usr-grafana-binary-NOTE** | 20 | NOTE | nein | `usr/share/grafana/bin/*` | stdlib | `historic noise` | Dismiss (Batch B) |
| **prometheus-binary-NOTE** | 14 | NOTE | nein | `bin/prometheus`, `bin/promtool` | stdlib | `historic noise` | Dismiss (Batch B) |
| **venv-pip** | 1 | NOTE | nein | `venv/lib/python*/pip-*` | pip | `false positive` | Dismiss (Test-Batch) |
| **cdb-base-WARNING-nofix** | 120 | WARNING | nein | `library/cdb_*` | ncurses, libudev1 u.a. | `needs review` | Upstream tracken |
| **cdb-base-ERROR-nofix** | 23 | ERROR | nein | `library/cdb_*` | ncurses-bin, libudev1 | `needs review` | Upstream tracken |
| **cdb-base-WARNING-fix** | 32 | WARNING | ja | `library/cdb_*` | libc6, openssl, libsqlite3 | `real risk` | Base-Image updaten |
| **cdb-base-ERROR-fix** | 16 | ERROR | ja | `library/cdb_*` | libc6, openssl-provider-legacy | `real risk` | Base-Image updaten |
| **grafana-image-WARNING/ERROR** | 67 | W+E | mix | `grafana/grafana` | libssl3, openssl, libssh-4 | `needs review` | Grafana-Image updaten |
| **usr-grafana-binary-W/E** | 189 | W+E | mix | `usr/share/grafana/bin/*` | stdlib, grafana Go deps | `needs review` | Grafana-Image updaten |
| **prometheus-binary-W/E** | 88 | W+E | mix | `bin/prometheus`, `bin/promtool` | stdlib, Go crypto | `needs review` | Prometheus updaten |
| **postgres-alpine** | 49 | W+E | ja | `library/postgres` | libssl3, libcrypto3, libxml2 | `real risk` | Postgres-Image updaten |
| **redis-alpine** | 38 | W+E | ja | `library/redis` | libssl3, libcrypto3 | `real risk` | Redis-Image updaten |

**Gesamtzählung nach Klasse:**

| Klasse | Alerts |
|--------|--------|
| `historic noise` + `false positive` (→ Dismiss) | **1157** |
| `needs review` (→ Upstream tracken / Image-Update planen) | **716** |
| `real risk` (→ Fix-Action nötig) | **135** |
| (Gosu in WARNING/ERROR: real false positive, aber separate Batch) | *(in 1157 enthalten)* |

---

## §3 Dismiss-Kandidaten

### Cluster: gosu-startup-binary (89 Alerts)

**Begründung:**
`gosu` ist ein startup-only Privilege-Drop-Binary, das ausschließlich in der Container-Entrypoint-Phase läuft, um vom `root`-User in einen unprivilegierten User zu wechseln. Es hat keine Netzwerkexposition, wird nach dem Start nicht mehr ausgeführt, und die Go-stdlib-CVEs in `gosu` erfordern eine aktive Nutzung der betroffenen Funktionen zur Ausnutzung. Das ist in diesem Deployment-Kontext nicht gegeben.

**Alert-IDs (Beispiele):** 3332, 3331, 3330, 3329, 3328, 3327, 2899, 2898, 2897, 2285 … (89 total)

**Standard-Kommentar:**
```
Cluster: gosu-startup-binary
Rationale: gosu is a startup-only privilege-drop binary in redis/postgres base
images. It runs once at container init to drop root privileges and is never
executed at runtime. Go stdlib CVEs in gosu have no exploitable attack surface
in this deployment context (no network exposure, no active invocation).
Historic scanner artifact. Reviewed: YYYY-MM-DD | Issue: #1651
Runbook: docs/security/TRIAGE_RUNBOOK.md §5
```

**Dismiss-Reason:** `false positive`
**Risiko falls falsch:** Minimal — gosu exec-model ist gut dokumentiert.

---

### Cluster: cdb-base-NOTE (964 Alerts)

**Begründung:**
NOTE-Severity entspricht MEDIUM/LOW in Trivy. Beide aktiven Scan-Workflows begrenzen sich heute auf `severity: CRITICAL,HIGH`. Die 964 NOTE-Alerts wurden in früheren Scan-Läufen (vor Einführung des Severity-Filters) hochgeladen und werden von GitHub nicht automatisch geschlossen, weil neue SARIF-Uploads die Regeln nicht mehr erwähnen. Diese Alerts sind reine Scan-Artefakte früherer Konfigurationsstände, nicht neue Findings.

**Alert-IDs (Beispiele):** 3518, 3516, 3515, 3514, 3512 … (964 total)

**Standard-Kommentar:**
```
Cluster: cdb-base-NOTE (MEDIUM/LOW severity artifact)
Rationale: NOTE-severity (MEDIUM/LOW) findings from pre-filter scan runs.
Current scan config restricts to CRITICAL/HIGH only (severity: CRITICAL,HIGH).
These alerts will not be re-raised by future scans. Historic scanner artifact
from configuration change. Not an active finding.
Reviewed: YYYY-MM-DD | Issue: #1651
Runbook: docs/security/TRIAGE_RUNBOOK.md §5
```

**Dismiss-Reason:** `won't fix` (historic, severity below active threshold)
**Risiko falls falsch:** Niedrig — MEDIUM/LOW-Findings in OS-Paketen haben keinen direkten Exploit-Pfad ohne CRITICAL/HIGH-Chaining.

---

### Cluster: grafana-NOTE + usr-grafana-NOTE + prometheus-NOTE (103 Alerts)

**Begründung:**
Gleiche Ursache wie `cdb-base-NOTE`: NOTE-Severity-Artefakte aus früheren Scan-Konfigurationen. Grafana ist ein internes Monitoring-Tool ohne externe Exposition. Prometheus ebenfalls intern.

**Alert-IDs (Beispiele grafana/):** 3524, 3522, 3408, 3407, 3406
**Alert-IDs (Beispiele bin/):** 3346, 3343, 3342, 3340, 3339

**Standard-Kommentar:**
```
Cluster: monitoring-tools-NOTE (grafana/prometheus MEDIUM/LOW artifact)
Rationale: NOTE-severity findings in internal monitoring tools (Grafana/Prometheus).
Severity below active scan threshold (CRITICAL/HIGH only). Monitoring tools have
no external exposure. Historic scanner artifact.
Reviewed: YYYY-MM-DD | Issue: #1651
Runbook: docs/security/TRIAGE_RUNBOOK.md §5
```

**Dismiss-Reason:** `won't fix`
**Risiko falls falsch:** Minimal — intern, kein direkter Exploit-Pfad bei MEDIUM/LOW.

---

### Cluster: venv-pip (1 Alert)

> [!CAUTION]
> **Korrigiert 2026-07-31 (Issue #4095).**
> Die untenstehende Begründung war als **generelle Regel** falsch. „Pfad beginnt
> mit `venv/`" ist **kein** Beleg für ein Dev-venv und **kein** False-Positive-Kriterium.
> `services/execution/Dockerfile` baut ein venv unter `/venv` und kopiert es per
> `COPY --from=build /venv /venv` in die Runtime-Stage. Im Image-Scan erscheint
> dieses produktive venv als `venv/lib/python3.14/site-packages/pip-*.dist-info/METADATA`
> — also exakt in der Form, die hier als „nicht Teil des produktiven Builds"
> eingestuft wurde. Ein solcher Alert ist ein **Image-Pfad und ein reales Finding**.
>
> Die konkrete Alert-ID 2736 bleibt unverändert dismissed: sie nennt
> `python3.11`, und kein CDB-Image nutzt Python 3.11 (produktiv: 3.14, lokale CI:
> 3.12). Für diesen Einzelfall bleibt die Dev-venv-Einordnung plausibel. Der
> historische Dismissal wird nicht angefasst.
>
> **Verbindliches Triage-Kriterium ab sofort:** Ein `venv/`-Pfad ist nur dann ein
> Dev-Artefakt, wenn die Python-Minor-Version **keinem** produktiven Image
> entspricht **und** die Quelle ein FS-Scan (`trivy.yml`, `scan-type: fs`) ist.
> Stammt der Alert aus dem Image-Scan (`security-scan.yml`, `trivy-scan-custom`)
> oder passt die Python-Version zu einem Service-Image, ist er zu fixen — nicht
> zu dismissen.

**Ursprüngliche Begründung (historisch, nicht mehr als Regel gültig):**
FS-Scan hat ein Python-venv gescannt (`venv/lib/python3.11/site-packages/pip-25.3.dist-info/METADATA`). Das venv ist nicht Teil des produktiven Builds.

**Alert-ID:** 2736

**Dismiss-Reason:** `false positive`

---

## §4 Rest-Backlog (real risk + needs review)

### Actionable (Fix-Issues benötigt)

| Issue-Vorschlag | Cluster | Alerts | Aktion |
|----------------|---------|--------|--------|
| Update Python/Debian base image | cdb-base-ERROR-fix + cdb-base-WARNING-fix | 48 | Dockerfile `FROM python:3.12-slim-bookworm` → neuere Revision; schließt libc6 + openssl CVEs |
| Update postgres image | postgres-alpine | 49 | `postgres:15.17-alpine` → aktuellste 15.x; libssl3/libcrypto3/libxml2 haben Fixes |
| Update redis image | redis-alpine | 38 | `redis:7.4.8-alpine` → neueste 7.x; libssl3/libcrypto3 haben Fixes |
| Update grafana image | grafana-WARNING/ERROR | 67 | `grafana/grafana:11.4.7-ubuntu` → aktuellste stable |
| Update prometheus image | prometheus-WARNING/ERROR | 88 | `prom/prometheus:v3.10.0` → aktuellste stable |

**Kritische CVEs in cdb-base-ERROR-fix (8 Services):**
- `CVE-2026-0861` — `libc6`, Fix: `2.41-12+deb13u2` (8 Alerts)
- `CVE-2026-28390` — `openssl-provider-legacy`, Fix: `3.5.5-1~deb13u2` (8 Alerts)
- (weitere 0 ERROR+fix CVEs in cdb_*)

**Hinweis:** Fix-Versionen wie `2.41-12+deb13u2` sind Debian-trixie (13)-Packages. Wenn Services Debian-bookworm (12) nutzen, ist der Fix erst nach Bookworm-Backport verfügbar. Überprüfen: `docker run --rm cdb_signal:latest dpkg -l libc6`.

### Upstream / No-Fix-Available

| Cluster | Alerts | Paket | Status |
|---------|--------|-------|--------|
| cdb-base-ERROR-nofix | 23 | ncurses-bin, libudev1 | Upstream-CVE, kein Fix — tracken |
| cdb-base-WARNING-nofix | 120 | ncurses, libudev1, weitere | Upstream-CVE, kein Fix — tracken |

Diese Alerts bleiben offen mit Kommentar `upstream-no-fix` und werden in der nächsten Triage-Runde re-evaluiert.

---

## §5 Sichere Umsetzungsreihenfolge

### Test-Batch (5 Alerts, manuell)

Zweck: Format und Dismiss-Kommentar validieren, bevor Skript läuft.

```bash
# Test: 5 gosu-Alerts manuell dismisssen
gh api -X PATCH repos/jannekbuengener/Claire_de_Binare/code-scanning/alerts/3332 \
  -f state=dismissed \
  -f dismissed_reason="false positive" \
  -f dismissed_comment="Cluster: gosu-startup-binary | Rationale: gosu is a startup-only privilege-drop binary. No runtime exposure. Historic scanner artifact. Issue: #1651"

gh api -X PATCH repos/jannekbuengener/Claire_de_Binare/code-scanning/alerts/3331 \
  -f state=dismissed \
  -f dismissed_reason="false positive" \
  -f dismissed_comment="Cluster: gosu-startup-binary | Rationale: gosu is a startup-only privilege-drop binary. No runtime exposure. Historic scanner artifact. Issue: #1651"

gh api -X PATCH repos/jannekbuengener/Claire_de_Binare/code-scanning/alerts/3330 \
  -f state=dismissed \
  -f dismissed_reason="false positive" \
  -f dismissed_comment="Cluster: gosu-startup-binary | Rationale: gosu is a startup-only privilege-drop binary. No runtime exposure. Historic scanner artifact. Issue: #1651"
```

Nach Test-Batch: Alerts in GitHub Security prüfen → Kommentar korrekt, Reason korrekt?

### Batch A — gosu + venv (90 Alerts)

```bash
# Script: dismiss_batch_a.sh
# Dismiss-Reason: false positive
# Cluster: gosu-startup-binary + venv-pip
REPO="jannekbuengener/Claire_de_Binare"
COMMENT_GOSU="Cluster: gosu-startup-binary | gosu is a startup-only privilege-drop binary in base images. No runtime attack surface for Go stdlib CVEs. False positive. Issue: #1651 | Runbook: docs/security/TRIAGE_RUNBOOK.md §5"
COMMENT_VENV="Cluster: venv-pip | Python venv in FS scan, not part of production build. False positive. Issue: #1651"

# gosu (89 IDs: 3332 3331 3330 3329 3328 3327 2899 2898 2897 2285 2284 2283 2282 2281
#              93 92 91 90 89 88 87 86 85 84 83 82 81 80 79 78 77 76 75 74 73 72 71 70
#              69 68 67 66 65 64 63 62 61 60 59 58 57 56 55 54 53 52 51 50 49 48 47 46
#              45 44 43 42 41 40 39 38 37 36 35 34 33 32 31 30 29 28 27 26 25 24 23 22
#              21 20 19 18 17 16 15 14 13)
for id in 3332 3331 3330 3329 3328 3327 2899 2898 2897 2285 2284 2283 2282 2281 93 92 91 90 89 88; do
  gh api -X PATCH "repos/$REPO/code-scanning/alerts/$id" \
    -f state=dismissed \
    -f dismissed_reason="false positive" \
    -f dismissed_comment="$COMMENT_GOSU"
  sleep 0.3
done

# venv (1 ID: 2736)
gh api -X PATCH "repos/$REPO/code-scanning/alerts/2736" \
  -f state=dismissed \
  -f dismissed_reason="false positive" \
  -f dismissed_comment="$COMMENT_VENV"
```

### Batch B — NOTE-Artefakte (1067 Alerts)

Nur nach erfolgreichem Batch A ausführen. Script wird aus den Alert-IDs aus dem Export generiert.

```bash
# Alle cdb_* NOTE + grafana NOTE + prometheus NOTE + usr NOTE (non-gosu)
# dismissed_reason: "won't fix"
# dismissed_comment: Cluster + Issue-Referenz (s. §3 Standard-Kommentar)
# Script-Generierung:
python3 - <<'EOF'
import json

with open('trivy_alerts_raw.json') as f:
    alerts = json.load(f)

REPO = "jannekbuengener/Claire_de_Binare"
NOTE_PATHS = lambda p: (
    p.startswith('library/cdb_') or
    p.startswith('grafana/') or
    p.startswith('bin/') or
    (p.startswith('usr/') and 'gosu' not in p)
)
COMMENT = ("Cluster: historic-NOTE-artifact | NOTE-severity (MEDIUM/LOW) finding "
           "from pre-filter scan run. Current config: severity CRITICAL/HIGH only. "
           "Not re-raised by future scans. Issue: #1651 | Runbook: docs/security/TRIAGE_RUNBOOK.md §5")

ids = [
    a['number'] for a in alerts
    if a.get('rule',{}).get('severity','').upper() == 'NOTE'
    and NOTE_PATHS(a.get('most_recent_instance',{}).get('location',{}).get('path',''))
]

print(f"# Total NOTE dismiss targets: {len(ids)}")
for i in ids:
    print(f"gh api -X PATCH repos/{REPO}/code-scanning/alerts/{i} "
          f"-f state=dismissed -f dismissed_reason=\"won't fix\" "
          f"-f dismissed_comment=\"{COMMENT}\" && sleep 0.3")
EOF
```

### Batch C — Rest-Review (nach Batch B)

Re-evaluate die verbliebenden `needs review`-Cluster auf Basis aktualisierter Image-Versionen:
- Grafana-Image updaten → viele WARNING/ERROR schließen sich automatisch
- Prometheus-Image updaten → gleiches Muster
- Python/Debian-Base-Image updaten → cdb_*-Fix-Alerts schließen

---

## §6 Empfohlene Follow-up Issues

| Issue | Titel | Cluster | Priorität |
|-------|-------|---------|-----------|
| Neu | Update Debian base image in cdb services | cdb-base-ERROR-fix (16 alerts) | High |
| Neu | Update postgres:15-alpine image | postgres-alpine (49) | High |
| Neu | Update redis:7-alpine image | redis-alpine (38) | High |
| Neu | Update grafana + prometheus images | grafana+prometheus (240) | Medium |
| Existiert | #1651 → Dismiss-Batches ausführen | gosu + NOTE-Artefakte (1157) | High |

---

## §7 Verweis

- Epic: [#1649](https://github.com/jannekbuengener/Claire_de_Binare/issues/1649)
- Issue: [#1651](https://github.com/jannekbuengener/Claire_de_Binare/issues/1651)
- Runbook: `docs/security/TRIAGE_RUNBOOK.md §5`
- Scan-Workflows: `.github/workflows/trivy.yml`, `.github/workflows/security-scan.yml`
- Alert-Export-Datum: 2026-07 (2015 offene Alerts)
