"""Local MCP server for BigQuery (read-only).

Exposes a small surface mirroring the managed BQ MCP, but invocable from
local subagents without ToolSearch / org-managed connectors. Auth uses
Application Default Credentials (run `gcloud auth application-default
login` once on the host).
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import tempfile
import threading
import traceback
from pathlib import Path
from typing import Any

_log_path = os.path.join(tempfile.gettempdir(), "mcp-bq-debug.log")
logging.basicConfig(
    filename=_log_path,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
_log = logging.getLogger("mcp-bq")
_log.info("=== server starting ===")
_log.info(f"python: {sys.executable}")
_log.info(f"BIGQUERY_PROJECT_ID={os.environ.get('BIGQUERY_PROJECT_ID')}")
_log.info(f"GOOGLE_APPLICATION_CREDENTIALS={os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
_log.info(f"NO_GCE_CHECK={os.environ.get('NO_GCE_CHECK')}")
_log.info(f"GCE_METADATA_HOST={os.environ.get('GCE_METADATA_HOST')}")

# Watchdog: log stack trace of ALL threads every 3s
_watchdog_thread_id = threading.get_ident()
def _watchdog():
    import time
    while True:
        time.sleep(3)
        frames = sys._current_frames()
        for tid, frame in frames.items():
            if tid == _watchdog_thread_id:
                continue
            stack = "".join(traceback.format_stack(frame))
            tname = next((t.name for t in threading.enumerate() if t.ident == tid), f"tid={tid}")
            _log.info(f"WATCHDOG [{tname}] stack:\n{stack}")
_wd = threading.Thread(target=_watchdog, daemon=True, name="watchdog")
_wd.start()
_watchdog_thread_id = _wd.ident
_log.info("watchdog thread started")

try:
    _log.info("importing google.cloud.bigquery...")
    from google.cloud import bigquery
    _log.info("google.cloud.bigquery imported OK")
except Exception:
    _log.error(f"import failed: {traceback.format_exc()}")
    raise

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("bq-local")

_SELECT_RE = re.compile(r"^\s*(--[^\n]*\n|/\*.*?\*/\s*)*\s*(with|select)\b", re.IGNORECASE | re.DOTALL)


def _client(project_id: str) -> bigquery.Client:
    _log.info(f"_client(project_id={project_id!r}) — creating bigquery.Client...")
    try:
        # Load credentials directly from the ADC file to avoid google.auth.default()
        # calling `gcloud` as a subprocess (which hangs in the MCP stdio context).
        from google.oauth2 import credentials as oauth2_credentials
        adc = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if adc and os.path.isfile(adc):
            _log.info(f"loading credentials directly from {adc}")
            creds = oauth2_credentials.Credentials.from_authorized_user_file(
                adc, scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            c = bigquery.Client(project=project_id, credentials=creds)
        else:
            _log.warning("ADC file not set or missing; falling back to google.auth.default()")
            c = bigquery.Client(project=project_id)
        _log.info("bigquery.Client created OK")
        return c
    except Exception:
        _log.error(f"bigquery.Client failed: {traceback.format_exc()}")
        raise


def _rows_to_list(row_iterator) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in row_iterator:
        out.append({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(row).items()})
    return out


def _run_readonly(project_id: str, query: str) -> dict[str, Any]:
    """Execução read-only central — compartilhada por execute_sql_readonly e execute_gabarito.

    Impõe SELECT/WITH-only como rede de segurança (o BQ também impõe via flag DML,
    mas o guard local previne escrita acidental).
    """
    if not _SELECT_RE.match(query):
        raise ValueError("Only SELECT/WITH queries are allowed in execute_sql_readonly.")

    client = _client(project_id)
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
def execute_sql_readonly(projectId: str, query: str) -> dict[str, Any]:
    """Run a read-only SQL query on BigQuery and return rows + execution proof.

    Returns a dict with the keys expected by the kb-evaluator contract:
    - jobComplete, queryId, totalBytesProcessed, totalBytesBilled, rows, schema.

    Enforces SELECT/WITH-only at the proxy level as a safety net (BQ also enforces
    via the DML flag, but local guard prevents accidental writes).
    """
    return _run_readonly(projectId, query)


@mcp.tool()
def list_dataset_ids(projectId: str) -> dict[str, Any]:
    """List dataset IDs in a project."""
    _log.info(f"list_dataset_ids(projectId={projectId!r}) called")
    try:
        client = _client(projectId)
        _log.info("calling client.list_datasets()...")
        datasets = list(client.list_datasets())
        _log.info(f"got {len(datasets)} datasets")
        return {"datasets": [{"id": f"{projectId}:{d.dataset_id}"} for d in datasets]}
    except Exception:
        _log.error(f"list_dataset_ids failed: {traceback.format_exc()}")
        raise


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


def _find_project_root() -> Path:
    """Sobe a partir deste arquivo até achar a pasta que contém knowledge-bases/.

    O cwd do processo MCP não é garantido (não há `cwd` na entrada de ~/.claude.json),
    então ancoramos no local do próprio server.py. Funciona tanto para a cópia que roda
    (<root>/mcp-bq/server.py) quanto para o fonte (<root>/.claude-plugin/mcps/bq/server.py).
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "knowledge-bases").is_dir():
            return parent
    return Path(os.environ.get("KB_ROOT", os.getcwd()))


