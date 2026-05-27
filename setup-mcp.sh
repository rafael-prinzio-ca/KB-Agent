#!/usr/bin/env bash
#
# setup-mcp.sh — bootstrap dos MCPs locais (kb-manager)
#
# Para cada .claude-plugin/mcps/<name>/ versionado:
#   1. Cria mcp-<name>/ se não existir (gerado, gitignored)
#   2. Cria mcp-<name>/.venv via python3.13 -m venv (idempotente)
#   3. Copia server.py de .claude-plugin/mcps/<name>/ → mcp-<name>/
#   4. pip install -r .claude-plugin/mcps/<name>/requirements.txt
#   5. Registra em ~/.claude.json se cred do .env preenchida; senão remove entrada
#
# Cleanup one-time: remove arquivos legados em ~/.claude/{agents,commands}/
# que este plugin tinha publicado em versões anteriores — agora a descoberta
# de agents/commands é via .claude/ do projeto (project-local), não user-level.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOME/.claude.json"
BACKUP="$HOME/.claude.json.bak"

# ── 1. Carregar .env ─────────────────────────────────────────────────────────

if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
  echo "ERROR: .env não encontrado em $PROJECT_ROOT" >&2
  echo "       Copie .env.example para .env e preencha BIGQUERY_PROJECT_ID." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source "$PROJECT_ROOT/.env"
set +a

PYTHON_BIN="${KB_EVAL_PYTHON:-/opt/homebrew/bin/python3.13}"

# Detectar Windows (Git Bash) — venvs usam Scripts/ em vez de bin/
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || -n "${WINDIR:-}" ]]; then
  VENV_BIN="Scripts"
else
  VENV_BIN="bin"
fi

# Detectar caminho do ADC (Application Default Credentials) por plataforma
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || -n "${WINDIR:-}" ]]; then
  # Windows — APPDATA é C:\Users\...\AppData\Roaming; substituir barras invertidas
  if [[ -n "${APPDATA:-}" ]]; then
    ADC_PATH="${APPDATA//\\//}/gcloud/application_default_credentials.json"
  else
    ADC_PATH="${HOME}/AppData/Roaming/gcloud/application_default_credentials.json"
  fi
else
  ADC_PATH="${HOME}/.config/gcloud/application_default_credentials.json"
fi

if [[ -f "$ADC_PATH" ]]; then
  echo "✓ Application Default Credentials encontrado: $ADC_PATH"
else
  echo "⚠ Application Default Credentials NÃO encontrado em: $ADC_PATH"
  echo "  Execute: gcloud auth application-default login"
  ADC_PATH=""
fi

if [[ -z "${BIGQUERY_PROJECT_ID:-}" || "$BIGQUERY_PROJECT_ID" == "SEU_PROJETO_AQUI" ]]; then
  echo "ERROR: BIGQUERY_PROJECT_ID em .env ainda está como placeholder." >&2
  exit 1
fi

# ── 2. Cleanup legado em ~/.claude/ (one-time) ───────────────────────────────

cleanup_legacy_user_level() {
  local removed=0
  local files=(
    "$HOME/.claude/agents/kb-evaluator.md"
    "$HOME/.claude/agents/kb-builder.md"
    "$HOME/.claude/agents/question-creator.md"
    "$HOME/.claude/commands/run-eval.md"
    "$HOME/.claude/commands/create-kb.md"
    "$HOME/.claude/commands/create-questions.md"
  )
  for f in "${files[@]}"; do
    if [[ -f "$f" ]]; then
      rm -f "$f"
      removed=$((removed + 1))
    fi
  done
  if [[ "$removed" -gt 0 ]]; then
    echo "✓ removidos $removed arquivo(s) legados de ~/.claude/ (descoberta agora via .claude/ do projeto)"
  fi
}

# ── 3. Bootstrap de um MCP (idempotente) ─────────────────────────────────────

bootstrap_mcp() {
  local name="$1"
  local src="$PROJECT_ROOT/.claude-plugin/mcps/$name"
  local dest="$PROJECT_ROOT/mcp-$name"

  if [[ ! -d "$src" ]]; then
    echo "ERROR: source $src ausente" >&2
    return 1
  fi
  if [[ ! -f "$src/server.py" ]]; then
    echo "ERROR: $src/server.py ausente" >&2
    return 1
  fi
  if [[ ! -f "$src/requirements.txt" ]]; then
    echo "ERROR: $src/requirements.txt ausente" >&2
    return 1
  fi

  mkdir -p "$dest"
  if [[ ! -d "$dest/.venv" ]]; then
    "$PYTHON_BIN" -m venv "$dest/.venv"
  fi
  cp "$src/server.py" "$dest/server.py"
  "$dest/.venv/$VENV_BIN/python" -m pip install --quiet --upgrade pip
  "$dest/.venv/$VENV_BIN/python" -m pip install --quiet -r "$src/requirements.txt"
  echo "✓ mcp-$name pronto"
}

