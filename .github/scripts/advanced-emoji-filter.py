#!/usr/bin/env python3
"""
Advanced Emoji Filter for GitHub Repositories
Erkennt, kategorisiert und behandelt Emojis in Code-Dateien
"""

import os
import re
import sys
import json
import yaml
import emoji
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class EmojiDetection:
    file_path: str
    line_number: int
    column: int
    emoji: str
    context_type: str  # 'code', 'comment', 'string', 'variable'
    severity: str
    line_content: str
    is_whitelisted: bool = False


class EmojiAnalyzer:
    def __init__(self, config_path: str = ".github/emoji-config.yaml"):
        self.config = self.load_config(config_path)
        self.detections: List[EmojiDetection] = []
        self.stats = {
            "files_scanned": 0,
            "emojis_found": 0,
            "blocked_emojis": 0,
            "whitelisted_emojis": 0,
        }

        # Kompilierte Regex für bessere Performance
        self.emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # Emoticons
            "\U0001F300-\U0001F5FF"  # Misc Symbols and Pictographs
            "\U0001F680-\U0001F6FF"  # Transport & Map
            "\U0001F1E6-\U0001F1FF"  # Regional Indicator Symbols
            "\U00002700-\U000027BF"  # Dingbats
            "\U00002600-\U000026FF"  # Misc symbols
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols
            "\U0001FA70-\U0001FAFF"  # Extended Symbols
            "\U0001F3FB-\U0001F3FF"  # Skin tone modifiers
            "\U0000200D"  # Zero width joiner
            "\U0000FE0F"  # Variation Selector-16
            "]+"
        )

        # Context-Erkennung Patterns
        self.comment_patterns = {
            "python": re.compile(r"#.*$", re.MULTILINE),
            "javascript": re.compile(r"//.*$|/\*.*?\*/", re.MULTILINE | re.DOTALL),
            "java": re.compile(r"//.*$|/\*.*?\*/", re.MULTILINE | re.DOTALL),
            "cpp": re.compile(r"//.*$|/\*.*?\*/", re.MULTILINE | re.DOTALL),
            "csharp": re.compile(r"//.*$|/\*.*?\*/", re.MULTILINE | re.DOTALL),
        }

        self.string_patterns = {
            "python": re.compile(
                r'(""".*?"""|\'\'\'.*?\'\'\'|".*?"|\'.*?\')', re.DOTALL
            ),
            "javascript": re.compile(r'(`.*?`|".*?"|\'.*?\')', re.DOTALL),
            "java": re.compile(r'".*?"', re.DOTALL),
        }

    def load_config(self, config_path: str) -> Dict:
        """Lädt Konfiguration aus YAML-Datei"""
        if not Path(config_path).exists():
            return self.get_default_config()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ Fehler beim Laden der Konfiguration: {e}")
            return self.get_default_config()

    def get_default_config(self) -> Dict:
        """Standard-Konfiguration"""
        return {
            "detection": {
                "mode": "strict",
                "file_extensions": [".py", ".js", ".ts", ".java", ".cpp", ".c"],
                "exclude_dirs": [".git", "node_modules", "__pycache__"],
                "exclude_files": [],
            },
            "whitelist": {
                "comments_allowed": ["✅", "❌", "⚠️"],
                "strings_allowed": [],
                "variables_allowed": [],
            },
            "actions": {"block_pr": True, "create_issue": False, "auto_fix": False},
            "severity": {
                "code": "error",
                "comments": "warning",
                "strings": "info",
                "tests": "info",
            },
        }

    def get_language_from_extension(self, file_path: str) -> str:
        """Bestimmt Programmiersprache aus Dateiendung"""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "javascript",
            ".jsx": "javascript",
            ".tsx": "javascript",
            ".java": "java",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".c": "cpp",
            ".cs": "csharp",
        }
        return ext_map.get(Path(file_path).suffix, "generic")

    def analyze_context(self, content: str, emoji_match, file_path: str) -> str:
        """Bestimmt Kontext des gefundenen Emojis"""
        lines = content.split("\n")
        line_num = content[: emoji_match.start()].count("\n")
        line_content = lines[line_num] if line_num < len(lines) else ""

        language = self.get_language_from_extension(file_path)

        # Prüfe ob in Kommentar
        if language in self.comment_patterns:
            comment_matches = list(self.comment_patterns[language].finditer(content))
            for match in comment_matches:
                if match.start() <= emoji_match.start() <= match.end():
                    return "comment"

        # Prüfe ob in String
        if language in self.string_patterns:
            string_matches = list(self.string_patterns[language].finditer(content))
            for match in string_matches:
                if match.start() <= emoji_match.start() <= match.end():
                    return "string"

        # Prüfe ob in Variablenname
        if re.search(r"\w+\s*=\s*.*" + re.escape(emoji_match.group()), line_content):
            return "variable"

        return "code"

    def is_whitelisted(self, emoji_char: str, context: str) -> bool:
        """Prüft ob Emoji auf Whitelist steht"""
        whitelist = self.config.get("whitelist", {})

        if context == "comment":
            return emoji_char in whitelist.get("comments_allowed", [])
        elif context == "string":
            return emoji_char in whitelist.get("strings_allowed", [])
        elif context == "variable":
            return emoji_char in whitelist.get("variables_allowed", [])

        return False

    def should_scan_file(self, file_path: Path) -> bool:
        """Prüft ob Datei gescannt werden soll"""
        # Prüfe Dateierweiterung
        if file_path.suffix not in self.config["detection"]["file_extensions"]:
            return False

        # Prüfe ausgeschlossene Verzeichnisse
        for exclude_dir in self.config["detection"]["exclude_dirs"]:
            if exclude_dir in str(file_path):
                return False

        # Prüfe ausgeschlossene Dateien (Regex)
        for pattern in self.config["detection"].get("exclude_files", []):
            if re.search(pattern, str(file_path)):
                return False

        return True

    def scan_file(self, file_path: Path) -> List[EmojiDetection]:
        """Scannt einzelne Datei nach Emojis"""
        detections = []

        try:
            content = file_path.read_text(encoding="utf-8")
            self.stats["files_scanned"] += 1

            # Suche mit Regex
            for match in self.emoji_pattern.finditer(content):
                emoji_char = match.group()
                context = self.analyze_context(content, match, str(file_path))
                is_whitelisted = self.is_whitelisted(emoji_char, context)

                # Berechne Zeilen- und Spaltennummer
                line_num = content[: match.start()].count("\n") + 1
                line_start = content.rfind("\n", 0, match.start()) + 1
                col_num = match.start() - line_start + 1

                # Hole Zeileninhalt
                lines = content.split("\n")
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""

                # Bestimme Severity
                severity = self.config["severity"].get(context, "warning")

                detection = EmojiDetection(
                    file_path=str(file_path),
                    line_number=line_num,
                    column=col_num,
                    emoji=emoji_char,
                    context_type=context,
                    severity=severity,
                    line_content=line_content.strip(),
                    is_whitelisted=is_whitelisted,
                )

                detections.append(detection)
                self.stats["emojis_found"] += 1

                if is_whitelisted:
                    self.stats["whitelisted_emojis"] += 1
                else:
                    self.stats["blocked_emojis"] += 1

            # Zusätzlich: Emoji-Library Check
            emoji_lib_results = emoji.emoji_list(content)
            for emoji_info in emoji_lib_results:
                # Prüfe ob schon durch Regex gefunden
                already_found = any(
                    d.line_number
                    == content[: emoji_info["match_start"]].count("\n") + 1
                    for d in detections
                )

                if not already_found:
                    # Ähnliche Verarbeitung wie oben...
                    pass

        except Exception as e:
            print(f"⚠️ Fehler beim Scannen von {file_path}: {e}")

        return detections

    def scan_repository(self, path: str = ".") -> None:
        """Scannt gesamtes Repository"""
        print(f"🔍 Scanne Repository: {path}")

        for file_path in Path(path).rglob("*"):
            if file_path.is_file() and self.should_scan_file(file_path):
                file_detections = self.scan_file(file_path)
                self.detections.extend(file_detections)

    def auto_fix_emojis(self, backup: bool = True) -> None:
        """Entfernt Emojis automatisch (mit Backup)"""
        if not self.config["actions"].get("auto_fix", False):
            return

        files_to_fix = {}

        # Gruppiere Detections nach Datei
        for detection in self.detections:
            if not detection.is_whitelisted and detection.severity in [
                "error",
                "warning",
            ]:
                if detection.file_path not in files_to_fix:
                    files_to_fix[detection.file_path] = []
                files_to_fix[detection.file_path].append(detection)

        # Fixe jede Datei
        for file_path, detections in files_to_fix.items():
            try:
                # Backup erstellen
                if backup:
                    backup_path = f"{file_path}.emoji-backup"
                    Path(backup_path).write_text(Path(file_path).read_text())
                    print(f"📁 Backup erstellt: {backup_path}")

                # Lade Dateiinhalt
                content = Path(file_path).read_text()

                # Sortiere Detections nach Position (rückwärts für korrekte Offsets)
                detections.sort(key=lambda d: d.line_number, reverse=True)

                # Entferne Emojis
                lines = content.split("\n")
                for detection in detections:
                    line_idx = detection.line_number - 1
                    if line_idx < len(lines):
                        lines[line_idx] = lines[line_idx].replace(detection.emoji, "")

                # Schreibe zurück
                Path(file_path).write_text("\n".join(lines))
                print(f"🔧 Emojis entfernt aus: {file_path}")

            except Exception as e:
                print(f"❌ Fehler beim Fixen von {file_path}: {e}")

    def generate_report(self) -> Dict:
        """Generiert detaillierten Report"""
        # Gruppiere nach Severity
        by_severity = {}
        by_context = {}
        by_file = {}

        for detection in self.detections:
            # Nach Severity
            if detection.severity not in by_severity:
                by_severity[detection.severity] = []
            by_severity[detection.severity].append(detection)

            # Nach Context
            if detection.context_type not in by_context:
                by_context[detection.context_type] = []
            by_context[detection.context_type].append(detection)

            # Nach Datei
            if detection.file_path not in by_file:
                by_file[detection.file_path] = []
            by_file[detection.file_path].append(detection)

        return {
            "summary": self.stats,
            "timestamp": datetime.now().isoformat(),
            "by_severity": {k: [asdict(d) for d in v] for k, v in by_severity.items()},
            "by_context": {k: [asdict(d) for d in v] for k, v in by_context.items()},
            "by_file": {k: [asdict(d) for d in v] for k, v in by_file.items()},
            "blocked_count": len([d for d in self.detections if not d.is_whitelisted]),
            "config": self.config,
        }

    def create_github_annotations(self) -> None:
        """Erstellt GitHub Annotations für Actions"""
        for detection in self.detections:
            if not detection.is_whitelisted:
                level = "error" if detection.severity == "error" else "warning"

                annotation = (
                    f"::{level} file={detection.file_path},"
                    f"line={detection.line_number},"
                    f"col={detection.column}::"
                    f"Emoji '{detection.emoji}' found in {detection.context_type}"
                )
                print(annotation)

                def export_results(self, format: str = "json") -> None:
                    """Exportiert Ergebnisse in verschiedene Formate"""
                    report = self.generate_report()

                    if format == "json":
                        with open("emoji-report.json", "w", encoding="utf-8") as f:
                            json.dump(report, f, indent=2, ensure_ascii=False)

                    elif format == "markdown":
                        with open("emoji-report.md", "w", encoding="utf-8") as f:
                            f.write("# 🚫 Emoji Detection Report\n\n")
                            f.write(f"**Scan Time:** {report['timestamp']}\n")
                            f.write(
                                f"**Files Scanned:** {report['summary']['files_scanned']}\n"
                            )
                            f.write(
                                f"**Emojis Found:** {report['summary']['emojis_found']}\n"
                            )
                            f.write(
                                f"**Blocked:** {report['summary']['blocked_emojis']}\n"
                            )
                            f.write(
                                f"**Whitelisted:** {report['summary']['whitelisted_emojis']}\n\n"
                            )

                            if report["blocked_count"] > 0:
                                f.write("## ❌ Blocked Emojis\n\n")
                                for file_path, detections in report["by_file"].items():
                                    blocked = [
                                        d for d in detections if not d["is_whitelisted"]
                                    ]
                                    if blocked:
                                        f.write(f"### `{file_path}`\n\n")
                                        for detection in blocked:
                                            f.write(
                                                f"- **Line {detection['line_number']}:** "
                                                f"`{detection['emoji']}` in {detection['context_type']} "
                                                f"({detection['severity']})\n"
                                            )
                                        f.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Advanced Emoji Filter")
    parser.add_argument(
        "--config", default=".github/emoji-config.yaml", help="Config file path"
    )
    parser.add_argument("--path", default=".", help="Path to scan")
    parser.add_argument(
        "--format", choices=["json", "markdown"], default="json", help="Output format"
    )
    parser.add_argument("--auto-fix", action="store_true", help="Auto-remove emojis")
    parser.add_argument(
        "--github-actions", action="store_true", help="GitHub Actions mode"
    )

    args = parser.parse_args()

    analyzer = EmojiAnalyzer(args.config)
    analyzer.scan_repository(args.path)

    # Auto-Fix wenn aktiviert
    if args.auto_fix:
        analyzer.auto_fix_emojis(backup=True)

    # Report generieren
    analyzer.export_results(args.format)

    if args.format == "json" and analyzer.config.get("reporting", {}).get(
        "markdown_summary", False
    ):
        analyzer.export_results("markdown")

    # GitHub Actions Ausgaben
    if args.github_actions:
        analyzer.create_github_annotations()

        # Summary für GitHub
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "w") as f:
                f.write(Path("emoji-report.md").read_text())

    # Exit Code basierend auf Konfiguration
    blocked_count = len([d for d in analyzer.detections if not d.is_whitelisted])

    if blocked_count > 0:
        if analyzer.config["detection"]["mode"] == "strict":
            print(f"\n❌ FEHLER: {blocked_count} blockierte Emojis gefunden!")
            sys.exit(1)
        else:
            print(f"\n⚠️ WARNUNG: {blocked_count} Emojis gefunden!")
            sys.exit(0)
    else:
        print("\n✅ Keine problematischen Emojis gefunden!")
        sys.exit(0)


if __name__ == "__main__":
    main()
