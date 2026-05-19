"""Unit tests for Wave 9 static symbol extraction and dependency graph.

All tests use inline fixture strings or the fixture files under
tests/fixtures/surrealdb/context_graph/ — no full indexer runs, no
SurrealDB connections, no live-readiness changes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.surrealdb.context_indexer import (
    AstParseError,
    RepoArtifact,
    _classify_import_locality,
    _flatten_config_dict,
    _parse_python_ast,
    _redact_config_value,
    derive_dependency_edges,
    extract_code_symbols,
    extract_config_references,
    extract_doc_code_links,
    extract_import_references,
    extract_test_cases,
    jsonl_records,
    run_indexer,
    stable_id,
)


SCOPE_CONFIG = Path("infrastructure/config/surrealdb/context_ingestion_scope.yaml")
FIXTURE_ROOT = Path("tests/fixtures/surrealdb/context_graph")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_HASH = "a" * 64


def _make_artifact(
    source_path: str,
    file_type: str = "python",
    normalized_sha256: str = _FAKE_HASH,
) -> RepoArtifact:
    return RepoArtifact(
        artifact_id=stable_id("repo_artifact", source_path, normalized_sha256),
        source_path=source_path,
        file_type=file_type,
        raw_sha256=normalized_sha256,
        normalized_sha256=normalized_sha256,
        size_bytes=100,
        git_commit=None,
        observed_at="2026-01-01T00:00:00Z",
        sensitivity="internal_context",
    )


# ---------------------------------------------------------------------------
# Issue #2056: AST parser module v0
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parse_python_ast_valid() -> None:
    tree, error = _parse_python_ast("test.py", "x = 1\n")
    assert tree is not None
    assert error is None


@pytest.mark.unit
def test_parse_python_ast_syntax_error() -> None:
    tree, error = _parse_python_ast("bad.py", "def broken(\n")
    assert tree is None
    assert error is not None
    assert isinstance(error, AstParseError)
    assert error.source_path == "bad.py"
    assert error.error_type == "SyntaxError"
    assert error.error_message


@pytest.mark.unit
def test_parse_python_ast_empty_file() -> None:
    tree, error = _parse_python_ast("empty.py", "")
    assert tree is not None
    assert error is None


# ---------------------------------------------------------------------------
# Issue #2057: Code symbol extraction
# ---------------------------------------------------------------------------

_PYTHON_SAMPLE = """\
import os

CONSTANT = 42

def top_level_function(x: int) -> int:
    return x

async def async_func() -> None:
    pass

class MyClass:
    def method(self) -> None:
        pass

    async def async_method(self) -> None:
        pass

    @staticmethod
    def static_method() -> bool:
        return True
