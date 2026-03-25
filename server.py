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
    """Input for LSP operations."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    file_path: str = Field(
        ...,
        description="Path to JavaScript/TypeScript file (relative to project root)",
        min_length=1,
        max_length=500,
    )
    line: int = Field(
        ...,
        description="Line number (0-indexed)",
        ge=0,
    )
    character: int = Field(
        ...,
        description="Character position (0-indexed)",
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
    """Go to definition of symbol at position.

    Args:
        params (LSPInput): File path, line, and character position

    Returns:
        str: Location of definition or error message
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
    """Get type and documentation info for symbol.

    Args:
        params (LSPInput): File path, line, and character position

    Returns:
        str: Type info and documentation or error message
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
    """Find all references to symbol.

    Args:
        params (LSPInput): File path, line, and character position

    Returns:
        str: List of references or error message
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

