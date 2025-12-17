"""
Gate Handler - Automatic trigger logic for human review.

Determines when pipeline should pause for human intervention
based on confidence scores, disagreements, and strategic keywords.
"""

from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime


class GateHandler:
    """
    Manages gate triggers and creates gate review files.

    Gates are triggered when:
    - Confidence scores fall below threshold
    - Too many disagreements between agents
    - Strategic keywords detected
    - Explicit HUMAN_REVIEW_REQUIRED flag
    """

    def __init__(self, gate_config: Dict[str, Any], docs_hub_path: Path):
        """
        Initialize gate handler.

        Args:
            gate_config: Gate configuration from pipeline_rules.yaml
            docs_hub_path: Path to Docs Hub workspace
        """
        self.config = gate_config
        self.docs_hub_path = docs_hub_path
        self.gates_dir = docs_hub_path / "discussions" / "gates"
        self.gates_dir.mkdir(parents=True, exist_ok=True)

    def should_trigger_gate(
        self,
        outputs: List[Dict[str, Any]],
        quality_metrics: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        Determine if gate should be triggered.

        Args:
            outputs: List of AgentOutput objects
            quality_metrics: Quality metrics from QualityMetrics.analyze_discussion()

        Returns:
            Tuple of (should_trigger, reasons)
        """
        reasons = []

        # Check confidence scores
        if quality_metrics.get("confidence_aggregation"):
            min_confidence = quality_metrics["confidence_aggregation"].get("min")
            threshold = self.config.get("confidence_threshold", 0.5)

            if min_confidence is not None and min_confidence < threshold:
                reasons.append(
                    f"Low confidence score: {min_confidence:.2f} < {threshold}"
                )

        # Check disagreement count
        disagreement_count = quality_metrics.get("disagreement_count", 0)
        disagreement_threshold = self.config.get("disagreement_threshold", 2)

        if disagreement_count > disagreement_threshold:
            reasons.append(
                f"High disagreement count: {disagreement_count} > {disagreement_threshold}"
            )

        # Check strategic keywords (outputs are dict from manifest)
        strategic_keywords = self.config.get("strategic_keywords", [])
        for output in outputs:
            content_preview = output.get("content_preview", "")
            for keyword in strategic_keywords:
                if keyword.lower() in content_preview.lower():
                    reasons.append(f"Strategic keyword detected: '{keyword}'")
                    break  # Only report once per output

        # Check explicit flags
        explicit_flags = self.config.get("explicit_flags", [])
        for output in outputs:
            content_preview = output.get("content_preview", "")
            for flag in explicit_flags:
                if flag in content_preview:
                    reasons.append(f"Explicit flag detected: '{flag}'")
                    break

        should_trigger = len(reasons) > 0
        return should_trigger, reasons

    def create_gate_file(
        self,
        thread_id: str,
        reasons: List[str],
        thread_dir: Path,
        quality_metrics: Dict[str, Any]
    ) -> Path:
        """
        Create gate review file for human decision.

        Args:
            thread_id: Thread identifier
            reasons: List of reasons why gate was triggered
            thread_dir: Path to thread directory
            quality_metrics: Quality metrics

        Returns:
            Path to created gate file
        """
        gate_file = self.gates_dir / f"GATE_{thread_id}.md"

        content = self._build_gate_content(
            thread_id,
            reasons,
            thread_dir,
            quality_metrics
        )

        gate_file.write_text(content, encoding="utf-8")
        return gate_file

    def _build_gate_content(
        self,
        thread_id: str,
        reasons: List[str],
        thread_dir: Path,
        quality_metrics: Dict[str, Any]
    ) -> str:
        """Build gate review markdown content."""
        timestamp = datetime.utcnow().isoformat() + "Z"

        reasons_list = "\n".join([f"- {r}" for r in reasons])

        # Quality summary
        disagreements = quality_metrics.get("disagreement_count", 0)
        echo_score = quality_metrics.get("echo_chamber_score")
        echo_str = f"{echo_score:.2f}" if echo_score is not None else "N/A"
        confidence_agg = quality_metrics.get("confidence_aggregation", {})
        min_conf = confidence_agg.get("min")
        min_conf_str = f"{min_conf:.2f}" if min_conf is not None else "N/A"

        verdict = quality_metrics.get("quality_verdict", "UNKNOWN")

        return f"""# Human Gate Review

**Thread ID:** {thread_id}
**Triggered:** {timestamp}
**Thread Location:** `{thread_dir.relative_to(self.docs_hub_path)}`

---

## Why This Gate Was Triggered

{reasons_list}

---

## Quality Metrics Summary

- **Disagreement Count:** {disagreements}
- **Echo Chamber Score:** {echo_str} (0.0=diverse, 1.0=echo chamber)
- **Minimum Confidence:** {min_conf_str}
- **Overall Verdict:** {verdict}

---

## Your Decision

Please review the discussion thread and make a decision:

- [ ] ✅ **PROCEED** - Create GitHub Issue
  - Discussion is mature enough
  - Disagreements are resolved or acceptable
  - Confidence is sufficient

- [ ] 🔄 **REVISE** - Additional Analysis Needed
  - Which agent should re-analyze?
  - What specific questions need answering?
  - What additional context is needed?

- [ ] ❌ **REJECT** - Archive Discussion
  - Why is this proposal not viable?
  - What fundamental issues prevent proceeding?
  - What would need to change?

### Your Notes

<!-- Add your reasoning here -->

---

## Next Steps After Decision

### If PROCEED:
```bash
# Create GitHub issue from this discussion
python scripts/discussion_pipeline/create_github_issue.py {thread_id}
```

### If REVISE:
```bash
# Resume pipeline with additional agents or context
# Note: Resume functionality pending implementation
# python scripts/discussion_pipeline/run_discussion.py {thread_id} --preset iterative
```

### If REJECT:
- Archive thread for future reference
- Document decision rationale in `manifest.json`

---

## Thread Files

Review these files before deciding:

- `{thread_dir}/manifest.json` - Pipeline metadata
- `{thread_dir}/DIGEST.md` - Discussion summary
- `{thread_dir}/*_output.md` - Individual agent analyses

---

*This gate was automatically triggered by the Discussion Pipeline.*
*Human review is required to proceed.*
"""
