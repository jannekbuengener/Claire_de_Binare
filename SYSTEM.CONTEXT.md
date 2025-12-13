# SYSTEM.CONTEXT
**Runtime & Environment Context**  
Version: 1.0  
Status: Non-Governance / Read-Only

---

## Zweck

Diese Datei dient ausschließlich als **technischer Laufzeit- und Umweltkontext**
für Agenten, Modelle und Infrastrukturentscheidungen.

Sie ist:
- keine Governance
- kein Memory
- kein Entscheidungsartefakt

---

## Schreibregeln

- ❌ Keine Agenten-Writes
- ❌ Keine autonomen Änderungen
- ✅ Änderungen nur durch den User
- ✅ Änderungen sind deklarativ, nicht interpretativ

---

## Betriebssystem
- Windows 11
- WSL2 (Linux)

## Runtime
- Docker Desktop
- Docker Compose
- Zielbild: Kubernetes

## Hardware
- Lokales Entwickler-System
- Ressourcen variabel

---

## WSL2 / Docker Desktop Konfiguration

```ini
[wsl2]
memory=8GB
processors=8
swap=4GB
localhostForwarding=true
defaultVhdSize=256GB
