"""
Pipeline Orchestrator - Core execution logic.

Manages sequential execution of agents, state tracking,
and output generation.
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

try:
    from .agents.base import AgentOutput
    from .agents.claude_agent import ClaudeAgent
    from .agents.gemini_agent import GeminiAgent
    from .agents.copilot_agent import CopilotAgent
    from .utils.config_loader import ConfigLoader
    from .quality.metrics import QualityMetrics
    from .gates.gate_handler import GateHandler
except ImportError:
    # Fallback for direct script execution
    from agents.base import AgentOutput
    from agents.claude_agent import ClaudeAgent
    from agents.gemini_agent import GeminiAgent
    from agents.copilot_agent import CopilotAgent
    from utils.config_loader import ConfigLoader
    from quality.metrics import QualityMetrics
    from gates.gate_handler import GateHandler


console = Console(force_terminal=True, legacy_windows=False)


class DiscussionOrchestrator:
    """
    Orchestrates multi-agent discussion pipeline.

    Responsibilities:
    - Create thread directories for outputs
    - Load pipeline configuration
    - Execute agents sequentially
    - Track pipeline state in manifest.json
    - Generate final digest
    """

    def __init__(self, config_loader: ConfigLoader):
        """
        Initialize orchestrator with configuration.

        Args:
            config_loader: ConfigLoader instance with Docs Hub access
        """
        self.config_loader = config_loader
        self.config = config_loader.load_config()
        self.docs_hub_path = config_loader.docs_hub_path

    def run_pipeline(
        self,
        proposal_path: Path,
        preset: str = "quick"
    ) -> Path:
        """
        Execute the discussion pipeline.

        Args:
            proposal_path: Path to proposal markdown file
            preset: Pipeline preset name (quick, standard, deep, etc.)

        Returns:
            Path to thread output directory

        Raises:
            FileNotFoundError: If proposal doesn't exist
            ValueError: If preset is invalid
        """
        if not proposal_path.exists():
            raise FileNotFoundError(f"Proposal not found: {proposal_path}")

        # Load proposal content
        proposal_content = proposal_path.read_text(encoding="utf-8")

        # Get pipeline configuration
        pipeline_config = self.config_loader.get_pipeline_preset(preset)
        agent_names = pipeline_config["agents"]

        # Create thread directory
        thread_dir = self._create_thread_directory(proposal_path.name)

        console.print("\n[bold cyan]🚀 Starting Discussion Pipeline[/bold cyan]")
        console.print(f"[dim]Preset: {preset}[/dim]")
        console.print(f"[dim]Agents: {' → '.join(agent_names)}[/dim]")
        console.print(f"[dim]Output: {thread_dir}[/dim]\n")

        # Initialize manifest
        manifest = self._init_manifest(
            proposal_path=str(proposal_path),
            pipeline=agent_names,
            preset=preset
        )

        # Execute agents sequentially
        context = [proposal_content]  # Start with proposal as first context

        for i, agent_name in enumerate(agent_names):
            step_num = i + 1
            total_steps = len(agent_names)

            console.print(f"[bold]🤖 Running {agent_name}[/bold] (Step {step_num}/{total_steps})")

            try:
                # Execute agent
                output = self._run_agent(agent_name, proposal_content, context[1:])  # Skip proposal itself in context

                # Save output to file
                output_file = thread_dir / f"{step_num:02d}_{agent_name}_output.md"
                output_file.write_text(output.content, encoding="utf-8")

                console.print(f"[green]✅ {agent_name} completed[/green]")
                if output.confidence_scores:
                    scores_str = ", ".join([f"{k}: {v:.2f}" for k, v in output.confidence_scores.items()])
                    console.print(f"   [dim]Confidence: {scores_str}[/dim]")

                # Update manifest
                manifest["agents_completed"].append(agent_name)
                manifest["outputs"].append(output.to_dict())
                manifest["current_step"] = step_num
                self._save_manifest(thread_dir, manifest)

                # Add output to context for next agent
                context.append(output.content)

            except Exception as e:
                console.print(f"[bold red]❌ {agent_name} failed: {e}[/bold red]")
                manifest["status"] = "failed"
                manifest["error"] = str(e)
                self._save_manifest(thread_dir, manifest)
                raise

        # Analyze quality metrics
        console.print("\n[bold]📊 Analyzing discussion quality...[/bold]")
        quality_metrics = QualityMetrics.analyze_discussion(thread_dir)

        manifest["quality_metrics"] = quality_metrics
        console.print(f"   [dim]Disagreements: {quality_metrics['disagreement_count']}[/dim]")
        if quality_metrics.get("echo_chamber_score") is not None:
            console.print(f"   [dim]Echo chamber score: {quality_metrics['echo_chamber_score']:.2f}[/dim]")
        console.print(f"   [dim]Quality verdict: {quality_metrics['quality_verdict']}[/dim]")

        # Check if gate should be triggered
        gate_handler = GateHandler(
            self.config_loader.get_gate_config(),
            self.docs_hub_path
        )

        should_trigger, reasons = gate_handler.should_trigger_gate(
            [manifest["outputs"][i] for i in range(len(agent_names))],
            quality_metrics
        )
        auto_proceed = self._should_auto_proceed(quality_metrics) if should_trigger else False

        if should_trigger:
            console.print(f"\n[bold yellow]⚠️  Gate triggered - Human review required[/bold yellow]")
            for reason in reasons:
                console.print(f"   [dim]- {reason}[/dim]")

            gate_file = gate_handler.create_gate_file(
                manifest["thread_id"],
                reasons,
                thread_dir,
                quality_metrics
            )

            manifest["gate_file"] = str(gate_file.relative_to(self.docs_hub_path))
            manifest["gate_reasons"] = reasons
            manifest["gate_auto_proceed"] = auto_proceed
            self._save_manifest(thread_dir, manifest)

            console.print(f"\n[bold]Gate file created:[/bold] {gate_file}")
            if auto_proceed:
                console.print(f"[dim]Auto-PROCEED based on quality metrics.[/dim]\n")
            else:
                console.print(f"[dim]Review and make decision: PROCEED / REVISE / REJECT[/dim]\n")
                return thread_dir

        # Generate digest
        console.print("\n[bold]📝 Generating digest...[/bold]")
        self._generate_digest(thread_dir, context)

        # Finalize manifest
        manifest["status"] = "completed"
        manifest["completed_at"] = datetime.utcnow().isoformat() + "Z"
        self._save_manifest(thread_dir, manifest)

        console.print(f"\n[bold green]✅ Pipeline completed successfully![/bold green]")
        console.print(f"[bold]Results:[/bold] {thread_dir / 'DIGEST.md'}\n")

        return thread_dir

    def _create_thread_directory(self, proposal_name: str) -> Path:
        """
        Create thread output directory in Docs Hub.

        Args:
            proposal_name: Name of proposal file

        Returns:
            Path to thread directory
        """
        timestamp = int(time.time())
        thread_name = f"THREAD_{timestamp}"
        thread_dir = self.docs_hub_path / "discussions" / "threads" / thread_name

        thread_dir.mkdir(parents=True, exist_ok=True)

        return thread_dir

    def _init_manifest(
        self,
        proposal_path: str,
        pipeline: List[str],
        preset: str
    ) -> Dict[str, Any]:
        """
        Initialize pipeline manifest.

        Args:
            proposal_path: Path to proposal file
            pipeline: List of agent names
            preset: Pipeline preset name

        Returns:
            Dict with manifest data
        """
        return {
            "thread_id": f"THREAD_{int(time.time())}",
            "proposal_path": proposal_path,
            "pipeline": pipeline,
            "preset": preset,
            "status": "in_progress",
            "current_step": 0,
            "agents_completed": [],
            "outputs": [],
            "started_at": datetime.utcnow().isoformat() + "Z",
            "completed_at": None,
            "error": None
        }

    def _save_manifest(self, thread_dir: Path, manifest: Dict[str, Any]) -> None:
        """Save manifest to thread directory."""
        manifest_file = thread_dir / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    def _run_agent(
        self,
        agent_name: str,
        proposal: str,
        context: List[str]
    ) -> AgentOutput:
        """
        Execute a specific agent.

        Args:
            agent_name: Name of agent to run
            proposal: Original proposal content
            context: Previous agent outputs

        Returns:
            AgentOutput from agent

        Raises:
            ValueError: If agent is unknown
        """
        agent_config = self.config_loader.get_agent_config(agent_name)

        if agent_name == "claude":
            agent = ClaudeAgent(agent_config)
        elif agent_name == "gemini":
            agent = GeminiAgent(agent_config)
        elif agent_name == "copilot":
            agent = CopilotAgent(agent_config)
        else:
            raise ValueError(f"Unknown agent: {agent_name}")

        return agent.analyze(proposal, context)

    def _should_auto_proceed(self, quality_metrics: Dict[str, Any]) -> bool:
        """Auto-PROCEED when quality is good enough."""
        verdict = (quality_metrics or {}).get("quality_verdict", "")
        min_confidence = (quality_metrics or {}).get("confidence_aggregation", {}).get("min")
        return verdict in {"EXCELLENT", "GOOD"} and (min_confidence is not None and min_confidence >= 0.65)

    def _generate_digest(self, thread_dir: Path, context: List[str]) -> None:
        """
        Generate final digest markdown.

        Args:
            thread_dir: Path to thread directory
            context: All outputs (proposal + agents)
        """
        manifest_file = thread_dir / "manifest.json"
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        digest_content = f"""# Discussion Digest

