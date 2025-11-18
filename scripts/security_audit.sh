#!/bin/bash
# SECURITY AUDIT SCRIPT - Claire de Binaire
# Phase 1: Kritische Security-Checks
# Ausführung: bash security_audit.sh

echo "================================================"
echo "  CLAIRE DE BINAIRE - SECURITY AUDIT PHASE 1"
echo "  Datum: $(date +%Y-%m-%d\ %H:%M)"
echo "================================================"
echo ""

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Audit-Report initialisieren
REPORT="backoffice/docs/audit/SECURITY_AUDIT_$(date +%Y%m%d_%H%M).md"
echo "# Security Audit Report" > $REPORT
echo "**Datum**: $(date)" >> $REPORT
echo "" >> $REPORT

echo -e "${YELLOW}[1/6] Checking .env for exposed secrets...${NC}"
echo "## 1. ENV File Security Check" >> $REPORT
echo '```' >> $REPORT

if [ -f ".env" ]; then
    # Suche nach potentiellen Secrets
    SECRETS=$(grep -E "password|secret|key|token" .env 2>/dev/null | grep -v "^#" | grep -v "=$" | grep -v '=""')
    if [ -n "$SECRETS" ]; then
        echo -e "${RED}❌ WARNING: Potential secrets found in .env:${NC}"
        echo "$SECRETS"
        echo "WARNING: Secrets found!" >> $REPORT
        echo "$SECRETS" >> $REPORT
    else
        echo -e "${GREEN}✅ No exposed secrets in .env${NC}"
        echo "✅ PASS: No exposed secrets" >> $REPORT
    fi
else
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "⚠️ .env not found" >> $REPORT
fi
echo '```' >> $REPORT
echo "" >> $REPORT

echo ""
echo -e "${YELLOW}[2/6] Comparing .env with .env.template...${NC}"
echo "## 2. ENV Template Validation" >> $REPORT

if [ -f "backoffice/templates/.env.template" ]; then
    echo '```diff' >> $REPORT
    diff -u backoffice/templates/.env.template .env >> $REPORT 2>&1 || true
    echo '```' >> $REPORT
    echo -e "${GREEN}✅ Diff completed (see report)${NC}"
else
    echo -e "${RED}❌ .env.template not found${NC}"
    echo "❌ FAIL: Template not found" >> $REPORT
fi
echo "" >> $REPORT

echo ""
echo -e "${YELLOW}[3/6] Checking for hardcoded credentials in Python files...${NC}"
echo "## 3. Hardcoded Credentials Check" >> $REPORT
echo '```' >> $REPORT

HARDCODED=$(grep -r "password\s*=\s*['\"]" backoffice/services --include="*.py" 2>/dev/null | grep -v "os.getenv" | grep -v "environ")
if [ -n "$HARDCODED" ]; then
    echo -e "${RED}❌ WARNING: Hardcoded credentials found:${NC}"
    echo "$HARDCODED"
    echo "WARNING: Hardcoded credentials!" >> $REPORT
    echo "$HARDCODED" >> $REPORT
else
    echo -e "${GREEN}✅ No hardcoded credentials in Python files${NC}"
    echo "✅ PASS: No hardcoded credentials" >> $REPORT
fi
echo '```' >> $REPORT
echo "" >> $REPORT

echo ""
echo -e "${YELLOW}[4/6] Validating Docker security flags...${NC}"
echo "## 4. Docker Security Configuration" >> $REPORT

echo "### Checking docker-compose.yml for security flags:" >> $REPORT
echo '```yaml' >> $REPORT

# Check for security configurations
SECURITY_CHECK=$(grep -E "user:|read_only:|tmpfs:|cap_drop:|security_opt:" docker-compose.yml 2>/dev/null)
if [ -n "$SECURITY_CHECK" ]; then
    echo -e "${GREEN}✅ Security flags found in docker-compose.yml${NC}"
    echo "$SECURITY_CHECK" >> $REPORT
else
    echo -e "${YELLOW}⚠️  No security flags in docker-compose.yml${NC}"
    echo "⚠️ WARNING: No security hardening detected" >> $REPORT
