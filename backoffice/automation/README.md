# Automation Scripts - Claire de Binaire

**Purpose**: Automated tasks for database backups, health checks, and maintenance.

---

## 📁 Available Scripts

### **1. ENV Validation** ⭐ NEW

**Files**:

- `check_env.sh` - Linux/Mac bash script
- `check_env.ps1` - Windows PowerShell script

**Purpose**: Validate `.env` file against expected configuration variables before deployment.

**Features**:

- ✅ Type validation (int, float, string, secret, enum)
- ✅ Range checking (min/max values)
- ✅ Required vs optional variables
- ✅ Secret length validation
- ✅ Colored output (errors, warnings, success)
- ✅ Detailed error messages
- ✅ Exit codes for CI/CD integration

---

### **2. PostgreSQL Backup**

**Files**:

- `postgres_backup.sh` - Linux/Mac bash script
- `postgres_backup.ps1` - Windows PowerShell script

**Purpose**: Create daily backups of the `claire_de_binaire` database with automatic retention management.

**Features**:

- ✅ Full logical backup (pg_dump)
- ✅ Automatic compression (gzip/zip)
- ✅ Backup verification
- ✅ 14-day retention (configurable)
- ✅ Detailed logging
- ✅ Connection testing
- ✅ Error handling

---

## 🚀 Usage

### **ENV Validation**

**Linux/Mac (Bash)**:

```bash
# Make script executable
chmod +x backoffice/automation/check_env.sh

# Run validation (checks .env in current directory)
./backoffice/automation/check_env.sh

# Or check specific file
./backoffice/automation/check_env.sh /path/to/.env
```

**Windows (PowerShell)**:

```powershell
# Run validation (checks .env in current directory)
.\backoffice\automation\check_env.ps1

# Or check specific file
.\backoffice\automation\check_env.ps1 -EnvFile "C:\path\to\.env"
```

**Exit Codes**:
- `0`: All checks passed (OK or warnings)
- `1`: Validation failed (errors found)
- `2`: .env file not found (Bash only)

**Example Output**:

```
=== ENV Validation for Claire de Binaire ===

[OK] .env found

Found 18 variables in .env

=== Validating Variables ===

[OK] POSTGRES_HOST = cdb_postgres
[OK] POSTGRES_PORT = 5432
[OK] POSTGRES_USER = claire_user
[OK] POSTGRES_PASSWORD = ******** (Length: 24)
[OK] POSTGRES_DB = claire_de_binaire
[OK] REDIS_HOST = cdb_redis
[OK] REDIS_PORT = 6379
[OK] REDIS_PASSWORD = ******** (Length: 24)
[OK] TRADING_MODE = paper
[OK] ACCOUNT_EQUITY = 100000.0

=== Validation Summary ===
OK: 18
Warnings: 0
Errors: 0

[SUCCESS] ENV Validation passed! ✅
```

---

### **PostgreSQL Backup**

**Linux/Mac (Bash)**:

```bash
# Make script executable
chmod +x backoffice/automation/postgres_backup.sh

# Run manually
./backoffice/automation/postgres_backup.sh

# Or with custom backup directory
BACKUP_DIR=/custom/path ./backoffice/automation/postgres_backup.sh
```

**Cron Setup** (Daily at 01:00):

```bash
# Edit crontab
crontab -e

# Add line:
0 1 * * * /path/to/Claire_de_Binare_Cleanroom/backoffice/automation/postgres_backup.sh
```

---

### **Windows (PowerShell)**

```powershell
# Run manually
.\backoffice\automation\postgres_backup.ps1

# Or with custom parameters
.\backoffice\automation\postgres_backup.ps1 -BackupDir "C:\Backups\CDB" -RetentionDays 30
```

**Task Scheduler Setup** (Daily at 01:00):

1. Open Task Scheduler
2. Create Basic Task
3. **Name**: "Claire de Binaire - Database Backup"
4. **Trigger**: Daily at 01:00
5. **Action**: Start a program
   - **Program**: `powershell.exe`
   - **Arguments**: `-ExecutionPolicy Bypass -File "C:\path\to\postgres_backup.ps1"`
6. **Settings**:
   - Run whether user is logged on or not
   - Run with highest privileges

---

## ⚙️ Configuration

### **Environment Variables**

Both scripts read from environment variables (set in `.env` or system):

```bash
# Required
POSTGRES_PASSWORD=your_password_here

# Optional (with defaults)
POSTGRES_HOST=localhost        # Default: localhost
POSTGRES_PORT=5432            # Default: 5432
POSTGRES_DB=claire_de_binaire # Default: claire_de_binaire
POSTGRES_USER=claire_user     # Default: claire_user

# Backup Configuration
BACKUP_DIR=$HOME/backups/cdb_postgres  # Linux/Mac default
# or C:\Users\<user>\backups\cdb_postgres (Windows default)

RETENTION_DAYS=14             # Default: 14 days
```

### **Customization**

