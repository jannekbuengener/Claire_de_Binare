# CDB_RL_SAFETY_POLICY
**Safe Reinforcement Learning – Canonical Safety Policy**  
Version: 1.0.0 • Date: 2025-12-12 • Status: Canonical

---

## 1. Ziel & Sicherheitsgarantie

Reinforcement Learning (RL) darf **ausschließlich innerhalb deterministischer,
technisch erzwungener Guardrails** operieren.

**Garantien**
- Keine autonome Ausführung ohne deterministische Prüfung
- Keine probabilistische Sicherheitslogik
- Sicherheit > Profit > Lernfortschritt

---

## 2. Deterministische Guardrails (TECHNISCH DEFINIERT)

**Definition**
Guardrails sind **reine, deterministische Funktionen**, die aus
(State × Action × Limits) → **erlaubte Aktion** berechnen.

**Eigenschaften**
- Kein Zufall
- Kein Modell
- Keine Seiteneffekte
- Replay-identisch

**Nachweis**
- Identischer Input → identischer Output
- CI-Replay-Tests erzwingen Determinismus

---

## 3. Trennung der Verantwortlichkeiten (HART ERZWUNGEN)

### 3.1 Systemkette

```
RL Policy → Risk / Constraint Layer → Action Masking → Execution
```

**Technische Durchsetzung**
- RL-Service besitzt **keinen Netzwerkpfad** zur Execution
- Nur Risk-Layer darf Orders erzeugen
- Execution akzeptiert nur signierte, validierte Actions

---

## 4. Action Masking (NICHT UMGEHBAR)

**Mechanismus**
- Aktionsraum wird **vor** Auswahl reduziert
- Verbotene Aktionen existieren technisch nicht

**Regeln**
- Default-Aktion: `HOLD`
- Mask basiert ausschließlich auf:
  - PSM-State (read-only)
  - Hard Risk Limits (read-only)

**Integrität**
- Hash-Prüfung der Input-States
- Abweichung → HOLD + Audit-Event

---

## 5. Kill-Switch Stufen (TECHNISCH DURCHGESETZT)

### 5.1 Stufen

1. **REDUCE_ONLY** – Positionsabbau erlaubt
2. **HARD_STOP** – keine neuen Orders
3. **EMERGENCY** – vollständiger Handelsstopp

### 5.2 Trigger

- Drawdown / Daily Loss
- Risk-Limit-Verletzung
- Systemfehler / Latenz
- Dateninkonsistenz

### 5.3 Durchsetzung

- Kill-Switch läuft **außerhalb** der Trading-Pipeline
- Status wird als Event persistiert
- Keine Rücknahme ohne User-Freigabe

---

## 6. Shadow & Canary Phasen (VERIFIZIERT)

### 6.1 Shadow

- 0 Kapital
- Identische Inputs
- Vergleich: RL vs. Referenzstrategie

### 6.2 Canary

- Hart begrenztes Kapital
- Separate Accounts / Limits
- Automatischer Abbruch bei Metrik-Verletzung

### 6.3 Promotion

- Metrics-Gates erfüllt
- Explizites User-Go
- Versionierter Wechsel

---

## 7. Audit & Explainability (IMMUTABLE)

**Pro Entscheidung**
- Input-State (Hash)
- Proposed Action
- Action Mask
- Executed Action
- Guardrail-Version
- RL-Policy-Version
- Timestamp

**Speicherung**
- Append-only Event-Store
- Manipulationssicher
- Replay-fähig

---

## 8. Tresor-Regel (ABSOLUT)

**RL darf niemals**
- Hard Limits ändern
- Keys, Wallets oder Custody berühren
- Governance oder Policies mutieren

**Durchsetzung**
- Kein Schreibzugriff
- Kein API-Zugriff
- CI- & Runtime-Guards

---

## 9. Durchsetzung & Audit

- CI prüft:
  - Guardrail-Determinismus
  - Masking-Korrektheit
  - Kill-Switch-Reaktionen
- Verstöße blockieren Releases

---

## 10. Gültigkeit

Diese Policy ist **kanonisch**.  
Autonomie ohne diese Sicherheitsgarantien ist verboten.

Keine Ausnahmen.
