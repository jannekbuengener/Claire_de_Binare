#!/usr/bin/env python3
"""
Discussion Pipeline CLI

Entry point for running multi-agent discussions on technical proposals.

Usage:
    python run_discussion.py <proposal_file> [options]

Examples:
    # Quick single-agent analysis
    python run_discussion.py proposal.md

    # Full multi-agent pipeline
    python run_discussion.py proposal.md --preset deep

    # Custom Docs Hub location
    python run_discussion.py proposal.md --docs-hub /path/to/docs
"""

import argparse
import sys
from pathlib import Path
from rich.console import Console
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import DiscussionOrchestrator
from utils.config_loader import ConfigLoader


console = Console(force_terminal=True, legacy_windows=False)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run multi-agent discussion pipeline on a technical proposal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s proposal.md
  %(prog)s proposal.md --preset standard
  %(prog)s proposal.md --docs-hub ../Claire_de_Binare_Docs

Presets:
  quick       Single agent (Claude) - fast analysis
  standard    Gemini + Claude - research + synthesis
  technical   Copilot + Claude - implementation focus
  deep        Gemini + Copilot + Claude - full analysis

Environment:
  ANTHROPIC_API_KEY   Required for Claude agent
  GOOGLE_API_KEY      Required for Gemini agent (Phase 2)
  GITHUB_TOKEN        Required for GitHub integration (Phase 3)
  DOCS_HUB_PATH       Optional path to Docs Hub workspace
        """
    )

    parser.add_argument(
        "proposal",
        type=str,
        help="Path to proposal markdown file"
    )

    parser.add_argument(
        "--preset",
        type=str,
        default="quick",
        choices=["quick", "standard", "technical", "deep", "iterative"],
        help="Pipeline preset to use (default: quick)"
    )

    parser.add_argument(
        "--docs-hub",
        type=str,
        default=None,
        help="Path to Docs Hub workspace (auto-detected if not specified)"
    )

    parser.add_argument(
        "--create-issue",
        action="store_true",
        help="Automatically create GitHub issue if pipeline succeeds (requires GITHUB_TOKEN)"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="Discussion Pipeline v0.1.0"
    )

    args = parser.parse_args()

    # Load environment variables from .env
    load_dotenv()

    # Validate proposal file
    proposal_path = Path(args.proposal).resolve()
    if not proposal_path.exists():
        console.print(f"[bold red]Error:[/bold red] Proposal file not found: {proposal_path}")
        sys.exit(1)

    if not proposal_path.suffix == ".md":
        console.print(f"[bold yellow]Warning:[/bold yellow] Proposal file should be Markdown (.md)")

    try:
        # Initialize configuration loader
        console.print("[dim]Loading configuration...[/dim]")
        config_loader = ConfigLoader(docs_hub_path=args.docs_hub)

        # Validate preset exists
        try:
            preset_config = config_loader.get_pipeline_preset(args.preset)
        except KeyError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            sys.exit(1)

        # Initialize orchestrator
        orchestrator = DiscussionOrchestrator(config_loader)

        # Run pipeline
        thread_dir = orchestrator.run_pipeline(
            proposal_path=proposal_path,
            preset=args.preset
        )

        # Success message
        console.print(f"[bold green]Success![/bold green] Discussion completed.")
        console.print(f"\n[bold]Output files:[/bold]")
        console.print(f"  Digest:   {thread_dir / 'DIGEST.md'}")
        console.print(f"  Manifest: {thread_dir / 'manifest.json'}")
        console.print(f"  Outputs:  {thread_dir}/")

        # Auto-create GitHub issue if requested
        if args.create_issue:
            import json
            manifest_file = thread_dir / "manifest.json"
            with open(manifest_file, "r") as f:
                manifest = json.load(f)

            # Only create issue if status is completed (not gated)
            if manifest.get("status") == "completed":
                console.print(f"\n[bold]Creating GitHub issue...[/bold]")
                try:
                    from github.issue_creator import GitHubIssueCreator

                    creator = GitHubIssueCreator(dry_run=False)
                    issue_url = creator.create_issue_from_thread(thread_dir)

                    console.print(f"[bold green]✅ Issue created:[/bold green] {issue_url}")
                except Exception as e:
                    console.print(f"[bold red]Failed to create issue:[/bold red] {e}")
                    console.print(f"[dim]You can create it manually later with:[/dim]")
                    console.print(f"[dim]  python create_github_issue.py {manifest['thread_id']}[/dim]")
            else:
                console.print(f"\n[yellow]Pipeline gated - no issue created.[/yellow]")
                console.print(f"[dim]Review gate file and decide, then create issue manually if approved.[/dim]")

    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Pipeline interrupted by user.[/yellow]")
        sys.exit(130)

    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        import traceback
        console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
