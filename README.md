# PyPI Explorer: a small MCP case study

A minimal MCP server that wraps a real REST API (the public PyPI JSON API), plus the
equivalent hand-written integration two AI applications would each need without MCP.
Built as the case study for *The Evolution of AI Tool Integration: MCP vs. Traditional
API Architectures*.

| File | What it is |
| --- | --- |
| `pypi_api.py` | Shared REST client for `https://pypi.org/pypi/<name>/json` (used by both approaches) |
| `server.py` | The MCP server: 3 tools, 1 resource template, 1 prompt |
| `bespoke_wrapper.py` | The traditional approach: tool schemas + dispatcher, written separately for two apps |
| `client.py` | Test client: launches the server, discovers its capabilities, calls tools |
| `measure.py` | Counts the integration code each approach needs |

## 1. Set up (5 minutes)

Needs Python 3.10 or newer.

```bash
cd pypi-mcp-case-study
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

This installs the official MCP Python SDK. In SDK version 2.x the high-level server class is
`MCPServer` (`from mcp.server.mcpserver import MCPServer`). Older tutorials call it `FastMCP`;
that name was removed in 2.0, so copy-pasted 1.x code will fail to import.

## 2. Run it

```bash
python client.py           # discovery + three tool calls, including an error case
python bespoke_wrapper.py  # the same calls through the hand-written layers
python measure.py          # integration line counts for the paper
```

`client.py` should print three tools with their descriptions and JSON input schemas, the
resource template `pypi://{name}/description`, the prompt `dependency_audit`, then real results
from PyPI and a clean "No package named ..." error.

## 3. Use it from a real AI app (optional, good for a screenshot)

**Claude Desktop:** open Settings → Developer → Edit Config (or open
`claude_desktop_config.json` directly: `%APPDATA%\Claude\` on Windows,
`~/Library/Application Support/Claude/` on macOS) and add:

```json
{
  "mcpServers": {
    "pypi-explorer": {
      "command": "C:/full/path/to/pypi-mcp-case-study/.venv/Scripts/python.exe",
      "args": ["C:/full/path/to/pypi-mcp-case-study/server.py"]
    }
  }
}
```

On macOS/Linux the command is `/full/path/to/.venv/bin/python`. Restart Claude Desktop and ask
"Compare httpx and requests on PyPI". It should call `compare_packages` without any code in
Claude Desktop knowing about PyPI. That is the N+M property from Section 3 of the paper.

**MCP Inspector** (a browser UI for testing servers; needs Node.js):

```bash
npx @modelcontextprotocol/inspector python server.py
```

## 4. Results

| Integration layer for the same 3 tools | Lines (no blanks/comments) |
| --- | --- |
| MCP server (written once) | 34 |
| Bespoke layer, application A (OpenAI-style schema) | 63 |
| Bespoke layer, application B (Anthropic-style schema) | 51 |

With N applications the bespoke approach needs roughly N × 57 lines, and MCP stays at 34.
Run `python measure.py` to reproduce these numbers.

**Caveats:**
- Lines of code is a rough proxy for effort, not a measure of it.
- The MCP server is shorter partly because the SDK generates input schemas from Python type hints.
  That is a real benefit of the protocol tooling, but it is not the same as less integration work.
- The bespoke baseline was written for this comparison, not taken from a production system.
- MCP hosts already contain a client, so the "+N" side of N+M is paid by the host vendors.
- This covers one tool provider. It says nothing about security or context-window cost.

## 5. Try it yourself: add a tool

Add this to `server.py` and rerun `client.py`. It is discovered automatically, with no change to
the client:

```python
@server.tool()
async def get_dependencies(name: str) -> list[str]:
    """List the direct dependencies of a PyPI package. Use this when the user asks
    what a package needs installed."""
    return pypi_api.summarise(await _fetch(name))["dependencies"]
```

Then add the same tool to both apps in `bespoke_wrapper.py` (a schema entry in each tools list
and a branch in each dispatcher), and compare how many places you had to edit in each approach.
