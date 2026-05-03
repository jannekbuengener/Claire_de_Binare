# External Reference Scan for Context Intelligence

**Issue:** #2251
**Epic:** #1976
**Date:** 2026-05-03
**Status:** Research-Dry-Run → Implementation-Ready

---

## Issue / Epic

- **Issue:** [#2251](https://github.com/jannekbuengener/Claire_de_Binare/issues/2251) — Evaluate external reference lists for Context Intelligence tooling and ops hardening
- **Epic:** [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976) — CDB Context Intelligence System — SurrealDB Agent Memory & Knowledge Core

---

## Executive Summary

This scan evaluates two external reference repositories for usability within the CDB Context Intelligence System, without creating uncontrolled dependency, runtime, or governance scope.

**Key Finding:** Both repositories are suitable as **reference** and **test corpus** sources only. No new dependencies are authorized by this document. Concrete tool recommendations are limited to 3-5 candidates per area.

---

## Scope

### Covered

- CLI/UX tools for Context Query CLI
- Schema/Contract/Validation tools
- Markdown/Docs parsing
- AST/Symbol/Dependency analysis
- Search/Ranking/Retrieval options
- Report/Control-Room outputs
- Security/Ops/Backup/CI/Hardening checklists
- Test corpus suitability for chunking, link extraction, ranking, stale-knowledge detection

### Non-Goals

- No vendoring of external repositories into CDB canon
- No new dependency without separate decision
- No runtime change
- No SurrealDB write/apply action
- No Trading/Risk/Execution/Strategy change
- No LR/Live/Echtgeld go
- No auto-live-enable

---

## Sources Read

| Source | Path | Type | Last Updated |
|--------|------|------|--------------|
| the-book-of-secret-knowledge | `D:\Dev\Tools\GitHub\Desktop\tools\the-book-of-secret-knowledge` | CLI/GUI/Systems/Security/Tools | 2026-05-02 |
| awesome-python | `D:\Dev\Tools\GitHub\Desktop\tools\awesome-python` | Python Libraries | 2026-05-02 |

**Licenses:**
- the-book-of-secret-knowledge: MIT
- awesome-python: CC0-1.0

---

## Decision Matrix

| Source | Category | Relevant CDB Issues | Possible Benefit | Risk | License/Maintenance Note | Recommendation |
|--------|----------|---------------------|------------------|------|-------------------------|----------------|
| awesome-python | CLI Development / click, typer | #2079-#2090 Context Query CLI | CLI framework for Context Query | Low (standard-library alternative) | Active community, regular updates | **Prioritized** |
| awesome-python | CLI Development / rich, textual | #2079-#2090 Context Query CLI | Terminal-UI for Briefing/Evidence | Low | Active development | **Candidate** |
| awesome-python | Text Processing / markdown-it-py, mistune | #2091-#2102 MCP Bridge | Markdown parsing for document processing | Low | 100% CommonMark support | **Candidate** |
| awesome-python | Text Processing / pyparsing | #2091-#2102 MCP Bridge | Schema/Contract parsing | Low | Established, stable | **Candidate** |
| awesome-python | Code Analysis / vulture, bandit | #2145-#2205 Governance Intelligence | Dead-code detection, security scan | Low | CI-ready | **Candidate** |
| awesome-python | Code Analysis / ruff | #2145-#2205 Governance Intelligence | Linting, code quality | Low | Already in CI | **Already in use** |
| awesome-python | Search / elasticsearch-py | #2091-#2102 MCP Bridge | Retrieval backend option | Medium (new dependency) | Heavy, separate deployment | **Deferred** |
| the-book-of-secret-knowledge | CLI Tools / fzf | #2079-#2090 Context Query CLI | Fuzzy search for CLI interaction | Low | Shell tool, not Python dependency | **Candidate** |
| the-book-of-secret-knowledge | Systems/Services / monitoring | #2197 Wave 21 | Monitoring/Ops reference | Low | Reference only, no vendoring | **Reference only** |
| the-book-of-secret-knowledge | Security / hardening | #2201 Protective hardening plan | Security checklists | Low | Reference only | **Reference only** |
| the-book-of-secret-knowledge | Containers / docker-compose | #2202 CI integration plan | CI reference | Low | Reference only | **Reference only** |

---

## Prioritized Candidates

### CLI/UX Tools (Context Query CLI)

1. **click** — established CLI framework, #2079-#2090
2. **typer** — modern type-hints-based CLI, #2079-#2090
3. **rich** — terminal formatting, #2079-#2090
4. **fzf** — fuzzy search (shell tool, not Python dependency)

### Text Processing / Markdown

1. **markdown-it-py** — 100% CommonMark, #2091-#2102
2. **mistune** — fastest pure Python Markdown parser, #2091-#2102
3. **pyparsing** — generic parsing, Schema/Contract

### Code Analysis / Governance

1. **vulture** — dead-code detection, #2145
2. **bandit** — security scan, #2145
3. **ruff** — already in CI, #2145 (active)

### Ops / Hardening (Reference, No Implementation)

1. **the-book-of-secret-knowledge** — Security checklists, #2201
2. **the-book-of-secret-knowledge** — CI/Backup strategies, #2202-#2203

---

## Test Corpus Suitability

| Aspect | the-book-of-secret-knowledge | awesome-python |
|--------|------------------------------|----------------|
| **Chunking** | ⚠️ HTML/Markdown-heavy, long lists | ✅ Markdown structure, clear sections |
| **Link Extraction** | ✅ Many references to external tools | ✅ Structured lists with URLs |
| **Ranking** | ⚠️ No explicit ranking, manual sort | ✅ Community sort (Stars), partially categorized |
| **Stale-Knowledge Detection** | ⚠️ Many temporary URLs (marked with `*`) | ✅ Active maintenance, regular updates |
| **Retrieval Regressions** | ⚠️ No tests defined | ⚠️ No tests defined |

**Recommendation:** `awesome-python` is more suitable as test corpus due to clear structure and active maintenance. `the-book-of-secret-knowledge` is useful as reference but less structured for automated tests.

---

## Explicit Non-Adoptions

- ❌ No dependencies in `requirements.txt` or `pyproject.toml`
- ❌ No external content copied to `docs/`
- ❌ No new runtime changes
- ❌ No SurrealDB migrations
- ❌ No Trading/Risk/Execution code changes
- ❌ No LR/Live/Echtgeld derivation
- ❌ **No dependency is authorized by this document**

---

## Follow-up Decisions

1. **CLI Framework Decision:** click vs. typer for Context Query CLI (#2079-#2090)
   - Recommendation: typer (modern, type-hints-native)

2. **Markdown Parser:** markdown-it-py vs. mistune
   - Recommendation: mistune (pure Python, faster)

3. **Governance Tools:** vulture for dead-code detection
   - Status: Evaluate, no current need

4. **Test Corpus Pilot:** awesome-python as primary test corpus
   - For: chunking tests, link extraction, ranking validation

---

## Validation

| Check | Result |
|-------|--------|
| Repo baseline before file creation | ✅ `## main...origin/main` (clean) |
| Current git status | ✅ exactly one untracked file: `docs/surrealdb/context-intelligence/external-reference-scan.md` |
| No other file changes | ✅ |
| No Runtime/Trading/Risk/Execution files touched | ✅ |
| No SurrealDB migration | ✅ |
| No MCP live write | ✅ |

This file is intentionally untracked until Jannek approves commit.

---

## Residual Uncertainties

1. **Tool suitability for SurrealDB-specific requirements:** The external repos offer no SurrealDB-specific libraries. Separate evaluations needed for SurrealDB operations.

2. **Test corpus automation:** Suitability as test corpus was only theoretically assessed. No practical tests performed.

3. **Runtime status of Paper services:** Not verifiable without Docker-MCP

---

## Live-Readiness / Echtgeld Boundary

- Board-Stage `trade-capable` remains orthogonal to LR
- LR verdict remains **NO-GO**
- No Echtgeld implication from this research document
- **No dependency is authorized by this document**

---

## Notes

- This document is research only, not implementation authorization
- Any tool adoption requires separate decision process
- All referenced tools must be evaluated against CDB governance rules before use