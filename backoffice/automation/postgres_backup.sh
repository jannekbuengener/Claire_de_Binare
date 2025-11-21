#!/bin/bash
# postgres_backup.sh - PostgreSQL Backup Script for Claire de Binaire
#
# Purpose: Create daily backups of the claire_de_binaire database
# Retention: 14 days
# Backup Type: Full logical backup (pg_dump)
#
# Usage: ./postgres_backup.sh
# Cron: 0 1 * * * /path/to/postgres_backup.sh

set -euo pipefail

# ============================================
# CONFIGURATION
# ============================================

# Database Configuration
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-claire_de_binaire}"
DB_USER="${POSTGRES_USER:-claire_user}"

# Backup Configuration
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/cdb_postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP=$(date +"%Y-%m-%d_%H%M")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${TIMESTAMP}.sql"
LOG_FILE="${BACKUP_DIR}/backup_log.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================
# FUNCTIONS
# ============================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR" "$1"
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

check_prerequisites() {
    log "INFO" "Checking prerequisites..."

    # Check if pg_dump is installed
    if ! command -v pg_dump &> /dev/null; then
        error_exit "pg_dump not found. Please install PostgreSQL client tools."
    fi

    # Check if backup directory exists, create if not
    if [ ! -d "$BACKUP_DIR" ]; then
        log "INFO" "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR" || error_exit "Failed to create backup directory"
    fi

    log "INFO" "Prerequisites check passed"
}

test_database_connection() {
    log "INFO" "Testing database connection..."

    if ! PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --schema-only \
        -f /dev/null 2>/dev/null; then
        error_exit "Database connection failed. Check credentials and connection."
    fi

    log "INFO" "Database connection successful"
}

create_backup() {
    log "INFO" "Starting backup: $BACKUP_FILE"

    # Create backup with pg_dump
    if PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -F p \
        --verbose \
        -f "$BACKUP_FILE" 2>&1 | tee -a "$LOG_FILE"; then

        # Get file size
        local file_size=$(du -h "$BACKUP_FILE" | cut -f1)
        log "INFO" "Backup created successfully: $BACKUP_FILE ($file_size)"

        # Compress backup
        if command -v gzip &> /dev/null; then
            log "INFO" "Compressing backup..."
            gzip "$BACKUP_FILE"
            BACKUP_FILE="${BACKUP_FILE}.gz"
            local compressed_size=$(du -h "$BACKUP_FILE" | cut -f1)
            log "INFO" "Backup compressed: $BACKUP_FILE ($compressed_size)"
        fi

        return 0
    else
        error_exit "Backup failed"
    fi
}

cleanup_old_backups() {
    log "INFO" "Cleaning up backups older than $RETENTION_DAYS days..."

    local deleted_count=0
    while IFS= read -r -d '' file; do
        log "INFO" "Deleting old backup: $file"
        rm "$file"
        ((deleted_count++))
    done < <(find "$BACKUP_DIR" -name "${DB_NAME}_backup_*.sql*" -type f -mtime +${RETENTION_DAYS} -print0)

    log "INFO" "Cleanup completed. Deleted $deleted_count old backup(s)"
}

verify_backup() {
    log "INFO" "Verifying backup integrity..."

    local backup_to_verify="$BACKUP_FILE"

    # If compressed, decompress temporarily for verification
    if [[ "$backup_to_verify" == *.gz ]]; then
        log "INFO" "Decompressing for verification..."
        gunzip -c "$backup_to_verify" > "${backup_to_verify%.gz}.tmp"
        backup_to_verify="${backup_to_verify%.gz}.tmp"
    fi

    # Check if file is valid SQL
    if head -n 1 "$backup_to_verify" | grep -q "PostgreSQL database dump"; then
        log "INFO" "Backup verification passed"
        [ -f "${backup_to_verify%.gz}.tmp" ] && rm "${backup_to_verify%.gz}.tmp"
        return 0
    else
        error_exit "Backup verification failed - file does not appear to be a valid PostgreSQL dump"
    fi
}

generate_summary() {
    log "INFO" "Backup Summary:"
    log "INFO" "  Database: $DB_NAME"
    log "INFO" "  Backup File: $BACKUP_FILE"
    log "INFO" "  Timestamp: $TIMESTAMP"

    # Count total backups
    local total_backups=$(find "$BACKUP_DIR" -name "${DB_NAME}_backup_*.sql*" -type f | wc -l)
    log "INFO" "  Total Backups: $total_backups"

    # Calculate total size
    local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    log "INFO" "  Total Backup Size: $total_size"
}

# ============================================
# MAIN EXECUTION
# ============================================

main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}PostgreSQL Backup Script${NC}"
    echo -e "${GREEN}Claire de Binaire - Database Backup${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    log "INFO" "Backup process started"

    # Check prerequisites
    check_prerequisites

    # Test database connection
    test_database_connection

    # Create backup
    create_backup

    # Verify backup
    verify_backup

    # Cleanup old backups
    cleanup_old_backups

    # Generate summary
    generate_summary

    log "INFO" "Backup process completed successfully"
    echo ""
    echo -e "${GREEN}✅ Backup completed successfully!${NC}"
    echo -e "${GREEN}Backup file: $BACKUP_FILE${NC}"
    echo ""
}

# Run main function
main "$@"
