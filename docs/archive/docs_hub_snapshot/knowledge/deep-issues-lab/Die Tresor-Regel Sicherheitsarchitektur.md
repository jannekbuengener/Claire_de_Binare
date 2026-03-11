---
id: CDB-DR-TR
title: 'Die Tresor-Regel: Sicherheitsarchitektur'
subtitle: 'Ein "Defense in Depth"-Ansatz für autonome KI-Trading-Systeme'
author: 'Jannek Buengener, ChatGPT, Claude Code, und Gemini'
date: '2025-12-16' # Datum aus Metadaten
status: 'Abgeschlossen' # Status aus Metadaten
version: '1.0' # Version aus Metadaten
tags:
  - Sicherheit
  - Architektur
  - KI-Trading
  - Tresor-Regel
  - MiCA
  - MiFID II RTS 6
---

# Die Tresor-Regel: Sicherheitsarchitektur

> **Management Summary**
>
> Dieses Dokument definiert eine mehrschichtige, auditierbare und regulatorisch konforme Sicherheitsarchitektur ("Tresor-Regel") für das autonome KI-Trading-System *Claire de Binare (CDB)*. Ziel ist es, autonome KI-Komponenten von kritischen Kontrollsystemen zu isolieren und höchste Sicherheit sowie operationale Resilienz zu gewährleisten.
>
> Die **Hypothese** ist, dass eine Kombination aus **kryptografischer Isolation** (MPC/HSM), **Netzwerk-Segmentation** (Kubernetes), **algorithmischer Begrenzung** (Action Masking) und **menschlicher Aufsicht** (HOTL/HITL) die Risiken eines kompromittierten oder fehlerhaften KI-Agenten auf ein Minimum reduziert. Die entworfene Architektur erfüllt die Kernanforderungen von MiCA und MiFID II RTS 6 und liefert einen umsetzbaren Plan für die Implementierung der Sicherheitskontrollen.

---

## 1. Kontext & Motivation

Das Projekt *Claire de Binare (CDB)* setzt autonome Reinforcement-Learning-Agenten für den Handel an Krypto-Börsen ein. Diese Autonomie birgt inhärente Risiken. Ein robustes Sicherheitsmodell ist daher unerlässlich. Die zunehmende Regulierung durch MiCA und den EU AI Act macht eine solche Architektur nicht nur zu einer technischen Notwendigkeit, sondern auch zu einer rechtlichen Anforderung.

## 2. Forschungsziel & Forschungsfragen

### 2.1. Forschungsziel

Definition einer mehrschichtigen, auditierbaren und regulatorisch konformen Sicherheitsarchitektur ("Tresor-Regel") für das autonome KI-Trading-System *Claire de Binare (CDB)*.

### 2.2. Forschungsfragen

1.  **Kryptografische Schlüssel:** Wie können kryptografische Schlüssel (API, Signing) sicher verwahrt und genutzt werden, ohne einen Single-Point-of-Failure zu schaffen?
    *Antwort: Durch eine Kombination aus MPC-Protokollen (Signing-Keys), HSMs und Secret-Management-Systemen (z.B. HashiCorp Vault für API-Keys).*
2.  **Netzwerk-Isolation:** Wie lässt sich eine KI-Komponente auf Netzwerkebene effektiv vom Rest der Infrastruktur isolieren?
    *Antwort: Mittels Kubernetes Restricted Namespaces, Service Mesh (z.B. Istio) und strikten Zero-Trust NetworkPolicies.*
3.  **Algorithmische Sicherheit:** Welche algorithmischen Sicherheitsmechanismen können verhindern, dass ein KI-Agent gefährliche oder unerwünschte Aktionen ausführt?
    *Antwort: Durch mehrschichtiges "Action Masking" und "Circuit-Breaker".*
4.  **Menschliche Aufsicht:** Wie kann menschliche Aufsicht effektiv in ein hochgradig autonomes System integriert werden?
    *Antwort: Durch "Human-on-the-Loop" (HOTL) als Standard und automatische Eskalation zu "Human-in-the-Loop" (HITL) für kritische Aktionen.*
5.  **Regulatorische Compliance:** Welche regulatorischen Rahmenbedingungen (MiCA, MiFID II) müssen berücksichtigt und wie können deren Anforderungen umgesetzt werden?
    *Antwort: Durch die direkte Integration von Pre-Trade Risk Controls, einer Kill-Switch-Funktionalität und Audit-Trails (5-7 Jahre gemäß RTS 6).*

## 3. Methodik

-   **Vorgehen:** Die Untersuchung basiert auf einem **Research Review** und einer **Architektursynthese**. Analysiert wurden Industriestandards (FIPS 140-3), State-of-the-Art-Protokolle (MPC-CMP) und Best Practices für Cloud-native Sicherheit.
-   **Werkzeuge:** Die Architektur stützt sich auf Technologien wie Kubernetes (EKS/GKE), HashiCorp Vault, External Secrets Operator, Service Meshes (Istio/Linkerd), OPA Gatekeeper und Python.
-   **Kontrollmechanismen:** Die Architektur selbst dient als primärer Kontrollmechanismus. Die Einhaltung der Regeln wird durch Code, Konfiguration und externe kryptografische Systeme erzwungen.

## 4. Architektur-Skizze: Die vier Säulen der Tresor-Regel

