# Zen MCP Server - Portable Workflow Blueprints

This document extracts the reusable architectural patterns from Zen MCP Server into portable blueprints that can be adapted for other AI agent systems.

---

## Table of Contents

1. [Multi-Step Investigation Workflow](#1-multi-step-investigation-workflow)
2. [Conversation Continuity Pattern](#2-conversation-continuity-pattern)
3. [Multi-Model Consensus Orchestration](#3-multi-model-consensus-orchestration)
4. [CLI Bridge Integration Pattern](#4-cli-bridge-integration-pattern)
5. [Provider Selection & Fallback Strategy](#5-provider-selection--fallback-strategy)
6. [File-Aware Context Management](#6-file-aware-context-management)
7. [Pipeline Composition Pattern](#7-pipeline-composition-pattern)

---

## 1. Multi-Step Investigation Workflow

### Pattern Overview
Systematic multi-step work patterns with expert analysis, used by tools like `debug`, `codereview`, and `planner`.

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKFLOW TOOL LIFECYCLE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │  Step 1  │───▶│  Step 2  │───▶│  Step N  │───▶│  Expert   │  │
│  │ (explore)│    │(validate)│    │(conclude)│    │ Analysis  │  │
│  └──────────┘    └──────────┘    └──────────┘    └───────────┘  │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              ConsolidatedFindings                        │   │
│  │  • findings[]      • relevant_files[]                    │   │
│  │  • files_checked[] • hypotheses[]                        │   │
│  │  • issues_found[]  • relevant_context[]                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Abstract Interface

```python
class WorkflowTool:
    """Base pattern for multi-step investigation tools."""

    # REQUIRED IMPLEMENTATIONS
    def get_required_actions(step_number, confidence, findings, total_steps, request) -> list[str]:
        """Define what actions CLI must take at each step."""
        pass

    def should_call_expert_analysis(consolidated_findings) -> bool:
        """Decide when to call external expert model."""
        pass

    def prepare_expert_analysis_context(consolidated_findings) -> str:
        """Prepare context for expert model call."""
        pass

    # ORCHESTRATION (provided by base)
    async def execute_workflow(arguments) -> list:
        """
        1. Validate request
        2. Track progress in ConsolidatedFindings
        3. Force CLI pauses between steps
        4. Call expert analysis when criteria met
        5. Return structured response
        """
```

### Confidence-Based Step Guidance

```python
def get_standard_required_actions(step_number, confidence, base_actions):
    if step_number == 1:
        # Initial exploration
        return [
            "Search for code related to the issue",
            "Examine relevant files",
            "Understand project structure",
            "Identify how functionality should work",
        ]
    elif confidence in ["exploring", "low"]:
        # Need deeper investigation
        return base_actions + [
            "Trace method calls and data flow",
            "Check edge cases and assumptions",
            "Look for related configuration",
        ]
    elif confidence in ["medium", "high"]:
        # Close to solution - verify
        return base_actions + [
            "Examine exact code where issue occurs",
            "Trace execution path to failure",
            "Verify hypothesis with evidence",
        ]
```

### Continuation Support

Workflow tools can be continued from previous conversations:
- If `continuation_id` provided, skip multi-step and go direct to expert analysis
- Preserves context from previous investigation steps

---

## 2. Conversation Continuity Pattern

### Pattern Overview
Stateless MCP protocol + persistent conversation memory = multi-turn AI-to-AI collaboration.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  CONVERSATION MEMORY SYSTEM                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐     ┌──────────────────────────────────────┐  │
│  │   Tool A    │────▶│         ThreadContext                 │  │
│  │  (analyze)  │     │  • thread_id: UUID                    │  │
│  └─────────────┘     │  • parent_thread_id: UUID (chains)    │  │
│         │            │  • turns: [ConversationTurn...]       │  │
│         ▼            │  • tool_name: str                     │  │
│  ┌─────────────┐     │  • initial_context: dict              │  │
│  │   Tool B    │────▶│                                       │  │
│  │ (codereview)│     └──────────────────────────────────────┘  │
│  └─────────────┘                     │                          │
│         │                            ▼                          │
│         ▼            ┌──────────────────────────────────────┐  │
│  ┌─────────────┐     │        ConversationTurn               │  │
│  │   Tool C    │────▶│  • role: "user" | "assistant"         │  │
│  │   (debug)   │     │  • content: str                       │  │
│  └─────────────┘     │  • files: list[str]                   │  │
│                      │  • images: list[str]                  │  │
│                      │  • tool_name: str                     │  │
│                      │  • model_provider: str                │  │
│                      │  • model_name: str                    │  │
│                      └──────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Core Operations

```python
# Create new conversation thread
thread_id = create_thread(tool_name, initial_request, parent_thread_id=None)

# Add turns to thread
add_turn(
    thread_id,
    role="assistant",
    content=response,
    files=["/path/to/file.py"],
    tool_name="analyze",
    model_provider="google",
    model_name="gemini-2.5-flash",
)

# Retrieve and chain threads
chain = get_thread_chain(thread_id, max_depth=20)

# Build history with file prioritization
history, tokens = build_conversation_history(context, model_context)
```

### Dual Prioritization Strategy

**File Prioritization (Newest-First):**
```
Turn 1: files = ["main.py", "utils.py"]
Turn 2: files = ["test.py"]
Turn 3: files = ["main.py", "config.py"]  # main.py appears again

Result: ["main.py", "config.py", "test.py", "utils.py"]
        ↑ main.py from Turn 3 takes precedence
```

**Turn Prioritization (Newest-First Collection → Chronological Presentation):**
```
Collection Phase (token budget):
  Turn 5 → Turn 4 → Turn 3 → (budget exceeded)
  Includes: Turn 5, Turn 4, Turn 3

Presentation Phase (LLM sees):
  "--- Turn 3 ---", "--- Turn 4 ---", "--- Turn 5 ---"
  Natural flow maintained
```

### Cross-Tool Continuation

Any tool can continue a conversation started by another:
```python
# Tool A starts conversation
thread_id = create_thread("analyze", request)
add_turn(thread_id, "assistant", analysis_result, tool_name="analyze")

# Tool B continues with same thread
context = get_thread(continuation_id)  # Gets full history including Tool A's work
# Tool B now has complete context including files from Tool A
```

---

## 3. Multi-Model Consensus Orchestration

### Pattern Overview
Query multiple AI models in parallel, synthesize their perspectives into consensus analysis.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONSENSUS WORKFLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────┐                                                  │
│  │   User     │                                                  │
│  │  Request   │                                                  │
│  └─────┬──────┘                                                  │
│        │                                                         │
│        ▼                                                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              PARALLEL MODEL QUERIES                         │ │
│  │                                                             │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │ │
│  │  │Model A  │  │Model B  │  │Model C  │  │Model N  │       │ │
│  │  │(gemini) │  │ (gpt)   │  │ (grok)  │  │(claude) │       │ │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘       │ │
│  │       │            │            │            │              │ │
│  │       ▼            ▼            ▼            ▼              │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │              Model Responses                         │   │ │
│  │  │  • response_text                                     │   │ │
│  │  │  • model_name                                        │   │ │
│  │  │  • provider                                          │   │ │
│  │  │  • stance (for/against/neutral) if directed          │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                         │                                        │
│                         ▼                                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  SYNTHESIS MODEL                            │ │
│  │                                                             │ │
│  │  "You are a Consensus Analyst reviewing perspectives       │ │
│  │   from multiple AI models. Your task is to:"               │ │
│  │                                                             │ │
│  │  1. AREAS OF AGREEMENT - Points all/most models agree on   │ │
│  │  2. AREAS OF DISAGREEMENT - Divergent viewpoints           │ │
│  │  3. UNIQUE INSIGHTS - Novel contributions from each        │ │
│  │  4. SYNTHESIS - Unified recommendation/conclusion          │ │
│  │  5. REASONING - Acknowledge uncertainty where present      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                         │                                        │
│                         ▼                                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 FINAL OUTPUT                                │ │
│  │  • consensus_summary                                        │ │
│  │  • individual_model_responses[]                             │ │
│  │  • agreement_areas[]                                        │ │
│  │  • disagreement_areas[]                                     │ │
│  │  • confidence_assessment                                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Stance Steering

```python
class StanceConfig:
    """Configure directed perspectives for models."""

    STANCE_PROMPTS = {
        "for": "Argue strongly IN FAVOR of this approach...",
        "against": "Argue strongly AGAINST this approach...",
        "neutral": "Provide a balanced, objective analysis...",
    }

    def get_stance_prompt(stance: str, base_prompt: str) -> str:
        return f"{STANCE_PROMPTS[stance]}\n\n{base_prompt}"
```

### Implementation Pattern

```python
async def execute_consensus(request):
    # 1. Prepare base prompt with file context
    base_prompt = prepare_prompt(request)

    # 2. Query models in parallel
    tasks = []
    for model_spec in request.models:
        stance_prompt = apply_stance(base_prompt, model_spec.stance)
        tasks.append(query_model(model_spec.name, stance_prompt))

    responses = await asyncio.gather(*tasks, return_exceptions=True)

    # 3. Format responses for synthesis
    formatted_responses = format_for_synthesis(responses)

    # 4. Call synthesis model
    synthesis = await synthesize(formatted_responses, request.synthesis_model)

    return ConsensusResult(
        individual_responses=responses,
        synthesis=synthesis,
    )
```

---

## 4. CLI Bridge Integration Pattern

### Pattern Overview
Bridge MCP requests to external AI CLIs (Gemini CLI, Claude CLI, etc.) for specialized capabilities.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLI BRIDGE PATTERN                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐                                             │
│  │   MCP Request   │                                             │
│  │   (clink tool)  │                                             │
│  └────────┬────────┘                                             │
│           │                                                      │
│           ▼                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   CLI Registry                              │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │ CLIClient Config (conf/cli_clients/*.yaml)           │  │ │
│  │  │ • name: "gemini"                                     │  │ │
│  │  │ • command: "gemini"                                  │  │ │
│  │  │ • roles:                                             │  │ │
│  │  │     default: { prompt_path: "prompts/default.md" }   │  │ │
│  │  │     coder: { prompt_path: "prompts/coder.md" }       │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│           │                                                      │
│           ▼                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   CLI Agent                                 │ │
│  │                                                             │ │
│  │  class BaseCLIAgent:                                        │ │
│  │      def run(role, prompt, system_prompt, files, images):  │ │
│  │          1. Build command line arguments                    │ │
│  │          2. Execute subprocess                              │ │
│  │          3. Parse output (JSON, JSONL, plain text)          │ │
│  │          4. Recover from errors if possible                 │ │
│  │                                                             │ │
│  │  class GeminiAgent(BaseCLIAgent):                           │ │
│  │      # Gemini-specific JSON error recovery                  │ │
│  │                                                             │ │
│  │  class CodexAgent(BaseCLIAgent):                            │ │
│  │      # JSONL output parsing                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│           │                                                      │
│           ▼                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Response Parser                           │ │
│  │                                                             │ │
│  │  class BaseCLIParser:                                       │ │
│  │      def parse(stdout, stderr) -> ParsedCLIResponse:       │ │
│  │          • content: str                                     │ │
│  │          • metadata: dict (model_used, events, etc.)        │ │
│  │                                                             │ │
│  │  Implementations: JSONParser, JSONLParser, PlainTextParser  │ │
│  └────────────────────────────────────────────────────────────┘ │
│           │                                                      │
│           ▼                                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Output Processing                         │ │
│  │                                                             │ │
│  │  • Apply output size limits (MAX_RESPONSE_CHARS)            │ │
│  │  • Extract <SUMMARY> tags if present                        │ │
│  │  • Prune metadata for large responses                       │ │
│  │  • Create continuation offer                                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

```python
class CLinkTool(SimpleTool):
    """Bridge MCP to external CLI agents."""

    def __init__(self):
        self._registry = get_registry()
        self._cli_names = self._registry.list_clients()
        self._role_map = {name: registry.list_roles(name) for name in cli_names}

    async def execute(self, arguments):
        # 1. Resolve CLI client and role
        client_config = self._registry.get_client(cli_name)
        role_config = client_config.get_role(role)

        # 2. Prepare prompt with conversation context
        prompt = await self._prepare_prompt_for_role(request, role_config)

        # 3. Create and run agent
        agent = create_agent(client_config)
        result = await agent.run(
            role=role_config,
            prompt=prompt,
            system_prompt=system_prompt,
            files=files,
            images=images,
        )

        # 4. Apply output limits and create response
        content, metadata = self._apply_output_limit(client_config, result)
        return ToolOutput(content=content, metadata=metadata)
```

### CLI Agent Factory

```python
def create_agent(client: ResolvedCLIClient) -> BaseCLIAgent:
    """Factory for CLI-specific agent implementations."""

    runner_name = (client.runner or client.name).lower()

    if runner_name == "gemini":
        return GeminiAgent(client)
    elif runner_name == "codex":
        return CodexAgent(client)
    else:
        return BaseCLIAgent(client)
```

---

## 5. Provider Selection & Fallback Strategy

### Pattern Overview
Centralized model provider registry with priority-based selection and capability-aware fallbacks.

### Provider Priority Order

```
1. GOOGLE    - Direct Gemini API access
2. OPENAI    - Direct OpenAI API access
3. AZURE     - Azure-hosted OpenAI deployments
4. XAI       - Direct X.AI GROK access
5. DIAL      - DIAL unified API access
6. CUSTOM    - Local/self-hosted models (Ollama, etc.)
7. OPENROUTER - Catch-all for cloud models
```

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  PROVIDER REGISTRY                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 Model Resolution                            │ │
│  │                                                             │ │
│  │  get_provider_for_model("gemini-2.5-flash")                │ │
│  │      │                                                      │ │
│  │      ▼                                                      │ │
│  │  for provider_type in PRIORITY_ORDER:                       │ │
│  │      provider = get_provider(provider_type)                 │ │
│  │      if provider.validate_model_name(model):                │ │
│  │          return provider                                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 Provider Initialization                     │ │
│  │                                                             │ │
│  │  • Lazy instantiation (created on first use)                │ │
│  │  • Singleton caching per provider type                      │ │
│  │  • API key resolution from environment                      │ │
│  │  • Provider-specific configuration (base URLs, etc.)        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 Capability-Based Selection                  │ │
│  │                                                             │ │
│  │  get_preferred_fallback_model(tool_category):              │ │
│  │      1. Get allowed models per provider (respecting limits) │ │
│  │      2. Ask each provider for preference                    │ │
│  │      3. Provider selects based on:                          │ │
│  │         • ToolModelCategory (BALANCED, EXTENDED, FAST)      │ │
│  │         • Model capabilities (thinking, context, images)    │ │
│  │         • Capability rank score                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 Model Restrictions                          │ │
│  │                                                             │ │
│  │  Environment variables per provider:                        │ │
│  │  • OPENAI_ALLOWED_MODELS="gpt-4o,gpt-4o-mini"             │ │
│  │  • GOOGLE_ALLOWED_MODELS="gemini-2.5-flash"               │ │
│  │                                                             │ │
│  │  Enforcement:                                               │ │
│  │  • Provider filters models in list_models()                 │ │
│  │  • Registry applies restrictions in get_available_models()  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Auto-Mode Pattern

When `DEFAULT_MODEL=auto`:
1. Schema marks `model` as required
2. CLI must select model from available options
3. Tool provides ranked suggestions based on category

```python
def get_model_field_schema(self):
    if self.is_effective_auto_mode():
        summaries, total, restricted = self._get_ranked_model_summaries()
        description = (
            "Auto mode. Select a model. "
            f"Top models: {summaries}. "
            "Use `listmodels` for full roster."
        )
        return {"type": "string", "description": description}
```

---

## 6. File-Aware Context Management

### Pattern Overview
Intelligent file processing with conversation awareness, deduplication, and token budget management.

### Core Principles

1. **Newest-First Prioritization**: Files from recent turns take precedence
2. **Deduplication**: Same file across turns → only newest reference included
3. **Token-Aware Embedding**: Respects model-specific token allocation
4. **Cross-Tool Access**: Files from previous tools remain accessible

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  FILE CONTEXT MANAGEMENT                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                Token Allocation                             │ │
│  │                                                             │ │
│  │  ModelContext.calculate_token_allocation():                 │ │
│  │      total_tokens     = model's context window              │ │
│  │      response_tokens  = reserved for model output           │ │
│  │      prompt_tokens    = total - response                    │ │
│  │      file_tokens      = prompt * file_ratio (default 50%)   │ │
│  │      history_tokens   = prompt - file_tokens                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                File Deduplication                           │ │
│  │                                                             │ │
│  │  filter_new_files(requested_files, continuation_id):       │ │
│  │      embedded = get_conversation_embedded_files(thread)     │ │
│  │      return [f for f in requested if f not in embedded]    │ │
│  │                                                             │ │
│  │  Note: Files already in conversation history are            │ │
│  │  referenced by note, not re-embedded                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                prompt.txt Mechanism                         │ │
│  │                                                             │ │
│  │  Purpose: Bypass MCP's ~25K token limit                     │ │
│  │                                                             │ │
│  │  Flow:                                                      │ │
│  │  1. CLI saves large prompt to prompt.txt                    │ │
│  │  2. CLI includes path in absolute_file_paths                │ │
│  │  3. Tool extracts content, removes from file list           │ │
│  │  4. Content becomes the user prompt                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                Line Number Handling                         │ │
│  │                                                             │ │
│  │  By default, all tools add line numbers to code files:      │ │
│  │      1→def hello():                                         │ │
│  │      2→    print("world")                                   │ │
│  │                                                             │ │
│  │  Benefits:                                                  │ │
│  │  • Precise code references in responses                     │ │
│  │  • "See line 42" → unambiguous communication                │ │
│  │  • Consistent across all tools                              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
def _prepare_file_content_for_prompt(
    self,
    request_files: list[str],
    continuation_id: Optional[str],
    model_context: ModelContext,
) -> tuple[str, list[str]]:
    """
    Central file processing with conversation awareness.

    Returns:
        (formatted_content, actually_processed_files)
    """
    # 1. Calculate token budget
    allocation = model_context.calculate_token_allocation()
    max_tokens = allocation.file_tokens

    # 2. Filter out already-embedded files
    files_to_embed = self.filter_new_files(request_files, continuation_id)

    # 3. Read and format new files only
    content = read_files(
        files_to_embed,
        max_tokens=max_tokens,
        include_line_numbers=True,
    )

    # 4. Add note about files in conversation history
    if len(files_to_embed) < len(request_files):
        skipped = [f for f in request_files if f not in files_to_embed]
        content += f"\n[Files in conversation history: {skipped}]"

    return content, files_to_embed
```

---

## 7. Pipeline Composition Pattern

### Pattern Overview
Compose multiple tools into pipelines (e.g., precommit runs review, security scan, test generation).

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  PIPELINE COMPOSITION                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 PrecommitTool                               │ │
│  │                                                             │ │
│  │  Pipeline Stages:                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │ 1. Code Review                                       │   │ │
│  │  │    • Quality assessment                              │   │ │
│  │  │    • Best practices                                  │   │ │
│  │  │    • Potential issues                                │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  │                          │                                  │ │
│  │                          ▼                                  │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │ 2. Security Analysis                                 │   │ │
│  │  │    • Vulnerability scan                              │   │ │
│  │  │    • Security best practices                         │   │ │
│  │  │    • Risk assessment                                 │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  │                          │                                  │ │
│  │                          ▼                                  │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │ 3. Test Generation                                   │   │ │
│  │  │    • Unit test suggestions                           │   │ │
│  │  │    • Edge case coverage                              │   │ │
│  │  │    • Test patterns                                   │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  │                          │                                  │ │
│  │                          ▼                                  │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │ 4. Synthesis                                         │   │ │
│  │  │    • Combined recommendations                        │   │ │
│  │  │    • Priority ranking                                │   │ │
│  │  │    • Action items                                    │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                 Stage Result Accumulation                   │ │
│  │                                                             │ │
│  │  Each stage produces:                                       │ │
│  │  • findings: list[str]                                      │ │
│  │  • severity: str                                            │ │
│  │  • recommendations: list[str]                               │ │
│  │                                                             │ │
│  │  Final synthesis receives all stage outputs for             │ │
│  │  comprehensive analysis                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Pattern

```python
class PipelineTool(BaseTool):
    """Tool that orchestrates multiple analysis stages."""

    def get_pipeline_stages(self) -> list[PipelineStage]:
        return [
            PipelineStage(
                name="code_review",
                system_prompt=REVIEW_PROMPT,
                focus_areas=["quality", "practices"],
            ),
            PipelineStage(
                name="security",
                system_prompt=SECURITY_PROMPT,
                focus_areas=["vulnerabilities", "risks"],
            ),
            PipelineStage(
                name="testing",
                system_prompt=TESTING_PROMPT,
                focus_areas=["coverage", "edge_cases"],
            ),
        ]

    async def execute(self, arguments):
        stages = self.get_pipeline_stages()
        results = []

        # Run each stage
        for stage in stages:
            result = await self._run_stage(stage, arguments, results)
            results.append(result)

        # Synthesize all results
        synthesis = await self._synthesize(results)

        return self._format_pipeline_output(results, synthesis)
```

---

## Summary: Reusable Patterns

| Pattern | Key Files | Use Case |
|---------|-----------|----------|
| Multi-Step Workflow | `tools/workflow/base.py`, `workflow_mixin.py` | Investigation tools requiring multiple passes |
| Conversation Continuity | `utils/conversation_memory.py` | Multi-turn AI collaboration across tools |
| Multi-Model Consensus | `tools/consensus.py` | Parallel model queries with synthesis |
| CLI Bridge | `tools/clink.py`, `clink/agents/*` | External CLI integration |
| Provider Registry | `providers/registry.py` | Model routing with fallbacks |
| File Context | `tools/shared/base_tool.py` | Token-aware file embedding |
| Pipeline Composition | `tools/precommit.py` | Multi-stage analysis |

Each pattern is designed to be:
- **Portable**: Core logic extractable to other systems
- **Composable**: Patterns can be combined
- **Extensible**: Clear extension points via abstract methods
- **Observable**: Comprehensive logging for debugging
