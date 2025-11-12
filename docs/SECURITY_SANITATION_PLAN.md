# Security Sanitation Plan

## Secret-Träger & Pattern
| Typ | Fundstelle | Hinweis |
|-----|------------|---------|
| .env | .env | Enthält produktionsnahe Zugangsdaten |
| Postgres-Env | postgres_env.txt, postgres_env_runtime.txt | Datenbank-Credentials im Klartext |
| Generische Muster | .env.*, *.pem, *.key, *.pfx, id_*, *.sqlite*, *.secrets | Vorbeugend blockieren (Inventur + Policy) |

## Maßnahmenreihenfolge
1. **Sofort-Rotation**  
   - Alle Credentials aus `.env`, `postgres_env*.txt` erneuern.  
   - Owner informieren, Systeme auf neue Secrets umstellen.
2. **Historie neutralisieren**  
   - `git filter-repo` (oder BFG) vorbereiten, alle Secret-Dateien und Muster entfernen.  
   - Vor dem Rewrite: Liste der betroffenen Commit-Hashes festhalten.
3. **Beispiel-Dateien beibehalten**  
   - Nur `.env.example` bzw. `docker/mcp/.env.example` etc. versionieren.  
   - Leitfaden in README ergänzen (kein Klartext im Repo).
4. **Repository neu aufsetzen**  
   - Rewrite durchführen, anschließend Remote forcieren (koordiniert).  
   - GitHub Secret Scanning & Push Protection aktivieren.  
   - Branch-Schutzregel anpassen, damit neue Secrets geblockt werden.
5. **Neu-Klonen erzwingen**  
   - Alle Mitwirkenden müssen nach Rewrite frisch klonen (`git clone`).  
   - Alte lokale Klone archivieren oder vernichten.
6. **Überwachung & Audits**  
   - Gitleaks/Secret-Scanner in CI als Pflichtlauf.  
   - Quartalsweise Review der `.gitignore`-Secret-Patterns.

## Ergebniszustand
- Repo enthält keine produktiven Secrets mehr.  
- Nur Templates/Examples mit Platzhaltern vorhanden.  
- Secret-Scanning dauerhaft aktiviert.  
- Dokumentierte Rotation & Benachrichtigung durchgeführt.

## Kommunikationspaket (Stakeholder)
> Subject: Cleanroom Secret Sanitation  
>  
> Das Repository wird historisch bereinigt, alle bisherigen Secrets rotieren sofort. Bitte nach Abschluss der Maßnahme neu klonen. Push Protection ist künftig aktiv; direkte Secret-Uploads werden blockiert. Rückfragen an Ops-Security.

## Akzeptanzkriterien
- Liste sämtlicher in der Inventur gefundenen Secret-Dateien vorhanden.
- Maßnahmen beschreiben konkrete Tools/Schritte (Rotation, filter-repo, Push Protection).
- Abschließender Zustand klar definiert: Repo ohne Secrets, `.env.example` verbleibt.