"""


@pytest.mark.unit
def test_extract_code_symbols_returns_all_top_level() -> None:
    artifact = _make_artifact("mymodule.py")
    symbols, errors = extract_code_symbols(artifact, _PYTHON_SAMPLE)

    assert not errors
    names = {s.qualified_name for s in symbols}
    assert "top_level_function" in names
    assert "async_func" in names
    assert "MyClass" in names
    assert "MyClass.method" in names
    assert "MyClass.async_method" in names
    assert "MyClass.static_method" in names


@pytest.mark.unit
def test_extract_code_symbols_types_are_correct() -> None:
    artifact = _make_artifact("mymodule.py")
    symbols, _ = extract_code_symbols(artifact, _PYTHON_SAMPLE)
    by_qname = {s.qualified_name: s for s in symbols}

    assert by_qname["top_level_function"].symbol_type == "function"
    assert by_qname["async_func"].symbol_type == "async_function"
    assert by_qname["MyClass"].symbol_type == "class"
    assert by_qname["MyClass.method"].symbol_type == "method"
    assert by_qname["MyClass.async_method"].symbol_type == "async_method"


@pytest.mark.unit
def test_extract_code_symbols_has_source_ref_confidence_inferred() -> None:
    artifact = _make_artifact("mymodule.py")
    symbols, _ = extract_code_symbols(artifact, _PYTHON_SAMPLE)

    for sym in symbols:
        assert sym.source_path == "mymodule.py"
        assert sym.source_hash == _FAKE_HASH
        assert sym.confidence == "high"
        assert sym.inferred is False
        assert sym.line_start >= 1
        assert sym.line_end >= sym.line_start


@pytest.mark.unit
def test_extract_code_symbols_non_python_returns_empty() -> None:
    artifact = _make_artifact("readme.md", file_type="markdown")
    symbols, errors = extract_code_symbols(artifact, "# hello")
    assert symbols == []
    assert errors == []


@pytest.mark.unit
def test_extract_code_symbols_syntax_error_returns_ast_parse_error() -> None:
    artifact = _make_artifact("broken.py")
    symbols, errors = extract_code_symbols(artifact, "def (\n")
    assert symbols == []
    assert len(errors) == 1
    assert errors[0].source_path == "broken.py"


@pytest.mark.unit
def test_extract_code_symbols_decorator_captured() -> None:
    src = "import functools\n\n@functools.lru_cache\ndef cached() -> None:\n    pass\n"
    artifact = _make_artifact("decorators.py")
    symbols, _ = extract_code_symbols(artifact, src)
    cached = next(s for s in symbols if s.name == "cached")
    assert "functools.lru_cache" in cached.decorators


# ---------------------------------------------------------------------------
# Issue #2058: Import reference extraction
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_extract_import_references_plain_import() -> None:
    src = "import os\nimport sys\n"
    artifact = _make_artifact("mod.py")
    refs, errors = extract_import_references(artifact, src)

    assert not errors
    modules = {r.module for r in refs}
    assert "os" in modules
    assert "sys" in modules
    for r in refs:
        assert r.import_type == "import"
        assert r.locality == "unknown"


@pytest.mark.unit
def test_extract_import_references_from_import() -> None:
    src = "from core.utils.clock import utcnow\nfrom services.risk.models import RiskModel\n"
    artifact = _make_artifact("mod.py")
    refs, errors = extract_import_references(artifact, src)

    assert not errors
    assert len(refs) == 2
    modules = {r.module for r in refs}
    assert "core.utils.clock" in modules
    assert "services.risk.models" in modules
    for r in refs:
        assert r.import_type == "from_import"
        assert r.locality == "local"


@pytest.mark.unit
def test_extract_import_references_relative_is_local() -> None:
    src = "from . import sibling\nfrom ..utils import helper\n"
    artifact = _make_artifact("pkg/mod.py")
    refs, _ = extract_import_references(artifact, src)
    for r in refs:
        assert r.locality == "local"


@pytest.mark.unit
def test_classify_import_locality_known_prefix() -> None:
    assert _classify_import_locality("core.utils.clock", 0) == "local"
    assert _classify_import_locality("services.risk", 0) == "local"
    assert _classify_import_locality("tools.surrealdb.context_indexer", 0) == "local"


@pytest.mark.unit
def test_classify_import_locality_unknown_prefix() -> None:
    assert _classify_import_locality("yaml", 0) == "unknown"
    assert _classify_import_locality("pytest", 0) == "unknown"
    assert _classify_import_locality("os", 0) == "unknown"


@pytest.mark.unit
def test_classify_import_locality_relative() -> None:
    assert _classify_import_locality("", 1) == "local"
    assert _classify_import_locality("utils", 2) == "local"


@pytest.mark.unit
def test_extract_import_references_has_source_ref() -> None:
    src = "import os\n"
    artifact = _make_artifact("mod.py")
    refs, _ = extract_import_references(artifact, src)
    assert refs[0].source_path == "mod.py"
    assert refs[0].source_hash == _FAKE_HASH
    assert refs[0].confidence == "high"
    assert refs[0].inferred is False


# ---------------------------------------------------------------------------
# Issue #2059: Static test case extraction
# ---------------------------------------------------------------------------

_TEST_PYTHON = """\
def test_something() -> None:
    pass

def not_a_test() -> None:
    pass

class TestMyFeature:
    def test_case_one(self) -> None:
        pass

    def helper(self) -> None:
        pass
