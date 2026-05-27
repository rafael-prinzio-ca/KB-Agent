"""Local MCP server for Looker.

Reads Looker dashboards/looks and returns metadata + SQL for each tile so
that `/create-kb` can compile a KB from existing Looker assets.

Auth: env vars LOOKERSDK_BASE_URL, LOOKERSDK_CLIENT_ID, LOOKERSDK_CLIENT_SECRET
(standard looker-sdk conventions). Configure via the project's `.env`; the
`setup-mcp.sh` script injects them into the MCP server process.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

# Use the Windows/macOS/Linux system certificate store so corporate proxy
# CA certificates are trusted without disabling verification entirely.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import looker_sdk
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("looker-local")

_DASHBOARD_RE = re.compile(r"/dashboards(?:/lookml)?/([\w-]+)", re.IGNORECASE)
_LOOK_RE = re.compile(r"/looks/(\d+)", re.IGNORECASE)


def _sdk() -> "looker_sdk.sdk.api40.methods.Looker40SDK":
    return looker_sdk.init40()


def _extract_dashboard_id(url_or_id: str) -> str:
    if "/" not in url_or_id and ":" not in url_or_id:
        return url_or_id
    m = _DASHBOARD_RE.search(url_or_id)
    if not m:
        raise ValueError(f"Could not parse Looker dashboard id from {url_or_id!r}")
    return m.group(1)


def _extract_look_id(url_or_id: str) -> int:
    if url_or_id.isdigit():
        return int(url_or_id)
    m = _LOOK_RE.search(url_or_id)
    if not m:
        raise ValueError(f"Could not parse Looker look id from {url_or_id!r}")
    return int(m.group(1))


def _tile_query(sdk, element) -> dict[str, Any] | None:
    query_id = getattr(element, "query_id", None) or getattr(getattr(element, "query", None), "id", None)
    if not query_id:
        return None
    q = sdk.query(query_id)
    try:
        sql = sdk.run_query(query_id=q.id, result_format="sql")
    except Exception as e:
        sql = f"-- SQL unavailable: {e}"
    return {
        "model": q.model,
        "explore": q.view,
        "fields": list(q.fields or []),
        "filters": dict(q.filters or {}),
        "sql": sql,
    }


@mcp.tool()
def get_dashboard(url_or_id: str) -> dict[str, Any]:
    """Fetch a Looker dashboard by URL or numeric/LookML ID. Returns title, description, and per-tile SQL."""
    sdk = _sdk()
    dashboard_id = _extract_dashboard_id(url_or_id)
    dash = sdk.dashboard(dashboard_id)
    tiles: list[dict[str, Any]] = []
    for el in dash.dashboard_elements or []:
        tiles.append({
            "id": el.id,
            "title": el.title,
            "type": el.type,
            "query": _tile_query(sdk, el),
        })
    return {
        "id": str(dash.id),
        "title": dash.title,
        "description": dash.description,
        "tile_count": len(tiles),
        "tiles": tiles,
    }


@mcp.tool()
def get_look(url_or_id: str) -> dict[str, Any]:
    """Fetch a single Looker Look by URL or numeric ID. Returns title, description, and SQL."""
    sdk = _sdk()
    look_id = _extract_look_id(url_or_id)
    look = sdk.look(look_id)
    query_dict = None
    if look.query:
        try:
            sql = sdk.run_query(query_id=look.query.id, result_format="sql")
        except Exception as e:
            sql = f"-- SQL unavailable: {e}"
        query_dict = {
            "model": look.query.model,
            "explore": look.query.view,
            "fields": list(look.query.fields or []),
            "filters": dict(look.query.filters or {}),
            "sql": sql,
        }
    return {
        "id": str(look.id),
        "title": look.title,
        "description": look.description,
        "query": query_dict,
    }


@mcp.tool()
def get_explore(model: str, explore: str) -> dict[str, Any]:
    """Fetch schema of a Looker Explore — useful to enrich a KB with available dimensions/measures."""
    sdk = _sdk()
    e = sdk.lookml_model_explore(lookml_model_name=model, explore_name=explore)
    return {
        "model": e.model_name,
        "explore": e.name,
        "label": e.label,
        "description": e.description,
        "fields": {
            "dimensions": [{"name": d.name, "type": d.type, "label": d.label, "description": d.description}
                           for d in (e.fields.dimensions or [])] if e.fields else [],
            "measures": [{"name": m.name, "type": m.type, "label": m.label, "description": m.description}
                         for m in (e.fields.measures or [])] if e.fields else [],
        },
    }


if __name__ == "__main__":
    mcp.run()
