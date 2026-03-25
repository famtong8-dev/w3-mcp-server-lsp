# W3 MCP LSP Server

Python MCP server wrapping TypeScript Language Server for JavaScript/TypeScript code intelligence.

**Status:** ✅ Working with real LSP protocol (not mock)

## Features

- **lsp_goto_definition** - Jump to symbol definition location
- **lsp_hover** - Get type information and documentation
- **lsp_find_references** - Find all references/usages of symbol

Supports JavaScript and TypeScript files via TypeScript Language Server.

## Quick Start

### 1. Clean Setup (Important!)

```bash
cd /path/to/w3-mcp-server-lsp

# Remove old lockfile and venv
rm -rf uv.lock .venv venv

# Unset old environment variable
unset VIRTUAL_ENV
```

### 2. Install Dependencies

```bash
# Install TypeScript Language Server
npm install -g typescript typescript-language-server

# Install Python dependencies (using uv)
uv sync

# Install MCP CLI dependencies
uv pip install 'mcp[cli]'
```

### 3. Verify Installation

```bash
# Check typescript-language-server
which typescript-language-server
typescript-language-server --version

# Check Python env
uv run python -c "from mcp.server.fastmcp import FastMCP; print('✓ MCP ready')"
```

### 4. Test with MCP Inspector

```bash
# Start MCP Inspector (interactive web UI)
uv run mcp dev server.py
```

Opens URL like:

```text
http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...
```

Features:

- ✅ Available tools listed in sidebar
- ✅ Test each tool interactively with JSON input
- ✅ Real-time request/response viewing
- ✅ Server logs and debugging
- ✅ No extra dependencies needed

## Usage

### Option A: MCP Inspector (Development)

Best way to test and debug:

```bash
cd /path/to/w3-mcp-server-lsp

# Start inspector
uv run mcp dev server.py
```

Opens web UI at `http://localhost:5173`:

- See available tools
- Test each tool with JSON input
- View request/response in real-time
- See server logs

### Option B: Direct Python

```bash
# Run server (stdio mode)
uv run python server.py
```

### Option C: Claude Code Integration

#### Method 1: From PyPI (Recommended)

Install from PyPI:

```bash
pip install w3-mcp-server-lsp
# or
uv pip install w3-mcp-server-lsp
```

Edit `~/.claude/claude_config.json` or `~/.mcp.json`:

```json
{
  "mcpServers": {
    "w3-lsp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--with", "w3-mcp-server-lsp", "w3-mcp-server-lsp"],
      "env": {
        "PROJECT_ROOT": "/path/to/your/project"
      }
    }
  }
}
```

**Advantages:**

- ✅ No need to clone the repo
- ✅ Easy version management
- ✅ Automatic dependency isolation

#### Method 2: From Local Source

Edit `~/.claude/claude_config.json`:

```json
{
  "mcpServers": {
    "w3-lsp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "server.py"],
      "cwd": "/path/to/w3-mcp-server-lsp",
      "env": {
        "PROJECT_ROOT": "/path/to/your/project"
      }
    }
  }
}
```

Then restart Claude Code.

## Tools Documentation

### ⚠️ IMPORTANT: 0-Indexed Line and Character Numbers

All tools use **0-indexed** positioning (start from 0, not 1):

| Editor Display | Tool Input | Formula                      |
| -------------- | ---------- | ---------------------------- |
| Ln 5, Col 10   | line: 4    | lsp_value = editor_value - 1 |
| Ln 1, Col 1    | line: 0    | character: 0                 |
| Ln 10, Col 5   | line: 9    | character: 4                 |

**Quick Reference:**

- Line 1 in editor = `line: 0` in tool
- Column 1 in editor = `character: 0` in tool

**How to Calculate Character Position:**

Given this code line:

```javascript
const greeting = "Hello";
0123456789...
```

- Position at `c` in `const` → `character: 0`
- Position at `o` in `const` → `character: 1`
- Position at `g` in `greeting` → `character: 6`
- Position at `H` in `"Hello"` → `character: 18`

**In VSCode:**

- Click on a character
- Look at status bar: `Ln X, Col Y`
- Use: `line: X-1, character: Y-1`

---

### lsp_goto_definition

Jump to definition of symbol at specified position.

**Input:**

```json
{
  "file_path": "fixtures/sample.js",
  "line": 4,
  "character": 9
}
```

