"""
CDB Agent SDK - Main Entry Point

Zentrale Einstiegspunkte für alle CDB Agenten.
"""


def main() -> None:
    """Zeigt verfügbare Agenten."""
    print("CDB Agent SDK - Verfügbare Agenten:")
    print()
    print("  cdb-dataflow     Data Flow & Observability Engineer")
    print("  cdb-determinism  Execution Determinism Inspector")
    print("  cdb-governance   Governance & Canon Auditor")
    print("  cdb-impact       Change Impact Analyst")
    print()
    print("Beispiel: uv run cdb-dataflow \"Zeige Redis Stream Status\"")


if __name__ == "__main__":
    main()
