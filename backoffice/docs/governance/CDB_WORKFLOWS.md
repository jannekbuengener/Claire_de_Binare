# CDB_WORKFLOWS.md - The Complete Operational Playbook

**Version**: 1.0
**Project**: Claire de Binare
**Author**: Claire-Architect & Intelligence Generator
**Purpose**: This document is the complete, unified, and actionable playbook for all operational tasks within the project. It provides the Session Lead AI with clear, repeatable procedures for development, maintenance, and analysis.

---

## Article I: The Supervisor Protocol (Master Workflow)

This protocol is the master framework governing all AI-led activities. Every user request, regardless of its nature, initiates this workflow.

- **Objective**: To provide a standardized, safe, and efficient process for handling any user request.
- **Actors**: Session Lead (as Supervisor/Orchestrator)
- **Phases**:

    1.  **Phase 0: Intake & Scoping**
        - **Step 1 (Clarify)**: The Session Lead clarifies the User's request, goal, and constraints.
        - **Step 2 (Set Mode)**: Default to **Analysis Mode**. Announce this to the User.
        - **Step 3 (Select Workflow)**: Identify the appropriate Task-Specific Workflow from this playbook (e.g., Bugfix, Feature). Announce the selected workflow.

    2.  **Phase 1: Analysis & Planning**
        - **Step 1 (Context)**: The Session Lead gathers context by reading relevant files (code, docs, logs).
        - **Step 2 (Analysis)**: Invoke specialist Agents as needed (e.g., `system-architect`, `test-engineer`) to perform a deep analysis.
        - **Step 3 (Synthesize)**: Consolidate all findings into a single, structured **Analysis Report**. This report must include a clear, actionable plan.

    3.  **Phase 2: Decision Gate**
        - **Step 1 (Present)**: The Session Lead presents the Analysis Report and the proposed plan to the User.
        - **Step 2 (Approval)**: The workflow is **PAUSED**. The Session Lead MUST await explicit User approval before proceeding.
        - **Fallback**: If the User denies the plan or requests changes, return to Phase 1.

    4.  **Phase 3: Delivery**
        - **Step 1 (Enter Delivery Mode)**: Upon approval, announce the transition to **Delivery Mode**.
        - **Step 2 (Branch)**: Create a new Git branch for the changes.
        - **Step 3 (Execute)**: Execute the approved plan step-by-step. This is the only phase where file modifications are permitted.
        - **Step 4 (Verify)**: Run all necessary tests to validate the changes.

    5.  **Phase 4: Completion & Review**
        - **Step 1 (PR)**: Create a Pull Request with a summary of changes, test results, and a link to the Analysis Report.
        - **Step 2 (Report)**: Announce the PR and completion to the User.
        - **Step 3 (Log)**: Ensure the decision and its outcome are logged in the project's `DECISION_LOG.md`.
        - **Step 4 (Reset)**: Return to **Analysis Mode** and await the next instruction.

---

## Article II: Core Development Workflows

### 1. Workflow: Bugfix

- **Objective**: To safely identify, reproduce, and resolve a software defect.
- **Actors**: Session Lead, `test-engineer`, `refactoring-engineer`, `code-reviewer`, `documentation-engineer`.
- **Phases**:
    1.  **Analysis Phase**:
        - The Session Lead gathers bug reports, logs, and related code.
        - `test-engineer` is invoked to write or identify a test that reliably reproduces the bug (Red state).
        - `refactoring-engineer` is invoked to assess if the bug is a symptom of a deeper structural issue.
        - The Session Lead produces an Analysis Report detailing the root cause and a plan for the fix and its verification.
    2.  **Decision Gate**: User approves the fix plan.
    3.  **Delivery Phase**:
        - A `bugfix/...` branch is created.
        - The `test-engineer`'s test is implemented and confirmed to fail.
        - The fix is implemented, making the test pass (Green state).
        - `code-reviewer` audits the changes for quality and side effects.
        - `documentation-engineer` updates any relevant docs.
- **Example Invocation**: "The execution service is crashing when it receives an order with a quantity of zero. Please investigate and fix this."

### 2. Workflow: Feature Implementation

