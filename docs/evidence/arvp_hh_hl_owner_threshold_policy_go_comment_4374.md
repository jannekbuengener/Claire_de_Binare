## GO_HH_HL_CLASSIFIER_THRESHOLD_POLICY_RATIFY (Owner draft — do not auto-post)

Authorizes only: Owner ratification of `uniform_negative_sign_reject_v1` for #4374 durable classifier.
Does **not** authorize Stage B / Paper / Live / Echtgeld / Promotion / Primary mutation / new replays.

```cdb.hh_hl_classifier_threshold_policy.v1
{
  "schema_version": "cdb.hh_hl_classifier_threshold_policy.v1",
  "policy_id": "uniform_negative_sign_reject_v1",
  "policy_status": "OWNER_RATIFIED",
  "issue": 4374,
  "auto_promotion": false,
  "pnl_only_ranking_forbidden": true,
  "promising_means": "only research follow-up, no promotion",
  "rejected_rules": [
    {
      "rule_id": "uniform_negative_sign_reject_v1",
      "reason_code": "ANALYZER_REJECTED_UNIFORM_NEGATIVE_SIGN",
      "requires": {
        "n_traded_equals_n_total": true,
        "n_total_gt_zero": true,
        "negative_share_net_pnl_quote": 1.0,
        "negative_share_expectancy_r": 1.0,
        "all_gates_not_ranking_ready": true
      }
    }
  ],
  "promising_rules": [],
  "owner_ratified_at_utc": "<OWNER_SETS_ISO_UTC>",
  "owner_github_login": "jannekbuengener",
  "notes": "Sign-consistency REJECTED only. PROMISING rules empty until separate Owner criteria."
}
```

After posting, recompute `policy_fingerprint` via:

`python -c "from tools.arvp_vacation.hh_hl_campaign_analyzer import build_threshold_policy; import json; print(json.dumps(build_threshold_policy(...), indent=2))"`
