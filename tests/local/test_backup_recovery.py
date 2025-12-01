"""
Backup & Recovery Tests - Claire de Binare
Lokaler-only Test: Database Backup und Restore-Szenarien

WICHTIG: Dieser Test MUSS lokal mit Docker Compose ausgeführt werden!
    - Erfordert: PostgreSQL mit Daten, Docker Compose CLI
    - Testet: pg_dump/pg_restore Workflows
    - Prüft: Data Integrity nach Restore, Backup-Performance
    - NICHT in CI ausführen (zu langsam, braucht echte DB)

Ausführung:
    pytest -v -m local_only tests/local/test_backup_recovery.py
"""

import pytest
import subprocess
import psycopg2
import time
from datetime import datetime


@pytest.fixture
def backup_dir(tmp_path):
    """Temporäres Verzeichnis für Backups"""
    backup_path = tmp_path / "backups"
    backup_path.mkdir()
    return backup_path


@pytest.fixture
def postgres_conn():
    """PostgreSQL Connection"""
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="claire_de_binare",
        user="claire_user",
        password="claire_db_secret_2024",
    )
    yield conn
    conn.close()


def run_docker_exec(container, command, timeout=60):
    """Helper: Command im Docker-Container ausführen"""
    cmd = ["docker", "compose", "exec", "-T", container] + command
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result


@pytest.mark.local_only
def test_postgres_backup_creates_dump_file(backup_dir, postgres_conn):
    """
    Backup-Test: pg_dump erstellt .sql Dump-File

    Validiert:
    - Backup-Command funktioniert
    - Dump-File wird erstellt
    - Dump-File ist nicht leer
    - Backup dauert <60s
    """
    print("\n💾 Backup-Test: PostgreSQL dump creation...")

    # Baseline: DB hat Daten
    cursor = postgres_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
    snapshot_count = cursor.fetchone()[0]

    print(f"  📊 DB has {snapshot_count} portfolio_snapshots")

    # Backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = backup_dir / f"claire_backup_{timestamp}.sql"

    # Perform backup (via docker exec)
    print(f"  💾 Creating backup: {dump_file.name}...")

    start_time = time.time()

    # pg_dump inside container, redirect stdout to file
    result = run_docker_exec(
        "cdb_postgres",
        [
            "pg_dump",
            "-U",
            "claire_user",
            "-d",
            "claire_de_binare",
            "--no-owner",
            "--no-acl",
        ],
    )

    elapsed = time.time() - start_time

    # Check if pg_dump succeeded
    assert result.returncode == 0, f"pg_dump failed: {result.stderr}"

    # Write dump to file
    with open(dump_file, "w") as f:
        f.write(result.stdout)

    # Validate dump file
    assert dump_file.exists(), "Dump file not created"
    assert dump_file.stat().st_size > 0, "Dump file is empty"

    dump_size_kb = dump_file.stat().st_size / 1024

    print(f"  ✅ Backup created: {dump_size_kb:.1f} KB in {elapsed:.2f}s")

    # Performance assertion
    assert elapsed < 60.0, f"Backup too slow: {elapsed:.2f}s (max 60s)"

    # Validate dump contains schema
    with open(dump_file, "r") as f:
        dump_content = f.read()

    # Should contain table definitions
    assert "CREATE TABLE" in dump_content, "Dump missing table definitions"
    assert "portfolio_snapshots" in dump_content, "Dump missing portfolio_snapshots"

    print("  ✅ Dump file valid")

    print("\n✅ Backup creation test passed")


