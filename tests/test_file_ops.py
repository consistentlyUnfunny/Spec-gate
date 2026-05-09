from specgate.tools.file_ops import configure_workspace, create_file, replace_content_block


def test_create_file_writes_inside_configured_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    configure_workspace(str(workspace))

    result = create_file.invoke({"filepath": "demo.py", "initial_content": "value = 1\n"})

    assert result == "Success: Created demo.py"
    assert (workspace / "demo.py").read_text(encoding="utf-8") == "value = 1\n"


def test_create_file_rejects_paths_outside_workspace(tmp_path):
    configure_workspace(str(tmp_path / "workspace"))

    result = create_file.invoke({"filepath": "../escape.py", "initial_content": ""})

    assert result.startswith("Error:")


def test_replace_content_block_writes_inside_configured_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "demo.py").write_text("value = 1\n", encoding="utf-8")
    configure_workspace(str(workspace))

    result = replace_content_block.invoke(
        {
            "filepath": "demo.py",
            "search_block": "value = 1",
            "replace_block": "value = 2",
        }
    )

    assert result == "Success: Modified demo.py"
    assert (workspace / "demo.py").read_text(encoding="utf-8") == "value = 2\n"
