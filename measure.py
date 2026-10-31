"""Count the integration code each approach needs, for the paper's case study.

Counts non-blank, non-comment source lines (docstrings included, because tool
descriptions are part of the integration) for:
  - MCP:     the error helper + the three tool functions in server.py (written ONCE)
  - Bespoke: each application's tool schemas + dispatcher in bespoke_wrapper.py
             (written once PER APPLICATION)

The shared REST client (pypi_api.py) is identical for both and is excluded.

    python measure.py
"""

import ast
from pathlib import Path


def loc_of(path: str, names: set[str]) -> int:
    src = Path(path).read_text().splitlines()
    tree = ast.parse("\n".join(src))
    total = 0
    for node in tree.body:
        name = getattr(node, "name", None)
        if name is None and isinstance(node, ast.Assign):
            name = node.targets[0].id
        if name in names:
            start = min([d.lineno for d in getattr(node, "decorator_list", [])] + [node.lineno])
            for line in src[start - 1 : node.end_lineno]:
                s = line.strip()
                if s and not s.startswith("#"):
                    total += 1
    return total


mcp_server = loc_of("server.py", {"_fetch", "get_package", "list_releases", "compare_packages"})
app_a = loc_of("bespoke_wrapper.py", {"APP_A_TOOLS", "app_a_dispatch"})
app_b = loc_of("bespoke_wrapper.py", {"APP_B_TOOLS", "app_b_dispatch"})
per_app = round((app_a + app_b) / 2)

print("Integration code for 3 PyPI tools (lines, excluding blanks and comments)\n")
print(f"  MCP server, written once ............ {mcp_server}")
print(f"  Bespoke layer, application A ........ {app_a}")
print(f"  Bespoke layer, application B ........ {app_b}")
print(f"\nProjected total as the number of AI applications (N) grows, one tool provider (M = 1):")
print(f"  {'N':>3} | {'bespoke (N x ~' + str(per_app) + ')':>22} | {'MCP (server once)':>18}")
for n in (1, 2, 3, 5, 10):
    print(f"  {n:>3} | {n * per_app:>22} | {mcp_server:>18}")
print("\nNote: MCP hosts already contain a client, so each extra application adds no PyPI-specific code.")
