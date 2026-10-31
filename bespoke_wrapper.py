"""The traditional (pre-MCP) approach, for comparison.

Without MCP, every AI application that wants these PyPI capabilities writes
its own integration layer: tool schemas in the format its model vendor
expects, plus a dispatcher that routes the model's tool calls to the REST
API. Below are the layers two different applications would each need.
A third application (or a new model vendor) means writing a third copy.

Nothing here calls a model; it is the code an application would wire into
its function-calling loop.
"""

import asyncio
import json

import pypi_api

# ------------------------------------------------------------------------
# Application A: uses an OpenAI-style function-calling schema
# ------------------------------------------------------------------------

APP_A_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_package",
            "description": "Get the latest version, summary, licence, supported Python versions "
                           "and dependencies of a Python package on PyPI.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Package name"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_releases",
            "description": "List the most recent releases of a PyPI package, newest first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_packages",
            "description": "Compare two or more PyPI packages side by side.",
            "parameters": {
                "type": "object",
                "properties": {"names": {"type": "array", "items": {"type": "string"}}},
                "required": ["names"],
            },
        },
    },
]


async def app_a_dispatch(tool_call: dict) -> str:
    """Route one OpenAI-style tool call to the REST API; return JSON text."""
    fn = tool_call["function"]
    args = json.loads(fn["arguments"])
    try:
        if fn["name"] == "get_package":
            result = pypi_api.summarise(await pypi_api.fetch_package(args["name"]))
        elif fn["name"] == "list_releases":
            data = await pypi_api.fetch_package(args["name"])
            result = pypi_api.releases(data, args.get("limit", 10))
        elif fn["name"] == "compare_packages":
            result = []
            for n in args["names"]:
                s = pypi_api.summarise(await pypi_api.fetch_package(n))
                result.append({"name": s["name"], "latest_version": s["latest_version"],
                               "license": s["license"], "dependency_count": len(s["dependencies"])})
        else:
            return json.dumps({"error": f"unknown tool {fn['name']}"})
    except pypi_api.PackageNotFound as e:
        return json.dumps({"error": str(e)})
    return json.dumps(result)


# ------------------------------------------------------------------------
# Application B: uses an Anthropic-style tool schema
# (same capabilities, different envelope, so it is rewritten)
# ------------------------------------------------------------------------

APP_B_TOOLS = [
    {
        "name": "get_package",
        "description": "Get the latest version, summary, licence, supported Python versions "
                       "and dependencies of a Python package on PyPI.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Package name"}},
            "required": ["name"],
        },
    },
    {
        "name": "list_releases",
        "description": "List the most recent releases of a PyPI package, newest first.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
            "required": ["name"],
        },
    },
    {
        "name": "compare_packages",
        "description": "Compare two or more PyPI packages side by side.",
        "input_schema": {
            "type": "object",
            "properties": {"names": {"type": "array", "items": {"type": "string"}}},
            "required": ["names"],
        },
    },
]


async def app_b_dispatch(tool_use: dict) -> dict:
    """Route one Anthropic-style tool_use block; return a tool_result block."""
    name, args = tool_use["name"], tool_use["input"]
    try:
        if name == "get_package":
            result = pypi_api.summarise(await pypi_api.fetch_package(args["name"]))
        elif name == "list_releases":
            data = await pypi_api.fetch_package(args["name"])
            result = pypi_api.releases(data, args.get("limit", 10))
        elif name == "compare_packages":
            result = []
            for n in args["names"]:
                s = pypi_api.summarise(await pypi_api.fetch_package(n))
                result.append({"name": s["name"], "latest_version": s["latest_version"],
                               "license": s["license"], "dependency_count": len(s["dependencies"])})
        else:
            return {"type": "tool_result", "tool_use_id": tool_use["id"],
                    "content": f"unknown tool {name}", "is_error": True}
    except pypi_api.PackageNotFound as e:
        return {"type": "tool_result", "tool_use_id": tool_use["id"], "content": str(e), "is_error": True}
    return {"type": "tool_result", "tool_use_id": tool_use["id"], "content": json.dumps(result)}


# ------------------------------------------------------------------------
# Quick self-test: simulate one tool call from each application
# ------------------------------------------------------------------------

async def _demo():
    a = await app_a_dispatch({"function": {"name": "get_package", "arguments": '{"name": "httpx"}'}})
    print("App A ->", a[:120], "...")
    b = await app_b_dispatch({"id": "toolu_1", "name": "list_releases", "input": {"name": "httpx", "limit": 3}})
    print("App B ->", b)


if __name__ == "__main__":
    asyncio.run(_demo())
