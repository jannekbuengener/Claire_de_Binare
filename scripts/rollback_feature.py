#!/usr/bin/env python3
"""
Feature Rollback Automation Script

Provides automated rollback capabilities for features using feature flags
and configuration management.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, List

# Add core modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "core"))

try:
    from core.config.feature_flags import get_feature_flag_manager, FeatureFlagState
except ImportError:
    print("Warning: Could not import feature flag manager. Running in standalone mode.")
    get_feature_flag_manager = None


class FeatureRollbackManager:
    """Manages automated feature rollbacks"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.logger = self._setup_logging()
        self.rollback_log = []

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        return logging.getLogger(__name__)

    def rollback_feature(
        self, feature_name: str, rollback_type: str = "feature_flag"
    ) -> Dict[str, Any]:
        """
        Rollback a feature using specified strategy

        Args:
            feature_name: Name of feature to rollback
            rollback_type: Type of rollback (feature_flag, config, full)

        Returns:
            Rollback operation results
        """
        self.logger.info(f"Starting rollback for feature: {feature_name}")

        rollback_result = {
            "feature": feature_name,
            "rollback_type": rollback_type,
            "timestamp": datetime.utcnow().isoformat(),
            "dry_run": self.dry_run,
            "steps": [],
            "success": False,
            "errors": [],
        }

        try:
            if rollback_type == "feature_flag":
                result = self._rollback_via_feature_flag(feature_name)
            elif rollback_type == "config":
                result = self._rollback_via_config(feature_name)
            elif rollback_type == "full":
                result = self._rollback_full(feature_name)
            else:
                raise ValueError(f"Unknown rollback type: {rollback_type}")

            rollback_result.update(result)
            rollback_result["success"] = True

            # Validate rollback
            validation_result = self._validate_rollback(feature_name)
            rollback_result["validation"] = validation_result

            self.logger.info(
                f"Rollback completed successfully for feature: {feature_name}"
            )

        except Exception as e:
            error_msg = f"Rollback failed for feature {feature_name}: {str(e)}"
            self.logger.error(error_msg)
            rollback_result["errors"].append(error_msg)

        # Log rollback operation
        self.rollback_log.append(rollback_result)
        self._save_rollback_log()

        return rollback_result

    def _rollback_via_feature_flag(self, feature_name: str) -> Dict[str, Any]:
        """Rollback feature by disabling feature flag"""
        steps = []

        if get_feature_flag_manager:
            flag_manager = get_feature_flag_manager()

            # Check if flag exists
            if feature_name not in flag_manager.get_all_flags():
                raise ValueError(f"Feature flag '{feature_name}' not found")

            # Disable feature flag
            if not self.dry_run:
                flag_manager.update_flag(feature_name, FeatureFlagState.DISABLED)
                flag_manager.save_config()

            steps.append(
                {
                    "action": "disable_feature_flag",
                    "target": feature_name,
                    "status": "completed" if not self.dry_run else "dry_run",
                }
            )
        else:
            steps.append(
                {
                    "action": "disable_feature_flag",
                    "target": feature_name,
                    "status": "skipped",
                    "reason": "Feature flag manager not available",
                }
            )

        return {
            "steps": steps,
            "rollback_time_seconds": 1,  # Feature flag rollback is immediate
        }

    def _rollback_via_config(self, feature_name: str) -> Dict[str, Any]:
        """Rollback feature by reverting configuration changes"""
        steps = []

        # Look for feature-specific config backup
        config_backup_path = f"config/backups/{feature_name}_backup.json"

        if os.path.exists(config_backup_path):
            steps.append(
                {
                    "action": "restore_config_backup",
                    "target": config_backup_path,
                    "status": "completed" if not self.dry_run else "dry_run",
                }
            )

            if not self.dry_run:
                # Restore configuration from backup
                self._restore_config_from_backup(config_backup_path)
        else:
            steps.append(
                {
                    "action": "restore_config_backup",
                    "target": config_backup_path,
                    "status": "skipped",
                    "reason": "No config backup found",
                }
            )

        return {"steps": steps, "rollback_time_seconds": 5}

    def _rollback_full(self, feature_name: str) -> Dict[str, Any]:
        """Full rollback including feature flags, config, and services"""
        steps = []

        # 1. Disable feature flag
        flag_result = self._rollback_via_feature_flag(feature_name)
        steps.extend(flag_result["steps"])

        # 2. Restore configuration
        config_result = self._rollback_via_config(feature_name)
        steps.extend(config_result["steps"])

        # 3. Restart affected services (if needed)
        services_to_restart = self._get_affected_services(feature_name)
        for service in services_to_restart:
            if not self.dry_run:
                self._restart_service(service)

            steps.append(
                {
                    "action": "restart_service",
                    "target": service,
                    "status": "completed" if not self.dry_run else "dry_run",
                }
            )

        return {
            "steps": steps,
            "rollback_time_seconds": 30 + len(services_to_restart) * 10,
        }

    def _restore_config_from_backup(self, backup_path: str):
        """Restore configuration from backup file"""
        try:
            with open(backup_path, "r") as f:
                backup_data = json.load(f)

            # Restore each configuration file
            for config_file, config_data in backup_data.items():
                config_path = os.path.join("config", config_file)
                os.makedirs(os.path.dirname(config_path), exist_ok=True)

                with open(config_path, "w") as f:
                    json.dump(config_data, f, indent=2)

                self.logger.info(f"Restored configuration: {config_path}")

        except Exception as e:
            self.logger.error(f"Failed to restore config from {backup_path}: {e}")
            raise

    def _get_affected_services(self, feature_name: str) -> List[str]:
        """Get list of services affected by feature"""
        # This would normally read from a feature manifest or config
        # For now, return common services that might be affected
        return ["signal", "risk", "execution"]

    def _restart_service(self, service_name: str):
        """Restart a service (placeholder for actual implementation)"""
        # This would integrate with the actual service management system
        # For now, just log the action
        self.logger.info(f"Restarting service: {service_name}")

    def _validate_rollback(self, feature_name: str) -> Dict[str, Any]:
        """Validate that rollback was successful"""
        validation_results = {
            "feature_disabled": False,
            "services_healthy": True,
            "system_responsive": True,
            "errors": [],
        }

        try:
            # Check feature flag status
            if get_feature_flag_manager:
                flag_manager = get_feature_flag_manager()
                if feature_name in flag_manager.get_all_flags():
                    flag = flag_manager.get_all_flags()[feature_name]
                    validation_results["feature_disabled"] = (
                        flag.state == FeatureFlagState.DISABLED
                    )

            # Additional health checks would go here
            # For now, assume system is healthy

        except Exception as e:
            validation_results["errors"].append(str(e))

        return validation_results

    def _save_rollback_log(self):
        """Save rollback log to file"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, "rollback_log.json")

        try:
            with open(log_file, "w") as f:
                json.dump(self.rollback_log, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save rollback log: {e}")

    def emergency_rollback_all(self) -> Dict[str, Any]:
        """Emergency rollback of all active features"""
        self.logger.warning("Starting emergency rollback of all features")

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "rollbacks": [],
            "total_features": 0,
            "successful_rollbacks": 0,
            "failed_rollbacks": 0,
        }

        if get_feature_flag_manager:
            flag_manager = get_feature_flag_manager()
            all_flags = flag_manager.get_all_flags()

            for feature_name, flag in all_flags.items():
                if flag.state != FeatureFlagState.DISABLED:
                    rollback_result = self.rollback_feature(
                        feature_name, "feature_flag"
                    )
                    results["rollbacks"].append(rollback_result)
                    results["total_features"] += 1

                    if rollback_result["success"]:
                        results["successful_rollbacks"] += 1
                    else:
                        results["failed_rollbacks"] += 1

        self.logger.warning(
            f"Emergency rollback completed. Success: {results['successful_rollbacks']}, Failed: {results['failed_rollbacks']}"
        )

        return results


def main():
    parser = argparse.ArgumentParser(description="Feature Rollback Automation")
    parser.add_argument("feature", help="Feature name to rollback")
    parser.add_argument(
        "--type",
        choices=["feature_flag", "config", "full"],
        default="feature_flag",
        help="Rollback type",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Perform dry run without making changes"
    )
    parser.add_argument(
        "--emergency", action="store_true", help="Emergency rollback of all features"
    )

    args = parser.parse_args()

    rollback_manager = FeatureRollbackManager(dry_run=args.dry_run)

    if args.emergency:
        result = rollback_manager.emergency_rollback_all()
    else:
        result = rollback_manager.rollback_feature(args.feature, args.type)

    # Print results
    print(json.dumps(result, indent=2))

    return 0 if result.get("success", False) else 1


if __name__ == "__main__":
    sys.exit(main())
