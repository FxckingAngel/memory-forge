import sqlite3

import pytest

from memory_forge.store import MemoryStore


@pytest.fixture()
def store(tmp_path):
    return MemoryStore(tmp_path / "memory.db")


def test_initializes_schema(tmp_path):
    db_path = tmp_path / "memory.db"
    MemoryStore(db_path)

    with sqlite3.connect(db_path) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'memories'"
        ).fetchone()

    assert version == 1
    assert table is not None


def test_remember_and_search_by_full_text(store):
    memory = store.remember(
        "Codex should use SQLite for local persistent memory.",
        tags=["Codex", "Storage"],
        project="memory-forge",
        source_agent="codex",
        importance=4,
    )

    results = store.search("persistent memory")

    assert results == [memory]
    assert results[0].tags == ["codex", "storage"]


def test_search_filters_by_project_tags_and_limit(store):
    store.remember("Use SQLite for project Alpha.", tags=["db"], project="alpha")
    store.remember("Use SQLite for project Beta.", tags=["db"], project="beta")
    store.remember("Use pytest for project Alpha.", tags=["tests"], project="alpha")

    results = store.search(project="alpha", tags=["db"], limit=1)

    assert len(results) == 1
    assert results[0].project == "alpha"
    assert results[0].tags == ["db"]


def test_search_relaxes_multi_term_query_when_exact_match_misses(store):
    memory = store.remember(
        "Memory Forge handles durable memory and active context.",
        project="memory-forge",
    )

    results = store.search("Memory Forge hidden history", project="memory-forge")

    assert results == [memory]


def test_update_reindexes_search(store):
    memory = store.remember("The old backend uses flat files.", tags=["backend"])

    updated = store.update(
        memory.id,
        content="The new backend uses SQLite FTS.",
        tags=["backend", "sqlite"],
        importance=5,
    )

    assert updated.importance == 5
    assert store.search("flat files") == []
    assert store.search("SQLite FTS")[0].id == memory.id


def test_forget_archives_by_default_and_can_include_archived(store):
    memory = store.remember("Archive this memory.", tags=["archive"])

    result = store.forget(memory.id)

    assert result == {"id": memory.id, "status": "archived"}
    assert store.search("Archive") == []
    archived = store.search("Archive", include_archived=True)
    assert archived[0].id == memory.id
    assert archived[0].archived_at is not None


def test_forget_hard_deletes(store):
    memory = store.remember("Hard delete this memory.")

    result = store.forget(memory.id, hard_delete=True)

    assert result == {"id": memory.id, "status": "deleted"}
    assert store.get(memory.id, include_archived=True) is None


def test_context_returns_prompt_ready_lines(store):
    store.remember(
        "The project should stay local-first.",
        tags=["privacy"],
        project="memory-forge",
        importance=5,
    )

    context = store.context(query="local-first", project="memory-forge")

    assert context["count"] == 1
    assert "- [memory-forge; privacy] The project should stay local-first." in context["context"]
    assert context["memories"][0]["project"] == "memory-forge"
    assert context["usage"]["chars"] == len(context["context"])
    assert context["usage"]["estimated_tokens"] > 0
    assert context["usage"]["fits_context_window"] is True


def test_context_falls_back_to_project_memories_when_query_misses(store):
    store.remember(
        "Always read AGENTS.md before changing this project.",
        tags=["agent-guidance"],
        project="memory-forge",
        importance=5,
    )

    context = store.context(
        query="unrelated hidden codex transcript",
        project="memory-forge",
    )

    assert context["count"] == 1
    assert context["fallback_used"] is True
    assert "Always read AGENTS.md" in context["context"]


def test_context_respects_character_budget(store):
    store.remember(
        (
            "This is a very long memory that should be shortened when the context "
            "budget is small. "
            * 8
        ),
        tags=["budget"],
        project="memory-forge",
    )

    context = store.context(query="shortened", max_chars=200)

    assert len(context["context"]) <= 200
    assert context["truncated"] is True
    assert context["max_chars"] == 200
    assert context["usage"]["max_estimated_tokens"] == 50


def test_context_can_budget_against_model_context_window(store):
    store.remember("alpha " * 200, project="memory-forge")

    context = store.context(
        project="memory-forge",
        max_chars=1000,
        context_window_tokens=120,
        reserved_prompt_tokens=20,
        reserved_output_tokens=80,
    )

    assert context["max_chars"] == 80
    assert context["usage"]["context_window_tokens"] == 120
    assert context["usage"]["reserved_prompt_tokens"] == 20
    assert context["usage"]["reserved_output_tokens"] == 80
    assert context["usage"]["available_memory_tokens"] == 20
    assert context["usage"]["fits_context_window"] is True


def test_compact_active_context_reports_usage_and_deduplicates(store):
    result = store.compact(
        """
        User wants Memory Forge to handle active context.
        User wants Memory Forge to handle active context.
        The client should send active context when it wants compaction.
        """,
        project="memory-forge",
        tags=["context"],
        source_agent="codex",
        max_chars=200,
    )

    assert result["compacted_context"].count(
        "User wants Memory Forge to handle active context."
    ) == 1
    assert "client should send active context" in result["compacted_context"]
    assert result["saved_memory"] is None
    assert result["usage"]["chars"] == len(result["compacted_context"])


def test_compact_can_budget_against_model_context_window(store):
    result = store.compact(
        "line one\nline two\nline three",
        context_window_tokens=100,
        reserved_prompt_tokens=10,
        reserved_output_tokens=60,
        max_chars=1000,
    )

    assert result["max_chars"] == 120
    assert result["usage"]["reserved_prompt_tokens"] == 10
    assert result["usage"]["available_memory_tokens"] == 30
    assert result["usage"]["fits_context_window"] is True


def test_compact_can_save_result_as_memory(store):
    result = store.compact(
        "Memory Forge should own durable memory and compacted context.",
        project="memory-forge",
        tags=["design"],
        source_agent="codex",
        save=True,
    )

    saved = result["saved_memory"]
    assert saved is not None
    assert saved["project"] == "memory-forge"
    assert saved["tags"] == ["design", "compacted-context"]
    assert store.search("compacted context")[0].id == saved["id"]


def test_validation_rejects_bad_inputs(store):
    with pytest.raises(ValueError, match="content"):
        store.remember("   ")

    with pytest.raises(ValueError, match="importance"):
        store.remember("Bad importance", importance=9)
