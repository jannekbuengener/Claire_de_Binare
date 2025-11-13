# TEST_RERUN_EVIDENCE_2025-11-12
## Controls & IDs
- .env SHA256: `a254821acdf4a50673f6c4062ab89161fe28cda8df7b384dc853171b751cb516`
- .env.gitignore: OK: present
- INTEGRATION_MOCK: `true`
## Security
- Trivy HIGH/CRITICAL (local image): 120
- Trivy HIGH/CRITICAL (registry image): n/a
- Gitleaks findings: 0
- Bandit findings (post-processed): 44
- verify_cve summary: {"pins_expected": {"aiohttp": "aiohttp==3.12.14", "cryptography": "cryptography==42.0.4"}, "pins_present": ["aiohttp==3.12.14", "cryptography==42.0.4"], "trivy_high_critical": 120, "pip_audit_high_critical": 0}
## Ports Appendix
- Items: 0
## Notes
- Remote-History-Rewrite: geplant, nicht ausgeführt.
- Sicherheitsgewinn durch Pins: siehe Trivy/Pip-Audit Vergleich.
## Review
✅ 2025-11-12 / Reviewer: Werner