Die "Tresor-Regel" basiert auf vier Säulen, die eine tiefgreifende Verteidigung (Defense in Depth) bilden:
1.  **Kryptografische Isolation:** Schutz der Schlüssel.
2.  **Netzwerk-Segmentation:** Isolation der Komponenten.
3.  **Algorithmische Begrenzung:** Einschränkung der Aktionen.
4.  **Menschliche Aufsicht:** Überwachung und Eingriffsmöglichkeit.

### 4.1. Schlüssel-Architektur: Proxy-basierte Credential Injection

Ein zentrales Prinzip ist, dass der RL-Agent niemals direkten Zugriff auf API-Schlüssel hat. Alle Aktionen werden über einen Gateway-Service geleitet, der die Credentials "out-of-band" hinzufügt:

```
[Agent Sandbox] → Funktionsaufruf → [Gateway/Proxy] → API-Key injiziert → [Exchange API]
```

### 4.2. Kubernetes-Architektur: DMZ-Modell

Die Infrastruktur wird in drei Zonen aufgeteilt:
-   **DMZ-Zone:** Externe Kommunikation (Ingress, API-Gateway).
-   **Application-Zone:** Trading-Services und KI-Komponenten.
-   **Vault-Zone:** Kritische Daten (PostgreSQL, Redis) und Secrets.
Ein Service Mesh erzwingt verschlüsselte Kommunikation (mTLS) zwischen den Zonen.

## 5. Ergebnisse & Erkenntnisse

### 5.1. Quantitative Resultate (Vergleich Key-Management)

| Kriterium | TSS/MPC | Multi-Signature | Bewertung |
| :--- | :--- | :--- | :--- |
| On-Chain-Footprint | Standard-Signatur | Mehrere Signaturen sichtbar | 👍 (Effizienter, privater) |
| Key Recovery | Automatische Rotation | Neue Adressen nötig | 👍 (Flexibler) |
| Latenz | 1 Signatur-Runde | Abhängig von Signern | 👍 (Schneller) |
| Blockchain-Support | Universal | Smart-Contract-abhängig | 👍 (Universeller) |

### 5.2. Qualitative Erkenntnisse

-   **Kryptografische Isolation ist machbar:** MPC-Protokolle (z.B. Fireblocks MPC-CMP) sind klassischen Multi-Sig-Lösungen überlegen und eliminieren den Single-Point-of-Failure eines materialisierten Private Keys.
-   **Kubernetes bietet robuste Isolations-Primitives:** "Restricted" Pod Security Standards und "Zero-Trust" NetworkPolicies können den Aktionsradius einer kompromittierten Komponente drastisch einschränken.
-   **Action Masking ist ein effektives algorithmisches Schutzschild:** Verhindert, dass der Agent gegen vordefinierte Regeln (z.B. Positionslimits, Verlustschwellen) verstößt.
-   **Menschliche Aufsicht bleibt unverzichtbar:** Das HOTL/HITL-Paradigma schafft eine Balance zwischen Autonomie und Kontrolle.
-   **Regulierung als Framework:** MiCA und MiFID II bieten ein bewährtes Framework für operationale Resilienz (z.B. Kill-Switches, Pre-Trade-Limits).

## 6. Risiken & Gegenmaßnahmen

| Risiko | Kategorie | Gegenmaßnahme |
| :--- | :--- | :--- |
| **API-Key-Kompromittierung** | Sicherheit | Proxy-basierte Credential Injection; IP-Whitelisting; Sub-Account-Isolation. |
| **Fehlerhafte KI-Entscheidung** | Modell | Action Masking; Circuit-Breaker-Pattern; Confidence-Based Escalation zu HITL. |
| **Bypass der Sicherheitskontrollen** | Architektur | Kubernetes Restricted PSS; Egress-Kontrolle via NetworkPolicies; mTLS via Service Mesh. |
| **Verletzung von Compliance** | Regulatorik | Implementierung der RTS 6 Kontrollen (Limits, Throttles); Audit-Trail-Logging (7 Jahre). |
| **Single Point of Failure** | Architektur | Einsatz von MPC statt eines einzelnen Keys; redundante Kubernetes-Nodes; HA-Datenbank-Setup. |

## 7. Entscheidung & Empfehlung

-   **Bewertung:** ✅ Go
-   **Begründung:** Die "Tresor-Regel" adressiert umfassend die identifizierten Sicherheitsrisiken und regulatorischen Anforderungen durch einen tiefgreifenden Defense-in-Depth-Ansatz. Sie schafft eine resiliente, auditierbare und technologisch fortschrittliche Grundlage für den Betrieb autonomer Trading-Systeme im CDB-Projekt.
-   **Empfohlene nächsten Schritte:**
    1.  Implementierung der Migrations-Roadmap (Umstellung auf gehärtete Kubernetes-Umgebung).
    2.  Prototyping des Gateway-Service (Credential-Injection).
    3.  Implementierung des Action-Masking-Frameworks.
    4.  Aufbau des HOTL/HITL-Dashboards.

## 8. Deliverables

-   Dieses Deep-Research-Dokument.
-   Eine detaillierte Migrations-Roadmap (siehe Anhang im Quelldokument).
-   Ein Governance-Framework-Template (siehe Anhang im Quelldokument).

---

## Referenzen

*   Interne Dokumente: `005 Die Tresor-Regel...`, `009 Die Tresor-Regel...`
*   Regulatorische Texte: EU MiCA, MiFID II (insb. RTS 6), EU AI Act.
*   Technologie-Provider: Fireblocks (MPC-CMP), HashiCorp (Vault).
*   Standards: FIPS 140-3, Kubernetes Pod Security Standards.
