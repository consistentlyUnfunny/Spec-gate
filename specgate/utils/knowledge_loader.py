import re
from dataclasses import dataclass
from pathlib import Path


WIKILINK_PATTERN = re.compile(r"\[\[([^\[\]|#]+)(?:#[^\[\]|]+)?(?:\|[^\[\]]+)?\]\]")


@dataclass(frozen=True)
class KnowledgeDocument:
    title: str
    path: Path
    content: str


class KnowledgeLoader:
    """
    Resolves Obsidian-style WikiLinks from SPEC.md into markdown snippets.
    """

    def __init__(self, project_root: str, knowledge_base: str, max_chars_per_doc: int = 4000):
        self.project_root = Path(project_root)
        self.knowledge_base = (self.project_root / knowledge_base).resolve()
        self.max_chars_per_doc = max_chars_per_doc

    def extract_wikilinks(self, markdown: str) -> list[str]:
        seen: set[str] = set()
        links: list[str] = []

        for match in WIKILINK_PATTERN.finditer(markdown):
            title = match.group(1).strip()
            if title and title not in seen:
                links.append(title)
                seen.add(title)

        return links

    def load_linked_documents(self, spec_markdown: str) -> list[KnowledgeDocument]:
        documents: list[KnowledgeDocument] = []

        for title in self.extract_wikilinks(spec_markdown):
            path = self._resolve_markdown_path(title)
            if not path:
                continue

            content = path.read_text(encoding="utf-8")[: self.max_chars_per_doc]
            documents.append(KnowledgeDocument(title=title, path=path, content=content))

        return documents

    def format_for_prompt(self, documents: list[KnowledgeDocument]) -> str:
        if not documents:
            return ""

        blocks = ["JIT KNOWLEDGE CONTEXT:"]
        for document in documents:
            rel_path = document.path.relative_to(self.project_root)
            blocks.append(f"\n--- {document.title} ({rel_path}) ---\n{document.content}")

        return "\n".join(blocks)

    def _resolve_markdown_path(self, title: str) -> Path | None:
        candidates = [
            self.knowledge_base / f"{title}.md",
            self.knowledge_base / title,
        ]

        slug = title.replace(" ", "-")
        if slug != title:
            candidates.append(self.knowledge_base / f"{slug}.md")

        for candidate in candidates:
            resolved = candidate.resolve()
            if not self._is_inside_knowledge_base(resolved):
                continue
            if resolved.is_file() and resolved.suffix.lower() == ".md":
                return resolved

        return None

    def _is_inside_knowledge_base(self, path: Path) -> bool:
        try:
            path.relative_to(self.knowledge_base)
        except ValueError:
            return False
        return True
