#!/usr/bin/env python3
"""MCP server for TypeScript Language Server."""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, field_validator, ConfigDict

from lsp_client import LSPClient

# Get project root from env or current directory
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", ".")).absolute()

# Global LSP client (initialized in lifespan)
lsp_client = None


@asynccontextmanager
async def app_lifespan(app):
    """Manage LSP client lifecycle."""
    global lsp_client
    lsp_client = LSPClient(str(PROJECT_ROOT))
    yield {"lsp": lsp_client}
    lsp_client.close()


mcp = FastMCP("w3-lsp", lifespan=app_lifespan)


class LSPInput(BaseModel):
    """Input for LSP operations.

    IMPORTANT: Line and character are 0-indexed (start from 0, not 1).

    Line conversion:
    - Editor shows: Ln 5
    - Use in tool: line: 4
    - Formula: lsp_line = editor_line - 1

    Character conversion (0-indexed within each line):
    - Example: const greeting = "Hello";
    - Position at 'c' in const → character: 0
    - Position at 'o' in const → character: 1
    - Position at 'g' in greeting → character: 6
    - Position at 'H' in "Hello" → character: 18
    - Editor shows: Col 10 → Use: character: 9
    - Formula: lsp_char = editor_col - 1
    """
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    file_path: str = Field(
        ...,
        description="Path to JavaScript/TypeScript file (relative to project root). Example: 'src/app.ts' or 'index.js'",
        min_length=1,
        max_length=500,
    )
    line: int = Field(
        ...,
        description="Line number (0-indexed). If editor shows Ln 5, use line: 4",
        ge=0,
    )
    character: int = Field(
        ...,
        description="Character position in line (0-indexed). Count from start: 'const' has character 0,1,2,3,4. If editor shows Col 10, use character: 9",
        ge=0,
    )

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("File path cannot be empty")
        return v.strip()


def format_location(location: dict) -> str:
    """Format location dict as readable string."""
    if not location:
        return "Not found"
    uri = location.get("uri", "").replace("file://", "")
    start = location.get("range", {}).get("start", {})
    line = start.get("line", 0) + 1
    char = start.get("character", 0)
    return f"{uri}:{line}:{char}"


@mcp.tool(
    name="lsp_goto_definition",
    annotations={
        "title": "Go to Definition",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def lsp_goto_definition(params: LSPInput, ctx: Context) -> str:
    """Jump to symbol definition location.

    Line and character numbers are 0-indexed. See LSPInput for conversion details.

    Args:
        params (LSPInput): File path, line, and character position (both 0-indexed)

    Returns:
        str: Location of definition (file:line:column) or "Definition not found"

    Example:
        {"file_path": "src/app.ts", "line": 4, "character": 9}
    """
    try:
        lsp = lsp_client
        full_path = PROJECT_ROOT / params.file_path

        if full_path.exists():
            with open(full_path, "r") as f:
                content = f.read()
            lang_id = "typescript" if params.file_path.endswith(".ts") else "javascript"
            lsp.open_document(str(full_path), lang_id, content)

        result = lsp.goto_definition(str(full_path), params.line, params.character)
        return format_location(result) if result else "Definition not found"
    except Exception as e:
        await ctx.error(f"Failed to get definition: {str(e)}")
        return f"Error: {str(e)}"


@mcp.tool(
    name="lsp_hover",
    annotations={
        "title": "Hover Information",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def lsp_hover(params: LSPInput, ctx: Context) -> str:
    """Get type information and documentation for symbol at position.

    Line and character numbers are 0-indexed. See LSPInput for conversion details.

    Args:
        params (LSPInput): File path, line, and character position (both 0-indexed)

    Returns:
        str: Type signature, documentation, or "No info available"

    Example:
        {"file_path": "src/app.ts", "line": 4, "character": 9}
    """
    try:
        lsp = lsp_client
        full_path = PROJECT_ROOT / params.file_path

        if full_path.exists():
            with open(full_path, "r") as f:
                content = f.read()
            lang_id = "typescript" if params.file_path.endswith(".ts") else "javascript"
            lsp.open_document(str(full_path), lang_id, content)

        result = lsp.hover(str(full_path), params.line, params.character)
        if result and "contents" in result:
            contents = result["contents"]
            return contents.get("value", str(contents)) if isinstance(contents, dict) else str(contents)
        return "No info available"
    except Exception as e:
        await ctx.error(f"Failed to get hover info: {str(e)}")
        return f"Error: {str(e)}"


@mcp.tool(
    name="lsp_find_references",
    annotations={
        "title": "Find References",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def lsp_find_references(params: LSPInput, ctx: Context) -> str:
    """Find all usages/references of symbol at position.

    Line and character numbers are 0-indexed. See LSPInput for conversion details.

    Args:
        params (LSPInput): File path, line, and character position (both 0-indexed)

    Returns:
        str: List of all references found (file:line:column), or "No references found"

    Example:
        {"file_path": "src/app.ts", "line": 4, "character": 9}
    """
    try:
        lsp = lsp_client
        full_path = PROJECT_ROOT / params.file_path

        if full_path.exists():
            with open(full_path, "r") as f:
                content = f.read()
            lang_id = "typescript" if params.file_path.endswith(".ts") else "javascript"
            lsp.open_document(str(full_path), lang_id, content)

        result = lsp.find_references(str(full_path), params.line, params.character)
        if result:
            refs = [format_location(loc) for loc in result]
            return f"Found {len(refs)} references:\n" + "\n".join(refs)
        return "No references found"
    except Exception as e:
        await ctx.error(f"Failed to find references: {str(e)}")
        return f"Error: {str(e)}"


def main():
    """Entry point for the MCP server."""
    try:
        mcp.run()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass


if __name__ == "__main__":
    main()

