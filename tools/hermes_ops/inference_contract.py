"""cdb-engineer ChatGPT/Codex subscription inference contract (#4501).

Pinned Hermes Agent v0.19.1 (commit cc4cab2…) already ships:
  provider: openai-codex
  transport: codex_responses
  auth_type: oauth_external

This module only enforces the CDB product contract on the repo-owned
cdb-engineer profile: subscription OAuth only, no paid API-key fallback.
Runs-API gateway auth (HERMES_CDB_ENGINEER_API_KEY / API_SERVER_KEY) is
out of scope and must not be treated as an inference key.
"""

from __future__ import annotations

from typing import Any

# Primary inference identity for cdb-engineer (Hermes provider id).
REQUIRED_PRIMARY_PROVIDER = "openai-codex"

# Auxiliary provider values that stay on ChatGPT/Codex subscription auth.
# In v0.19.1, auxiliary accepts "codex" (alias of openai-codex) and "main"
# (inherits the main agent provider). "auto" is forbidden because it can
# fall through to OpenRouter / other API-key providers.
ALLOWED_AUXILIARY_PROVIDERS = frozenset({"codex", "main", "openai-codex"})

# Paid / API-key inference providers that must never appear for cdb-engineer.
FORBIDDEN_INFERENCE_PROVIDERS = frozenset(
    {
        "auto",
        "openrouter",
        "openai-api",
        "openai",
        "anthropic",
        "gemini",
        "google",
        "ai-gateway",
        "deepinfra",
        "nvidia",
        "vercel",
        "huggingface",
        "novita",
        "kilo",
        "kilocode",
        "zai",
        "minimax",
        "minimax-cn",
        "deepseek",
        "alibaba",
        "xai",
    }
)

# Env names that must not be declared as consumable inference credentials
# for cdb-engineer (distribution.yaml env_requires / .env.EXAMPLE).
FORBIDDEN_INFERENCE_ENV = frozenset(
    {
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "AI_GATEWAY_API_KEY",
        "DEEPINFRA_API_KEY",
        "NVIDIA_API_KEY",
        "HF_TOKEN",
        "ZAI_API_KEY",
        "GLM_API_KEY",
        "MINIMAX_API_KEY",
        "MINIMAX_CN_API_KEY",
        "DEEPSEEK_API_KEY",
        "XAI_API_KEY",
        "KILOCODE_API_KEY",
        "NOVITA_API_KEY",
    }
)

# Auxiliary tasks that declare provider in Hermes v0.19.1 DEFAULT_CONFIG.
REQUIRED_AUXILIARY_TASKS = (
    "vision",
    "web_extract",
    "compression",
    "skills_hub",
    "approval",
    "mcp",
    "title_generation",
    "memory_query_rewrite",
    "tts_audio_tags",
    "triage_specifier",
    "kanban_decomposer",
    "profile_describer",
    "goal_judge",
    "curator",
    "monitor",
    "background_review",
    "moa_reference",
    "moa_aggregator",
)


