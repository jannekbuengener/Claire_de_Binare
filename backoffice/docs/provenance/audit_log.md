# Audit-Protokoll - Dokumenten-Transfer-Pipeline

## Erste Audit-Runde

**Auditor**: claire-risk-engine-guardian
**Datum**: 2025-11-14
**Scope**: Read-only Analyse von `sandbox/output.md`

### Logische Inkonsistenzen

- **[Abschnitt: Risk-Engine-Workflow → Schutzschichten]**: Zeile "Marktanomalien" ohne ENV-Variable markiert (`—`), aber Text beschreibt konkrete Limits (Slippage >1%, Spread >5x). Wo werden diese Schwellwerte konfiguriert?
- **[Abschnitt: Risk-Engine-Workflow → Alert-Codes]**: `RISK_LIMIT` hat zwei mögliche Levels (CRITICAL/WARNING), aber keine Regel, wann welches Level greift. Beispiel: Ist Exposure-Verstoß CRITICAL oder WARNING?
- **[Abschnitt: Systemarchitektur → Event-Topics]**: `order_results` Consumer als "Alle" bezeichnet. Welche Services konsumieren konkret? Risk Manager? Dashboard? Persistenz-Layer?

### Risk-relevante Lücken

- **[Abschnitt: Risk-Engine-Workflow → Schutzschichten]**: Keine Angabe, was nach Trading-Stopp (Daily Drawdown) passiert. Automatischer Restart am nächsten Tag? Manuelle Freigabe erforderlich?
- **[Abschnitt: Risk-Engine-Workflow → Schutzschichten]**: Datenstille-Timeout (>30s) dokumentiert, aber keine Angabe, ob Positionen bei Datenstille geschlossen werden oder nur neue Orders pausiert werden.
- **[Abschnitt: Konfiguration → Secrets]**: Keine Angabe zu Rotation-Policy oder Fallback bei fehlerhaftem Secret (z.B. falsches Redis-Passwort).
- **[Abschnitt: Konfiguration → Risk-Parameter]**: Keine Min/Max-Grenzen für Parameter. Sind negative Werte möglich? Können Parameter zur Laufzeit geändert werden oder nur beim Start?

### Unklare Formulierungen

- **[Abschnitt: Risk-Engine-Workflow → Schutzschichten]**: "Order trimmen/ablehnen" bei Einzelpositions-Limit - Regel für die Entscheidung fehlt. Wann wird getrimmt, wann abgelehnt?
- **[Abschnitt: Systemarchitektur → Infrastruktur]**: Prometheus Port als 19090 dokumentiert, aber typischer Prometheus-Port ist 9090. Warum abweichend?
- **[Abschnitt: Konfiguration → Startup-Verhalten]**: "Fehlende Variablen → Startup-Fehler" - wird der Container crashen oder in einen Retry-Loop gehen?

### Positive Feststellungen

- ✅ Klare Tabellenstruktur durchgehend verwendet
- ✅ ENV-Variablen konsistent benannt und referenziert
- ✅ Prioritäten in Risk-Engine klar nummeriert
- ✅ Alert-Codes zentral dokumentiert

### DevOps-Anmerkungen

**Von**: devops-infrastructure-architect

- **Namenskonvention**: ENV-Variablen gemischt mit/ohne Präfix. Empfehlung: Einheitliches Präfix `CDB_` für alle projekt-spezifischen Variablen (z.B. `CDB_MAX_POSITION_PCT` statt `MAX_POSITION_PCT`) zur Vermeidung von Kollisionen mit System-ENV.
- **Timeout-Einheiten**: `DATA_STALE_TIMEOUT_SEC` hat Suffix `_SEC`, aber andere Timeouts fehlen (z.B. Retry-Intervalle). Konsistenz: entweder alle Timeouts mit Suffix oder keine.
- **Monitoring-Gap**: Keine Angabe, ob Prometheus Alerts bei CRITICAL-Level automatisch getriggert werden. Alert-Manager-Integration dokumentieren oder als "TODO" markieren.
- **Port-Dokumentation**: Host-Port-Mapping (19090→9090) jetzt klar, aber keine Angabe zu Firewall-Regeln oder Netzwerk-Policies für Production. Scope dieses Dokuments?

## Zweite Audit-Runde

**Auditor**: claire-risk-engine-guardian
**Datum**: 2025-11-14
**Scope**: Stabilität und Vollständigkeit nach agata-van-data und devops-infrastructure-architect

### Verbesserungen im Vergleich zur ersten Runde

