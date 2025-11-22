"""
Local-Only Tests - Claire de Binare

Tests in diesem Verzeichnis sind NUR für lokale Ausführung gedacht:
- Erfordern Docker Compose mit allen Services
- Sind ressourcenintensiv (Memory, CPU, Zeit)
- Testen realistische System-Szenarien
- NICHT in CI ausführen

Ausführung:
    pytest -v -m local_only tests/local/
"""
