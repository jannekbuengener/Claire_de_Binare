"""
GitHub Issue Creator - Converts approved discussions to GitHub issues.

Uses PyGithub to create issues with proper formatting, labels,
and links back to discussion threads.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from github import Github, GithubException


class GitHubIssueCreator:
    """
    Creates GitHub issues from discussion pipeline outputs.

    Features:
    - Rich issue body with agent analysis summaries
    - Automatic label assignment based on proposal tags
    - Links back to discussion thread
    - Dry-run mode for preview
    - Error handling and validation
    """

    def __init__(self, repo_name: Optional[str] = None, dry_run: bool = False):
        """
        Initialize GitHub issue creator.

        Args:
            repo_name: GitHub repository (owner/repo). Auto-detected if None.
            dry_run: If True, preview issue without creating
        """
        self.dry_run = dry_run

        # Get GitHub token
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token and not dry_run:
            raise ValueError("GITHUB_TOKEN environment variable not set")

        if not dry_run:
            self.github = Github(github_token)
        else:
            self.github = None

        # Auto-detect or use provided repo
        self.repo_name = repo_name or self._detect_repo_name()

        if not dry_run and self.github:
            try:
                self.repo = self.github.get_repo(self.repo_name)
            except GithubException as e:
                raise ValueError(f"Cannot access repository {self.repo_name}: {e}")
        else:
            self.repo = None

    def _detect_repo_name(self) -> str:
        """Auto-detect GitHub repo from git remote."""
        import subprocess
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()

            # Parse git@github.com:owner/repo.git or https://github.com/owner/repo.git
            if "github.com" in remote_url:
                parts = remote_url.split("github.com")[-1]
                parts = parts.strip("/:").replace(".git", "")
                return parts

            raise ValueError("Cannot parse GitHub repo from remote URL")

        except Exception as e:
            raise ValueError(f"Cannot auto-detect repo. Please specify --repo: {e}")

    def create_issue_from_thread(
        self,
        thread_dir: Path,
        template_path: Optional[Path] = None,
        labels: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Create GitHub issue from discussion thread.

        Args:
            thread_dir: Path to thread directory
            template_path: Optional custom template
            labels: Optional list of label names to apply

        Returns:
            Issue URL if created, None if dry-run
        """
        # Load manifest
        manifest_file = thread_dir / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_file}")

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # Check if already completed
        if manifest.get("status") not in ["completed", "gated"]:
            raise ValueError(f"Thread not ready for issue creation. Status: {manifest.get('status')}")

        # Load template
        if template_path is None:
            # Use default template from Docs Hub
            template_path = self._find_default_template(thread_dir)

        issue_body = self._render_template(template_path, manifest, thread_dir)
        issue_title = self._extract_title(manifest)

        # Apply labels
        issue_labels = labels or self._infer_labels(manifest)

        if self.dry_run:
            # Preview mode
            print("\n" + "="*80)
            print("DRY RUN - Issue Preview")
            print("="*80)
            print(f"\nRepository: {self.repo_name}")
            print(f"Title: {issue_title}")
            print(f"Labels: {', '.join(issue_labels)}")
            print("\nBody:")
            print("-"*80)
            print(issue_body)
            print("="*80)
            return None

        # Create issue
        try:
            issue = self.repo.create_issue(
                title=issue_title,
                body=issue_body,
                labels=issue_labels
            )

            # Update manifest with issue link
            manifest["github_issue"] = {
                "number": issue.number,
                "url": issue.html_url,
                "created_at": issue.created_at.isoformat()
            }

            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

            return issue.html_url

        except GithubException as e:
            raise RuntimeError(f"Failed to create GitHub issue: {e}")

    def _find_default_template(self, thread_dir: Path) -> Path:
        """Find default issue template in Docs Hub."""
        # Navigate from thread dir to Docs Hub
        docs_hub = thread_dir.parents[2]  # discussions/threads/THREAD_X -> docs_hub
        template_path = docs_hub / "docs" / "templates" / "github_issue.md"

        if not template_path.exists():
            raise FileNotFoundError(
                f"Default template not found: {template_path}\n"
                "Please create template or specify --template"
            )

        return template_path

    def _render_template(
        self,
        template_path: Path,
        manifest: Dict[str, Any],
        thread_dir: Path
    ) -> str:
        """
        Render issue template with manifest data.

        Args:
            template_path: Path to markdown template
            manifest: Thread manifest data
            thread_dir: Path to thread directory

        Returns:
            Rendered issue body
        """
        template = template_path.read_text(encoding="utf-8")

        # Extract data for template
        thread_id = manifest.get("thread_id", "UNKNOWN")
        proposal_path = manifest.get("proposal_path", "")
        proposal_name = Path(proposal_path).name if proposal_path else "Unknown Proposal"
        pipeline = " → ".join(manifest.get("pipeline", []))

        # Quality metrics
        quality = manifest.get("quality_metrics", {})
        quality_verdict = quality.get("quality_verdict", "N/A")
        disagreements = quality.get("disagreement_count", 0)
        echo_score = quality.get("echo_chamber_score")
        echo_str = f"{echo_score:.2f}" if echo_score is not None else "N/A"

        # Agent summaries
        agent_summaries = self._extract_agent_summaries(manifest, thread_dir)

        # Template variables
        variables = {
            "{thread_id}": thread_id,
            "{proposal_name}": proposal_name,
            "{pipeline}": pipeline,
            "{quality_verdict}": quality_verdict,
            "{disagreement_count}": str(disagreements),
            "{echo_chamber_score}": echo_str,
            "{agent_summaries}": agent_summaries,
            "{thread_path}": str(thread_dir.relative_to(thread_dir.parents[2])),
            "{repo_name}": self.repo_name if self.repo_name else "unknown"
        }

        # Replace variables
        rendered = template
        for key, value in variables.items():
            rendered = rendered.replace(key, value)

        return rendered

    def _extract_agent_summaries(
        self,
        manifest: Dict[str, Any],
        thread_dir: Path
    ) -> str:
        """Extract key points from each agent's output."""
        summaries = []

        for i, output_info in enumerate(manifest.get("outputs", [])):
            agent_name = output_info.get("agent", f"Agent {i+1}")
            output_file = thread_dir / f"{i+1:02d}_{agent_name}_output.md"

            if output_file.exists():
                content = output_file.read_text(encoding="utf-8")
                # Extract first section after frontmatter as summary
                summary = self._extract_summary(content)
            else:
                summary = "Output file not found"

            summaries.append(f"### {agent_name.title()}\n\n{summary}")

        return "\n\n".join(summaries)

    def _extract_summary(self, content: str, max_chars: int = 500) -> str:
        """Extract summary from agent output."""
        # Skip YAML frontmatter
        if content.startswith("---"):
            end_marker = content.find("---", 3)
            if end_marker != -1:
                content = content[end_marker + 3:].strip()

        # Take first section or paragraph
        lines = content.split("\n")
        summary_lines = []
        char_count = 0

        for line in lines:
            if line.startswith("##") and summary_lines:
                break  # Stop at second heading
            summary_lines.append(line)
            char_count += len(line)
            if char_count > max_chars:
                break

        summary = "\n".join(summary_lines).strip()
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."

        return summary

    def _extract_title(self, manifest: Dict[str, Any]) -> str:
        """Extract issue title from manifest."""
        proposal_path = manifest.get("proposal_path", "")
        proposal_name = Path(proposal_path).stem if proposal_path else "Discussion"

        # Remove common prefixes
        proposal_name = proposal_name.replace("PROPOSAL_", "").replace("proposal_", "")
        proposal_name = proposal_name.replace("_", " ").title()

        return f"Discussion: {proposal_name}"

    def _infer_labels(self, manifest: Dict[str, Any]) -> List[str]:
        """Infer labels from manifest data."""
        labels = ["discussion-pipeline"]

        # Add quality-based labels
        quality = manifest.get("quality_metrics", {})
        verdict = quality.get("quality_verdict", "")

        if "EXCELLENT" in verdict:
            labels.append("high-quality")
        elif "CONCERNING" in verdict or "POOR" in verdict:
            labels.append("needs-review")

        # Add pipeline preset as label
        preset = manifest.get("preset")
        if preset:
            labels.append(f"preset:{preset}")

        return labels
