# Minimal Workflow Orchestration Framework

**Goal:** Implement single orchestrator model with six-phase workflow structure eliminating autonomous agent complexity.

**Thread:** THREAD_1765983125  
**Proposal:** workflow-orchestration-framework.md  
**Verdict:** ACCEPTABLE_NO_DISAGREEMENTS (0.70)  
**Gate:** AUTO PROCEED  

## Action Items Checklist

- [ ] **Orchestrator Engine** (Owner: Infra, Size: L)  
  Done when: Single orchestrator implemented in scripts/discussion_pipeline/orchestrator.py replacing autonomous agents

- [ ] **Six-Phase Workflow Structure** (Owner: Signal, Size: M)  
  Done when: Intake → Analysis → Delegation → Delivery → PR → Review phases implemented with clear gates

- [ ] **Delegation Rule Engine** (Owner: Risk, Size: M)  
  Done when: Agent delegation logic implemented determining required vs. optional agent involvement based on task complexity

- [ ] **Workflow State Management** (Owner: Infra, Size: M)  
  Done when: Workflow state persistence implemented with resume capability and failure recovery

- [ ] **Phase Gate Validation** (Owner: Risk, Size: S)  
  Done when: Automated validation implemented between phases preventing progression without completion criteria

- [ ] **Workflow Templates** (Owner: Signal, Size: S)  
  Done when: Reusable workflow templates created for common patterns (feature, bugfix, optimization, etc.)

- [ ] **Performance Monitoring** (Owner: Research, Size: M)  
  Done when: Workflow execution metrics collected with performance optimization feedback loop

- [ ] **Legacy Migration** (Owner: Infra, Size: L)  
  Done when: Existing workflows migrated to orchestrator model with backward compatibility and validation

## Implementation Brief
**Files:**
- `scripts/discussion_pipeline/orchestrator.py` (change)
- `scripts/discussion_pipeline/workflow_engine.py` (add)
- `scripts/discussion_pipeline/phase_gates.py` (add)
- `scripts/discussion_pipeline/state_manager.py` (add)
- `scripts/discussion_pipeline/templates/` (add directory)
- `scripts/discussion_pipeline/monitoring.py` (add)
- `scripts/migrate_workflows.py` (add)

**Functions/Classes:**
- `WorkflowEngine` class in workflow_engine.py
- `PhaseGate` class in phase_gates.py
- `StateManager` class in state_manager.py
- `WorkflowTemplate` class in templates/
- `WorkflowMonitor` class in monitoring.py
- `WorkflowMigrator` class in migrate_workflows.py
- Updated `Orchestrator` class in orchestrator.py

**Steps (ordered):**
1. Refactor orchestrator.py to single orchestrator model
2. Implement six-phase workflow engine in workflow_engine.py
3. Create phase gate validation system in phase_gates.py
4. Build workflow state management in state_manager.py
5. Create workflow templates for common patterns
6. Implement performance monitoring in monitoring.py
7. Migrate existing workflows with migrate_workflows.py
8. Add delegation rule engine integration

**Constraints (do not touch):**
- Existing agent interfaces and communication
- Pipeline output format requirements
- GitHub integration functionality
- Quality assessment system

**Done when:** Single orchestrator operational with six-phase structure and existing workflows migrated

## Implementation Notes
- Foundational change simplifying multi-agent coordination complexity
- Single point of control improves reliability and debugging capability
- Claude-Code compatibility maintained throughout implementation

## Implementation Brief
Files to touch:
- scripts/discussion_pipeline/orchestrator.py
- scripts/discussion_pipeline/workflow_engine.py
- scripts/discussion_pipeline/gates/gate_handler.py
- scripts/discussion_pipeline/quality/metrics.py
- scripts/discussion_pipeline/run_discussion.py
- scripts/discussion_pipeline/utils/config_loader.py
Functions / Classes:
- DiscussionOrchestrator.run_pipeline / _run_agent / _generate_digest
- WorkflowEngine.execute_workflow
- GateHandler.should_trigger_gate / create_gate_file
- QualityMetrics.analyze_discussion / count_disagreements / aggregate_confidence_scores
- ensure_proposal_file (run_discussion.py)
- ConfigLoader.load_config / get_pipeline_preset
Ordered Steps:
1. Align DiscussionOrchestrator with WorkflowEngine.phases so each intake → review phase is recorded when run_pipeline executes.
2. Have ConfigLoader.load_config and get_pipeline_preset supply the agent list, gate thresholds, and quality config before orchestrator startup.
3. Use QualityMetrics.analyze_discussion to compute disagreements/confidence and feed those metrics to GateHandler.should_trigger_gate to enforce phase gates.
4. Keep run_discussion.py as the CLI front-end that ensures a proposal exists, calls the orchestrator, and prints the digest/manifest file paths.
5. When GateHandler triggers, its create_gate_file writes the gate metadata referenced by the workflow state so humans can resume or reject the thread.
Edge Cases:
- Missing pipeline_rules.yaml causes ConfigLoader to raise FileNotFoundError; run_discussion.py already halts with an error message.
- GateHandler detects a strategic keyword (from gate_config) mid-run; orchestrator must stop before digest generation.
- WorkflowEngine.execute_workflow sees an empty phase list due to config mistakes; orchestrator should fall back to the preset agent order.
Constraints (do not touch):
- agent-specific analysis logic (Claude/Gemini/Copilot)
- services/risk or execution code
- Docs Hub canonical files in Claire_de_Binare_Docs
Done when:
- The orchestrator executes a deterministic six-phase workflow, gating via QualityMetrics/GateHandler, while run_discussion.py prints the digest and manifest for Claude to review.

---
**Status:** DONE  
**Completed:** 2025-12-17T15:50:00Z  
**Commit:** e2eff22