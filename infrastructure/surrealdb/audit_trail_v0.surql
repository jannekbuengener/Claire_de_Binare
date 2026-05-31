-- T3 Audit Trail v0 — minimal operator bootstrap schema
-- Scope: audit_observation only in NS cdb / DB audit_trail
-- No agent_memory, no CIS tables, no trading objects

DEFINE NAMESPACE IF NOT EXISTS cdb;
USE NS cdb;
DEFINE DATABASE IF NOT EXISTS audit_trail;
USE DB audit_trail;

DEFINE TABLE IF NOT EXISTS audit_observation SCHEMAFULL;
DEFINE FIELD observation_id ON TABLE audit_observation TYPE string;
DEFINE FIELD observation_type ON TABLE audit_observation TYPE string;
DEFINE FIELD subject_ref ON TABLE audit_observation TYPE option<record>;
DEFINE FIELD message ON TABLE audit_observation TYPE string;
DEFINE FIELD evidence_refs ON TABLE audit_observation TYPE array;
DEFINE FIELD confidence ON TABLE audit_observation TYPE option<float>;
DEFINE FIELD observed_by ON TABLE audit_observation TYPE string;
DEFINE FIELD observed_at ON TABLE audit_observation TYPE datetime;
DEFINE FIELD comment ON TABLE audit_observation TYPE string;
DEFINE FIELD severity ON TABLE audit_observation TYPE string;
DEFINE FIELD related_claims ON TABLE audit_observation TYPE array;
DEFINE FIELD related_decisions ON TABLE audit_observation TYPE array;
DEFINE FIELD related_memory ON TABLE audit_observation TYPE array;
DEFINE FIELD status ON TABLE audit_observation TYPE string;
DEFINE FIELD created_at ON TABLE audit_observation TYPE datetime VALUE $value OR time::now();
DEFINE INDEX idx_audit_observation_observation_id_unique ON TABLE audit_observation FIELDS observation_id UNIQUE;
DEFINE INDEX idx_audit_observation_type ON TABLE audit_observation FIELDS observation_type;
DEFINE INDEX idx_audit_observation_observed_at ON TABLE audit_observation FIELDS observed_at;
DEFINE INDEX idx_audit_observation_created_at ON TABLE audit_observation FIELDS created_at;
DEFINE INDEX idx_audit_observation_severity ON TABLE audit_observation FIELDS severity;
DEFINE INDEX idx_audit_observation_status ON TABLE audit_observation FIELDS status;
