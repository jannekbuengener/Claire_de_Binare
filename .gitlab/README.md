GitLab-Projektkonfiguration für Claire de Binare (Cleanroom)

- CI/CD: siehe `.gitlab-ci.yml` (Lint + Tests ohne local_only).
- Issue-Templates: liegen unter `.gitlab/issue_templates/` (Bug, Feature, Tech_Debt, Incident, Test_Addition).
- Labels: `.gitlab/labels.json` plus Seeder `.gitlab/create_labels.sh` (braucht `jq`, Variablen `GL_TOKEN`, `GL_PROJECT_ID`, optional `GL_API_URL`).
- Default-Issue-Template wählst du im GitLab-UI unter *Settings → General → Default description template*.
