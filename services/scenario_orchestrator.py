"""
Scenario Orchestrator

Führt mehrere Paper-Trading Runs mit verschiedenen Konfigurationen aus:
- Lädt Scenario-Definitionen aus YAML
- Führt jeden Scenario aus (parallel oder sequenziell)
- Sammelt Ergebnisse
- Generiert Vergleichs-Report

CLI Usage:
    claire run-scenarios --config backtests/momentum_profiles.yaml
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

import yaml

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.paper_trading_runner import PaperTradingRunner
from services.trading_statistics import ReportGenerator

logger = logging.getLogger(__name__)


# ==============================================================================
# SCENARIO ORCHESTRATOR
# ==============================================================================


class ScenarioOrchestrator:
    """
    Orchestrates multiple paper trading scenarios.

    Workflow:
    1. Load scenario config (YAML)
    2. Create runner for each scenario
    3. Run scenarios (sequential for now)
    4. Collect results
    5. Generate comparison report
    """

    def __init__(self, config_path: Path, output_dir: Path):
        """
        Initialize scenario orchestrator.

        Args:
            config_path: Path to scenario config YAML
            output_dir: Output directory for reports
        """
        self.config_path = Path(config_path)
        self.output_dir = Path(output_dir)

        # Load config
        self.config = self._load_config()

        logger.info(
            f"📋 Scenario Orchestrator initialized "
            f"({len(self.config['scenarios'])} scenarios)"
        )

    def _load_config(self) -> Dict:
        """
        Load scenario configuration from YAML.

        Returns:
            Config dict
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        # Validate config
        if "scenarios" not in config:
            raise ValueError("Config missing 'scenarios' key")

        logger.info(f"📄 Loaded config: {self.config_path}")

        return config

    def run_all_scenarios(self) -> List[Dict]:
        """
        Run all scenarios from config.

        Returns:
            List of scenario results
        """
        logger.info(
            f"🚀 Running {len(self.config['scenarios'])} scenarios..."
        )

        results = []

        for scenario in self.config["scenarios"]:
            result = self._run_scenario(scenario)
            results.append(result)

        logger.info("✅ All scenarios complete")

        # Generate comparison report
        self._save_comparison_report(results)

        return results

    def _run_scenario(self, scenario: Dict) -> Dict:
        """
        Run single scenario.

        Args:
            scenario: Scenario config dict

        Returns:
            Scenario result dict
        """
        name = scenario["name"]

        logger.info(f"▶️  Running scenario: {name}")

        # Extract parameters
        strategy = scenario.get("strategy", "momentum_v1")
        risk_profile = scenario.get("risk_profile")
        custom_risk_params = scenario.get("risk_params", {})

        # Get period
        period = scenario.get("period", self.config.get("default_period", {}))
        from_date = period.get("from")
        to_date = period.get("to")
        days = period.get("days")

        # Create runner
        runner = PaperTradingRunner(
            strategy_name=strategy,
            risk_profile=risk_profile or "balanced",
            output_dir=self.output_dir / name.replace(" ", "_"),
        )

        # Override risk params if specified
        if custom_risk_params:
            runner.risk_config.update(custom_risk_params)
            logger.debug(f"Applied custom risk params: {custom_risk_params}")

        # Parse dates
        from_dt = None
        to_dt = None

        if from_date:
            from datetime import datetime, timezone

            from_dt = datetime.fromisoformat(from_date).replace(
                tzinfo=timezone.utc
            )
        if to_date:
            from datetime import datetime, timezone

            to_dt = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc)

        # Run
        result = runner.run(from_date=from_dt, to_date=to_dt, days=days)

        # Add scenario name to result
        result["scenario_name"] = name

        logger.info(
            f"✅ Scenario '{name}' complete: "
            f"{result['statistics']['total_trades']} trades, "
            f"{result['statistics']['total_return_pct']:+.2f}% return"
        )

        return result

    def _save_comparison_report(self, results: List[Dict]) -> None:
        """
        Save comparison report for all scenarios.

        Args:
            results: List of scenario results
        """
        # Prepare data for comparison
        comparison_data = [
            {
                "name": r["scenario_name"],
                "stats": r["statistics"],
            }
            for r in results
        ]

        # Generate comparison table
        comparison_text = ReportGenerator.compare_scenarios(comparison_data)

        # Log to console
        logger.info(f"\n{comparison_text}")

        # Save to file
        output_path = self.output_dir / "scenario_comparison.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(comparison_text)

        logger.info(f"📄 Comparison report saved: {output_path}")

        # Save detailed JSON
        import json

        json_path = self.output_dir / "scenario_comparison.json"

        with open(json_path, "w") as f:
            json.dump(
                {
                    "config": str(self.config_path),
                    "scenarios": comparison_data,
                },
                f,
                indent=2,
            )

        logger.info(f"📄 Detailed JSON saved: {json_path}")


# ==============================================================================
# CLI HELPER FUNCTION
# ==============================================================================


def run_scenarios_from_config(config_path: str, output_dir: str = "backtest_results/scenarios") -> List[Dict]:
    """
    Run scenarios from config file.

    Args:
        config_path: Path to scenario config YAML
        output_dir: Output directory

    Returns:
        List of scenario results
    """
    orchestrator = ScenarioOrchestrator(
        config_path=Path(config_path), output_dir=Path(output_dir)
    )

    results = orchestrator.run_all_scenarios()

    return results


# ==============================================================================
# EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example: Run scenarios from config
    # run_scenarios_from_config("backtests/momentum_profiles.yaml")

    logger.info("Scenario Orchestrator loaded. Use run_scenarios_from_config() to run.")