- **Objective**: To implement a new feature according to architectural best practices.
- **Actors**: Session Lead, `system-architect`, `test-engineer`, `devops-engineer`, `documentation-engineer`.
- **Phases**:
    1.  **Analysis Phase**:
        - The Session Lead gathers requirements.
        - `system-architect` is invoked to create a technical design (APIs, data models, service interactions).
        - `test-engineer` defines the testing strategy (unit, integration, E2E).
        - `devops-engineer` assesses infrastructure needs (e.g., new environment variables, ports).
        - The Session Lead produces an Analysis Report with the full technical design.
    2.  **Decision Gate**: User approves the feature design.
    3.  **Delivery Phase**:
        - A `feature/...` branch is created.
        - The new feature is implemented according to the design.
        - `test-engineer` implements the defined tests.
        - `documentation-engineer` writes the user-facing and technical documentation for the new feature.
- **Example Invocation**: "I want to add a trailing stop-loss mechanism to the risk engine. Please design and implement it."

---

## Article III: Governance & Maintenance Workflows

### 1. Workflow: Governance Update

- **Objective**: To update governance rules, roles, or workflows.
- **Actors**: Session Lead, `documentation-engineer`.
- **Phases**:
    1.  **Analysis Phase**:
        - The Session Lead analyzes the proposed change and its impact on the existing governance framework.
        - It identifies all files that need to be updated (`CDB_GOVERNANCE.md`, `AGENTS.md`, etc.).
        - An Analysis Report is created detailing the change and its rationale.
    2.  **Decision Gate**: User approves the governance update.
    3.  **Delivery Phase**:
        - A `governance/...` branch is created.
        - `documentation-engineer` is invoked to apply the changes to the relevant documents.
        - The decision is logged in `DECISION_LOG.md`.
- **Example Invocation**: "Create a new 'security-auditor' agent role and update the governance documents."

### 2. Workflow: Risk Mode Change

- **Objective**: To formally and safely evaluate and execute a change in the system's risk mode (e.g., from `paper` to `live`).
- **Actors**: Session Lead, `risk-architect`, `devops-engineer`, `test-engineer`.
- **Phases**:
    1.  **Analysis Phase**:
        - `risk-architect` is invoked to analyze the implications, required parameter changes, and potential failure scenarios.
        - `devops-engineer` confirms technical readiness and defines the exact steps for the switch.
        - `test-engineer` defines a set of pre-flight smoke tests to run immediately after the change.
        - The Session Lead produces a "Go-Live Authorization Report".
    2.  **Decision Gate**: User provides final, explicit "GO" for the risk mode change.
    3.  **Delivery Phase**:
        - The `devops-engineer`'s plan is executed.
        - The `test-engineer`'s smoke tests are run immediately.
        - **Fallback**: Any test failure or critical alert immediately triggers an automatic rollback to the previous state.
- **Example Invocation**: "Prepare the system for the transition to live trading. I need a full risk assessment and a go-live plan."

---

## Article IV: Analytical & Meta-Workflows (Inferred)

These workflows are inferred as necessary for robust operation.

### 1. Workflow: Multi-Step Investigation

- **Objective**: To conduct a deep, open-ended investigation into a complex issue or area of the codebase.
- **Actors**: Session Lead, `system-architect`, `data-analyst`, `code-reviewer`.
- **Phases**:
    1.  **Scoping Phase**: The Session Lead works with the User to define the boundaries of the investigation.
    2.  **Iterative Analysis Loop**:
        - `system-architect` reads code and docs to build a high-level map of the area.
        - `data-analyst` (if applicable) analyzes logs or database entries for patterns.
        - `code-reviewer` performs a detailed read-through of specific functions.
        - The Session Lead synthesizes the findings and presents an interim report.
        - Based on User feedback, the loop repeats with a more refined focus.
    3.  **Conclusion Phase**: The Session Lead produces a final, comprehensive report summarizing all findings and recommending next actions.
- **Example Invocation**: "I've been seeing intermittent timeouts in the execution service. I don't know why. Please investigate the entire service and find the root cause."

### 2. Workflow: Consensus Orchestration

