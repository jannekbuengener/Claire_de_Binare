# Discussion Pipeline - Code Documentation

**Purpose:** Local code reference for Discussion Pipeline implementation  
**System Documentation:** See canonical documentation in Docs Hub  
**Implementation:** This directory (`scripts/discussion_pipeline/`)

## Quick Reference

### Usage
```bash
# Single-Agent Analysis
python run_discussion.py proposal.md

# Multi-Agent Deep Analysis  
python run_discussion.py proposal.md --preset deep

# Full Pipeline with GitHub Issue
python run_discussion.py proposal.md --preset deep --create-issue
```

### Key Components
- `run_discussion.py` → Main entry point
- `orchestrator.py` → Multi-agent coordination
- `workflow_engine.py` → Pipeline execution
- `create_github_issue.py` → GitHub integration
- `agents/` → Agent implementations
- `quality/` → Quality analysis modules

## Canonical Documentation

**⚠️ For complete system documentation, see:**  
`Claire_de_Binare_Docs/knowledge/systems/DISCUSSION_PIPELINE_SYSTEM.md`

This canonical documentation contains:
- Full system overview & architecture
- Quality analysis framework
- Gate system documentation  
- Usage examples & best practices
- Implementation details & metrics

## Development

- Run tests: `python -m pytest tests/`
- Dry run: `python run_discussion.py --dry-run proposal.md`
- Debug: Set `DISCUSSION_DEBUG=1`

---

**Code:** This directory  
**Docs:** Docs Hub canonical location