**Bash Script**:

```bash
# Override via environment variables
export BACKUP_DIR=/custom/backup/location
export RETENTION_DAYS=30
./postgres_backup.sh
```

**PowerShell Script**:

```powershell
# Override via parameters
.\postgres_backup.ps1 -BackupDir "C:\CustomBackup" -RetentionDays 30
```

---

## 📊 Backup Details

### **File Naming**

```
claire_de_binaire_backup_YYYY-MM-DD_HHMM.sql.gz   # Linux/Mac
claire_de_binaire_backup_YYYY-MM-DD_HHMM.sql.zip  # Windows
```

**Examples**:

```
claire_de_binaire_backup_2025-11-21_0100.sql.gz
claire_de_binaire_backup_2025-11-22_0100.sql.gz
```

### **Retention Logic**

- Keeps backups for **14 days** (default)
- Automatically deletes older backups
- Configurable via `RETENTION_DAYS`

### **Compression**

- **Linux/Mac**: gzip (`.gz`)
- **Windows**: ZIP (`.zip`)
- Typical compression ratio: ~90% (10x smaller)

---

## 🔍 Logs

**Log File Location**:

```bash
# Linux/Mac
$BACKUP_DIR/backup_log.txt

# Windows
$BackupDir\backup_log.txt
```

**Log Format**:

```
[2025-11-21 01:00:01] [INFO] Backup process started
[2025-11-21 01:00:02] [INFO] Checking prerequisites...
[2025-11-21 01:00:02] [INFO] Testing database connection...
[2025-11-21 01:00:03] [INFO] Backup created successfully: ...
[2025-11-21 01:00:10] [INFO] Backup compressed: ... (45.23 MB)
[2025-11-21 01:00:11] [INFO] Backup verification passed
[2025-11-21 01:00:11] [INFO] Cleanup completed. Deleted 1 old backup(s)
[2025-11-21 01:00:11] [INFO] Backup process completed successfully
```

---

## ✅ Verification

### **Manual Verification**

**Linux/Mac**:

```bash
# List backups
ls -lh $BACKUP_DIR

# Check latest backup
gunzip -c $BACKUP_DIR/claire_de_binaire_backup_*.sql.gz | head -n 5

# Should see: "-- PostgreSQL database dump"
```

**Windows**:

```powershell
# List backups
Get-ChildItem $env:USERPROFILE\backups\cdb_postgres

# Extract and check (manual)
Expand-Archive -Path "backup_file.sql.zip" -DestinationPath "temp"
Get-Content "temp\backup_file.sql" -Head 5

# Should see: "-- PostgreSQL database dump"
```

### **Automated Verification**

Both scripts automatically verify:

1. ✅ Backup file created
2. ✅ File is valid PostgreSQL dump
3. ✅ Compression successful (if available)

---

## 🔄 Restore from Backup

### **Linux/Mac**

```bash
# Decompress backup
gunzip claire_de_binaire_backup_2025-11-21_0100.sql.gz

# Restore to database
PGPASSWORD=$POSTGRES_PASSWORD psql \
  -h localhost \
  -p 5432 \
  -U claire_user \
  -d claire_de_binaire \
  -f claire_de_binaire_backup_2025-11-21_0100.sql
```

### **Windows**

```powershell
# Extract backup
Expand-Archive -Path "claire_de_binaire_backup_2025-11-21_0100.sql.zip" -DestinationPath "."

# Restore to database
$env:PGPASSWORD = $env:POSTGRES_PASSWORD
psql -h localhost -p 5432 -U claire_user -d claire_de_binaire -f "claire_de_binaire_backup_2025-11-21_0100.sql"
```

---

## 🛠️ Troubleshooting

### **Problem: pg_dump not found**

**Solution**:

```bash
# Linux/Mac
sudo apt install postgresql-client  # Debian/Ubuntu
brew install postgresql              # macOS

# Windows
# Install PostgreSQL client tools from:
# https://www.postgresql.org/download/windows/
# Add to PATH: C:\Program Files\PostgreSQL\16\bin
```

---

### **Problem: Connection refused**

**Solution**:

1. Check if PostgreSQL is running:

   ```bash
   docker compose ps cdb_postgres
   ```

2. Check credentials in `.env`:

   ```bash
   cat .env | grep POSTGRES
   ```

3. Test connection manually:

   ```bash
   PGPASSWORD=$POSTGRES_PASSWORD psql -h localhost -U claire_user -d claire_de_binaire -c "SELECT 1"
   ```

---

### **Problem: Permission denied (backup directory)**

**Linux/Mac**:

```bash
# Create directory with correct permissions
mkdir -p ~/backups/cdb_postgres
chmod 755 ~/backups/cdb_postgres
```

**Windows**:

```powershell
# Run PowerShell as Administrator
# Or change BackupDir to user-writable location
```

---

### **Problem: POSTGRES_PASSWORD not set**

**Solution**:

