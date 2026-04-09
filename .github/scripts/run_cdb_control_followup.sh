#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "usage: $0 <prompt-file> <finding-text> <output-json> [summary-md]" >&2
  exit 2
fi

prompt_file="$1"
finding_text="$2"
output_json="$3"
summary_md="${4:-}"

command -v gh >/dev/null 2>&1 || {
  echo "gh CLI not found in PATH" >&2
  exit 1
}

command -v jq >/dev/null 2>&1 || {
  echo "jq not found in PATH" >&2
  exit 1
}

if [[ ! -f "$prompt_file" ]]; then
  echo "prompt file not found: $prompt_file" >&2
  exit 1
fi

mkdir -p "$(dirname "$output_json")"
if [[ -n "$summary_md" ]]; then
  mkdir -p "$(dirname "$summary_md")"
fi

tmp_raw="$(mktemp)"
trap 'rm -f "$tmp_raw"' EXIT

gh models run --file "$prompt_file" --var "input=$finding_text" > "$tmp_raw"

jq -e '
  type == "object" and
  (.classification | type == "string") and
  (.classification == "report_only" or .classification == "follow_up_issue" or .classification == "unclear") and
  (.confidence | type == "number") and
  (.confidence >= 0 and .confidence <= 1) and
  (.affected_artifacts | type == "array") and
  (all(.affected_artifacts[]; type == "string" and length > 0)) and
  (.suggested_next_step | type == "string")
' "$tmp_raw" > /dev/null

jq . "$tmp_raw" > "$output_json"

if [[ -n "$summary_md" ]]; then
  {
    echo "## CDB Control Follow-up Classification"
    echo
    echo "- Prompt: \`$prompt_file\`"
    echo "- Classification: \`$(jq -r '.classification' "$output_json")\`"
    echo "- Confidence: \`$(jq -r '.confidence' "$output_json")\`"
    echo "- Affected artifacts: \`$(jq -r '.affected_artifacts | join(", ")' "$output_json")\`"
    echo "- Suggested next step: $(jq -r '.suggested_next_step' "$output_json")"
    echo
    echo "### Finding"
    echo
    printf '%s\n' "$finding_text"
    echo
    echo "### JSON"
    echo
    echo '```json'
    jq . "$output_json"
    echo '```'
  } > "$summary_md"
fi
