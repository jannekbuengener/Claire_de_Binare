agent: copilot
scope: workflow
phase: 6
labels: ["agent:copilot","scope:workflow","phase:workflow","status:in-review"]
related_files: [".github/workflows/auto-label-from-branch.yml",".github/workflows/labels.json",".github/BRANCH_LABELING.md"]

What:
Add automatic PR labeling based on branch name and sync labels.

Why:
Reduce triage time, improve determinism.

How:
GitHub Action + labels.json + docs.

DoD:
- [ ] workflow added
- [ ] labels synced
- [ ] docs added
