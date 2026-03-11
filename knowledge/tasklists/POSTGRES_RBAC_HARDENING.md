# POSTGRES_RBAC_HARDENING

Date: 2025-12-19
Scope: PostgreSQL RBAC and hardening tasks (M8 Phase 3)

## Tasks
- Role-based access control (least privilege roles)
- Connection limits per role
- SSL/TLS enforcement and certificate rotation
- Audit logging settings

## Implementation notes
- Requires updates in infrastructure configuration and compose/secrets.
- Needs Working Repo changes.

## Verification
- Role permissions verified
- Connection limits enforced
- TLS enabled for external connections