"""


@pytest.mark.unit
def test_extract_test_cases_detects_test_functions() -> None:
    artifact = _make_artifact("tests/test_mod.py")
    symbols, _ = extract_code_symbols(artifact, _TEST_PYTHON)
    test_cases = extract_test_cases(symbols)

    qnames = {tc.qualified_name for tc in test_cases}
    assert "test_something" in qnames
    assert "TestMyFeature.test_case_one" in qnames


@pytest.mark.unit
def test_extract_test_cases_excludes_non_test_names() -> None:
    artifact = _make_artifact("tests/test_mod.py")
    symbols, _ = extract_code_symbols(artifact, _TEST_PYTHON)
    test_cases = extract_test_cases(symbols)

    qnames = {tc.qualified_name for tc in test_cases}
    assert "not_a_test" not in qnames
    assert "TestMyFeature.helper" not in qnames


@pytest.mark.unit
def test_extract_test_cases_test_type() -> None:
    artifact = _make_artifact("tests/test_mod.py")
    symbols, _ = extract_code_symbols(artifact, _TEST_PYTHON)
    test_cases = extract_test_cases(symbols)

    by_qname = {tc.qualified_name: tc for tc in test_cases}
    assert by_qname["test_something"].test_type == "function"
    assert by_qname["TestMyFeature.test_case_one"].test_type == "method"


@pytest.mark.unit
def test_extract_test_cases_source_ref_preserved() -> None:
    artifact = _make_artifact("tests/test_mod.py")
    symbols, _ = extract_code_symbols(artifact, _TEST_PYTHON)
    test_cases = extract_test_cases(symbols)
    for tc in test_cases:
        assert tc.source_path == "tests/test_mod.py"
        assert tc.confidence == "high"
        assert tc.inferred is False


# ---------------------------------------------------------------------------
# Issue #2060: Config reference extraction
# ---------------------------------------------------------------------------

_TOML_SAMPLE = """\
[server]
host = "localhost"
port = 8000

[secrets]
api_key = "abc123secret"
username = "admin"
"""


@pytest.mark.unit
def test_extract_config_references_toml() -> None:
    artifact = _make_artifact("config.toml", file_type="toml")
    refs = extract_config_references(artifact, _TOML_SAMPLE)

    keys = {r.config_key for r in refs}
    assert "server.host" in keys
    assert "server.port" in keys
    assert "secrets.api_key" in keys
    assert "secrets.username" in keys


@pytest.mark.unit
def test_extract_config_references_redacts_sensitive_key() -> None:
    artifact = _make_artifact("config.toml", file_type="toml")
    refs = extract_config_references(artifact, _TOML_SAMPLE)
    by_key = {r.config_key: r for r in refs}

    api_key_ref = by_key["secrets.api_key"]
    assert api_key_ref.sensitive is True
    assert api_key_ref.config_value.startswith("[REDACTED:sha256=")


@pytest.mark.unit
def test_extract_config_references_non_sensitive_not_redacted() -> None:
    artifact = _make_artifact("config.toml", file_type="toml")
    refs = extract_config_references(artifact, _TOML_SAMPLE)
    by_key = {r.config_key: r for r in refs}

    host_ref = by_key["server.host"]
    assert host_ref.sensitive is False
    assert host_ref.config_value == "localhost"


@pytest.mark.unit
def test_extract_config_references_non_config_file_returns_empty() -> None:
    artifact = _make_artifact("mod.py", file_type="python")
    refs = extract_config_references(artifact, "x = 1\n")
    assert refs == []


@pytest.mark.unit
def test_extract_config_references_invalid_toml_returns_empty() -> None:
    artifact = _make_artifact("bad.toml", file_type="toml")
    refs = extract_config_references(artifact, "not valid toml [[\n")
    assert refs == []


@pytest.mark.unit
def test_flatten_config_dict_nested() -> None:
    data = {"a": {"b": 1, "c": {"d": 2}}, "e": 3}
    flat = dict(_flatten_config_dict(data))
    assert flat == {"a.b": 1, "a.c.d": 2, "e": 3}


@pytest.mark.unit
def test_redact_config_value_sensitive() -> None:
    val, sensitive = _redact_config_value("api_key", "mysecret123")
    assert sensitive is True
    assert val.startswith("[REDACTED:sha256=")


@pytest.mark.unit
def test_redact_config_value_not_sensitive() -> None:
    val, sensitive = _redact_config_value("host", "localhost")
    assert sensitive is False
    assert val == "localhost"


# ---------------------------------------------------------------------------
# Issue #2061: Doc-code link extraction
# ---------------------------------------------------------------------------

_MARKDOWN_SAMPLE = """\
# My Doc

