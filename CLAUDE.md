# CLAUDE.md

Contexto para o Claude trabalhar neste repositório sem regredir invariantes. Complementa o [README.md](README.md) — não duplica o passo-a-passo de uso.

## O que é

`kb-manager` é um plugin do Claude Code que constrói, versiona e avalia **Knowledge Bases sobre dados** (data dictionaries + perguntas-benchmark). Ciclo coberto por dois slash commands: `/create-kb` (build/update) e `/run-eval` (avaliação).

Stack: slash commands + subagents Claude + 3 MCPs Python locais (`bq_local`, `looker_local`, `metabase_local`) que falam com BigQuery, Looker e Metabase.

## Invariantes — NÃO QUEBRAR

Estes são os "porquês" do design. Mudar qualquer um exige discussão explícita com o usuário antes.

### 1. `question-creator` NUNCA lê `kb.md`

O agente de perguntas chama os MCPs Looker/Metabase **diretamente**, não derivado da KB. Motivo: se perguntas saíssem do `kb.md`, KB e benchmark evoluiriam juntos (problema do "alvo móvel") e seria impossível medir melhoria entre versões. Se for tentado refatorar para "reaproveitar contexto", **pare e confirme**.

Aplicação prática:
- `question-creator.md` não recebe e não deve ler `KB_PATH`.
- Em `--regenerate-questions`, perguntas vêm das fontes novamente, não do `kb.md` atual.
- Default em update de KB existente: **manter `questions.json` intacto** (alvo fixo).

### 2. Champion-vs-candidate é o caminho de update

Em `/create-kb` com `kb.md` existente, o builder escreve em `kb-candidate.md` (nunca sobrescreve direto). Avalia ambos com as MESMAS perguntas, mostra diff e pergunta se promove. Se for tentado "atualizar in-place", **pare e confirme**.

### 3. Claude principal é o ÚNICO ponto de interação com o usuário

Subagents (`kb-builder`, `question-creator`, `kb-evaluator`) **não fazem AskUserQuestion**. O orquestrador coleta tudo upfront e passa via prompt estruturado. Não adicione `AskUserQuestion` na definição de subagent.

### 4. `kb-evaluator` retorna prova de execução

Saída obrigatória inclui `sql_executado`, `bytes_processed`, `job_id`. Se algum vier `null` quando `encontrada: true`, o subagente alucinou — `/run-eval` valida via `execucao_ok` e reprova. Não relaxe essa validação.

### 5. BigQuery é read-only

MCP `bq_local` usa `execute_sql_readonly`. Nunca trocar por `execute_sql` (que permite escrita). Se precisar de escrita, é caso novo — discutir antes.

## Layout (o que é versionado vs gerado)

**Versionado:**
- `.claude/commands/*.md` — slash commands (project-local)
- `.claude/agents/*.md` — subagents (project-local)
- `.claude-plugin/plugin.json` — manifesto
- `.claude-plugin/mcps/<name>/{server.py,requirements.txt}` — **source-of-truth dos MCPs**
- `knowledge-bases/<kb>/{kb.md,questions.json}` — KBs (conteúdo curado)
- `scripts/sync-repos.sh`, `setup-mcp.sh`, `.env.example`

**Gerado (gitignored — ver [.gitignore](.gitignore)):**
- `mcp-bq/`, `mcp-looker/`, `mcp-metabase/` — instâncias instaladas (venvs) pelo `setup-mcp.sh`. **Editar aqui é inútil** — `setup-mcp.sh` sobrescreve a partir de `.claude-plugin/mcps/`. Sempre edite o source-of-truth.
- `repos/` — clones LookML + Dataform via `sync-repos.sh`
- `knowledge-bases/*/results/` — snapshots de avaliação
- `.env` — secrets

**Backups (no disco, sem rotação):**
- `kb.md.bak.<ts>` ao promover candidate
- `questions.json.bak.<ts>` ao `--regenerate-questions`
- `kb-candidate.md` é efêmero — em execução interrompida fica órfão; `/create-kb` no Passo 1a trata.

## Convenções

- **Slug de KB**: `[a-z0-9-]+` (minúsculas, dígitos, hífens). Sem espaços, acentos, underscores. Validado no Passo 1 de `/create-kb`.
- **Idioma**: tudo em português (commands, agents, README, mensagens). Manter consistência.
- **Snapshots `results/`**:
  - `<ts>.json` = canônico (de `/run-eval` ou pós-promoção)
  - `<ts>.champion.json` / `<ts>.candidate.json` = staging do champion-vs-candidate (consolidado conforme decisão)
- **Datas relativas** em prompts/AskUserQuestion: sempre converter para absoluto antes de gravar em `kb.md`.

## Workflow de mudanças comuns

| Quero mudar… | Onde mexer |
|---|---|
| Comportamento de `/create-kb` ou `/run-eval` | `.claude/commands/<cmd>.md` |
| Comportamento de um subagent | `.claude/agents/<agent>.md` |
| Schema/lógica de um MCP | `.claude-plugin/mcps/<name>/server.py` → depois rodar `./setup-mcp.sh` |
| Dependências de um MCP | `.claude-plugin/mcps/<name>/requirements.txt` → `./setup-mcp.sh` |
| Lista de repos sincronizados | `.env` (`KB_GITHUB_ORG`, `KB_GITHUB_REPOS`) |
| Permissões pré-aprovadas | [.claude/settings.json](.claude/settings.json) |
| Manifesto do plugin (commands/agents/mcps declarados) | `.claude-plugin/plugin.json` |

Após editar MCP source, **sempre** rode `./setup-mcp.sh` — instâncias em `mcp-*/` são cópias.

Após mudar `.claude/commands/`, `.claude/agents/` ou `.claude-plugin/plugin.json`: o usuário precisa **reiniciar o Claude Code** para o plugin recarregar. Avise quando for o caso.

## Armadilhas conhecidas

- **MCPs não respondem**: 9/10 vezes é credencial vazia no `.env` ou `gcloud auth application-default login` expirada. Não tente "corrigir" o código do MCP antes de verificar credenciais.
- **`gh repo clone` falha em `sync-repos.sh`**: SSO da org não autorizado. `gh repo view <ORG>/<repo>` aciona o prompt. Não é bug do script.
- **Pergunta histórica que sempre passou reprovou**: pode ser drift de dados no BigQuery (legítimo — atualize `kb.md`) ou tolerância apertada demais. Não relaxe tolerância sem confirmar.
- **`kb-candidate.md` órfão**: execução anterior interrompida. `/create-kb` Passo 1a trata com AskUserQuestion (descartar/usar/abortar). Não delete preventivamente.
- **Editar `mcp-bq/server.py` direto**: será sobrescrito no próximo `setup-mcp.sh`. Sempre `.claude-plugin/mcps/bq/server.py`.

## Como começar a trabalhar aqui

Antes de mexer em algo, leia na ordem:
1. [README.md](README.md) — uso e arquitetura geral
2. [.claude-plugin/plugin.json](.claude-plugin/plugin.json) — o que é exposto e como
3. O command/agent específico que vai tocar — eles têm o contrato completo no próprio frontmatter + corpo

Convenção do projeto: commands e agents são **auto-contidos e prescritivos** (não dependem de docs externas para funcionar). Se precisar adicionar contexto que vale para todos, é candidato a este CLAUDE.md — não a redundar em cada agente.