fi
echo '```' >> $REPORT
echo "" >> $REPORT

echo ""
echo -e "${YELLOW}[5/6] Checking file permissions...${NC}"
echo "## 5. File Permissions Audit" >> $REPORT

# Check for world-readable sensitive files
echo "### World-readable files check:" >> $REPORT
echo '```' >> $REPORT
WORLD_READABLE=$(find . -name "*.env" -o -name "*key*" -o -name "*secret*" 2>/dev/null | xargs ls -la 2>/dev/null | grep "^-rw.r..r..")
if [ -n "$WORLD_READABLE" ]; then
    echo -e "${YELLOW}⚠️  World-readable sensitive files found${NC}"
    echo "⚠️ Files with loose permissions:" >> $REPORT
    echo "$WORLD_READABLE" >> $REPORT
else
    echo -e "${GREEN}✅ File permissions look secure${NC}"
    echo "✅ PASS: No world-readable sensitive files" >> $REPORT
fi
echo '```' >> $REPORT
echo "" >> $REPORT

echo ""
echo -e "${YELLOW}[6/6] Checking for exposed ports...${NC}"
echo "## 6. Port Exposure Check" >> $REPORT

echo "### Ports in docker-compose.yml:" >> $REPORT
echo '```' >> $REPORT
PORTS=$(grep -E "^\s*-\s*\"[0-9]+:[0-9]+\"" docker-compose.yml 2>/dev/null)
if [ -n "$PORTS" ]; then
    echo "Found exposed ports:" >> $REPORT
    echo "$PORTS" >> $REPORT
    
    # Check if ports are localhost-bound
    EXTERNAL=$(echo "$PORTS" | grep -v "127.0.0.1")
    if [ -n "$EXTERNAL" ]; then
        echo -e "${YELLOW}⚠️  Ports exposed to all interfaces${NC}"
        echo "⚠️ WARNING: Ports not bound to localhost only" >> $REPORT
    else
        echo -e "${GREEN}✅ Ports bound to localhost only${NC}"
        echo "✅ PASS: Ports properly restricted" >> $REPORT
    fi
else
    echo -e "${GREEN}✅ No exposed ports found${NC}"
    echo "✅ No ports exposed" >> $REPORT
fi
echo '```' >> $REPORT
echo "" >> $REPORT

# Summary
echo ""
echo "================================================"
echo "           AUDIT SUMMARY"
echo "================================================"

echo "## Summary" >> $REPORT
echo "" >> $REPORT

# Count issues
CRITICAL=$(grep -c "WARNING:" $REPORT 2>/dev/null || echo 0)
WARNINGS=$(grep -c "⚠️" $REPORT 2>/dev/null || echo 0)
PASS=$(grep -c "✅ PASS" $REPORT 2>/dev/null || echo 0)

echo "- **Critical Issues**: $CRITICAL" >> $REPORT
echo "- **Warnings**: $WARNINGS" >> $REPORT
echo "- **Passed Checks**: $PASS" >> $REPORT
echo "" >> $REPORT

if [ $CRITICAL -gt 0 ]; then
    echo -e "${RED}❌ CRITICAL: $CRITICAL security issues found!${NC}"
    echo "**Status**: ❌ FAILED - Critical issues need immediate attention" >> $REPORT
else
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  WARNING: $WARNINGS warnings found${NC}"
        echo "**Status**: ⚠️ PASSED WITH WARNINGS" >> $REPORT
    else
        echo -e "${GREEN}✅ PASSED: All security checks passed!${NC}"
        echo "**Status**: ✅ PASSED" >> $REPORT
    fi
fi

echo ""
echo "---" >> $REPORT
echo "_Generated by security_audit.sh_" >> $REPORT

echo -e "${GREEN}Report saved to: $REPORT${NC}"
echo ""
echo "Next steps:"
echo "1. Review the report: $REPORT"
echo "2. Fix any CRITICAL issues immediately"
echo "3. Address WARNINGs before deployment"
echo "4. Run Phase 2: ENV Standardization audit"