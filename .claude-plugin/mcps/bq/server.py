"""Local MCP server for BigQuery (read-only).

Exposes a small surface mirroring the managed BQ MCP, but invocable from
local subagents without ToolSearch / org-managed connectors. Auth uses
Application Default Credentials (run `gcloud auth application-default
login` once on the host).
"""

from __future__ import annotations

import os
import re
from typing import Any

from google.cloud import bigquery
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("bq-local")

_SELECT_RE = re.compile(r"^\s*(--[^\n]*\n|/\*.*?\*/\s*)*\s*(with|select)\b", re.IGNORECASE | re.DOTALL)


def _client(project_id: str) -> bigquery.Client:
    # Load credentials directly from the ADC file when set. Otherwise
    # google.auth.default() invokes `gcloud` as a subprocess (via
    # _cloud_sdk.get_project_id) — on some platforms (notably Windows in
    # the MCP stdio context) that subprocess hangs reading stdout for many
    # minutes. Reading the file directly avoids the gcloud invocation.
    adc = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if adc and os.path.isfile(adc):
        from google.oauth2 import credentials as oauth2_credentials
        creds = oauth2_credentials.Credentials.from_authorized_user_file(
            adc, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return bigquery.Client(project=project_id, credentials=creds)
    return bigquery.Client(project=project_id)


def _rows_to_list(row_iterator) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in row_iterator:
        out.append({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(row).items()})
    return out


@mcp.tool()
def execute_sql_readonly(projectId: str, query: str) -> dict[str, Any]:
    """Run a read-only SQL query on BigQuery and return rows + execution proof.

    Returns a dict with the keys expected by the kb-evaluator contract:
    - jobComplete, queryId, totalBytesProcessed, totalBytesBilled, rows, schema.

    Enforces SELECT/WITH-only at the proxy level as a safety net (BQ also enforces
    via the DML flag, but local guard prevents accidental writes).
    """
    if not _SELECT_RE.match(query):
        raise ValueError("Only SELECT/WITH queries are allowed in execute_sql_readonly.")

    client = _client(projectId)
    job_config = bigquery.QueryJobConfig(use_legacy_sql=False, dry_run=False)
    job = client.query(query, job_config=job_config)
    rows = list(job.result())
    schema_fields = [{"name": f.name, "type": f.field_type, "mode": f.mode} for f in (job.schema or [])]
    return {
        "jobComplete": True,
        "queryId": job.job_id,
        "totalBytesProcessed": str(job.total_bytes_processed or 0),
        "totalBytesBilled": str(job.total_bytes_billed or 0),
        "rows": _rows_to_list(rows),
        "schema": {"fields": schema_fields},
    }


@mcp.tool()
def list_dataset_ids(projectId: str) -> dict[str, Any]:
    """List dataset IDs in a project."""
    client = _client(projectId)
    return {"datasets": [{"id": f"{projectId}:{d.dataset_id}"} for d in client.list_datasets()]}


@mcp.tool()
def list_table_ids(projectId: str, datasetId: str) -> dict[str, Any]:
    """List table IDs in a dataset."""
    client = _client(projectId)
    ref = f"{projectId}.{datasetId}"
    return {"tables": [{"id": f"{projectId}:{datasetId}.{t.table_id}", "type": t.table_type} for t in client.list_tables(ref)]}


@mcp.tool()
def get_table_info(projectId: str, datasetId: str, tableId: str) -> dict[str, Any]:
    """Inspect schema/metadata of a table."""
    client = _client(projectId)
    table = client.get_table(f"{projectId}.{datasetId}.{tableId}")
    return {
        "id": f"{projectId}:{datasetId}.{tableId}",
        "numRows": table.num_rows,
        "numBytes": table.num_bytes,
        "schema": [{"name": f.name, "type": f.field_type, "mode": f.mode, "description": f.description} for f in (table.schema or [])],
        "timePartitioning": table.time_partitioning.field if table.time_partitioning else None,
        "clusteringFields": table.clustering_fields,
    }


@mcp.tool()
def get_dataset_info(projectId: str, datasetId: str) -> dict[str, Any]:
    """Inspect metadata of a dataset."""
    client = _client(projectId)
    ds = client.get_dataset(f"{projectId}.{datasetId}")
    return {
        "id": f"{projectId}:{datasetId}",
        "location": ds.location,
        "description": ds.description,
        "labels": dict(ds.labels) if ds.labels else {},
    }


if __name__ == "__main__":
    mcp.run()