- ✅ **[Abschnitt: Risk-Engine-Workflow → Schutzschichten]**: ENV-Variablen für Marktanomalien ergänzt (`MAX_SLIPPAGE_PCT`, `MAX_SPREAD_MULTIPLIER`, `DATA_STALE_TIMEOUT_SEC`)
- ✅ **[Abschnitt: Risk-Engine-Workflow → Schutzschichten]**: Recovery-Verhalten klar dokumentiert (Daily Drawdown: manuelle Freigabe, Marktanomalien: Retry, Datenstille: automatisch)
- ✅ **[Abschnitt: Risk-Engine-Workflow → Schutzschichten]**: Datenstille-Verhalten spezifiziert ("Neue Orders pausieren, Positionen halten")
- ✅ **[Abschnitt: Risk-Engine-Workflow → Alert-Codes]**: Level-Regel ergänzt mit konkreten Beispielen und JSON-Payloads
- ✅ **[Abschnitt: Systemarchitektur → Event-Topics]**: `order_results` Consumer konkret benannt (Risk Manager, Dashboard, PostgreSQL)
- ✅ **[Abschnitt: Systemarchitektur → Infrastruktur]**: Prometheus Port-Mapping erklärt (19090→9090)
- ✅ **[Abschnitt: Konfiguration → Risk-Parameter]**: Min/Max-Grenzen für alle Parameter ergänzt
- ✅ **[Abschnitt: Konfiguration → Risk-Parameter]**: Laufzeit-Verhalten ("nur beim Start") und Startup-Verhalten (Crash vs. Retry) dokumentiert
- ✅ **[Abschnitt: Konfiguration → Secrets]**: Secret-Rotation-Policy und Fehlerverhalten bei falschen Credentials hinzugefügt
- ✅ **[Neue Sektion: Usage]**: Zielgruppen, Rollen-Mapping und Integration mit anderen Dokumenten klar strukturiert

### Kritische Punkte (bewusst offen)

- **[Abschnitt: Risk-Engine-Workflow → Schutzschichten, Priorität 5]**: "Order trimmen auf Limit (nicht ablehnen)" - im ursprünglichen Audit als unklar markiert, jetzt explizit "trimmen", aber keine Begründung, warum niemals ablehnen. Risiko: Was wenn Signal-Mindestgröße unterschritten wird?
- **[Abschnitt: Konfiguration → Risk-Parameter]**: Range-Check-Verhalten ("WARN-Log, Fallback auf Standard") weicher als erwartet. Bei kritischen Risk-Parametern (z.B. Drawdown >20%) wäre Startup-Fehler sicherer als Silent-Fallback.
- **[DevOps-Anmerkungen]**: ENV-Präfix-Empfehlung (`CDB_*`) nicht in output.md übernommen, bleibt als offene Empfehlung. Konsistenz unklar: Werden existierende Variablen migriert oder bleiben beide Konventionen parallel?

### Verbleibende Lücken (niedrige Priorität)

- **[Abschnitt: Usage → Integration mit anderen Dokumenten]**: Verweise auf Dokumentenpfade, aber keine Angabe, was bei Diskrepanz gilt (z.B. wenn `EVENT_SCHEMA.json` und dieses Dokument widersprechen).
- **[DevOps-Anmerkungen → Monitoring-Gap]**: Alert-Manager-Integration nicht in output.md aufgenommen. Als TODO markieren oder außerhalb Scope?
- **[Abschnitt: Risk-Engine-Workflow → Recovery-Verhalten]**: "Manuelle Freigabe via Admin-Befehl" - kein Verweis, wo dieser Befehl dokumentiert ist oder wie er aussieht.

### Stabilitätsbewertung

**Status**: ✅ **Produktionsreif für interne Referenz**

**Begründung**:
- Alle kritischen Lücken der ersten Audit-Runde geschlossen
- Strukturierte Tabellen durchgehend, konsistente Formatierung
- Risk-relevante Parameter vollständig dokumentiert (Defaults, Min/Max, Verhalten)
- Usage-Sektion klärt Zielgruppe und Integration

**Offene Punkte** sind bewusste Design-Entscheidungen (Trimming-Regel, Fallback-Verhalten) oder Out-of-Scope (Production Networking, Alert-Manager). Keine Blocker für Nutzung als interne Architektur-Referenz.

**Empfehlung**: Dokument in `backoffice/docs/` aufnehmen, ADR in `DECISION_LOG.md` für ENV-Präfix-Empfehlung erstellen.
