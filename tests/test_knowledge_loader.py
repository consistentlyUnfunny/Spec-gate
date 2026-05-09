from specgate.utils.knowledge_loader import KnowledgeLoader


def test_extract_wikilinks_deduplicates_and_ignores_aliases(tmp_path):
    loader = KnowledgeLoader(str(tmp_path), "docs")

    links = loader.extract_wikilinks("[[Architecture Notes]] and [[Architecture Notes|arch]] and [[API#Auth]]")

    assert links == ["Architecture Notes", "API"]


def test_load_linked_documents_resolves_markdown_inside_knowledge_base(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "Architecture Notes.md").write_text("Use durable checkpoints.", encoding="utf-8")
    (docs / "Missing.txt").write_text("ignore me", encoding="utf-8")

    loader = KnowledgeLoader(str(tmp_path), "docs")
    documents = loader.load_linked_documents("[[Architecture Notes]] [[Missing]]")

    assert len(documents) == 1
    assert documents[0].title == "Architecture Notes"
    assert documents[0].content == "Use durable checkpoints."


def test_format_for_prompt_includes_relative_source_path(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "Architecture Notes.md").write_text("Use durable checkpoints.", encoding="utf-8")

    loader = KnowledgeLoader(str(tmp_path), "docs")
    documents = loader.load_linked_documents("[[Architecture Notes]]")

    prompt = loader.format_for_prompt(documents)

    assert "JIT KNOWLEDGE CONTEXT" in prompt
    assert "Architecture Notes" in prompt
    assert "docs" in prompt
    assert "Use durable checkpoints." in prompt
