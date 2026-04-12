# cdb-control-followup-classifier — Unit Notes

## Status rationale

`manual_only` — this workflow has no automatic trigger. It exists as a human-dispatch
tool for classifying issues against the CDB control-followup framework. It should
remain manual: the classification is context-sensitive and the human decides when
re-classification is warranted.

## Gold-im-Keller context

Identified in #1633 audit as a Gold-im-Keller candidate: the underlying prompt
(`.github/prompts/cdb-control-followup.prompt.yml`) is the same prompt used by the
automated post-merge scanner. This shared prompt is the real asset; the classifier
workflow is the manual dispatch entry point for the same logic.

## Shared dependency with cdb-post-merge-followup-scanner

Both units share `.github/prompts/cdb-control-followup.prompt.yml`. Changes to that
prompt affect both units. The manifest for each unit declares the shared prompt under
`dependencies.prompts`.

## Output surface notes

- The `result.json` artifact is the machine-readable classification output.
- The `summary.md` artifact is the human-readable summary.
- Issue comment posting is optional and controlled by the `post_comment` input;
  it does not auto-post by default.

## Caveats

- No SLA on response — it is HITL by design.
- The `issue_number` input is required; running without a valid issue number will fail.
- `models: read` permission is required for the GitHub Models API call in the prompt runner.

## Related issues

- #1445: Weekly cockpit (indirect consumer of outputs)
- #1633: Workflow audit (classified this unit as manual-only, Gold-im-Keller)
- #1644: This collection-layer entry
