# GROUP 1: Hygiene & Documentation Cleanup

**Agent:** Codex (Execution Agent)
**Priority:** HIGH
**Issues:** #138, #139, #143, #150
**Estimated Duration:** 15-20 minutes

---

## MISSION

Clean up documentation violations in Working Repo by fixing broken references and removing governance documentation.

---

## SCOPE (Deterministic Tasks Only)

### TASK 1: Fix README.md Broken Reference (#139)

**File:** `C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\README.md`

**Changes Required:**
1. **Line 6** - Remove `REPO_INDEX.md` from frontmatter:
   ```yaml
   upstream:
     - docker-compose.yml  # Remove REPO_INDEX.md line
   ```

2. **Line 27** - Update broken reference:
   ```markdown
   For more information about the project structure, see the documentation in the Docs Hub repository.
   ```

**Acceptance Criteria:**
- [ ] No more references to `REPO_INDEX.md`
- [ ] README.md remains clear and helpful
- [ ] Commit message: `fix: Remove broken REPO_INDEX.md references (#139)`

---

### TASK 2: Migrate Tool Documentation (#143, #150)

**Files to Move:**
- `tools/enforce-root-baseline.README.md` → `Claire_de_Binare_Docs/tools/`

**Steps:**
1. Create target directory if needed:
   ```bash
   cd C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs
   mkdir -p tools
   ```

2. Move file:
   ```bash
   git mv C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare\tools\enforce-root-baseline.README.md \
          C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare_Docs\tools\
   ```

3. Add frontmatter to moved file:
   ```yaml
   ---
   relations:
     role: tool_documentation
     domain: infrastructure
     status: active
     source_repo: Claire_de_Binare
   ---
   ```

**Acceptance Criteria:**
- [ ] File moved successfully
- [ ] Frontmatter added
- [ ] No broken references in Working Repo
- [ ] Commit in Working Repo: `chore: Migrate enforce-root-baseline docs to Docs Hub (#143, #150)`
- [ ] Commit in Docs Hub: `docs: Add enforce-root-baseline documentation from Working Repo (#143, #150)`

---

### TASK 3: Verify No Other Documentation Violations

**Check these directories:**
```bash
cd C:\Users\janne\Documents\GitHub\Workspaces\Claire_de_Binare
find . -name "*.md" -path "./tools/*" -o -name "*.md" -path "./scripts/*"
```

**Expected remaining files (ALLOWED - technical docs):**
- `./scripts/discussion_pipeline/README.md` - Technical pipeline docs
- `./scripts/discussion_pipeline/SYSTEM_DOCS.md` - Technical system docs
- `./scripts/discussion_pipeline/ENHANCED_PIPELINE_DESIGN.md` - Technical design docs
- `./tools/research/CDB_TOOL_INDEX.md` - Technical index

**If found (NOT ALLOWED - governance docs):**
- Any strategic planning documents
- Any governance documents
- Any policy documents

---

## STOP CONDITIONS

**STOP if:**
- Target directory in Docs Hub doesn't exist and can't be created
- Git conflicts occur
- Unable to move files (permissions, locks)
- Unclear whether a file is governance vs. technical

**ESCALATE to Orchestrator (Claude) if:**
- More documentation violations found than expected
- Unsure whether a file should be moved
- Conflicts with open PRs

---

## OUTPUT REQUIREMENTS

1. **Completion Report:**
   - Which tasks completed
   - Which tasks blocked
   - Commit SHAs for both repos
   - Any issues discovered

2. **Updated Issues:**
   - Close #138 (already complete)
   - Close #139 (after README fix)
   - Update #143 with progress
   - Update #150 with progress

---

## EXECUTION CHECKLIST

- [ ] Read this entire task specification
- [ ] Verify current Working Repo state
- [ ] Execute TASK 1 (README fix)
- [ ] Execute TASK 2 (File migration)
- [ ] Execute TASK 3 (Verification)
- [ ] Create commits in both repos
- [ ] Update GitHub issues
- [ ] Report completion to Orchestrator

---

**START EXECUTION**
