from memory_forge.server import SERVER_INSTRUCTIONS, default_db_path, mcp


def test_server_exposes_memory_instructions():
    assert mcp.name == "Memory Forge"
    assert "only durable memory source" in SERVER_INSTRUCTIONS
    assert "memory_context" in SERVER_INSTRUCTIONS


def test_default_db_path_uses_memory_forge_home(monkeypatch, tmp_path):
    monkeypatch.delenv("MEMORY_FORGE_DB", raising=False)
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    assert default_db_path() == tmp_path / ".memory-forge" / "memory.db"
