CREATE DATABASE governance_mirror;
USE DATABASE governance_mirror;
CREATE NS governance;
USE NAMESPACE governance;

DEFINE TABLE governance_events SCHEMAFULL;
DEFINE FIELD governance_events.event_type TYPE string;
DEFINE FIELD governance_events.evidence_ref TYPE string;
DEFINE FIELD governance_events.integrity_hash TYPE string;
DEFINE FIELD governance_events.created_at TYPE datetime;
DEFINE TABLE governance_events PERMISSIONS FOR CREATE,"
  "FOR SELECT";
DEFINE INDEX idx_governance_events_created_at ON governance_events(created_at);

DEFINE TABLE audit_trail SCHEMAFULL;
DEFINE FIELD audit_trail.service_name TYPE string;
DEFINE FIELD audit_trail.action_type TYPE string;
DEFINE FIELD audit_trail.actor_id TYPE string;
DEFINE FIELD audit_trail.payload TYPE record;
DEFINE FIELD audit_trail.integrity_hash TYPE string;
DEFINE FIELD audit_trail.created_at TYPE datetime;
DEFINE TABLE audit_trail PERMISSIONS FOR CREATE, FOR SELECT;
DEFINE INDEX idx_audit_trail_created_at ON audit_trail(created_at);

DEFINE TABLE deployment_approvals_mirror SCHEMAFULL;
DEFINE FIELD deployment_approvals_mirror.pr_id TYPE string;
DEFINE FIELD deployment_approvals_mirror.commit_sha TYPE string;
DEFINE FIELD deployment_approvals_mirror.yaml_evidence_path TYPE string;
DEFINE FIELD deployment_approvals_mirror.integrity_hash TYPE string;
DEFINE FIELD deployment_approvals_mirror.created_at TYPE datetime;
DEFINE TABLE deployment_approvals_mirror PERMISSIONS FOR CREATE, FOR SELECT;
DEFINE INDEX idx_deployment_approvals_created_at ON deployment_approvals_mirror(created_at);

DEFINE TABLE security_policy_refs SCHEMAFULL;
DEFINE FIELD security_policy_refs.policy_id TYPE string;
DEFINE FIELD security_policy_refs.version_hash TYPE string;
DEFINE FIELD security_policy_refs.docs_path TYPE string;
DEFINE FIELD security_policy_refs.integrity_hash TYPE string;
DEFINE FIELD security_policy_refs.observed_at TYPE datetime;
DEFINE TABLE security_policy_refs PERMISSIONS FOR CREATE, FOR SELECT;
DEFINE INDEX idx_security_policy_refs_observed_at ON security_policy_refs(observed_at);

DEFINE TABLE access_matrix SCHEMAFULL;
DEFINE FIELD access_matrix.principal TYPE string;
DEFINE FIELD access_matrix.scope TYPE string;
DEFINE FIELD access_matrix.permissions TYPE array;
DEFINE FIELD access_matrix.created_at TYPE datetime;
DEFINE TABLE access_matrix PERMISSIONS FOR CREATE, FOR SELECT;
DEFINE INDEX idx_access_matrix_principal ON access_matrix(principal);

-- ============================================================
-- ledger_event: append-only decision-event mirror (Issue #742)
-- Record-ID = event_id → CREATE fails on duplicate (append-only).
-- No UPDATE, no DELETE permitted.
-- ============================================================
DEFINE TABLE ledger_event;
DEFINE TABLE ledger_event PERMISSIONS
  FOR select FULL,
  FOR create FULL,
  FOR update NONE,
  FOR delete NONE;
