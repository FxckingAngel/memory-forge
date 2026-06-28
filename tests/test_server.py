from memory_forge.server import SERVER_INSTRUCTIONS, default_db_path, mcp


def test_server_exposes_memory_instructions():
    assert mcp.name == "Memory Forge"
    assert "agent memory layer" in SERVER_INSTRUCTIONS
    assert "every active-context chunk" in SERVER_INSTRUCTIONS
    assert "memory_context" in SERVER_INSTRUCTIONS
    assert "reserved_prompt_tokens" in SERVER_INSTRUCTIONS
    assert "no longer needed verbatim" in SERVER_INSTRUCTIONS
    assert "remember this" in SERVER_INSTRUCTIONS
    assert "always read a file" in SERVER_INSTRUCTIONS
    assert "replace the bulky prompt content" in SERVER_INSTRUCTIONS


def test_default_db_path_uses_memory_forge_home(monkeypatch, tmp_path):
    monkeypatch.delenv("MEMORY_FORGE_DB", raising=False)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    assert default_db_path() == tmp_path / ".memory-forge" / "memory.db"