**Output:**

```text
/path/to/fixtures/sample.js:5:9
```

---

### lsp_hover

Get type information and documentation for symbol.

**Input:**

```json
{
  "file_path": "fixtures/sample.js",
  "line": 5,
  "character": 10
}
```

**Output:**

```typescript
(parameter) a: any
```

---

### lsp_find_references

Find all references/usages of symbol.

**Input:**

```json
{
  "file_path": "fixtures/sample.js",
  "line": 4,
  "character": 9
}
```

**Output:**

```text
Found 2 references:
/path/to/fixtures/sample.js:5:9
/path/to/fixtures/sample.js:14:22
```

## Configuration

### PROJECT_ROOT

Specifies the root directory of your project. Files paths in tool calls are relative to this.

**Set via:**

1. **Environment variable:**

   ```bash
   export PROJECT_ROOT="/path/to/your/project"
   uv run python server.py
   ```

2. **Current directory (default):**

   ```bash
   cd /path/to/your/project
   uv run python /path/to/w3-mcp-server-lsp/server.py
   ```

3. **In .claude/settings.json:**

   ```json
   "env": {
     "PROJECT_ROOT": "/path/to/your/project"
   }
   ```

### Line and Character Numbers (0-indexed)

LSP uses 0-indexed positions:

- VSCode shows: `Ln 5, Col 10`
- LSP needs: `line: 4, character: 9`

**Formula:** `lsp_value = vscode_value - 1`

## Project Structure

```text
w3-mcp-server-lsp/
├── server.py           # MCP server entry point
├── lsp_client.py       # LSP protocol implementation
├── pyproject.toml      # Project config
├── fixtures/
│   └── sample.js       # Sample file for testing
├── test_mcp_server.py  # Integration test
├── test_lsp_debug.py   # Debug test with logging
└── README.md
```

## How It Works

### Architecture

```text
MCP Client (Claude, IDE, etc.)
    ↓
MCP Server (server.py)
    ↓
LSP Client (lsp_client.py)
    ↓
TypeScript Language Server (subprocess)
```

### LSP Protocol Flow

1. **Initialization**
   - Send: `initialize` request
   - Receive: server capabilities
   - Send: `initialized` notification

2. **Document Opening**
   - Send: `textDocument/didOpen` notification
   - Content provided inline

3. **Queries**
   - Send: `textDocument/definition`, `textDocument/hover`, etc.
   - Receive: results from language server

4. **Details**
   - Communication: JSON-RPC over stdin/stdout
   - Binary mode: Avoids text encoding issues
   - Notification handling: Skip server notifications, match message IDs

## Testing

### Interactive Testing (Recommended)

```bash
uv run mcp dev server.py
```

Web UI opens at `http://localhost:5173`:

- Test tools visually
- See real-time results
- View server logs

### Direct Server

```bash
uv run python server.py
```

Runs in stdio mode, ready to connect from Claude Code or other MCP clients.

## Troubleshooting

### TypeScript Language Server not found

```bash
# Install
npm install -g typescript typescript-language-server

# Verify
which typescript-language-server
```

### MCP module not found

```bash
# Install dependencies
pip install -e .

# Or manually
pip install mcp pydantic
```

### Server hangs on startup

- Check if TypeScript Language Server is installed
- Check terminal for error messages
- Try: `typescript-language-server --stdio` directly

### Tool returns `None` or error

- Verify file path is relative to PROJECT_ROOT
- Check line/character numbers are 0-indexed
- Check server logs output in terminal
- Use MCP Inspector (`uv run mcp dev server.py`) to see requests/responses

## Future Enhancements

- [ ] Go support (gopls language server)
- [ ] Python support (pylsp/pyright)
- [ ] Multiple language servers in single MCP server
- [ ] Caching of responses
- [ ] Batch operations

## Development

### Testing with MCP Inspector

```bash
uv run mcp dev server.py
```

Web UI at `http://localhost:5173` shows:

- Available tools and schemas
- Real-time request/response
- Server logs
- Interactive testing

### Running Directly

```bash
uv run python server.py
```

For debugging, check logs output in terminal.

## References

- [Language Server Protocol](https://microsoft.github.io/language-server-protocol/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [TypeScript Language Server](https://github.com/typescript-language-server/typescript-language-server)
- [FastMCP](https://github.com/anthropics/mcp-fastmcp)

## License

MIT
