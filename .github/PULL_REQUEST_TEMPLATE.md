# Pull Request - Claire de Binaire

## 📋 Beschreibung

<!-- Kurze Zusammenfassung der Änderungen -->

### Was wurde geändert?
<!-- Bullet-Points mit konkreten Änderungen -->

-
-
-

### Warum?
<!-- Grund für die Änderung: Bug-Fix, Feature, Refactoring, etc. -->

### Zugehöriges Issue/Ticket
<!-- Falls vorhanden: Closes #123 -->

---

## ✅ Pre-Merge Checkliste

### Code-Qualität

- [ ] Alle Tests laufen lokal durch (`make test`)
- [ ] Coverage ≥ 95% (`make coverage-check`)
- [ ] Linting sauber (`make lint`)
- [ ] Type-Hints korrekt (`make type-check`)
- [ ] Security-Scan ohne Findings (`make security-check`)

### Testing

- [ ] Neue Features haben Unit-Tests
- [ ] Edge-Cases sind getestet
- [ ] Integration-Tests aktualisiert (falls nötig)
- [ ] Tests sind deterministisch (keine Flakiness)

### Dokumentation

- [ ] Code-Kommentare vorhanden (wo sinnvoll)
- [ ] Docstrings aktualisiert
- [ ] README/Docs aktualisiert (falls nötig)
- [ ] CHANGELOG.md Entry (falls relevant)

### Git & CI/CD

- [ ] Branch up-to-date mit `main`/`develop`
- [ ] Keine Merge-Konflikte
- [ ] Commit-Messages aussagekräftig
- [ ] Keine `.env` oder Secrets committed
- [ ] Alle GitHub Actions Checks grün

### Docker & Deployment

- [ ] docker-compose.yml validiert (`make docker-health`)
- [ ] ENV-Variablen dokumentiert (falls neue hinzugefügt)
- [ ] Migrations getestet (falls DB-Änderungen)

---

## 🧪 Lokale Verifikation

```bash
# Kommandos, die lokal grün sein sollten:
make clean
make test-all
make lint
make security-check
make docker-health  # Falls Docker-Änderungen
```

**Lokal getestet am**: <!-- Datum -->

**Test-Ergebnisse**:
- Tests: ✅ / ❌
- Coverage: XX%
- Linting: ✅ / ❌

---

## 📸 Screenshots (optional)

<!-- Falls UI/Grafana/Logs betroffen -->

---

## 🔗 Verwandte PRs

<!-- Falls Multi-PR-Feature -->

- #XXX
- #YYY

---

## 🚨 Breaking Changes

<!-- Falls API/Konfiguration sich ändert -->

- [ ] Keine Breaking Changes
- [ ] Breaking Changes vorhanden (siehe unten)

### Migration-Guide (falls Breaking Changes)

<!-- Schritte für Migration/Upgrade -->

---

## 📝 Reviewer-Notizen

<!-- Spezielle Hinweise für Reviewer -->

### Worauf sollte besonders geachtet werden?

-
-

### Bekannte Limitierungen

-

---

## ✍️ Zusätzliche Informationen

<!-- Alles weitere, was relevant ist -->

---

**Reviewers**: @username <!-- GitHub Handle der Reviewer -->

**Priorität**: 🔴 High / 🟡 Medium / 🟢 Low

**Typ**: 🐛 Bug-Fix / ✨ Feature / 🔧 Refactoring / 📚 Documentation / 🚀 Performance