def _norm_provider(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def validate_cdb_engineer_distribution(
    dist: dict[str, Any], *, env_example_text: str | None = None
) -> list[str]:
    """Validate distribution.yaml (+ optional .env.EXAMPLE text) for #4501."""
    errors: list[str] = []
    cdb = dist.get("cdb") or {}
    if not isinstance(cdb, dict):
        return ["distribution.cdb must be a mapping"]

    inference = cdb.get("inference")
    if not isinstance(inference, dict):
        errors.append("cdb.inference mapping required for cdb-engineer")
    else:
        if (
            _norm_provider(inference.get("primary_provider"))
            != REQUIRED_PRIMARY_PROVIDER
        ):
            errors.append(
                "cdb.inference.primary_provider must be "
                f"{REQUIRED_PRIMARY_PROVIDER!r}"
            )
        if inference.get("paid_api_fallback") is not False:
            errors.append("cdb.inference.paid_api_fallback must be false")
        auth = str(inference.get("allowed_auth") or "").strip().lower()
        if auth not in {
            "chatgpt_codex_oauth_subscription",
            "chatgpt_codex_oauth",
            "oauth_external",
        }:
            errors.append(
                "cdb.inference.allowed_auth must declare ChatGPT/Codex OAuth "
                "subscription"
            )

    env_requires = dist.get("env_requires") or []
    if not isinstance(env_requires, list):
        errors.append("env_requires must be a list")
        env_requires = []
    for entry in env_requires:
        if not isinstance(entry, dict):
            errors.append("env_requires entries must be mappings")
            continue
        name = str(entry.get("name") or "").strip()
        if name in FORBIDDEN_INFERENCE_ENV:
            errors.append(f"env_requires must not declare paid inference env {name}")

    if env_example_text is not None:
        for line in env_example_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            key = stripped.split("=", 1)[0].strip()
            if key in FORBIDDEN_INFERENCE_ENV:
                errors.append(f".env.EXAMPLE must not declare paid inference env {key}")
    return errors


def validate_cdb_engineer_config(cfg: dict[str, Any]) -> list[str]:
    """Validate non-secret config.yaml inference fields for Hermes v0.19.1."""
    errors: list[str] = []

    model = cfg.get("model")
    if not isinstance(model, dict):
        errors.append(
            "config.yaml model must be a mapping with provider "
            f"{REQUIRED_PRIMARY_PROVIDER!r} (Hermes v0.19.1 schema)"
        )
    else:
        provider = _norm_provider(model.get("provider"))
        if provider != REQUIRED_PRIMARY_PROVIDER:
            errors.append(
                "config.yaml model.provider must be "
                f"{REQUIRED_PRIMARY_PROVIDER!r} (got {provider!r})"
            )
        if provider in FORBIDDEN_INFERENCE_PROVIDERS:
            errors.append(f"config.yaml model.provider forbidden: {provider!r}")
        # base_url must not redirect openai-codex onto api.openai.com / openrouter
        base_url = str(model.get("base_url") or "").strip().lower()
        if base_url and any(
            needle in base_url
            for needle in ("openrouter.ai", "api.openai.com", "generativelanguage")
        ):
            errors.append(
                "config.yaml model.base_url must not point at paid API endpoints"
            )

    fallback = cfg.get("fallback_providers", [])
    if fallback is None:
        fallback = []
    if not isinstance(fallback, list):
        errors.append("fallback_providers must be a list")
    elif fallback:
        for i, entry in enumerate(fallback):
            if isinstance(entry, dict):
                fb = _norm_provider(entry.get("provider"))
            else:
                fb = _norm_provider(entry)
            if (
                fb
                and fb != REQUIRED_PRIMARY_PROVIDER
                and fb not in ALLOWED_AUXILIARY_PROVIDERS
            ):
                errors.append(
                    f"fallback_providers[{i}] paid/API provider forbidden: {fb!r}"
                )
            if fb in FORBIDDEN_INFERENCE_PROVIDERS:
                errors.append(f"fallback_providers[{i}] forbidden provider: {fb!r}")
        # Any non-empty paid chain is forbidden; empty list is required.
        errors.append(
            "fallback_providers must be empty for cdb-engineer "
            "(OAuth unavailable must fail closed)"
        )

    # Single-dict / alternate fallback_model form also present in Hermes schema.
    fallback_model = cfg.get("fallback_model")
    if fallback_model:
        errors.append(
            "fallback_model must be absent/empty for cdb-engineer "
            "(no paid API fallback)"
        )

    auxiliary = cfg.get("auxiliary")
    if not isinstance(auxiliary, dict):
        errors.append(
            "config.yaml auxiliary mapping required so auto→OpenRouter "
            "cannot activate"
        )
        return errors

    for task in REQUIRED_AUXILIARY_TASKS:
        block = auxiliary.get(task)
        if not isinstance(block, dict):
            errors.append(f"auxiliary.{task} must be a mapping with provider")
            continue
        provider = _norm_provider(block.get("provider"))
        if provider not in ALLOWED_AUXILIARY_PROVIDERS:
            errors.append(
                f"auxiliary.{task}.provider must be one of "
                f"{sorted(ALLOWED_AUXILIARY_PROVIDERS)} (got {provider!r})"
            )
        if provider in FORBIDDEN_INFERENCE_PROVIDERS:
            errors.append(f"auxiliary.{task}.provider forbidden: {provider!r}")
        chain = block.get("fallback_chain")
        if chain:
            errors.append(
                f"auxiliary.{task}.fallback_chain must be empty/absent "
                "(no paid API fallback)"
            )
        api_key = str(block.get("api_key") or "").strip()
        if api_key and not api_key.startswith("${"):
            # Non-secret config must not embed keys; env interpolation markers
            # are also disallowed here because paid inference keys are forbidden.
            errors.append(f"auxiliary.{task}.api_key must be empty for cdb-engineer")
    return errors
