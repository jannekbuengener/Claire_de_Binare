"""
Real 72-Hour Validation Fetcher - NO MORE FAKE RESULTS
URGENT: Replaces simulated test results with real validation data
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path

from core.utils.clock import utcnow

class RealValidationFetcher:
    """Fetch REAL 72-hour validation results - NO MORE FAKE"""

    def __init__(self):
        self.validation_db_path = os.getenv(
            "VALIDATION_DB_PATH", "/app/data/validation_results.db"
        )
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create validation database if it doesn't exist"""
        Path(self.validation_db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.validation_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT NOT NULL,
                total_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                total_pnl REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                sharpe_ratio REAL DEFAULT 0.0,
                avg_trade_duration TEXT DEFAULT '0h',
                largest_loss REAL DEFAULT 0.0,
                largest_win REAL DEFAULT 0.0,
                final_balance REAL DEFAULT 0.0,
                test_passed BOOLEAN DEFAULT FALSE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

    def get_latest_72h_results(self) -> Optional[Dict]:
        """Get latest REAL 72-hour validation results"""
        conn = sqlite3.connect(self.validation_db_path)
        cursor = conn.cursor()

        # Get latest completed 72-hour validation
        cursor.execute(
            """
            SELECT * FROM validation_runs 
            WHERE status = 'completed'
            AND end_time IS NOT NULL
            AND datetime(end_time) >= datetime(start_time, '+71 hours')
            ORDER BY end_time DESC
            LIMIT 1
        """
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Convert to dict
        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row))

        # Calculate validation age
        end_time = datetime.fromisoformat(result["end_time"])
        hours_ago = (utcnow() - end_time).total_seconds() / 3600

        # Validation expires after 7 days
        if hours_ago > 168:  # 7 days
            return {
                "test_passed": False,
                "error": "Validation results expired",
                "message": f"Last validation was {hours_ago:.1f} hours ago. Max age: 168 hours",
                "timestamp": result["end_time"],
            }

        # Return real validation results
        return {
            "test_passed": bool(result["test_passed"]),
            "test_completed": True,
            "duration_hours": 72,
            "total_trades": result["total_trades"],
            "win_rate": result["win_rate"],
            "total_pnl": result["total_pnl"],
            "max_drawdown": result["max_drawdown"],
            "sharpe_ratio": result["sharpe_ratio"],
            "avg_trade_duration": result["avg_trade_duration"],
            "largest_loss": result["largest_loss"],
            "largest_win": result["largest_win"],
            "final_balance": result["final_balance"],
            "timestamp": result["end_time"],
            "validation_age_hours": hours_ago,
        }

    def start_72h_validation(self) -> int:
        """Start new 72-hour validation run - REAL validation"""
        conn = sqlite3.connect(self.validation_db_path)
        cursor = conn.cursor()

        start_time = utcnow().isoformat()

        cursor.execute(
            """
            INSERT INTO validation_runs (start_time, status)
            VALUES (?, 'running')
        """,
            (start_time,),
        )

        run_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return run_id

    def update_validation_progress(self, run_id: int, metrics: Dict):
        """Update validation run with real trading metrics"""
        conn = sqlite3.connect(self.validation_db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE validation_runs SET
                total_trades = ?,
                win_rate = ?,
                total_pnl = ?,
                max_drawdown = ?,
                sharpe_ratio = ?,
                avg_trade_duration = ?,
                largest_loss = ?,
                largest_win = ?,
                final_balance = ?
            WHERE id = ?
        """,
            (
                metrics.get("total_trades", 0),
                metrics.get("win_rate", 0.0),
                metrics.get("total_pnl", 0.0),
                metrics.get("max_drawdown", 0.0),
                metrics.get("sharpe_ratio", 0.0),
                metrics.get("avg_trade_duration", "0h"),
                metrics.get("largest_loss", 0.0),
                metrics.get("largest_win", 0.0),
                metrics.get("final_balance", 0.0),
                run_id,
            ),
        )

        conn.commit()
        conn.close()

    def complete_validation(self, run_id: int, test_passed: bool):
        """Mark validation as completed with pass/fail result"""
        conn = sqlite3.connect(self.validation_db_path)
        cursor = conn.cursor()

        end_time = utcnow().isoformat()

        cursor.execute(
            """
            UPDATE validation_runs SET
                end_time = ?,
                status = 'completed',
                test_passed = ?
            WHERE id = ?
        """,
            (end_time, test_passed, run_id),
        )

        conn.commit()
        conn.close()

    def is_validation_required(self) -> bool:
        """Check if new 72-hour validation is required"""
        latest = self.get_latest_72h_results()

        if not latest:
            return True  # No validation found

        if not latest.get("test_passed", False):
            return True  # Last validation failed

        # Check if validation is still valid (less than 7 days old)
        age_hours = latest.get("validation_age_hours", 999)
        return age_hours > 168  # Require new validation after 7 days
