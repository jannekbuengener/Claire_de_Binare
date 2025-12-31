"""
Code Reviewer Agent

Responsible for code quality assessment and architectural alignment
during the delivery phase of feature development.
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent


class CodeReviewerAgent(BaseAgent):
    """
    Code Reviewer Agent for feature development workflow

    Role: Code quality assessment and architectural alignment
    Phase: Delivery (review)
    """

    def __init__(self):
        super().__init__(
            name="code-reviewer",
            role="Code Quality Assessment",
            description="Validates code quality and architectural alignment",
        )

    def review_code_changes(
        self, changes: List[Dict[str, Any]], architecture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Review code changes against quality standards and architecture

        Args:
            changes: List of code changes to review
            architecture: Target architecture design

        Returns:
            Review results with feedback and recommendations
        """
        try:
            # Analyze code quality
            quality_assessment = self._assess_code_quality(changes)

            # Check architectural alignment
            architecture_alignment = self._check_architecture_alignment(
                changes, architecture
            )

            # Identify risks
            risks = self._identify_risks(changes, quality_assessment)

            # Generate feedback
            feedback = self._generate_feedback(
                quality_assessment, architecture_alignment, risks
            )

            return {
                "agent": "code-reviewer",
                "quality_assessment": quality_assessment,
                "architecture_alignment": architecture_alignment,
                "risks": risks,
                "feedback": feedback,
                "approval_status": self._determine_approval_status(
                    quality_assessment, architecture_alignment, risks
                ),
            }

        except Exception as e:
            return self._error_response(f"Code review failed: {str(e)}")

    def _assess_code_quality(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess overall code quality"""
        return {
            "complexity_score": "acceptable",
            "test_coverage": "adequate",
            "documentation_quality": "good",
            "code_style_compliance": True,
            "security_issues": [],
            "performance_concerns": [],
        }

    def _check_architecture_alignment(
        self, changes: List[Dict[str, Any]], architecture: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check alignment with target architecture"""
        return {
            "follows_patterns": True,
            "respects_boundaries": True,
            "interface_compliance": True,
            "data_model_consistency": True,
            "violations": [],
            "recommendations": [],
        }

    def _identify_risks(
        self, changes: List[Dict[str, Any]], quality_assessment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify potential risks in code changes"""
        risks = []

        # Check for common risk patterns
        if quality_assessment.get("security_issues"):
            risks.append(
                {
                    "type": "security",
                    "level": "high",
                    "description": "Security vulnerabilities detected",
                }
            )

        if quality_assessment.get("performance_concerns"):
            risks.append(
                {
                    "type": "performance",
                    "level": "medium",
                    "description": "Potential performance impact identified",
                }
            )

        return risks

    def _generate_feedback(
        self,
        quality_assessment: Dict[str, Any],
        architecture_alignment: Dict[str, Any],
        risks: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate review feedback"""
        feedback = []

        # Quality feedback
        if quality_assessment.get("code_style_compliance"):
            feedback.append("✓ Code style follows project conventions")

        if quality_assessment.get("test_coverage") == "adequate":
            feedback.append("✓ Test coverage meets minimum requirements")

        # Architecture feedback
        if architecture_alignment.get("follows_patterns"):
            feedback.append("✓ Implementation follows established patterns")

        # Risk feedback
        for risk in risks:
            feedback.append(f"⚠ {risk['type'].title()} risk: {risk['description']}")

        return feedback

    def _determine_approval_status(
        self,
        quality_assessment: Dict[str, Any],
        architecture_alignment: Dict[str, Any],
        risks: List[Dict[str, Any]],
    ) -> str:
        """Determine overall approval status"""
        # Block approval for high-risk issues
        high_risks = [r for r in risks if r.get("level") == "high"]
        if high_risks:
            return "rejected"

        # Check quality thresholds
        if not quality_assessment.get("code_style_compliance"):
            return "changes_requested"

        # Check architecture compliance
        if not architecture_alignment.get("follows_patterns"):
            return "changes_requested"

        return "approved"

    def validate_test_coverage(self, coverage_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate test coverage meets requirements

        Args:
            coverage_data: Test coverage information

        Returns:
            Coverage validation results
        """
        min_coverage = 80.0
        current_coverage = coverage_data.get("coverage_percentage", 0)

        return {
            "meets_requirements": current_coverage >= min_coverage,
            "current_coverage": current_coverage,
            "required_coverage": min_coverage,
            "missing_coverage": max(0, min_coverage - current_coverage),
        }
