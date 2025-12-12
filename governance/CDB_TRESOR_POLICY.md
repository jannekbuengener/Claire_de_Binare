# CDB_TRESOR_POLICY
**Tresor-Zone – Canonical Security & Custody Policy**  
Version: 1.0.0 • Date: 2025-12-12 • Status: Canonical

---

## 1. Ziel & Sicherheitsgarantie

Die **Tresor-Zone** ist die **unantastbare Sicherheitsdomäne** von CDB.
Sie schützt das System vor **irreversiblen Verlusten**, Fehlkonfigurationen,
Autonomieüberschreitungen und Operator-Ausfällen.

**Garantien**
- Kein autonomer Zugriff (KI oder Service)
- Kein impliziter Zugriff durch Fehlkonfiguration
- Jeder Zugriff ist human-only, nachvollziehbar und reversibel

---

## 2. Umfang der Tresor-Zone (TECHNISCH IDENTIFIZIERT)

Die Tresor-Zone umfasst **ausschließlich und vollständig**:

### 2.1 Kryptografische & finanzielle Assets
- API-/Exchange-Credentials
- Wallet-/Signing-Keys
- Withdrawal- & Custody-Mechanismen

### 2.2 Systemische Hard Limits
- Exposure Caps
- Max Drawdown
- Daily Loss Limits
- Leverage Caps

### 2.3 Sicherheitssteuerung
- Kill-Switch-Konfiguration (alle Stufen)
- Emergency-Flags

### 2.4 Governance-Kern
- `CDB_CONSTITUTION.md`
- `CDB_GOVERNANCE.md`
- alle `CDB_*_POLICY.md` mit Status **Canonical**

**Technische Abgrenzung**
- Tresor-Zone liegt **außerhalb** des Repos
- Keine Mounts, keine Volumes, keine Netzpfade aus Runtime-Containern

---

## 3. Grundregeln (HART ERZWUNGEN)

### 3.1 KI-Zugriffsverbot

- KI-Container ohne:
  - Secret-Zugriff
  - Netzwerkpfad zum Tresor
  - Schreibrechte auf Governance

➡️ Technisch nicht erreichbar.

---

### 3.2 Secret-Exfiltration verhindern

- Repo-Scans blockieren:
  - Secrets
  - Private Keys
  - Token
- Logs sind secret-frei (Redaction-Pflicht)
- KI-Kontexte erhalten niemals Secret-Material

---

### 3.3 Human-Only Änderungen

- Tresor-Änderungen:
  - ausschließlich manuell
  - mit expliziter Bestätigung
- Kein API-, Bot- oder KI-Zugriff
- Vier-Augen-Prinzip optional, aber empfohlen

---

### 3.4 Fehlkonfigurations-Resistenz

- Default-Deny Design
- Keine Fallbacks mit erhöhten Rechten
- Fehlkonfiguration = sicherer Stillstand

---

## 4. Technische Durchsetzung (OSS-FIRST)

**Pflichtmechanismen**
- Dedizierter Secret Manager (z. B. Vault, age, sops)
- Least-Privilege-Rollen
- Physische Trennung Trading / Custody
- Netzwerksegmentierung

**Verifikation**
- CI prüft Repo auf Secret-Freiheit
- Runtime-Checks validieren fehlende Mounts
- Abweichung = Blockade

---

## 5. Machine-Lost-Prevention (TECHNISCH)

**Ziel**
Kein Ausfall von KI oder Services darf den Operator handlungsunfähig machen.

**Mechanismen**
- Tresor-Zugriff unabhängig von KI
- Kill-Switch manuell triggerbar (Out-of-Band)
- Alle Limits lokal rekonstruierbar
- Offline-Zugriff auf Tresor möglich

➡️ System bleibt kontrollierbar, auch bei KI-Ausfall.

---

## 6. Audit & Integritätsnachweis

- Jeder Tresor-Zugriff:
  - Zeit
  - Zweck
  - verantwortliche Person
- Logs append-only
- Regelmäßige Integritätsprüfungen

---

## 7. Gültigkeit

Diese Tresor-Policy ist **kanonisch**.  
Verletzungen gelten als **Systemverlust-Risiko**.

Keine Ausnahmen.
