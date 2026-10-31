"""Test client: launches server.py over stdio and exercises it the way a host would.

Shows runtime discovery (paper, Section 5.4): the client learns the tools,
their descriptions and input schemas from the server, with nothing hard-coded.

    python client.py
"""

import asyncio
import json
import os
import sys

from mcp import Client, StdioServerParameters


async def main():
    # The SDK starts stdio servers with a minimal environment; pass ours through so
    # proxy and certificate settings (if your network needs them) still apply.
    params = StdioServerParameters(command=sys.executable, args=["server.py"], env=dict(os.environ))
    async with Client(params) as client:
        # 1. Discovery: what can this server do?
        tools = await client.list_tools()
        print(f"Discovered {len(tools.tools)} tools:")
        for t in tools.tools:
            print(f"  - {t.name}: {t.description.split('.')[0]}.")
            print(f"      input schema: {json.dumps(t.input_schema)}")

        templates = await client.list_resource_templates()
        print(f"\nResource templates: {[r.uri_template for r in templates.resource_templates]}")

        prompts = await client.list_prompts()
        print(f"Prompts: {[p.name for p in prompts.prompts]}")

        # 2. Invocation: call a tool exactly as a host would after the model picks it.
        print("\nCalling compare_packages(['httpx', 'requests']) ...")
        result = await client.call_tool("compare_packages", {"names": ["httpx", "requests"]})
        for block in result.content:
            print(block.text if hasattr(block, "text") else block)

        print("\nCalling list_releases('mcp', limit=3) ...")
        result = await client.call_tool("list_releases", {"name": "mcp", "limit": 3})
        for block in result.content:
            print(block.text if hasattr(block, "text") else block)

        # 3. Error path: a package that does not exist.
        print("\nCalling get_package('this-package-does-not-exist-xyz') ...")
        result = await client.call_tool("get_package", {"name": "this-package-does-not-exist-xyz"})
        print("is_error:", result.is_error, "|", result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
