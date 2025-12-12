# SYSTEM_CONTEXT – Runtime Facts (v1.0)

## Betriebssystem
- Windows 11
- WSL2 (Linux)

## Runtime
- Docker Desktop
- Docker Compose
- Zielbild: Kubernetes

## Hardware (deklarativ)
- Lokales Entwickler-System
- Ressourcen variabel

## Zweck
Reiner Kontext für Performance- und Infra-Entscheidungen.
Keine Governance.

## WSL2 Global Configuration for Docker Desktop on Windows 10

# CDB stack: Grafana, Prometheus, Loki, Agents
[wsl2]

# Limit RAM usage to avoid Windows slowdown and Docker overload
memory=8GB

# Allocate enough CPU cores for parallel container workloads
processors=8

# Controlled swap size for stable performance without thrashing
swap=4GB

# Allow localhost networking between Windows <-> WSL2
localhostForwarding=true

# Prevent VHDX disk images from growing endlessly
defaultVhdSize=256GB