# ── 4. Merge dos 3 MCPs em ~/.claude.json (condicional por cred) ─────────────

install_mcps() {
  if [[ -f "$TARGET" ]]; then
    cp "$TARGET" "$BACKUP"
  fi

  local bq_venv="$PROJECT_ROOT/mcp-bq/.venv/$VENV_BIN/python"
  local bq_server="$PROJECT_ROOT/mcp-bq/server.py"
  local looker_venv="$PROJECT_ROOT/mcp-looker/.venv/$VENV_BIN/python"
  local looker_server="$PROJECT_ROOT/mcp-looker/server.py"
  local metabase_venv="$PROJECT_ROOT/mcp-metabase/.venv/$VENV_BIN/python"
  local metabase_server="$PROJECT_ROOT/mcp-metabase/server.py"

  "$bq_venv" - \
    "$TARGET" \
    "$bq_venv" "$bq_server" "$BIGQUERY_PROJECT_ID" "${ADC_PATH:-}" \
    "$looker_venv" "$looker_server" \
    "${LOOKERSDK_BASE_URL:-}" "${LOOKERSDK_CLIENT_ID:-}" "${LOOKERSDK_CLIENT_SECRET:-}" \
    "$metabase_venv" "$metabase_server" \
    "${METABASE_URL:-}" "${METABASE_API_KEY:-}" <<'PY'
import json, os, sys

(target,
 bq_venv, bq_server, bq_project, adc_path,
 looker_venv, looker_server, looker_url, looker_id, looker_secret,
 metabase_venv, metabase_server, metabase_url, metabase_key) = sys.argv[1:15]

cfg = json.load(open(target)) if os.path.exists(target) else {}
cfg.setdefault("mcpServers", {})

# bq_local — always
bq_env = {"BIGQUERY_PROJECT_ID": bq_project, "GOOGLE_CLOUD_PROJECT": bq_project}
if adc_path:
    bq_env["GOOGLE_APPLICATION_CREDENTIALS"] = adc_path
cfg["mcpServers"]["bq_local"] = {
    "command": bq_venv,
    "args": [bq_server],
    "env": bq_env,
}
print(f"✓ MCP bq_local registrado (BIGQUERY_PROJECT_ID={bq_project})")

# notion_local — always removed (workspace policy blocks)
if cfg["mcpServers"].pop("notion_local", None):
    print("✓ MCP notion_local removido (resíduo de versão anterior)")

# looker_local — conditional
if looker_url and looker_id and looker_secret:
    cfg["mcpServers"]["looker_local"] = {
        "command": looker_venv,
        "args": [looker_server],
        "env": {
            "LOOKERSDK_BASE_URL": looker_url,
            "LOOKERSDK_CLIENT_ID": looker_id,
            "LOOKERSDK_CLIENT_SECRET": looker_secret,
        },
    }
    print(f"✓ MCP looker_local registrado (base_url={looker_url})")
else:
    cfg["mcpServers"].pop("looker_local", None)
    missing = []
    if not looker_url: missing.append("LOOKERSDK_BASE_URL")
    if not looker_id: missing.append("LOOKERSDK_CLIENT_ID")
    if not looker_secret: missing.append("LOOKERSDK_CLIENT_SECRET")
    print(f"⚠ looker_local não registrado — faltando: {', '.join(missing)}")

# metabase_local — conditional
if metabase_url and metabase_key:
    cfg["mcpServers"]["metabase_local"] = {
        "command": metabase_venv,
        "args": [metabase_server],
        "env": {
            "METABASE_URL": metabase_url,
            "METABASE_API_KEY": metabase_key,
        },
    }
    print(f"✓ MCP metabase_local registrado (url={metabase_url})")
else:
    cfg["mcpServers"].pop("metabase_local", None)
    missing = []
    if not metabase_url: missing.append("METABASE_URL")
    if not metabase_key: missing.append("METABASE_API_KEY")
    print(f"⚠ metabase_local não registrado — faltando: {', '.join(missing)}")

with open(target, "w") as f:
    json.dump(cfg, f, indent=2)
PY

  echo ""
  echo "Configuração persistida em: $TARGET"
  [[ -f "$BACKUP" ]] && echo "Backup do estado anterior: $BACKUP"
}

# ── Run ──────────────────────────────────────────────────────────────────────

echo
echo "Bootstrap dos MCPs locais (kb-manager)..."
echo
cleanup_legacy_user_level
bootstrap_mcp bq
bootstrap_mcp looker
bootstrap_mcp metabase
echo
install_mcps
echo
echo "Pronto. Reinicie o Claude Code para os MCPs entrarem em efeito."
echo "(agents/commands são descobertos automaticamente via .claude/ do projeto.)"
