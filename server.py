"""PyPI Explorer: a small MCP server that wraps the PyPI JSON REST API.

It exposes all three MCP primitives discussed in the paper (Section 5.2):
  - Tools     (model-controlled):       get_package, list_releases, compare_packages
  - Resources (application-controlled): pypi://{name}/description
  - Prompts   (user-controlled):        dependency_audit

Run it over stdio (how Claude Desktop and most hosts launch local servers):
    python server.py
"""

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

import pypi_api

server = MCPServer(
    name="pypi-explorer",
    instructions="Look up Python packages on PyPI: versions, licences, dependencies and release history.",
)


async def _fetch(name: str) -> dict:
    """Fetch a package, turning 'not found' into a clean error the model can read."""
    try:
        return await pypi_api.fetch_package(name)
    except pypi_api.PackageNotFound as e:
        raise ToolError(str(e)) from e


# ---------------------------------------------------------------- tools
# The docstring becomes the tool description the LLM reads, and the type
# hints become the JSON input schema. This is the "description written for
# the model" that plain REST APIs lack (paper, Section 4.2).


@server.tool()
async def get_package(name: str) -> dict:
    """Get the latest version, summary, licence, supported Python versions and
    dependencies of a Python package on PyPI. Use this when the user asks what a
    package is, which version is current, or what it depends on."""
    return pypi_api.summarise(await _fetch(name))


@server.tool()
async def list_releases(name: str, limit: int = 10) -> list[dict]:
    """List the most recent releases of a PyPI package, newest first, with the
    date each was uploaded. Use this for questions about release history or how
    actively a package is maintained."""
    return pypi_api.releases(await _fetch(name), limit)


@server.tool()
async def compare_packages(names: list[str]) -> list[dict]:
    """Compare two or more PyPI packages side by side (latest version, licence,
    Python requirement, number of dependencies). Use this when the user is
    choosing between alternative libraries."""
    rows = []
    for name in names:
        s = pypi_api.summarise(await _fetch(name))
        rows.append({
            "name": s["name"],
            "latest_version": s["latest_version"],
            "license": s["license"],
            "requires_python": s["requires_python"],
            "dependency_count": len(s["dependencies"]),
        })
    return rows


# ------------------------------------------------------------ resources


@server.resource("pypi://{name}/description", mime_type="text/markdown")
async def package_description(name: str) -> str:
    """The full long description (usually the README) of a PyPI package."""
    data = await _fetch(name)
    return data["info"].get("description") or "(no description published)"


# --------------------------------------------------------------- prompts


@server.prompt()
def dependency_audit(package: str) -> str:
    """Audit a package's dependencies before adopting it."""
    return (
        f"Use the PyPI tools to audit the Python package '{package}'. "
        "Report its latest version, licence and supported Python versions, "
        "list its direct dependencies, and check how recently it was released. "
        "Finish with a one-paragraph recommendation on whether it looks safe to adopt."
    )


if __name__ == "__main__":
    server.run()  # stdio transport by default
