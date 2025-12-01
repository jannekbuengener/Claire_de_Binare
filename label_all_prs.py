#!/usr/bin/env python3
"""
label_all_prs.py - Automatisches Label-System für Pull Requests
Erstellt für: Claire de Binare Claire de Binare
Datum: 2025-11-22

Verwendet die GitHub API über gh CLI oder direkt über requests.
"""

import json
import subprocess
import sys
from typing import List, Dict, Set
from pathlib import Path


# Farben für Terminal-Output
class Colors:
    GREEN = "\033[0;32m"
    BLUE = "\033[0;34m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    NC = "\033[0m"  # No Color


class PRLabeler:
    """Automatisches Label-System für Pull Requests"""

    def __init__(self, repo: str):
        self.repo = repo
        self.label_rules = self._load_label_rules()
        self.stats = {"total_prs": 0, "labeled_prs": 0, "skipped_prs": 0}

    def _load_label_rules(self) -> Dict:
        """Lade Label-Regeln aus pr_labels.json"""
        json_path = Path(__file__).parent / "pr_labels.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._get_default_rules()

    def _get_default_rules(self) -> Dict:
        """Standard Label-Regeln"""
        return {
            "label_rules": {
                "type_labels": {
                    "feat": ["feat:", "feature:"],
                    "fix": ["fix:", "bugfix:"],
                    "docs": ["docs:", "documentation:"],
                    "test": ["test:", "tests:"],
                    "refactor": ["refactor:"],
                    "chore": ["chore:"],
                    "ci": ["ci:", "ci/cd:"],
                },
                "area_labels": {
                    "risk-engine": [
                        "risk",
                        "risk-engine",
                        "risk_engine",
                        "risk manager",
                    ],
                    "signal-engine": ["signal", "signal-engine", "signal_engine"],
                    "execution": ["execution", "exec"],
                    "testing": ["test", "testing", "pytest", "coverage"],
                    "infrastructure": [
                        "infrastructure",
                        "docker",
                        "compose",
                        "deployment",
                    ],
                    "security": ["security", "secrets", "audit"],
                    "performance": ["performance", "optimization", "speed"],
                },
                "special_labels": {
                    "dependencies": ["bump", "dependabot", "dependencies"]
                },
            }
        }

    def run_gh_command(self, *args) -> str:
        """Führe gh CLI Kommando aus"""
        try:
            result = subprocess.run(
                ["gh", *args], capture_output=True, text=True, check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}❌ Fehler: {e}{Colors.NC}")
            print(f"Output: {e.stderr}")
            sys.exit(1)

    def check_gh_cli(self) -> bool:
        """Prüfe ob gh CLI installiert und authentifiziert ist"""
        try:
            # Prüfe Installation
            subprocess.run(["gh", "--version"], capture_output=True, check=True)

            # Prüfe Authentifizierung
            subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)

            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_all_prs(self) -> List[Dict]:
        """Hole alle Pull Requests"""
        print(f"{Colors.BLUE}Hole alle Pull Requests...{Colors.NC}")

        output = self.run_gh_command(
            "api",
            f"repos/{self.repo}/pulls",
            "--paginate",
            "-X",
            "GET",
            "-f",
            "state=all",
            "-f",
            "per_page=100",
        )

        prs = json.loads(output)
        print(f"📊 Gefunden: {len(prs)} Pull Requests")
        return prs

    def get_available_labels(self) -> List[Dict]:
        """Hole verfügbare Labels im Repository"""
        print(f"{Colors.BLUE}Prüfe verfügbare Labels...{Colors.NC}")

        output = self.run_gh_command("api", f"repos/{self.repo}/labels", "--paginate")

        labels = json.loads(output)
        print(f"🏷️  Verfügbare Labels: {len(labels)}")
        return labels

    def create_standard_labels(self):
        """Erstelle Standard-Labels wenn keine vorhanden"""
        print(f"{Colors.YELLOW}⚠️  Erstelle Standard-Labels...{Colors.NC}")

        standard_labels = [
            {
                "name": "feat",
                "description": "Feature - Neue Funktionalität",
                "color": "0e8a16",
            },
            {
                "name": "fix",
                "description": "Bugfix - Fehlerbehebung",
                "color": "d73a4a",
            },
            {"name": "docs", "description": "Dokumentation", "color": "0075ca"},
            {"name": "test", "description": "Tests", "color": "ffd700"},
            {"name": "refactor", "description": "Refactoring", "color": "fbca04"},
            {"name": "chore", "description": "Chore - Wartung", "color": "fef2c0"},
            {"name": "ci", "description": "CI/CD", "color": "1e90ff"},
            {"name": "risk-engine", "description": "Risk Engine", "color": "ff6347"},
            {
                "name": "signal-engine",
                "description": "Signal Engine",
                "color": "4169e1",
            },
            {
                "name": "execution",
                "description": "Execution Service",
                "color": "32cd32",
            },
            {
                "name": "testing",
                "description": "Testing Infrastructure",
                "color": "ffa500",
            },
            {
                "name": "infrastructure",
                "description": "Infrastructure",
                "color": "8b4513",
            },
            {"name": "security", "description": "Security", "color": "b22222"},
            {"name": "performance", "description": "Performance", "color": "9370db"},
        ]

        for label in standard_labels:
            try:
                self.run_gh_command(
                    "api",
                    f"repos/{self.repo}/labels",
                    "--method",
                    "POST",
                    "-f",
                    f'name={label["name"]}',
                    "-f",
                    f'description={label["description"]}',
                    "-f",
                    f'color={label["color"]}',
                )
                print(f"  ✅ Erstellt: {label['name']}")
            except Exception:
                pass  # Label existiert bereits

    def analyze_pr(self, pr: Dict) -> Set[str]:
        """Analysiere PR und bestimme passende Labels"""
        title = pr.get("title", "").lower()
        body = pr.get("body", "") or ""
        body_lower = body.lower()

        labels_to_add = set()

        # Typ-Labels
        type_rules = self.label_rules.get("label_rules", {}).get("type_labels", {})
        for label, keywords in type_rules.items():
            for keyword in keywords:
                if title.startswith(keyword.lower()):
                    labels_to_add.add(label)
                    break

        # Bereichs-Labels
        area_rules = self.label_rules.get("label_rules", {}).get("area_labels", {})
        for label, keywords in area_rules.items():
            for keyword in keywords:
                if keyword.lower() in title or keyword.lower() in body_lower:
                    labels_to_add.add(label)
                    break

        # Spezial-Labels
        special_rules = self.label_rules.get("label_rules", {}).get(
            "special_labels", {}
        )
        for label, keywords in special_rules.items():
            for keyword in keywords:
                if keyword.lower() in title or keyword.lower() in body_lower:
                    labels_to_add.add(label)
                    break

        return labels_to_add

    def add_labels_to_pr(self, pr_number: int, labels: Set[str]):
        """Füge Labels zu PR hinzu"""
        if not labels:
            return

        for label in labels:
            try:
                self.run_gh_command(
                    "api",
                    f"repos/{self.repo}/issues/{pr_number}/labels",
                    "--method",
                    "POST",
                    "-f",
                    f"labels[]={label}",
                )
            except Exception:
                pass  # Label existiert bereits oder andere Fehler

    def process_all_prs(self):
        """Verarbeite alle Pull Requests"""
        prs = self.get_all_prs()
        labels = self.get_available_labels()

        # Erstelle Labels falls nötig
        if len(labels) == 0:
            self.create_standard_labels()

        print(f"\n{Colors.BLUE}Analysiere Pull Requests...{Colors.NC}\n")

        for pr in prs:
            self.stats["total_prs"] += 1

            pr_number = pr["number"]
            pr_title = pr["title"]
            pr_state = pr["state"]
            pr_merged = pr.get("merged_at") is not None

            print("━" * 60)
            print(f"{Colors.GREEN}PR #{pr_number}{Colors.NC}: {pr_title}")
            print(f"Status: {pr_state} | Merged: {pr_merged}")

            # Analysiere PR
            labels_to_add = self.analyze_pr(pr)

            if labels_to_add:
                print(f"🏷️  Labels: {', '.join(sorted(labels_to_add))}")
                self.add_labels_to_pr(pr_number, labels_to_add)
                self.stats["labeled_prs"] += 1
                print("✅ Labels hinzugefügt")
            else:
                print(f"{Colors.YELLOW}⚠️  Keine passenden Labels gefunden{Colors.NC}")
                self.stats["skipped_prs"] += 1

            print()

    def print_summary(self):
        """Drucke Zusammenfassung"""
        print("━" * 60)
        print(f"\n{Colors.GREEN}✅ Fertig!{Colors.NC}\n")
        print("📊 Statistik:")
        print(f"   Gesamt PRs:     {self.stats['total_prs']}")
        print(f"   Gelabelt:       {self.stats['labeled_prs']}")
        print(f"   Übersprungen:   {self.stats['skipped_prs']}")
        print()

    def run(self):
        """Hauptprogramm"""
        print(
            f"{Colors.BLUE}🏷️  Label-Bot für Claire de Binare Pull Requests{Colors.NC}"
        )
        print("=" * 60)
        print()

        # Prüfe Voraussetzungen
        print(f"{Colors.BLUE}Schritt 1: Prüfe GitHub CLI...{Colors.NC}")
        if not self.check_gh_cli():
            print(
                f"{Colors.RED}❌ GitHub CLI nicht gefunden oder nicht authentifiziert!{Colors.NC}"
            )
            print("Installation: brew install gh / sudo apt install gh")
            print("Authentifizierung: gh auth login")
            sys.exit(1)
        print("✅ GitHub CLI bereit")
        print()

        # Verarbeite PRs
        try:
            self.process_all_prs()
            self.print_summary()
        except Exception as e:
            print(f"{Colors.RED}❌ Fehler: {e}{Colors.NC}")
            sys.exit(1)


def main():
    """Main Entry Point"""
    repo = "jannekbuengener/Claire_de_Binare"

    # Argument Parsing (optional)
    if len(sys.argv) > 1:
        repo = sys.argv[1]

    labeler = PRLabeler(repo)
    labeler.run()


if __name__ == "__main__":
    main()
