# kb-manager

Sistema para **construir, versionar e avaliar Knowledge Bases sobre dados** dentro do Claude Code.

Cada KB vive em `knowledge-bases/<nome>/` e contém:
- **`kb.md`** — data dictionary curado a partir de Looker/Metabase + definições do usuário (regras de negócio).
- **`questions.json`** — conjunto de perguntas quantitativas que medem se a KB é boa o bastante para que um agente sem contexto prévio gere o SQL certo no BigQuery.
- **`results/<timestamp>.json`** — snapshots de avaliação (cada execução do `/run-eval`).

Dois comandos cobrem o ciclo completo:

| Comando | Propósito |
|---|---|
| `/create-kb <kb> [--regenerate-questions]` | Constrói ou atualiza uma KB. Em KB existente, faz **champion-vs-candidate** (gera `kb-candidate.md`, avalia ambos com as MESMAS perguntas, mostra diff e pergunta se promove). |
| `/run-eval <kb>` | Avalia uma KB pronta. Dispara `kb-evaluator` em paralelo (1 instância por pergunta), executa SQL real no BigQuery, grava snapshot em `results/`. |

## Arquitetura

```
/create-kb <kb>
  ├─ scripts/sync-repos.sh         (clona/atualiza LookML + Dataform em repos/)
  ├─ AskUserQuestion: período, URLs Looker/Metabase, definições
  ├─ AskUserQuestion (se vai gerar questions): qtd, dificuldade, tipos, foco
  ├─ PARALELO:
  │   ├─ kb-builder agent          (compila kb.md ou kb-candidate.md)
  │   └─ question-creator agent    (gera questions.json — NÃO lê kb.md, anti "alvo móvel")
  └─ Se candidate: 2N kb-evaluator paralelo + diff + AskUserQuestion (promover/descartar/manter)

/run-eval <kb>
  └─ N kb-evaluator paralelo       (1 instância por pergunta, SQL real no BigQuery)
```

**Princípio-chave**: `question-creator` chama os MCPs Looker/Metabase **diretamente** (não lê `kb.md`). Isso evita o problema do "alvo móvel" — se as perguntas saíssem do `kb.md`, KB e benchmark evoluiriam juntos e seria impossível medir melhoria real entre versões. Cada agent vê a mesma realidade (as fontes) mas interpreta independente.

## Pré-requisitos

| Ferramenta | Como instalar |
|---|---|
| Python 3.13 | `brew install python@3.13` |
| `gcloud` ADC | `gcloud auth application-default login` (escopo `https://www.googleapis.com/auth/bigquery.readonly`) |
| `gh` CLI | `brew install gh` + `gh auth login --hostname github.com` (com SSO se a org exige) |
| Claude Code | https://claude.ai/code |

## Instalação

```bash
# 1. Clone (ou já tem o repo)
cd "/caminho/para/kb-manager"

# 2. .env a partir do template
cp .env.example .env
$EDITOR .env
# Preencha pelo menos BIGQUERY_PROJECT_ID. Looker/Metabase/GitHub são opcionais.

# 3. Bootstrap dos MCPs locais (instala venvs + registra em ~/.claude.json)
./setup-mcp.sh

# 4. Autentique gh para a org alvo (se for usar sync-repos)
gh auth login --hostname github.com
gh repo view <ORG>/<algum-repo>   # confirma que SSO está OK

# 5. Reinicie o Claude Code para os MCPs e os slash commands ficarem disponíveis
```

## .env — campos

| Campo | Obrigatório | Para que serve |
|---|---|---|
| `BIGQUERY_PROJECT_ID` | ✅ | Projeto BQ default usado pelo `kb-evaluator` ao executar SQL |
| `LOOKERSDK_BASE_URL` + `LOOKERSDK_CLIENT_ID` + `LOOKERSDK_CLIENT_SECRET` | opcional | `kb-builder` e `question-creator` leem dashboards/looks/explores |
| `METABASE_URL` + `METABASE_API_KEY` | opcional | Idem, para Metabase |
| `KB_GITHUB_ORG` + `KB_GITHUB_REPOS` | opcional | `scripts/sync-repos.sh` clona esses repos em `repos/` para os agentes cruzarem com LookML/SQLX |

## Uso diário

### Criar uma KB nova (do zero)

```
/create-kb vendas-mtd
```

O command:
1. Sincroniza `repos/` (LookML + Dataform).
2. Pergunta período, URLs Looker, URLs Metabase, definições adicionais.
3. Pergunta quantidade, dificuldade, tipos e foco das perguntas.
4. Dispara `kb-builder` e `question-creator` em paralelo.
5. Termina. Próximo passo: `/run-eval vendas-mtd`.

### Avaliar uma KB

```
/run-eval vendas-mtd
```

Lê `kb.md` + `questions.json`, dispara N `kb-evaluator` em paralelo, cada um executando SQL real no BigQuery. Grava `results/<timestamp>.json` com `valor_obtido`, `delta_relativo`, `status` e prova de execução (`sql_executado`, `bytes_processed`, `job_id`).

### Atualizar uma KB existente (champion-vs-candidate)

