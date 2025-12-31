---
doc_id: CDB-DOC-000021
title: SYSTEM DOCS
type: spec
status: active
owners: ["TBD"]
tags: []
aliases: []
relations: []
---
# System-Level Documentation for the Discussion Pipeline

## Overview

This document provides system-level documentation for the existing discussion pipeline, focusing on its current implementation, key components, and operational flow. It serves as a technical reference for understanding how raw discussions are processed and integrated into the knowledge base.

## Key Components

1.  **Input Sources:**
    *   **Agent Outputs:** Text logs from AI agents (Gemini, Claude, Copilot) are the primary input. These often contain unstructured or semi-structured conversational data.
    *   **Manual Inputs:** Human-generated meeting notes, chat excerpts, or research findings are manually added to the pipeline.

2.  **Processing Logic (Python Scripts):**
    *   **`pipeline_orchestrator.py` (CDB-CODE-working:infrastructure/scripts/discussion_pipeline/pipeline_orchestrator.py):** The main script responsible for coordinating the flow. It reads inputs, triggers LLM processing, and manages output.
    *   **`llm_processor.py` (CDB-CODE-working:infrastructure/scripts/discussion_pipeline/llm_processor.py):** Contains logic for interacting with various Large Language Models (LLMs) (e.g., via API calls) for summarization, entity extraction, and reformatting.
    *   **`output_formatter.py` (CDB-CODE-working:infrastructure/scripts/discussion_pipeline/output_formatter.py):** Transforms processed LLM outputs into standardized Markdown or YAML formats suitable for documentation.

3.  **Intermediate Storage:**
    *   Raw inputs and LLM outputs are temporarily stored in designated folders (e.g., `discussions/threads/`) before final integration.

4.  **Integration Points:**
    *   **Git Repository:** Final structured Markdown files are committed to the relevant Git repositories (e.g., `Claire_de_Binare_Docs`).
    *   **Knowledge Base:** Eventually, insights are intended to feed into a structured knowledge base or graph database.

## Operational Flow

1.  A new raw discussion (e.g., agent output file) is placed into an input directory.
2.  `pipeline_orchestrator.py` detects the new input.
3.  The orchestrator calls `llm_processor.py` to send the raw text to an LLM for processing (summarization, entity extraction).
4.  The LLM's structured output is received by `llm_processor.py`.
5.  `output_formatter.py` takes the LLM output and converts it into a standardized Markdown file.
6.  The formatted Markdown file is saved to an output directory, ready for human review and eventual commitment.

## Technologies Used

*   **Python:** For all processing scripts.
*   **Git:** For version control and documentation storage.
*   **LLMs:** Gemini, Claude, Copilot (CDB-SVC-gemini, CDB-SVC-claude, CDB-SVC-copilot).
*   **YAML/Markdown:** For structured documentation output.

## TBD / Future Enhancements

*   Automated detection of new inputs (e.g., via file system watchers or message queues).
*   Direct integration with `doc_registry.yaml` for automatic updates.
*   More sophisticated conflict resolution mechanisms.
*   Performance monitoring for LLM calls and processing times.
*   Refer to CDB-DOC-000019 for the enhanced pipeline design.