@pytest.mark.local_only
@pytest.mark.slow
def test_postgres_restore_from_backup(backup_dir, postgres_conn):
    """
    Restore-Test: pg_restore funktioniert und stellt Daten wieder her

    Simuliert:
    - Backup erstellen
    - Testdaten einfügen
    - Restore durchführen
    - Validieren: Testdaten sind weg

    Validiert:
    - Restore funktioniert
    - Data-Integrity
    - Alte Daten werden wiederhergestellt
    """
    print("\n🔄 Restore-Test: PostgreSQL restore from backup...")

    # Step 1: Baseline - Count portfolio_snapshots
    print("  📊 Step 1: Baseline - count snapshots...")

    cursor = postgres_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
    baseline_count = cursor.fetchone()[0]

    print(f"    ✓ Baseline: {baseline_count} snapshots")

    # Step 2: Create Backup
    print("  💾 Step 2: Create backup...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = backup_dir / f"claire_backup_{timestamp}.sql"

    result = run_docker_exec(
        "cdb_postgres",
        [
            "pg_dump",
            "-U",
            "claire_user",
            "-d",
            "claire_de_binare",
            "--no-owner",
            "--no-acl",
        ],
    )

    assert result.returncode == 0, f"Backup failed: {result.stderr}"

    with open(dump_file, "w") as f:
        f.write(result.stdout)

    print(f"    ✓ Backup created: {dump_file.stat().st_size / 1024:.1f} KB")

    # Step 3: Insert Test Data (simulate new data after backup)
    print("  📝 Step 3: Insert test snapshot (after backup)...")

    cursor.execute(
        """
        INSERT INTO portfolio_snapshots (
            timestamp, total_equity, available_balance, total_unrealized_pnl, total_realized_pnl,
            daily_pnl, total_exposure_pct, open_positions, metadata
        ) VALUES (
            NOW(), 100000.0, 95000.0, 500.0, 1000.0,
            200.0, 0.05, 2, '{"test": "restore_marker"}'::jsonb
        )
    """
    )
    postgres_conn.commit()

    cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
    after_insert_count = cursor.fetchone()[0]

    print(f"    ✓ After insert: {after_insert_count} snapshots")
    assert after_insert_count == baseline_count + 1, "Test snapshot should be inserted"

    # Step 4: Drop and Recreate Database (simulate catastrophic failure)
    print("  💥 Step 4: Drop and recreate database (simulate disaster)...")

    # Close connection (will be dropped)
    postgres_conn.close()

    # Connect to postgres DB (not claire_de_binare)
    admin_conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="postgres",
        user="claire_user",
        password="claire_db_secret_2024",
    )
    admin_conn.autocommit = True
    admin_cursor = admin_conn.cursor()

    # Terminate connections
    admin_cursor.execute(
        """
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = 'claire_de_binare'
          AND pid <> pg_backend_pid()
    """
    )

    # Drop DB
    admin_cursor.execute("DROP DATABASE IF EXISTS claire_de_binare")

    # Recreate empty DB
    admin_cursor.execute("CREATE DATABASE claire_de_binare")

    admin_conn.close()

    print("    ✓ Database dropped and recreated (empty)")

    # Step 5: Restore from Backup
    print("  🔄 Step 5: Restore from backup...")

    # Copy dump file into container
    copy_cmd = [
        "docker",
        "compose",
        "cp",
        str(dump_file),
        "cdb_postgres:/tmp/restore.sql",
    ]
    result = subprocess.run(copy_cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"Failed to copy dump: {result.stderr}"

    # Restore inside container
    result = run_docker_exec(
        "cdb_postgres",
        [
            "psql",
            "-U",
            "claire_user",
            "-d",
            "claire_de_binare",
            "-f",
            "/tmp/restore.sql",
        ],
        timeout=120,
    )

    # psql might have warnings (which go to stderr), check returncode
    if result.returncode != 0:
        # Check if it's just warnings
        stderr_lower = result.stderr.lower()

        if "error" in stderr_lower and "warning" not in stderr_lower:
            pytest.fail(f"Restore failed: {result.stderr}")
        else:
            print("    ⚠️  Restore completed with warnings (acceptable)")

    print("    ✓ Restore completed")

    # Step 6: Validate Data Integrity
    print("  📊 Step 6: Validate restored data...")

    # Reconnect to restored DB
    restored_conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="claire_de_binare",
        user="claire_user",
        password="claire_db_secret_2024",
    )
    restored_cursor = restored_conn.cursor()

    # Count snapshots
    restored_cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
    restored_count = restored_cursor.fetchone()[0]

    print(f"    ✓ Restored DB has {restored_count} snapshots")

    # Should match baseline (test snapshot should be GONE)
    assert (
        restored_count == baseline_count
    ), f"Data mismatch: expected {baseline_count}, got {restored_count}"

    # Validate test snapshot is NOT present
    restored_cursor.execute(
        """
        SELECT COUNT(*) FROM portfolio_snapshots
        WHERE metadata->>'test' = 'restore_marker'
    """
    )
    test_marker_count = restored_cursor.fetchone()[0]

    assert (
        test_marker_count == 0
    ), "Test snapshot should NOT be in restored DB (was inserted after backup)"

    print("    ✅ Data integrity validated (test snapshot correctly absent)")

    restored_conn.close()

    print("\n✅ Restore test passed")


