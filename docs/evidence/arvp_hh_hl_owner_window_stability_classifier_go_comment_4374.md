## GO_HH_HL_WINDOW_STABILITY_CLASSIFIER_EXECUTE (Owner draft — do not auto-post)

Authorizes only: Primary read-only `window_stability` build → validate → durable classifier → new classification artifact → STOP.
Does **not** reuse Primary GO `5222204496` or Reproduction GO `5223567140`.
Does **not** authorize Paper / Live / Echtgeld / Promotion / Stage B / OOS / Stress / Primary mutation / new replays.

```cdb.hh_hl_window_stability_classifier_authorization.v1
{
  "schema_version": "cdb.hh_hl_window_stability_classifier_authorization.v1.draft",
  "status": "GO_HH_HL_WINDOW_STABILITY_CLASSIFIER_EXECUTE",
  "repository": "jannekbuengener/Claire_de_Binare",
  "issue": 4374,
  "authorizing_github_login": "jannekbuengener",
  "lr_status": "NO-GO",
  "campaign_id": "arvp-hh-hl-continuation-4374-prep-v1",
  "execute_prompt_path": "agents/prompts/2026-08-08-4374-window-stability-classifier-execute-prompt.md",
  "physical_parameter_set_fingerprint": "9067cd6aa48ad2cc2a7932af50e990888048b8f912b8f3e3ad0dd5b318d1c0a4",
  "campaign_summary_fingerprint": "e5faae11041706e8668252387808f3bd193bdb24c8505d6ba1a7e162413adf28",
  "reproduction_owner_go_comment_id": 5223567140,
  "authorizes": [
    "build_window_stability_from_primary_readonly",
    "validate_window_stability_artifact",
    "run_durable_hh_hl_classifier",
    "write_new_classification_artifact"
  ],
  "does_not_authorize": [
    "stage_b",
    "oos",
    "stress",
    "paper",
    "live",
    "echtgeld",
    "promotion",
    "primary_mutation",
    "new_replay_runs",
    "reproduction_rerun",
    "merge",
    "issue_close"
  ],
  "expires_at_utc": "<OWNER_SETS_FUTURE_UTC>"
}
```
