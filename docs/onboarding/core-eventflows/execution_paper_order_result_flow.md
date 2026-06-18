# Execution, Paper/Mock and Order Result Feedback

## Status

Docs-only onboarding artifact. Visual orientation — not authoritative.

## Parent / Issue Refs

- Parent: [#3253 Core-System Eventflow Map Pack](https://github.com/jannekbuengener/Claire_de_Binare/issues/3253)
- Issue: [#3258 Map Execution, Paper/Mock and Order Result Feedback](https://github.com/jannekbuengener/Claire_de_Binare/issues/3258)

## Purpose

Show how orders from Risk are processed by Execution, how the paper/mock boundary works, and how order results flow back to Risk and persistence. This is the path between a risk-approved order and a recorded fill.

## Mermaid Diagram

See [`diagrams/execution_paper_order_result_flow.mmd`](diagrams/execution_paper_order_result_flow.mmd) for the source file.

```mermaid
flowchart TB
    subgraph INPUT["INPUT: Orders Stream"]
        RISK["cdb_risk<br/>risk-approved orders"] --> ORD["orders Redis Stream"]
    end

    subgraph EXEC["EXECUTION SERVICE (cdb_execution)"]
        EP["Execution Processor"]
        BOUNDARY{"Execution<br/>Boundary"}
    end

    subgraph PAPER["PAPER / MOCK — default path · active"]
        SIM["Paper Engine<br/>simulated fills · results"]
        SIM --> FR["stream.fills"]
        SIM --> ORI["order_results"]
    end

    subgraph LIVE["LIVE EXCHANGE — gated · blocked"]
        EXL["Exchange Adapter"]
        LR_BLOCK["LR NO-GO · future only<br/>requires explicit human gate"]
    end

    subgraph FEEDBACK["FEEDBACK LOOP"]
        RISK2["cdb_risk<br/>position · exposure update"]
        DW["cdb_db_writer<br/>persistence"]
    end

    ORD --> EP
    EP --> BOUNDARY
    BOUNDARY -->|"default"| SIM
    BOUNDARY -.->|"gated · blocked"| EXL
    EXL -.->|"blocked"| LR_BLOCK

    FR --> RISK2
    ORI --> RISK2
    FR --> DW
    ORI --> DW

    RISK2 -.->|"exposure feedback"| RISK

    style EXL fill:#f99,stroke:#c33,stroke-dasharray:5 5
    style LR_BLOCK fill:#fcc,stroke:#c33
    style BOUNDARY fill:#ff9,stroke:#c93
    style PAPER fill:#efe,stroke:#6a6
    style LIVE fill:#fee,stroke:#c66
```

## What New Developers Must Understand

1. **Paper/Mock is the default mode.** Every order runs through paper/mock execution unless explicitly gated for live. This is not a config flag — it is a safety invariant.
2. **Execution does not authorize trades.** It receives risk-approved orders and processes them. It does not decide what to trade, how much, or whether to trade at all.
3. **Live/Exchange is a gated future boundary.** The live exchange adapter exists in code but requires explicit LR gate clearance and human approval. It is never the default path.
4. **Order results flow bidirectionally.** `order_results` and `stream.fills` update Risk (position tracking, exposure) and DB Writer (persistence) simultaneously.
5. **No order is final until it appears in `order_results`.** Execution may reject an order (e.g. invalid parameters, rate limits). Consumers must handle both fill and reject paths.

## Source of Truth / Primary Repo Sources

- [`services/execution/README.md`](../../services/execution/README.md) — Execution service documentation
- [`tools/paper_trading/README.md`](../../tools/paper_trading/README.md) — Paper runner documentation
- [`knowledge/ARCHITECTURE_MAP.md`](../../knowledge/ARCHITECTURE_MAP.md) — Channel map, invariants

## Safety Boundaries

- Execution is strictly a processor. It has no authority to generate orders or modify risk parameters.
- Paper/mock execution produces realistic fills but never touches a real exchange.
- Live exchange integration is gated by the LR process and requires explicit human GO.
- All order results are recorded in Redis Streams and PostgreSQL for full auditability.

## Non-Goals

- Not an order type reference
- Not an exchange adapter implementation guide
- Not a paper simulation accuracy analysis

## Common Failure Modes / Onboarding Traps

| Trap | Reality |
|------|---------|
| Assuming paper execution equals live execution | Paper fills have no slippage, latency, or liquidity constraints. Replay-vs-paper comparison exists precisely to quantify these gaps. |
| Expecting Execution to validate risk | Execution trusts that Risk has already validated the order. It processes what it receives. |
| Confusing paper runner with execution paper mode | Paper Runner (`tools/paper_trading/`) is a separate portfolio simulator. Execution's built-in paper mode is the default order processing path. |

## LR NO-GO / Kein Live-Go / Kein Echtgeld-Go

LR remains NO-GO ([`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)).
Board stage `trade-capable` is not Live-Go.
No Echtgeld-Go.
