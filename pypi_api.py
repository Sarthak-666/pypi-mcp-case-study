"""Thin client for the public PyPI JSON REST API (no API key needed).

Both the MCP server and the bespoke baseline import this module, so the
comparison in the case study measures only the *integration layer* each
approach needs on top of the same REST calls.

API docs: https://docs.pypi.org/api/json/
"""

import httpx

BASE_URL = "https://pypi.org/pypi"
TIMEOUT = 15.0


class PackageNotFound(Exception):
    pass


async def fetch_package(name: str) -> dict:
    """GET /pypi/<name>/json and return the decoded JSON body."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}/{name}/json")
    if resp.status_code == 404:
        raise PackageNotFound(f"No package named '{name}' on PyPI")
    resp.raise_for_status()
    return resp.json()


def summarise(data: dict) -> dict:
    """Pick the fields a person (or a model) actually needs."""
    info = data["info"]
    return {
        "name": info["name"],
        "latest_version": info["version"],
        "summary": info.get("summary") or "",
        "license": info.get("license_expression") or info.get("license") or "unknown",
        "requires_python": info.get("requires_python") or "any",
        "home_page": info.get("home_page") or (info.get("project_urls") or {}).get("Homepage", ""),
        "dependencies": info.get("requires_dist") or [],
    }


def releases(data: dict, limit: int) -> list[dict]:
    """Most recent releases first, with their upload date."""
    out = []
    for version, files in data["releases"].items():
        if not files:
            continue
        uploaded = min(f["upload_time_iso_8601"] for f in files)
        out.append({"version": version, "uploaded": uploaded[:10]})
    out.sort(key=lambda r: r["uploaded"], reverse=True)
    return out[:limit]