```
/create-kb vendas-mtd
```

Em KB com `kb.md` existente, o command:
1. Gera `kb-candidate.md` (em vez de sobrescrever `kb.md`).
2. **Mantém `questions.json` intacto** (default — alvo fixo entre versões).
3. Roda 2N `kb-evaluator` em paralelo: N contra champion + N contra candidate.
4. Mostra diff por pergunta (mantém aprovado / mantém reprovado / melhorou ✨ / regrediu ⚠).
5. Pergunta: promover / descartar / manter para inspeção.

### Atualizar perguntas explicitamente

```
/create-kb vendas-mtd --regenerate-questions
```

Use quando a KB ganhou conteúdo novo que as perguntas atuais não cobrem, ou quando o conjunto ficou "fácil demais". Backup do `questions.json` anterior em `questions.json.bak.<timestamp>`. **Atenção**: snapshots de `results/` anteriores ficam menos comparáveis (alvo móvel).

## Estrutura do projeto

```
kb-manager/
├── .claude/
│   ├── commands/                    # slash commands (project-local)
│   │   ├── create-kb.md
│   │   └── run-eval.md
│   └── agents/                      # subagents (project-local)
│       ├── kb-builder.md
│       ├── kb-evaluator.md
│       └── question-creator.md
├── .claude-plugin/
│   ├── plugin.json                  # manifesto do plugin
│   └── mcps/                        # source-of-truth dos MCPs (server.py + requirements.txt)
│       ├── bq/
│       ├── looker/
│       └── metabase/
├── knowledge-bases/                 # uma pasta por KB
│   └── <kb>/
│       ├── kb.md
│       ├── kb-candidate.md          # efêmero, gerado pelo /create-kb em modo candidate
│       ├── kb.md.bak.<ts>           # backup ao promover
│       ├── questions.json
│       ├── questions.json.bak.<ts>  # backup ao --regenerate-questions
│       └── results/
│           └── <ts>.json
├── repos/                           # GERADO por sync-repos.sh (gitignored)
│   ├── looker/                      # LookML autoritativo
│   └── gcp-dataform-contaazul/      # Dataform SQLX autoritativo
├── scripts/
│   └── sync-repos.sh                # clona/atualiza repos GitHub
├── mcp-bq/                          # GERADO por setup-mcp.sh (gitignored)
├── mcp-looker/                      # idem
├── mcp-metabase/                    # idem
├── setup-mcp.sh                     # bootstrap dos MCPs locais (entry-point)
├── .env                             # gitignored
├── .env.example
└── README.md                        # você está aqui
```

## Troubleshooting

| Sintoma | Causa provável | Como resolver |
|---|---|---|
| `/create-kb` ou `/run-eval` não aparecem | Plugin não foi recarregado | Reinicie o Claude Code |
| `MCP bq_local` falha em qualquer query | ADC expirada ou projeto errado | `gcloud auth application-default login` e confirme `BIGQUERY_PROJECT_ID` no `.env` |
| `MCP looker_local` / `metabase_local` não responde | Credencial vazia no `.env` ou MCP não registrado | Preencha `.env` e rode `./setup-mcp.sh` de novo |
| `scripts/sync-repos.sh` falha com erro de gh | gh não autenticado ou SSO não autorizado | `gh auth status` + `gh repo view <ORG>/<repo>` para acionar o prompt de SSO |
| `kb-evaluator` retorna `encontrada: true` mas `sql_executado: null` | Subagente alucinou — não chamou a tool | Bug; reporte. Validação no `/run-eval` (`execucao_ok`) já detecta e reprova |
| Reprovação em pergunta histórica que sempre passou | Drift de dados no BigQuery | Verifique se o número validado em `kb.md` ainda corresponde à query atual; pode ser legítimo (atualize a KB) ou tolerância apertada demais |
| `kb-candidate.md` órfão | Execução anterior de `/create-kb` foi interrompida | `/create-kb` no Passo 1 detecta e pergunta o que fazer (descartar/usar/abortar) |

## Convenções

- **Slug de KB**: minúsculas, dígitos e hífens (`[a-z0-9-]+`). Sem espaços, acentos ou underscores.
- **Snapshots `results/`**:
  - `<ts>.json` = avaliação canônica (de `/run-eval` ou pós-promoção)
  - `<ts>.champion.json` / `<ts>.candidate.json` = staging interno do champion-vs-candidate (consolidado conforme a decisão de promoção)
- **Backups**: sem rotação automática. Usuário gerencia (`rm knowledge-bases/*/*.bak.*`).
- **Questions estáveis**: a regra default é **não mover o alvo**. Para regenerar conscientemente, use `--regenerate-questions`.

## Distribuição interna

Para um colega começar do zero:

```bash
git clone <repo-url> kb-manager
cd kb-manager
cp .env.example .env
$EDITOR .env                                # preenche credenciais
./setup-mcp.sh
gh auth login --hostname github.com         # se for usar sync-repos
# Abre o Claude Code apontando para esta pasta
# Reinicia o Claude Code se já estava aberto
# Pronto — /create-kb e /run-eval disponíveis
```