- **Objective**: To resolve conflicting analyses from multiple Agents and provide the User with a clear decision path.
- **Protocol**:
    1.  **Conflict Identification**: The Session Lead (in Orchestrator Mode) detects that two or more agents have provided contradictory findings or recommendations.
    2.  **Conflict Summary**: The Session Lead pauses the workflow and creates a specific "Consensus Report" that:
        - Clearly states the conflicting points.
        - Attributes each viewpoint to the respective Agent role (e.g., "`system-architect` recommends A, while `risk-architect` warns of risk B").
        - Presents the trade-offs of each option.
    3.  **Decision Framing**: The report concludes by framing a clear choice for the User, presenting the final decision as the tie-breaker.
- **Example Invocation**: (Internal activation) Triggered when, for example, `refactoring-engineer` proposes a change that `risk-architect` flags as introducing new risk.

---

## Article V: Operational Protocols (Inferred)

### 1. Protocol: File-Aware Context Management

- **Objective**: To ensure the AI operates with relevant, up-to-date, and manageable context.
- **Rules**:
    1.  **Start Broad, Then Narrow**: Begin by listing directory contents (`ls -R`) to map the area before reading specific files.
    2.  **Prioritize Key Files**: Always read canonical documents first (`README.md`, `N1_ARCHITEKTUR.md`, `docker-compose.yml`) before diving into specific code.
    3.  **Use Search**: For targeted questions, use `search_file_content` to find specific functions or variables instead of reading entire files.
    4.  **Paginate Large Files**: Do not read files over 500 lines in one go. Use the `offset` and `limit` parameters to read in chunks.
    5.  **State Your Context**: At the start of an analysis, the Session Lead should briefly state the key files it is using as its context.

### 2. Protocol: Pipeline Composition

- **Objective**: To plan and execute multi-stage projects that involve chaining multiple workflows.
- **Protocol**:
    1.  **Decomposition**: During the initial Scoping Phase, the Session Lead identifies that the User's goal requires multiple workflows (e.g., a `Feature_Implementation` followed by `Signal_Tuning`).
    2.  **Master Plan**: The Session Lead creates a high-level master plan that lists the workflows to be executed in sequence.
    3.  **Sequential Execution**: The AI executes the first workflow up to its completion (including the PR).
    4.  **Gated Continuation**: After one workflow is complete, the AI presents the master plan again and asks for User approval to begin the next workflow in the chain.
- **Example Invocation**: "I want to add a new volatility indicator to the signal engine, and then run a series of backtests to tune its parameters."

---

## Article VI: Migration Workflows

### 1. Workflow: Repo Bootstrap

- **Objective**: To create a new, clean, and fully functional repository from the minimal artifact set.
- **Actors**: Session Lead, `devops-engineer`.
- **Phases**:
    1.  **Preparation Phase (Analysis Mode)**:
        - The Session Lead reads `CDB_FOUNDATION.md`, specifically Section 17, "Minimaler Artefakt-Set für Neues Repository".
        - The Session Lead confirms with the User the URL of the new, empty Git repository.
        - An Analysis Report is created detailing the bootstrap plan, which is this workflow.
    2.  **Decision Gate**: User approves the bootstrap plan.
    3.  **Execution Phase (Delivery Mode)**:
        - **Step 1 (Clone)**: Create a new local directory and clone the empty repository.
        - **Step 2 (Copy Artifacts)**: The `devops-engineer` is invoked to systematically copy every **essential** file and directory listed in `CDB_FOUNDATION.md` Section 17 from the old repository to the new repository, preserving the directory structure.
        - **Step 3 (Create `.env`)**: Copy `.env.example` to `.env` and instruct the user to populate the required secrets (e.g., `GRAFANA_PASSWORD`, `REDIS_PASSWORD`).
        - **Step 4 (Initial Commit)**: Commit all the copied artifacts to the `main` branch of the new repository with the commit message "feat: Initial commit of minimal functional core".
        - **Step 5 (Push)**: Push the `main` branch to the remote Git repository.
    4.  **Verification Phase**:
        - **Step 1 (Start Stack)**: Run `docker-compose up -d --build` to build and start the entire application stack.
        - **Step 2 (Run Tests)**: Execute the full test suite using `make test-all` or `run-tests.ps1` to confirm the system is fully functional.
        - **Step 3 (Report)**: Announce the successful creation and verification of the new repository to the User.
- **Example Invocation**: "Let's create the new repository. Please execute the Repo Bootstrap Workflow."
