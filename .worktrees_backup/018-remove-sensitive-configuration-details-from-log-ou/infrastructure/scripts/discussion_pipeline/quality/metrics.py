"""
Quality Metrics for Multi-Agent Discussions.

Measures discussion quality through:
- Disagreement detection and counting
- Echo chamber score (similarity analysis)
- Confidence score aggregation
"""

from typing import List, Dict, Any
from pathlib import Path
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class QualityMetrics:
    """
    Analyzes quality of multi-agent discussions.

    Metrics:
    - Disagreement count: Number of explicit conflicts
    - Echo chamber score: 0.0 (diverse) to 1.0 (identical)
    - Confidence aggregation: Min/max/avg across agents
    """

    @staticmethod
    def count_disagreements(outputs: List[str]) -> int:
        """
        Count explicit disagreement markers in agent outputs.

        Args:
            outputs: List of agent output markdown texts

        Returns:
            Number of disagreements found
        """
        disagreement_patterns = [
            r"🔴\s*Disagreement",
            r"I disagree",
            r"My position differs",
            r"Contrary to.*claim",
            r"However.*incorrect",
        ]

        total_disagreements = 0
        for output in outputs:
            for pattern in disagreement_patterns:
                matches = re.findall(pattern, output, re.IGNORECASE)
                total_disagreements += len(matches)

        return total_disagreements

    @staticmethod
    def calculate_echo_chamber_score(outputs: List[str]) -> float:
        """
        Calculate similarity between agent outputs using TF-IDF + cosine similarity.

        Returns:
            0.0 = completely diverse perspectives (good)
            1.0 = identical outputs (echo chamber, bad)

        Args:
            outputs: List of agent output markdown texts

        Returns:
            Echo chamber score between 0.0 and 1.0
        """
        if len(outputs) < 2:
            return 0.0  # Can't measure similarity with < 2 outputs

        # Extract just the content (strip YAML frontmatter)
        clean_outputs = [QualityMetrics._extract_content(o) for o in outputs]

        try:
            # TF-IDF vectorization
            vectorizer = TfidfVectorizer(
                stop_words="english", max_features=500, ngram_range=(1, 2)
            )
            tfidf_matrix = vectorizer.fit_transform(clean_outputs)

            # Cosine similarity between all pairs
            similarities = cosine_similarity(tfidf_matrix)

            # Average pairwise similarity (excluding diagonal)
            n = len(similarities)
            total_similarity = (
                similarities.sum() - n
            )  # Subtract diagonal (self-similarity = 1.0)
            avg_similarity = total_similarity / (n * (n - 1))

            return float(avg_similarity)

        except Exception:
            # If TF-IDF fails (e.g., empty outputs), return 0
            return 0.0

    @staticmethod
    def aggregate_confidence_scores(outputs: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Aggregate confidence scores across agents.

        Args:
            outputs: List of agent confidence score dicts

        Returns:
            Dict with min, max, avg, and per-agent scores
        """
        all_scores = []
        per_agent = {}

        for i, scores in enumerate(outputs):
            if scores:
                agent_avg = np.mean(list(scores.values()))
                all_scores.append(agent_avg)
                per_agent[f"agent_{i+1}"] = {"avg": float(agent_avg), "scores": scores}

        if not all_scores:
            return {"min": None, "max": None, "avg": None, "per_agent": {}}

        return {
            "min": float(np.min(all_scores)),
            "max": float(np.max(all_scores)),
            "avg": float(np.mean(all_scores)),
            "per_agent": per_agent,
        }

    @staticmethod
    def _extract_content(markdown: str) -> str:
        """
        Extract main content from markdown, stripping YAML frontmatter.

        Args:
            markdown: Full markdown text

        Returns:
            Content without frontmatter
        """
        if markdown.startswith("---"):
            # Find end of frontmatter
            end_marker = markdown.find("---", 3)
            if end_marker != -1:
                return markdown[end_marker + 3 :].strip()

        return markdown.strip()

    @staticmethod
    def analyze_discussion(thread_dir: Path) -> Dict[str, Any]:
        """
        Analyze a complete discussion thread.

        Args:
            thread_dir: Path to thread directory

        Returns:
            Dict with all quality metrics
        """
        # Load all agent outputs
        output_files = sorted(thread_dir.glob("*_output.md"))
        outputs = [f.read_text(encoding="utf-8") for f in output_files]

        if not outputs:
            return {
                "disagreement_count": 0,
                "echo_chamber_score": None,
                "confidence_aggregation": {},
                "quality_verdict": "NO_DATA",
            }

        # Extract confidence scores from each output
        confidence_scores = []
        for output in outputs:
            scores = QualityMetrics._extract_confidence_from_yaml(output)
            confidence_scores.append(scores)

        # Calculate metrics
        disagreement_count = QualityMetrics.count_disagreements(outputs)
        echo_score = QualityMetrics.calculate_echo_chamber_score(outputs)
        confidence_agg = QualityMetrics.aggregate_confidence_scores(confidence_scores)

        # Quality verdict
        verdict = QualityMetrics._determine_verdict(
            disagreement_count, echo_score, confidence_agg.get("min")
        )

        return {
            "disagreement_count": disagreement_count,
            "echo_chamber_score": echo_score,
            "confidence_aggregation": confidence_agg,
            "quality_verdict": verdict,
        }

    @staticmethod
    def _extract_confidence_from_yaml(markdown: str) -> Dict[str, float]:
        """Extract confidence_scores from YAML frontmatter."""
        if not markdown.startswith("---"):
            return {}

        end_marker = markdown.find("---", 3)
        if end_marker == -1:
            return {}

        try:
            import yaml

            frontmatter = markdown[3:end_marker].strip()
            data = yaml.safe_load(frontmatter)
            return data.get("confidence_scores", {}) if data else {}
        except Exception:
            return {}

    @staticmethod
    def _determine_verdict(
        disagreement_count: int, echo_score: float, min_confidence: float
    ) -> str:
        """
        Determine overall quality verdict.

        Returns:
            EXCELLENT / GOOD / ACCEPTABLE / CONCERNING / POOR
        """
        if min_confidence is None:
            return "NO_CONFIDENCE_DATA"

        # Echo chamber is bad
        if echo_score and echo_score > 0.7:
            return "POOR_ECHO_CHAMBER"

        # Low confidence is concerning
        if min_confidence < 0.5:
            return "CONCERNING_LOW_CONFIDENCE"

        # Too few disagreements might indicate lack of critical thinking
        if disagreement_count == 0:
            return "ACCEPTABLE_NO_DISAGREEMENTS"

        # Good balance: some disagreements, diverse perspectives, decent confidence
        if disagreement_count >= 1 and echo_score < 0.5 and min_confidence >= 0.6:
            return "EXCELLENT"

        if min_confidence >= 0.6:
            return "GOOD"

        return "ACCEPTABLE"