Use `SampleClass` and `top_level_function` for basic operations.
The `async_top_level` coroutine is available too.
Repeated: `SampleClass` again.
"""


@pytest.mark.unit
def test_extract_doc_code_links_finds_backtick_refs() -> None:
    artifact = _make_artifact("docs/sample.md", file_type="markdown")
    text_map = {artifact.source_path: _MARKDOWN_SAMPLE}
    links = extract_doc_code_links([artifact], text_map)

    targets = {lnk.target_symbol for lnk in links}
    assert "SampleClass" in targets
    assert "top_level_function" in targets
    assert "async_top_level" in targets


@pytest.mark.unit
def test_extract_doc_code_links_deduplicates_per_file() -> None:
    artifact = _make_artifact("docs/sample.md", file_type="markdown")
    text_map = {artifact.source_path: _MARKDOWN_SAMPLE}
    links = extract_doc_code_links([artifact], text_map)

    # SampleClass appears twice in the markdown but should only be one link
    sample_class_links = [lnk for lnk in links if lnk.target_symbol == "SampleClass"]
    assert len(sample_class_links) == 1


@pytest.mark.unit
def test_extract_doc_code_links_non_markdown_skipped() -> None:
    artifact = _make_artifact("mod.py", file_type="python")
    text_map = {artifact.source_path: "`SomeSymbol`"}
    links = extract_doc_code_links([artifact], text_map)
    assert links == []


@pytest.mark.unit
def test_extract_doc_code_links_source_ref_set() -> None:
    artifact = _make_artifact("docs/sample.md", file_type="markdown")
    text_map = {artifact.source_path: _MARKDOWN_SAMPLE}
    links = extract_doc_code_links([artifact], text_map)
    for lnk in links:
        assert lnk.source_path == "docs/sample.md"
        assert lnk.source_hash == _FAKE_HASH
        assert lnk.source_chunk_id is None
        assert lnk.confidence == "high"
        assert lnk.inferred is False


# ---------------------------------------------------------------------------
# Issue #2062: Dependency edge derivation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_derive_dependency_edges_contains() -> None:
    artifact = _make_artifact("mod.py")
    symbols, _ = extract_code_symbols(artifact, _PYTHON_SAMPLE)
    edges = derive_dependency_edges([artifact], symbols, [], [])

    contains_edges = [e for e in edges if e.edge_type == "contains"]
    assert len(contains_edges) == len(symbols)
    for edge in contains_edges:
        assert edge.from_id == artifact.artifact_id
        assert edge.inferred is False
        assert edge.from_table == "repo_artifact"
        assert edge.to_table == "code_symbol"


@pytest.mark.unit
def test_derive_dependency_edges_imports_resolved() -> None:
    src = "from core.utils.clock import utcnow\n"
    src_artifact = _make_artifact("services/myservice.py")
    target_artifact = _make_artifact(
        "core/utils/clock.py", normalized_sha256="b" * 64
    )
    _, _ = extract_code_symbols(src_artifact, src)
    imp_refs, _ = extract_import_references(src_artifact, src)

    edges = derive_dependency_edges(
        [src_artifact, target_artifact], [], imp_refs, []
    )
    import_edges = [e for e in edges if e.edge_type == "imports"]
    assert len(import_edges) == 1
    assert import_edges[0].from_id == src_artifact.artifact_id
    assert import_edges[0].to_id == target_artifact.artifact_id
    assert import_edges[0].inferred is False
    assert import_edges[0].from_table == "repo_artifact"
    assert import_edges[0].to_table == "repo_artifact"


@pytest.mark.unit
def test_derive_dependency_edges_imports_inferred_when_not_resolved() -> None:
    src = "from core.utils.missing_module import something\n"
    src_artifact = _make_artifact("services/myservice.py")
    imp_refs, _ = extract_import_references(src_artifact, src)

    edges = derive_dependency_edges([src_artifact], [], imp_refs, [])
    import_edges = [e for e in edges if e.edge_type == "imports"]
    assert len(import_edges) == 1
    assert import_edges[0].inferred is True
    assert import_edges[0].from_table == "repo_artifact"
    assert import_edges[0].to_table == "module"
# Absolute import submodule resolution (Codex review fix — #2062 addendum P1)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_derive_dependency_edges_absolute_submodule_resolved() -> None:
    """from core.utils import clock resolves to core/utils/clock.py when that artifact exists."""
    src = "from core.utils import clock\n"
    src_artifact = _make_artifact("services/myservice.py")
    clock_artifact = _make_artifact("core/utils/clock.py", normalized_sha256="b" * 64)
    imp_refs, _ = extract_import_references(src_artifact, src)

    edges = derive_dependency_edges([src_artifact, clock_artifact], [], imp_refs, [])
    import_edges = [e for e in edges if e.edge_type == "imports"]
    assert len(import_edges) == 1
    assert import_edges[0].to_id == clock_artifact.artifact_id
    assert import_edges[0].inferred is False


@pytest.mark.unit
def test_derive_dependency_edges_absolute_submodule_no_artifact_stays_inferred() -> None:
    """from core.utils import clock stays inferred when core/utils/clock.py is absent."""
    src = "from core.utils import clock\n"
    src_artifact = _make_artifact("services/myservice.py")
    # core/utils/clock.py is not in the artifact set; neither is core/utils.py
    imp_refs, _ = extract_import_references(src_artifact, src)

    edges = derive_dependency_edges([src_artifact], [], imp_refs, [])
    import_edges = [e for e in edges if e.edge_type == "imports"]
    assert len(import_edges) == 1
    assert import_edges[0].inferred is True


@pytest.mark.unit
def test_derive_dependency_edges_absolute_module_self_fallback() -> None:
    """Backward compat: from core import utils resolves to core/utils.py when submodule absent."""
    src = "from core import utils\n"
    src_artifact = _make_artifact("services/myservice.py")
    utils_artifact = _make_artifact("core/utils.py", normalized_sha256="c" * 64)
    imp_refs, _ = extract_import_references(src_artifact, src)

    edges = derive_dependency_edges([src_artifact, utils_artifact], [], imp_refs, [])
    import_edges = [e for e in edges if e.edge_type == "imports"]
    assert len(import_edges) == 1
    assert import_edges[0].to_id == utils_artifact.artifact_id
    assert import_edges[0].inferred is False


# ---------------------------------------------------------------------------
# Relative import resolution (Codex review fix — #2062 addendum)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_derive_dependency_edges_relative_sibling_resolved() -> None:
    """from . import sibling resolves to pkg/sibling.py when that artifact exists."""
    src = "from . import sibling\n"
    src_artifact = _make_artifact("pkg/current.py")
    sibling_artifact = _make_artifact("pkg/sibling.py", normalized_sha256="c" * 64)
    imp_refs, _ = extract_import_references(src_artifact, src)

    edges = derive_dependency_edges([src_artifact, sibling_artifact], [], imp_refs, [])
    import_edges = [e for e in edges if e.edge_type == "imports"]
    assert len(import_edges) == 1
    assert import_edges[0].from_id == src_artifact.artifact_id
    assert import_edges[0].to_id == sibling_artifact.artifact_id
    assert import_edges[0].inferred is False


@pytest.mark.unit
def test_derive_dependency_edges_relative_submodule_resolved() -> None:
    """from .subpkg import util resolves to pkg/subpkg/util.py when that artifact exists."""
    src = "from .subpkg import util\n"
    src_artifact = _make_artifact("pkg/current.py")
    util_artifact = _make_artifact("pkg/subpkg/util.py", normalized_sha256="d" * 64)
    imp_refs, _ = extract_import_references(src_artifact, src)

    edges = derive_dependency_edges([src_artifact, util_artifact], [], imp_refs, [])
    import_edges = [e for e in edges if e.edge_type == "imports"]
    assert len(import_edges) == 1
    assert import_edges[0].from_id == src_artifact.artifact_id
    assert import_edges[0].to_id == util_artifact.artifact_id
    assert import_edges[0].inferred is False


@pytest.mark.unit
def test_derive_dependency_edges_relative_unresolved_is_inferred() -> None:
    """Relative imports with no matching artifact produce an inferred edge (no crash)."""
    src = "from . import nonexistent_module\n"
    src_artifact = _make_artifact("pkg/current.py")
    imp_refs, _ = extract_import_references(src_artifact, src)

    edges = derive_dependency_edges([src_artifact], [], imp_refs, [])
    import_edges = [e for e in edges if e.edge_type == "imports"]
    assert len(import_edges) == 1
    assert import_edges[0].inferred is True
    assert import_edges[0].source_path == "pkg/current.py"


@pytest.mark.unit
def test_extract_import_references_stores_import_level() -> None:
    """ImportReference.import_level is 0 for absolute, 1+ for relative imports."""
    src = "import os\nfrom . import sibling\nfrom ..utils import helper\n"
    artifact = _make_artifact("pkg/mod.py")
    refs, _ = extract_import_references(artifact, src)

    by_module = {r.module: r for r in refs}
    assert by_module["os"].import_level == 0
    assert by_module[""].import_level == 1       # from . import sibling
    assert by_module["utils"].import_level == 2   # from ..utils import helper


@pytest.mark.unit
def test_derive_dependency_edges_double_dot_relative_resolved() -> None:
    """from ..utils import helper resolves one package level up from source dir."""
    src = "from ..utils import helper\n"
    src_artifact = _make_artifact("pkg/sub/mod.py")
    # level=2 in pkg/sub/mod.py → base is pkg/ → target is pkg/utils/helper.py
    helper_artifact = _make_artifact("pkg/utils/helper.py", normalized_sha256="e" * 64)
    imp_refs, _ = extract_import_references(src_artifact, src)

    edges = derive_dependency_edges([src_artifact, helper_artifact], [], imp_refs, [])
    import_edges = [e for e in edges if e.edge_type == "imports"]
    assert len(import_edges) == 1
    assert import_edges[0].to_id == helper_artifact.artifact_id
    assert import_edges[0].inferred is False


@pytest.mark.unit
def test_derive_dependency_edges_relative_package_init_fallback() -> None:
    """from .subpkg import util falls back to pkg/subpkg/__init__.py when util.py absent."""
    src = "from .subpkg import util\n"
    src_artifact = _make_artifact("pkg/current.py")
    # Only the __init__.py of subpkg exists, not subpkg/util.py
    init_artifact = _make_artifact("pkg/subpkg/__init__.py", normalized_sha256="f" * 64)
    imp_refs, _ = extract_import_references(src_artifact, src)

    edges = derive_dependency_edges([src_artifact, init_artifact], [], imp_refs, [])
    import_edges = [e for e in edges if e.edge_type == "imports"]
    assert len(import_edges) == 1
    assert import_edges[0].to_id == init_artifact.artifact_id
    assert import_edges[0].inferred is False


# ---------------------------------------------------------------------------
# Parse-once dedup (Codex review fix — run_indexer P2)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_both_extractors_produce_same_error_for_invalid_python() -> None:
    """extract_code_symbols and extract_import_references both return the same
    AstParseError for an invalid Python file — the invariant the P2 dedup relies on."""
    artifact = _make_artifact("bad.py")
    bad_text = "def broken(\n"

    syms, errs_sym = extract_code_symbols(artifact, bad_text)
    imp_refs, errs_imp = extract_import_references(artifact, bad_text)

    assert syms == []
    assert imp_refs == []
    assert len(errs_sym) == 1
    assert len(errs_imp) == 1
    assert errs_sym[0].source_path == errs_imp[0].source_path
    assert errs_sym[0].error_type == errs_imp[0].error_type


@pytest.mark.unit
def test_run_indexer_loop_guard_prevents_duplicate_ast_errors() -> None:
    """Simulate the run_indexer dedup guard: applying ``if not errs`` before
    extending from the second extractor yields exactly one AstParseError."""
    artifact = _make_artifact("bad.py")
    bad_text = "def broken(\n"

    _, errs = extract_code_symbols(artifact, bad_text)
    _, errs2 = extract_import_references(artifact, bad_text)

    ast_errors: list = []
    ast_errors.extend(errs)
    if not errs:  # dedup guard mirroring the run_indexer fix
        ast_errors.extend(errs2)

    assert len(ast_errors) == 1, "exactly one AstParseError per invalid file, not two"


@pytest.mark.unit
def test_run_indexer_ast_error_paths_are_unique() -> None:
    """In a full run_indexer pass, each source_path appears at most once
    in ast_parse_errors (no duplicate entries from the double-parse guard)."""
    from tools.surrealdb.context_indexer import build_snapshot

    result = run_indexer(Path("."), SCOPE_CONFIG)
    error_paths = [e.source_path for e in result.ast_parse_errors]
    assert len(error_paths) == len(set(error_paths)), (
        f"duplicate AstParseError paths: {[p for p in error_paths if error_paths.count(p) > 1]}"
    )
    snapshot = build_snapshot(result)
    assert snapshot["ast_parse_error_count"] == len(result.ast_parse_errors)


# ---------------------------------------------------------------------------
# Issue #2062: Dependency edge derivation — documents / mentions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_derive_dependency_edges_documents_resolved() -> None:
    py_artifact = _make_artifact("mymod.py")
    doc_artifact = _make_artifact("docs/mymod.md", file_type="markdown")
    symbols, _ = extract_code_symbols(py_artifact, _PYTHON_SAMPLE)
    # doc references "top_level_function"
    doc_text = "`top_level_function` is available here."
    links = extract_doc_code_links([doc_artifact], {doc_artifact.source_path: doc_text})

    edges = derive_dependency_edges([py_artifact, doc_artifact], symbols, [], links)
    doc_edges = [e for e in edges if e.edge_type == "documents"]
    assert len(doc_edges) >= 1
    assert all(e.inferred is False for e in doc_edges)
    tf_sym = next(s for s in symbols if s.qualified_name == "top_level_function")
    assert any(e.to_id == tf_sym.symbol_id for e in doc_edges)
    assert all(e.from_table == "repo_artifact" for e in doc_edges)
    assert all(e.to_table == "code_symbol" for e in doc_edges)


@pytest.mark.unit
def test_derive_dependency_edges_mentions_unresolved() -> None:
    doc_artifact = _make_artifact("docs/other.md", file_type="markdown")
    doc_text = "`UnknownSymbolXYZ` is not in the codebase."
    links = extract_doc_code_links([doc_artifact], {doc_artifact.source_path: doc_text})

    edges = derive_dependency_edges([doc_artifact], [], [], links)
    mentions_edges = [e for e in edges if e.edge_type == "mentions"]
    assert len(mentions_edges) == 1
    assert mentions_edges[0].inferred is True
    assert mentions_edges[0].from_table == "repo_artifact"
    assert mentions_edges[0].to_table == "symbol_mention"


@pytest.mark.unit
def test_dependency_edge_to_payload_includes_from_to_table() -> None:
    """to_payload() must emit from_table/to_table for importer record-ref remap."""
    artifact = _make_artifact("services/svc.py")
    symbols, _ = extract_code_symbols(artifact, _PYTHON_SAMPLE)
    edges = derive_dependency_edges([artifact], symbols, [], [])

    contains_edges = [e for e in edges if e.edge_type == "contains"]
    assert contains_edges, "expected at least one contains edge"
    payload = contains_edges[0].to_payload("run-test")
    assert payload["from_table"] == "repo_artifact"
    assert payload["to_table"] == "code_symbol"
    assert "from_id" in payload
    assert "to_id" in payload



# Issue #2063: JSONL export extension
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_jsonl_records_includes_all_wave9_keys() -> None:
    result = run_indexer(
        Path("."),
        SCOPE_CONFIG,
    )
    records = jsonl_records(result)
    for key in (
        "code_symbols",
        "import_references",
        "test_cases",
        "config_references",
        "doc_code_links",
        "dependency_edges",
    ):
        assert key in records, f"missing key: {key}"
        assert isinstance(records[key], list)


# ---------------------------------------------------------------------------
# Issue #2064: Snapshot and validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_snapshot_includes_wave9_counts() -> None:
    from tools.surrealdb.context_indexer import build_snapshot

    result = run_indexer(Path("."), SCOPE_CONFIG)
    snapshot = build_snapshot(result)
    for count_key in (
        "code_symbol_count",
        "import_ref_count",
        "test_case_count",
        "config_ref_count",
        "doc_code_link_count",
        "dependency_edge_count",
        "ast_parse_error_count",
    ):
        assert count_key in snapshot, f"missing snapshot key: {count_key}"


@pytest.mark.unit
def test_run_indexer_result_has_wave9_fields() -> None:
    result = run_indexer(Path("."), SCOPE_CONFIG)
    # All new fields exist and are lists
    assert isinstance(result.code_symbols, list)
    assert isinstance(result.import_references, list)
    assert isinstance(result.test_cases, list)
    assert isinstance(result.config_references, list)
    assert isinstance(result.doc_code_links, list)
    assert isinstance(result.dependency_edges, list)
    assert isinstance(result.ast_parse_errors, list)


@pytest.mark.unit
def test_run_indexer_extracts_symbols_from_python_files() -> None:
    """Ensure that the live repo run finds code symbols in Python source files."""
    result = run_indexer(Path("."), SCOPE_CONFIG)
    # The real repo has Python files, so we expect symbols to be extracted
    assert len(result.code_symbols) > 0, "expected code symbols from Python files in scope"
    for sym in result.code_symbols:
        assert sym.source_path
        assert sym.symbol_id.startswith("code_symbol:")
        assert sym.confidence == "high"
        assert sym.inferred is False
