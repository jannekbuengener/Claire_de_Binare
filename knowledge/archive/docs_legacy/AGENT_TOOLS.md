# docs/AGENT_TOOLS.md
Diese Mini-Toolchain ist dafür da, dass Claude/Codex auf deinem Rechner sauber Kontext ziehen kann, ohne wild über ganze Laufwerke zu suchen.

## CDB CLI (PowerShell)
Im Repo-Root:

- Doctor (Tool-Baseline check):
  - `pwsh -File tools\cdb.ps1 doctor`

- Context (JSON für Agenten):
  - `pwsh -File tools\cdb.ps1 context -OutFile .\logs\agent_context.json`

- Search (nur im Repo):
  - `pwsh -File tools\cdb.ps1 search -Pattern "paper trading"`