**Thread ID:** {manifest['thread_id']}
**Proposal:** {Path(manifest['proposal_path']).name}
**Pipeline:** {' → '.join(manifest['pipeline'])}
**Status:** {manifest['status']}
**Started:** {manifest['started_at']}
**Completed:** {manifest.get('completed_at', 'N/A')}

---

## Pipeline Execution

"""

        # Add summary of each agent's output
        for i, output_info in enumerate(manifest["outputs"]):
            agent_name = output_info["agent"]
            output_file = thread_dir / f"{i+1:02d}_{agent_name}_output.md"

            digest_content += f"""### {i+1}. {agent_name.title()} Analysis

**File:** `{output_file.name}`
**Confidence:** {output_info.get('confidence_scores', {})}

"""

            # Add preview of output
            if output_file.exists():
                full_output = output_file.read_text(encoding="utf-8")
                # Extract first 300 chars as preview
                preview = full_output[:300] + "..." if len(full_output) > 300 else full_output
                digest_content += f"""```
{preview}
```

"""

        digest_content += """---

## Next Steps

- Review individual agent outputs in this thread directory
- Make a gate decision if needed (PROCEED / REVISE / REJECT)
- If approved, create GitHub issue from this discussion

---

*Generated by Discussion Pipeline*
"""

        digest_file = thread_dir / "DIGEST.md"
        digest_file.write_text(digest_content, encoding="utf-8")
