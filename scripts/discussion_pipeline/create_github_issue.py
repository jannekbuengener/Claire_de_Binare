#!/usr/bin/env python3
"""
Create GitHub Issue from Discussion Thread

Standalone script to create GitHub issues from completed pipeline threads.

Usage:
    python create_github_issue.py <thread_id> [options]

Examples:
    # Dry-run (preview)
    python create_github_issue.py THREAD_1765955316 --dry-run

    # Create issue
    python create_github_issue.py THREAD_1765955316

    # Custom repo
    python create_github_issue.py THREAD_1765955316 --repo owner/repo

    # Custom labels
    python create_github_issue.py THREAD_1765955316 --labels bug,enhancement
"""

import argparse
import sys
from pathlib import Path
from rich.console import Console
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from github.issue_creator import GitHubIssueCreator
from utils.config_loader import ConfigLoader


console = Console(force_terminal=True, legacy_windows=False)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Create GitHub issue from discussion pipeline thread",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s THREAD_1765955316 --dry-run
  %(prog)s THREAD_1765955316 --repo owner/repo
  %(prog)s THREAD_1765955316 --labels bug,enhancement

Environment:
  GITHUB_TOKEN   Required for creating issues (not needed for --dry-run)
        """,
    )

    parser.add_argument(
        "thread_id", type=str, help="Thread ID (e.g., THREAD_1765955316)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview issue without creating (no GITHUB_TOKEN needed)",
    )

    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="GitHub repository (owner/repo). Auto-detected if not specified.",
    )

    parser.add_argument(
        "--labels",
        type=str,
        default=None,
        help="Comma-separated list of labels to apply",
    )

    parser.add_argument(
        "--template",
        type=str,
        default=None,
        help="Custom issue template path (uses default if not specified)",
    )

    parser.add_argument(
        "--docs-hub",
        type=str,
        default=None,
        help="Path to Docs Hub workspace (auto-detected if not specified)",
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    try:
        # Initialize config loader to find Docs Hub
        console.print("[dim]Locating Docs Hub...[/dim]")
        config_loader = ConfigLoader(docs_hub_path=args.docs_hub)
        docs_hub_path = config_loader.docs_hub_path

        # Find thread directory
        thread_dir = docs_hub_path / "discussions" / "threads" / args.thread_id

        if not thread_dir.exists():
            console.print(f"[bold red]Error:[/bold red] Thread not found: {thread_dir}")
            sys.exit(1)

        console.print(f"[dim]Found thread: {thread_dir}[/dim]\n")

        # Parse labels
        labels = None
        if args.labels:
            labels = [label.strip() for label in args.labels.split(",")]

        # Parse template
        template_path = None
        if args.template:
            template_path = Path(args.template)
            if not template_path.exists():
                console.print(
                    f"[bold red]Error:[/bold red] Template not found: {template_path}"
                )
                sys.exit(1)

        # Initialize issue creator
        if args.dry_run:
            console.print(
                "[bold yellow]DRY RUN MODE - No issue will be created[/bold yellow]\n"
            )

        creator = GitHubIssueCreator(repo_name=args.repo, dry_run=args.dry_run)

        # Create issue
        issue_url = creator.create_issue_from_thread(
            thread_dir=thread_dir, template_path=template_path, labels=labels
        )

        if issue_url:
            console.print("\n[bold green]✅ Issue created successfully![/bold green]")
            console.print(f"[bold]URL:[/bold] {issue_url}\n")
        elif args.dry_run:
            console.print("\n[bold yellow]Preview complete.[/bold yellow]")
            console.print("[dim]Remove --dry-run to create issue.[/dim]\n")

    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
        sys.exit(130)

    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        import traceback

        console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
