# Plan: Agent & Docs Orchestration

This document outlines the concrete steps to implement the "Smarter Plan" for orchestrating the Claire de Binare documentation and agent ecosystem.

## PR-/Commit-Plan

1.  **`fix(hygiene): remove setup guide from working repo`**
    - Removes `docs/SETUP_GUIDE.md` from the `Claire_de_Binare` repo to resolve Issue #11.
2.  **`feat(docs): add architecture cockpit skeleton`**
    - Creates `knowledge/ARCHITECTURE_COCKPIT.md` in the Docs Hub with the final markdown structure, robust links, and correct runbook commands.
3.  **`feat(docs): create agent documentation structure`**
    - Creates the `agents/` directory in the Docs Hub with a `README.md` and referencing placeholder files that point to the canonical source in `.cdb_local/agents`.
4.  **`feat(docs): create missing governance file placeholders`**
    - Creates the remaining missing governance documents as placeholder files, as required by Issue #13.
5.  **`refactor(docs): update main README to point to cockpit`**
    - Revises the main `README.md` of the Docs Hub to serve as a lean entry point, directing users and agents to the new cockpit.
6.  **`chore: close issue #12 as resolved`**
    - Officially proposes closing Issue #12 (Governance Path Consolidation) as the analysis was completed successfully.
7.  **`chore: push main branch to origin`**
    - The user can then push the cleaned-up `main` branch to the remote repository using `git push origin main`.
