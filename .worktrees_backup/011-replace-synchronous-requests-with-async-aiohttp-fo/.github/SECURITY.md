# Security Policy

## Supported Versions

Currently supported versions for security updates:

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| dev     | :white_check_mark: |
| < 1.0   | :x:                |

---

## Reporting a Vulnerability

**DO NOT** create public issues for security vulnerabilities.

### Preferred Method
1. **Email:** [Security contact - add your email]
2. **Subject:** `[SECURITY] CDB Vulnerability Report`
3. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline
- **Acknowledgment:** Within 24 hours
- **Initial Assessment:** Within 72 hours
- **Status Update:** Weekly until resolved
- **Fix Timeline:** Critical (7 days), High (14 days), Medium (30 days)

---

## Security Measures

### Implemented
- ✅ Secrets scanning (Gitleaks)
- ✅ Dependency audit (pip-audit)
- ✅ Security linting (Bandit)
- ✅ `.env` templates (no secrets in repo)
- ✅ Docker secret management
- ✅ API key restrictions (IP-binding, asset limits)

### Planned (M8 - Production Hardening)
- 🔄 Penetration testing
- 🔄 Container image scanning (Trivy)
- 🔄 TLS/SSL for all external connections
- 🔄 Redis authentication
- 🔄 PostgreSQL hardening
- 🔄 Network isolation review

---

## Security Checklist (Pre-Deployment)

### Code
- [ ] No hardcoded secrets
- [ ] All ENV vars in `.env.example`
- [ ] Bandit scan passes
- [ ] Dependencies audited (pip-audit)
- [ ] Type checking passes (mypy)

### Infrastructure
- [ ] Docker secrets configured
- [ ] PostgreSQL password rotation
- [ ] Redis AUTH enabled
- [ ] Firewall rules configured
- [ ] Logs secured (no PII)

### API Security
- [ ] MEXC API key IP-bound
- [ ] Asset whitelist active (BTC/USDC/USDE)
- [ ] Rate limiting configured
- [ ] TLS certificate valid

### Monitoring
- [ ] Security alerts configured
- [ ] Audit logs enabled
- [ ] Anomaly detection active
- [ ] Incident response plan documented

---

## Known Security Boundaries

### By Design
- **Paper Trading Mode:** No real capital at risk (M7 phase)
- **Kill Switch:** Manual intervention required (not automated)
- **Tresor Zone:** Physically separated (not in Docker stack)

### Dependencies
- See `requirements.txt` for all Python dependencies
- Regular updates via Dependabot
- Critical CVEs patched within 7 days

---

## Compliance

### Standards
- OWASP Top 10 awareness
- Secure coding practices (Bandit rules)
- Dependency hygiene (SemVer, audit)

### Audit Trail
- Git history (all changes tracked)
- Event sourcing (all trading events logged)
- PostgreSQL audit logs

---

## Security Roadmap

### M8 - Production Hardening & Security Review
- [ ] Full penetration test
- [ ] Container security scan
- [ ] Network isolation review
- [ ] Secrets rotation policy
- [ ] Incident response playbook

### M9 - Release 1.0
- [ ] Security audit sign-off
- [ ] Production deployment checklist
- [ ] Monitoring dashboards live
- [ ] Kill-switch tested

---

## Contact

For security concerns:
- **Repository:** Private (no public disclosure)
- **Maintainer:** @jannekbuengener
- **Security Lead:** TBD

---

**Last Updated:** 2025-12-16  
**Policy Version:** 1.0
