#!/usr/bin/env bash
#
# sync-repos.sh — clona/atualiza repos GitHub listados em .env para repos/
#
# Para cada repo em $KB_GITHUB_REPOS (espaço-separado, sem prefixo da org):
#   1. Se repos/<repo> não existe → gh repo clone "$KB_GITHUB_ORG/<repo>" repos/<repo>
#   2. Se já existe          → git -C repos/<repo> pull --ff-only --quiet
#
# Pré-requisitos:
#   - gh instalado e autenticado (gh auth login --hostname github.com)
#   - SSO da org ativado para o token, se aplicável
#
# Exit code:
#   0  → todos os repos sincronizados com sucesso (ou KB_GITHUB_REPOS vazio)
#   1  → pelo menos um repo falhou ao clonar/atualizar

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOS_DIR="$PROJECT_ROOT/repos"

# ── 1. Carregar .env ─────────────────────────────────────────────────────────

if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
  echo "ERROR: .env não encontrado em $PROJECT_ROOT" >&2
  echo "       Copie .env.example para .env e preencha KB_GITHUB_REPOS." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source "$PROJECT_ROOT/.env"
set +a

KB_GITHUB_ORG="${KB_GITHUB_ORG:-}"
KB_GITHUB_REPOS="${KB_GITHUB_REPOS:-}"

# ── 2. Saída limpa se nada a sincronizar ────────────────────────────────────

if [[ -z "$KB_GITHUB_REPOS" ]]; then
  echo "ℹ KB_GITHUB_REPOS vazio em .env — nenhum repo a sincronizar."
  exit 0
fi

if [[ -z "$KB_GITHUB_ORG" ]]; then
  echo "ERROR: KB_GITHUB_REPOS preenchido mas KB_GITHUB_ORG vazio em .env." >&2
  exit 1
fi

# ── 3. Validar gh CLI ───────────────────────────────────────────────────────

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI não encontrado. Instale com 'brew install gh'." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh não autenticado. Rode 'gh auth login --hostname github.com'." >&2
  echo "       Se a org $KB_GITHUB_ORG exige SSO, autorize o token na UI do GitHub." >&2
  exit 1
fi

# ── 4. Sincronizar cada repo ────────────────────────────────────────────────

mkdir -p "$REPOS_DIR"

failures=0
echo
echo "Sincronizando repos em $REPOS_DIR (org: $KB_GITHUB_ORG)..."
echo

for repo in $KB_GITHUB_REPOS; do
  dest="$REPOS_DIR/$repo"
  remote="$KB_GITHUB_ORG/$repo"

  if [[ -d "$dest/.git" ]]; then
    if git -C "$dest" pull --ff-only --quiet 2>/dev/null; then
      echo "↻ $repo atualizado"
    else
      echo "⚠ $repo — falha no git pull (verifique conexão/SSO)" >&2
      failures=$((failures + 1))
    fi
  elif [[ -e "$dest" ]]; then
    echo "⚠ $repo — $dest existe mas não é um repo git; removendo e clonando" >&2
    rm -rf "$dest"
    if gh repo clone "$remote" "$dest" -- --quiet 2>/dev/null; then
      echo "✓ $repo clonado"
    else
      echo "⚠ $repo — falha no gh repo clone $remote" >&2
      failures=$((failures + 1))
    fi
  else
    if gh repo clone "$remote" "$dest" -- --quiet 2>/dev/null; then
      echo "✓ $repo clonado"
    else
      echo "⚠ $repo — falha no gh repo clone $remote" >&2
      failures=$((failures + 1))
    fi
  fi
done

echo
if [[ "$failures" -gt 0 ]]; then
  echo "⚠ $failures repo(s) falharam — KBs construídas agora podem usar código defasado." >&2
  exit 1
fi

echo "✓ Todos os repos sincronizados."
exit 0
