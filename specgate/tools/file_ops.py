from langchain_core.tools import tool
from pydantic import BaseModel, Field
from pathlib import Path


class ReplaceBlockArgs(BaseModel):
    filepath: str = Field(..., description = "Path to the file to modify, relative to project root.")
    search_block: str = Field(..., description="The exact existing lines of code to be replaced. Must match character-for-character.")
    replace_block: str = Field(..., description="The new lines of code to insert in place of the search_block.")

@tool("replace_content_block", args_schema=ReplaceBlockArgs)
def replace_content_block(filepath: str, search_block: str, replace_block: str) -> str:
    """
    Custom tool to replace specific block of content in a file
    WriteTool and ModifyTool can waste token by overriding the whole file
    """

    target_file = Path(filepath)

    if not target_file.exists():
        return f"Error: File {filepath} does not exist. Use create_file tool to create a file first"

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
    target_file = Path(filepath)
    if target_file.exists():
        return f"Error: File {filepath} already exists. Use replace_content_block to modify it."
    
    target_file.parent.mkdir(parents = True, exist_ok = True)
    target_file.write_text(initial_content, encoding = "utf-8")
    return f"Success: Created {filepath}"