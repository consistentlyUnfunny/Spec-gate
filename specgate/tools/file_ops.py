from langchain_core.tools import tool
from pydantic import BaseModel, Field
from pathlib import Path

WORKSPACE_ROOT = Path(".").resolve()


def configure_workspace(root: str) -> None:
    global WORKSPACE_ROOT
    WORKSPACE_ROOT = Path(root).resolve()
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)


def resolve_workspace_path(filepath: str) -> Path:
    target_file = (WORKSPACE_ROOT / filepath).resolve()
    try:
        target_file.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise ValueError(f"Path {filepath} escapes configured work_dir.") from exc
    return target_file


class ReplaceBlockArgs(BaseModel):
    filepath: str = Field(..., description = "Path to the file to modify, relative to the configured work_dir.")
    search_block: str = Field(..., description="The exact existing lines of code to be replaced. Must match character-for-character.")
    replace_block: str = Field(..., description="The new lines of code to insert in place of the search_block.")

@tool("replace_content_block", args_schema=ReplaceBlockArgs)
def replace_content_block(filepath: str, search_block: str, replace_block: str) -> str:
    """
    Custom tool to replace specific block of content in a file
    WriteTool and ModifyTool can waste token by overriding the whole file
    """

    try:
        target_file = resolve_workspace_path(filepath)
    except ValueError as exc:
        return f"Error: {exc}"

    if not target_file.exists():
        return f"Error: File {filepath} does not exist inside {WORKSPACE_ROOT}. Use create_file tool to create a file first"

    content = target_file.read_text(encoding = "utf-8")

    if search_block not in content:
        return f"Error: 'search_block' not found in {filepath}. Must provide exact match of existing content, including whitespace and indentation"
    
    new_content = content.replace(search_block, replace_block, 1)
    target_file.write_text(new_content, encoding = "utf-8")

    return f"Success: Modified {filepath}"


@tool
def create_file(filepath: str, initial_content: str) -> str:
    """
    Create a new file with initial content
    """
    try:
        target_file = resolve_workspace_path(filepath)
    except ValueError as exc:
        return f"Error: {exc}"

    if target_file.exists():
        return f"Error: File {filepath} already exists. Use replace_content_block to modify it."
    
    target_file.parent.mkdir(parents = True, exist_ok = True)
    target_file.write_text(initial_content, encoding = "utf-8")
    return f"Success: Created {filepath}"
