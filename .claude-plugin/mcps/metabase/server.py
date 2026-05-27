"""Local MCP server for Metabase.

Reads Metabase questions (cards) and dashboards via the REST API and
returns metadata + native SQL for each. Used by `/create-kb` to bootstrap
a KB from existing Metabase assets.

Auth: env vars METABASE_URL, METABASE_API_KEY (sent as X-API-Key header).
Configure via the project's `.env`; setup-mcp.sh injects them into the
MCP server process.
"""

from __future__ import annotations

import os
import re
from typing import Any

# Use the system certificate store so corporate proxy CA certificates are
# trusted without disabling SSL verification entirely.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("metabase-local")

_CARD_RE = re.compile(r"/(?:question|card)/(\d+)", re.IGNORECASE)
_DASH_RE = re.compile(r"/dashboard/(\d+)", re.IGNORECASE)


def _base_url() -> str:
    url = os.environ.get("METABASE_URL", "").rstrip("/")
    if not url:
        raise RuntimeError("METABASE_URL not set in environment")
    return url


def _headers() -> dict[str, str]:
    key = os.environ.get("METABASE_API_KEY", "")
    if not key:
        raise RuntimeError("METABASE_API_KEY not set in environment")
    return {"X-API-Key": key, "Accept": "application/json"}


def _get(path: str) -> Any:
    r = requests.get(f"{_base_url()}{path}", headers=_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def _extract_id(pattern: re.Pattern[str], url_or_id: str) -> int:
    if url_or_id.isdigit():
        return int(url_or_id)
    m = pattern.search(url_or_id)
    if not m:
        raise ValueError(f"Could not parse id from {url_or_id!r}")
    return int(m.group(1))


def _simplify_query(dataset_query: dict[str, Any] | None) -> dict[str, Any] | None:
    if not dataset_query:
        return None
    q_type = dataset_query.get("type")
    out: dict[str, Any] = {"type": q_type, "database": dataset_query.get("database")}
    if q_type == "native":
        native = dataset_query.get("native") or {}
        out["sql"] = native.get("query")
        out["template_tags"] = list((native.get("template-tags") or {}).keys())
    else:
        out["mbql"] = dataset_query.get("query")
    return out


@mcp.tool()
def get_question(url_or_id: str) -> dict[str, Any]:
    """Fetch a Metabase question (card) by URL or numeric ID. Returns name, description, and SQL (when native)."""
    card_id = _extract_id(_CARD_RE, url_or_id)
    card = _get(f"/api/card/{card_id}")
    return {
        "id": card.get("id"),
        "name": card.get("name"),
        "description": card.get("description"),
        "collection_id": card.get("collection_id"),
        "query": _simplify_query(card.get("dataset_query")),
        "result_metadata": [
            {"name": c.get("name"), "display_name": c.get("display_name"), "base_type": c.get("base_type")}
            for c in (card.get("result_metadata") or [])
        ],
    }


@mcp.tool()
def get_dashboard(url_or_id: str) -> dict[str, Any]:
    """Fetch a Metabase dashboard by URL or numeric ID. Returns its cards (each with name, description, SQL)."""
    dash_id = _extract_id(_DASH_RE, url_or_id)
    dash = _get(f"/api/dashboard/{dash_id}")
    cards: list[dict[str, Any]] = []
    for dc in dash.get("dashcards") or []:
        card = dc.get("card") or {}
        if not card:
            continue
        cards.append({
            "id": card.get("id"),
            "name": card.get("name"),
            "description": card.get("description"),
            "query": _simplify_query(card.get("dataset_query")),
        })
    return {
        "id": dash.get("id"),
        "name": dash.get("name"),
        "description": dash.get("description"),
        "card_count": len(cards),
        "cards": cards,
    }


@mcp.tool()
def get_database_schema(database_id: int) -> dict[str, Any]:
    """Fetch a Metabase database's metadata (tables + columns). Useful to enrich KB with schema info."""
    meta = _get(f"/api/database/{database_id}/metadata")
    tables = []
    for t in meta.get("tables") or []:
        tables.append({
            "id": t.get("id"),
            "name": t.get("name"),
            "schema": t.get("schema"),
            "description": t.get("description"),
            "fields": [{"name": f.get("name"), "base_type": f.get("base_type"), "description": f.get("description")}
                       for f in (t.get("fields") or [])],
        })
    return {
        "id": meta.get("id"),
        "name": meta.get("name"),
        "engine": meta.get("engine"),
        "tables": tables,
    }


if __name__ == "__main__":
    mcp.run()
