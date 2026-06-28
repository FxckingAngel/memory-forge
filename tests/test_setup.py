from memory_forge.setup import apply_codex_setup, configure_codex_text, main


def test_configure_codex_text_disables_builtin_memory_and_registers_mcp():
    config = """
[windows]
sandbox = "elevated"

[features]
memories = true

[projects.'c:\\users\\example\\repo']
trust_level = "trusted"
""".lstrip()

    result = configure_codex_text(
        config,
        db_path="C:\\Users\\example\\.memory-forge\\memory.db",
        server_command="memory-forge",
        server_args=[],
    )

    assert "[windows]" in result
    assert "[projects.'c:\\users\\example\\repo']" in result
    assert "[features]\nmemories = false" in result
    assert "[memories]" in result
    assert "use_memories = false" in result
    assert "generate_memories = false" in result
    assert "disable_on_external_context = true" in result
    assert "[mcp_servers.memory_forge]" in result
    assert 'command = "memory-forge"' in result
    assert "args = []" in result
    assert "[mcp_servers.memory_forge.env]" in result
    assert 'MEMORY_FORGE_DB = "C:\\\\Users\\\\example\\\\.memory-forge\\\\memory.db"' in result


def test_apply_codex_setup_writes_config(tmp_path):
    config_path = tmp_path / "config.toml"

    result = apply_codex_setup(
        config_path=config_path,
        db_path=tmp_path / "memory.db",
        server_command="memory-forge",
    )

    assert result.changed is True
    assert config_path.exists()
    assert "memories = false" in config_path.read_text(encoding="utf-8")


def test_codex_setup_cli_supports_checkout_mode(tmp_path, capsys):
    config_path = tmp_path / "config.toml"
    checkout = tmp_path / "checkout"

    exit_code = main(
        [
            "codex",
            "--config",
            str(config_path),
            "--db",
            str(tmp_path / "memory.db"),
            "--from-checkout",
            str(checkout),
            "--dry-run",
        ]
    )

    output = capsys.readouterr().out
    escaped_checkout = str(checkout.resolve()).replace("\\", "\\\\")
    assert exit_code == 0
    assert "command = \"uv\"" in output
    assert f'"--directory", "{escaped_checkout}"' in output
    assert '"run", "memory-forge"' in output
    assert not config_path.exists()


def test_codex_setup_check_returns_one_when_changes_needed(tmp_path):
    exit_code = main(["codex", "--config", str(tmp_path / "missing.toml"), "--check"])

    assert exit_code == 1
