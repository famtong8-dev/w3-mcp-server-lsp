---
name: w3-mcp-server-lsp
description: Find symbol positions with ripgrep, then use w3-mcp-server-lsp MCP tools for code intelligence
user-invocable: true
---

# Find Symbol with Ripgrep + MCP

Combine ripgrep search with w3-mcp-server-lsp for fast symbol location finding.

## Get PROJECT_ROOT

```bash
# Priority order:
PROJECT_ROOT=${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}
```

## Quick Command

```bash
rg <symbol> <file> --line-number --column --no-heading | cut -d: -f1,2
```

**Example:**
```bash
rg updateArtifactStatistic app/controllers/artifactStudy.js --line-number --column --no-heading | cut -d: -f1,2
# Output:
# 7:31
# 51:13
```

## Convert to MCP Format

Ripgrep outputs **1-indexed** (editor format), MCP needs **0-indexed**:

| Output | Line | Char | MCP (0-indexed) |
|--------|------|------|-----------------|
| 7:31   | 7-1  | 31-1 | line: 6, character: 30 |
| 51:13  | 51-1 | 13-1 | line: 50, character: 12 |

## Use with MCP

Pass converted values to:
- `lsp_goto_definition` - Jump to definition
- `lsp_hover` - Get type info
- `lsp_find_references` - Find usages

## Requirements

- Ripgrep installed: `rg`
- File path relative to PROJECT_ROOT
- Correct 0-indexed conversion (subtract 1)
