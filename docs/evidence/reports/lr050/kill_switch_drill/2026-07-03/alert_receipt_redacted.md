# LR-050 Kill-Switch Drill — Alert Receipt (Redacted) (#2984)

**Correlated during:** File Kill Switch active (`2026-07-03T20:04:22.865Z` — `2026-07-03T20:04:28.535Z` UTC)

## Important limitation (explicit)

**No Prometheus auto-alert on `risk_kill_switch_active` is claimed or observed.**  
Per [`LR-050-OBSERVABILITY-GATES.md`](../../../../../../docs/live-readiness/LR-050-OBSERVABILITY-GATES.md), file Kill Switch state does not fire a matching Prometheus alert rule. This drill uses a **correlated Grafana SMTP test notification** on the canonical operator channel from #2981.

## Correlated operator alert test

| Field | Value |
|-------|-------|
| Test method | `grafana_test_notification` |
| Receiver class | `grafana-smtp-operator` |
| Contact point name | `email-main` |
| Grafana receiver resource | `ZW1haWwtbWFpbg` |
| API path | `POST /apis/notifications.alerting.grafana.app/v1beta1/namespaces/default/receivers/ZW1haWwtbWFpbg/test` |
| Alert label `alertname` | `CDB-LR050-KillSwitchDrill` |
| Severity | `critical` |
| Kill switch active during test | **yes** |
| Test start UTC | `2026-07-03T20:04:25.037Z` |
| Test response UTC | `2026-07-03T20:04:28.521Z` |
| Grafana API HTTP status | **200** |
| Grafana API response | `success` |
| Grafana reported duration | `1s457ms` |
| Operator receipt UTC | `2026-07-03T20:04:30.524Z` |

## Operator receipt

Operator confirms notification received on configured human inbox channel (`[REDACTED_OPERATOR_CHANNEL]`) while File Kill Switch was active. See [`operator_attestation.md`](operator_attestation.md).

## Redaction

- No email addresses, SMTP credentials, tokens, or webhook URLs
- No raw notification body with PII
- No Alertmanager internal webhook path used as proof

## Verdict

**PASS** — Correlated Grafana-SMTP operator receipt observed during staged kill-switch active window.