def _project_of_sql(query: str, default: str) -> str:
    """projectId = 1ª parte do FQN da primeira tabela em backticks; senão o default.

    Espelha a regra do antigo golden-runner: `projeto.dataset.tabela` → `projeto`;
    `dataset.tabela` (sem projeto) → default (BIGQUERY_PROJECT_ID).
    """
    m = re.search(r"`([^`]+)`", query)
    if m:
        parts = m.group(1).split(".")
        if len(parts) >= 3:
            return parts[0]
    return default


@mcp.tool()
def execute_gabarito(kb_dir: str, question_id: int) -> dict[str, Any]:
    """Único leitor server-side da face secreta (questions.secret.json).

    Dado (kb_dir, question_id): lê a gabarito_sql da pergunta, executa-a VERBATIM
    no BigQuery read-only (reusa _run_readonly → guard SELECT/WITH + prova) e devolve
    o valor de referência + prova (gabarito_job_id, gabarito_bytes). Espelha o contrato
    do antigo subagente golden-runner: NUNCA reescreve a SQL, nunca monta prompt de
    avaliador, nunca escreve em results/. É a peça isolada do Invariante #1/#7 —
    o orquestrador nunca abre a face secreta; ela é lida só aqui, dentro do MCP.
    """
    _log.info(f"execute_gabarito(kb_dir={kb_dir!r}, question_id={question_id})")

    def _fail(msg: str) -> dict[str, Any]:
        _log.error(f"execute_gabarito #{question_id}: {msg}")
        return {
            "id": question_id, "esperava_encontrar": None, "gabarito_sql": None,
            "resposta_esperada_unidade": None, "tolerancia_relativa": None,
            "valor_gabarito": None, "gabarito_job_id": None, "gabarito_bytes": None,
            "gabarito_ok": False, "erro": msg,
        }

    # 1. Localizar e ler a face secreta (o orquestrador NUNCA abre este arquivo).
    base = Path(kb_dir)
    if not base.is_absolute():
        base = _find_project_root() / kb_dir
    secret_path = base / "questions.secret.json"
    try:
        items = json.loads(secret_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return _fail(f"não abriu a face secreta ({secret_path}): {exc}")

    # 2. Achar a pergunta pelo id.
    q = next((x for x in items if x.get("id") == question_id), None)
    if q is None:
        return _fail("id não encontrado na face secreta")

    esperava = q.get("esperava_encontrar")
    sql = q.get("gabarito_sql")
    unidade = q.get("resposta_esperada_unidade", "")
    tol = q.get("tolerancia_relativa")

    # 3. Sem verdade numérica a estabelecer (anti-alucinação / legado sem SQL).
    #    gabarito_ok = null (NÃO false — o scoring 6.0 distingue os dois).
    if not esperava or not sql:
        return {
            "id": question_id, "esperava_encontrar": esperava, "gabarito_sql": None,
            "resposta_esperada_unidade": unidade, "tolerancia_relativa": tol,
            "valor_gabarito": None, "gabarito_job_id": None, "gabarito_bytes": None,
            "gabarito_ok": None,
        }

    # 4. Executar VERBATIM, read-only. Falha de execução → gabarito_ok:false (sem prova).
    project = _project_of_sql(sql, os.environ.get("BIGQUERY_PROJECT_ID", "contaazul-ssbi"))
    try:
        res = _run_readonly(project, sql)
    except Exception as exc:
        _log.error(f"execute_gabarito #{question_id}: falha na execução: {exc}")
        return {
            "id": question_id, "esperava_encontrar": esperava, "gabarito_sql": sql,
            "resposta_esperada_unidade": unidade, "tolerancia_relativa": tol,
            "valor_gabarito": None, "gabarito_job_id": None, "gabarito_bytes": None,
            "gabarito_ok": False, "erro": str(exc)[:200],
        }

    job_id = res.get("queryId")
    gbytes = int(res.get("totalBytesProcessed") or 0)
    rows = res.get("rows") or []

    # 5. Extrair o escalar da única chave de rows[0]. Query rodou (temos prova),
    #    mas rows vazio / valor não-numérico → gabarito_ok:false COM prova.
    try:
        raw = list(rows[0].values())[0]
        num = float(raw)
        num = int(num) if num.is_integer() else num
    except (IndexError, TypeError, ValueError) as exc:
        return {
            "id": question_id, "esperava_encontrar": esperava, "gabarito_sql": sql,
            "resposta_esperada_unidade": unidade, "tolerancia_relativa": tol,
            "valor_gabarito": None, "gabarito_job_id": job_id, "gabarito_bytes": gbytes,
            "gabarito_ok": False, "erro": f"sem escalar numérico em rows[0]: {exc}",
        }

    return {
        "id": question_id, "esperava_encontrar": esperava, "gabarito_sql": sql,
        "resposta_esperada_unidade": unidade, "tolerancia_relativa": tol,
        "valor_gabarito": num, "gabarito_job_id": job_id, "gabarito_bytes": gbytes,
        "gabarito_ok": True,
    }


if __name__ == "__main__":
    mcp.run()