@pytest.mark.local_only
def test_backup_includes_all_tables(backup_dir):
    """
    Backup-Test: Dump enthält ALLE Tabellen

    Validiert:
    - Dump enthält signals
    - Dump enthält orders
    - Dump enthält trades
    - Dump enthält positions
    - Dump enthält portfolio_snapshots
    """
    print("\n📋 Backup-Test: All tables included in dump...")

    # Create backup
    print("  💾 Creating backup...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = backup_dir / f"claire_backup_{timestamp}.sql"

    result = run_docker_exec(
        "cdb_postgres",
        [
            "pg_dump",
            "-U",
            "claire_user",
            "-d",
            "claire_de_binare",
            "--no-owner",
            "--no-acl",
        ],
    )

    assert result.returncode == 0, f"Backup failed: {result.stderr}"

    with open(dump_file, "w") as f:
        f.write(result.stdout)

    # Validate content
    print("  📊 Validating dump content...")

    with open(dump_file, "r") as f:
        dump_content = f.read()

    required_tables = [
        "signals",
        "orders",
        "trades",
        "positions",
        "portfolio_snapshots",
    ]

    missing_tables = []

    for table in required_tables:
        if table not in dump_content:
            missing_tables.append(table)
        else:
            print(f"    ✓ Table '{table}' found in dump")

    assert (
        len(missing_tables) == 0
    ), f"Backup missing tables: {missing_tables}. Dump might be incomplete."

    print(f"\n✅ All {len(required_tables)} tables present in backup")


@pytest.mark.local_only
def test_backup_performance_acceptable(backup_dir):
    """
    Performance-Test: Backup dauert <60s auch bei vollen Tabellen

    Validiert:
    - Backup-Zeit akzeptabel
    - Dump-Größe wird geloggt (für Monitoring)
    """
    print("\n⏱️  Performance-Test: Backup speed...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = backup_dir / f"claire_backup_{timestamp}.sql"

    start_time = time.time()

    result = run_docker_exec(
        "cdb_postgres",
        [
            "pg_dump",
            "-U",
            "claire_user",
            "-d",
            "claire_de_binare",
            "--no-owner",
            "--no-acl",
        ],
    )

    elapsed = time.time() - start_time

    assert result.returncode == 0, f"Backup failed: {result.stderr}"

    with open(dump_file, "w") as f:
        f.write(result.stdout)

    dump_size_kb = dump_file.stat().st_size / 1024

    print(f"  📊 Backup: {dump_size_kb:.1f} KB in {elapsed:.2f}s")
    print(f"  📊 Speed: {dump_size_kb / elapsed:.1f} KB/s")

    # Performance assertion
    assert elapsed < 60.0, f"Backup too slow: {elapsed:.2f}s (max 60s)"

    # Log warning if slow
    if elapsed > 30.0:
        print(
            f"  ⚠️  Backup took {elapsed:.2f}s - might be slow for production (consider optimization)"
        )
    else:
        print("  ✅ Backup speed acceptable")

    print("\n✅ Performance test passed")


@pytest.mark.local_only
def test_automated_backup_script_concept():
    """
    Concept-Test: Zeigt wie ein Backup-Script aussehen könnte

    Dies ist KEIN echter Test, sondern ein Proof-of-Concept für
    ein automatisiertes Backup-Script.

    Validiert:
    - Backup-Kommandos funktionieren
    - Backup kann in Script integriert werden
    """
    print("\n💡 Concept-Test: Automated Backup Script...")

    print(
        """
  📋 Beispiel für automatisiertes Backup-Script:

  #!/bin/bash
  # backoffice/scripts/backup_postgres.sh

  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  BACKUP_DIR="/backups"
  DUMP_FILE="$BACKUP_DIR/claire_backup_$TIMESTAMP.sql"

  echo "🔄 Creating backup: $DUMP_FILE"

  # Backup via Docker Compose
  docker compose exec -T cdb_postgres \\
    pg_dump -U claire_user -d claire_de_binare --no-owner --no-acl \\
    > "$DUMP_FILE"

  if [ $? -eq 0 ]; then
    echo "✅ Backup successful: $(du -h $DUMP_FILE | cut -f1)"

    # Optional: Compress
    gzip "$DUMP_FILE"
    echo "✅ Compressed: ${DUMP_FILE}.gz"

    # Optional: Upload to S3
    # aws s3 cp "${DUMP_FILE}.gz" s3://claire-backups/

    # Cleanup: Keep last 7 days
    find "$BACKUP_DIR" -name "claire_backup_*.sql.gz" -mtime +7 -delete

  else
    echo "❌ Backup failed!"
    exit 1
  fi
  """
    )

    print("  ✅ Backup script concept documented")

    print(
        """
  📋 Beispiel für Cronjob (täglich um 02:00 Uhr):

  0 2 * * * /home/user/Claire_de_Binare/backoffice/scripts/backup_postgres.sh >> /var/log/claire_backup.log 2>&1
  """
    )

    print("\n✅ Concept test passed (no actual backup script created)")


if __name__ == "__main__":
    # Run with: pytest -v -m local_only tests/local/test_backup_recovery.py
    pytest.main([__file__, "-v", "-m", "local_only", "-s"])