```bash
# Linux/Mac
export POSTGRES_PASSWORD=your_password_here
./postgres_backup.sh

# Windows
$env:POSTGRES_PASSWORD = "your_password_here"
.\postgres_backup.ps1
```

---

## 📈 Monitoring

### **Check Backup Status**

**Linux/Mac**:

```bash
# View log
tail -f $BACKUP_DIR/backup_log.txt

# Count backups
ls $BACKUP_DIR/claire_de_binaire_backup_*.sql.gz | wc -l

# Total size
du -sh $BACKUP_DIR
```

**Windows**:

```powershell
# View log
Get-Content "$env:USERPROFILE\backups\cdb_postgres\backup_log.txt" -Tail 20

# Count backups
(Get-ChildItem "$env:USERPROFILE\backups\cdb_postgres\claire_de_binaire_backup_*.sql.zip").Count

# Total size
(Get-ChildItem "$env:USERPROFILE\backups\cdb_postgres" | Measure-Object -Property Length -Sum).Sum / 1MB
```

---

## 📊 ENV Validation - Validated Variables

The ENV validation scripts check the following variables:

### **Database Configuration**
- `POSTGRES_HOST` (string, required) - Default: `cdb_postgres`
- `POSTGRES_PORT` (int, required, 1024-65535) - Default: `5432`
- `POSTGRES_USER` (string, required) - Default: `claire_user`
- `POSTGRES_PASSWORD` (secret, required, min 8 chars)
- `POSTGRES_DB` (string, required) - Default: `claire_de_binare`

### **Redis Configuration**
- `REDIS_HOST` (string, required) - Default: `cdb_redis`
- `REDIS_PORT` (int, required, 1024-65535) - Default: `6379`
- `REDIS_PASSWORD` (secret, required, min 8 chars)
- `REDIS_DB` (int, optional, 0-15) - Default: `0`

### **Grafana Configuration**
- `GRAFANA_PASSWORD` (secret, optional, min 5 chars) - Default: `admin`

### **Risk Limits** (⚠️ NICHT ÄNDERN ohne Rücksprache!)
- `MAX_POSITION_PCT` (float, required, 0.01-1.0) - Default: `0.10` (10%)
- `MAX_DAILY_DRAWDOWN_PCT` (float, required, 0.01-0.5) - Default: `0.05` (5%)
- `MAX_TOTAL_EXPOSURE_PCT` (float, required, 0.1-1.0) - Default: `0.30` (30%)
- `CIRCUIT_BREAKER_THRESHOLD_PCT` (float, required, 0.05-0.5) - Default: `0.10` (10%)
- `MAX_SLIPPAGE_PCT` (float, required, 0.001-0.1) - Default: `0.02` (2%)

### **System Configuration**
- `DATA_STALE_TIMEOUT_SEC` (int, required, 10-300) - Default: `60`
- `LOG_LEVEL` (enum, optional: DEBUG, INFO, WARNING, ERROR) - Default: `INFO`

### **Trading Configuration**
- `TRADING_MODE` (enum, required: paper, live) - Default: `paper`
- `ACCOUNT_EQUITY` (float, required, 1000-10000000) - Default: `100000.0`

### **MEXC API** (Optional for N1 Paper-Test, Required for Live-Trading)
- `MEXC_API_KEY` (secret, optional, min 32 chars)
- `MEXC_API_SECRET` (secret, optional, min 32 chars)

---

## 📋 Best Practices

### **ENV Validation**
1. **Run Before Deployment**:
   - Always validate `.env` before starting services
   - Integrate into CI/CD pipeline

2. **Secure Secrets**:
   - Never commit `.env` to git (in `.gitignore`)
   - Use strong passwords (≥16 chars recommended)
   - Rotate secrets regularly

3. **Test After Changes**:
   - Run validation after editing `.env`
   - Check for typos in variable names

### **PostgreSQL Backup**
1. **Test Backups Regularly**:
   - Perform restore test monthly
   - Verify data integrity

2. **Monitor Disk Space**:
   - Backups grow over time
   - Adjust retention if needed

3. **Secure Credentials**:
   - Never commit `.env` with passwords
   - Use environment variables

4. **Test Automation**:
   - Verify cron/Task Scheduler runs
   - Check logs after first automated run

5. **Backup Strategy**:
   - Keep critical backups offsite
   - Consider cloud storage for long-term retention

---

## 🔗 Related Documentation

- **Database Schema**: [`backoffice/docs/DATABASE_SCHEMA.sql`](../docs/DATABASE_SCHEMA.sql)
- **Project Status**: [`backoffice/PROJECT_STATUS.md`](../PROJECT_STATUS.md)
- **Issue Backlog**: [`backoffice/docs/ISSUES_BACKLOG.md`](../docs/ISSUES_BACKLOG.md)

---

**Created**: 2025-11-21
**Maintainer**: Claude (AI Assistant)
**Project**: Claire de Binaire - Autonomous Crypto Trading Bot
