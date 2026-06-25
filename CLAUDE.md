# CLAUDE.md

Contexto para o Claude trabalhar neste repositório sem regredir invariantes. Complementa o [README.md](README.md) — não duplica o passo-a-passo de uso.

## O que é

`kb-manager` é um plugin do Claude Code que constrói, versiona e avalia **Knowledge Bases sobre dados** (data dictionaries + perguntas-benchmark). Ciclo coberto por três slash commands: `/create-kb` (build/update), `/run-eval` (avaliação; `--quick` = check diário binário vs última run verde) e `/eval-report` (relatório histórico — leitura pura, gera HTML para gestores).

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

### 6. Observabilidade é camada não-invasiva por cima do núcleo

Snapshots são `{ meta, results }` (o array por-pergunta vai em `results`, **inalterado**); `results/_index.json` é append-only e **derivado** (reconstruível varrendo snapshots; falha de escrita nunca aborta); `/eval-report` é **leitura pura** (sem agentes, sem BigQuery). Hashes e índice nunca abortam uma run. Tudo isso foi adicionado **sem tocar os 3 subagents** — o carimbo de `meta` é feito pelos orquestradores. Não mova lógica de observabilidade para dentro dos subagents nem torne a escrita do índice fatal.

### 7. Gabarito dinâmico — a verdade é a `gabarito_sql` executada na run

Cada pergunta do `questions.json` carrega uma `gabarito_sql` (query canônica). A "resposta certa" **não** é um número estático — é o resultado de rodar essa SQL **na própria run**, contra o BigQuery ao vivo. Motivo: o banco sofre **atualização retroativa**, então um valor congelado fica errado sem a KB ter piorado. Regras que sustentam o design (mudar exige discussão):

- A `gabarito_sql` é executada **verbatim pelo orquestrador** (`/run-eval` Passo 2.5, `/create-kb` Passo 6a.5) via `execute_sql_readonly` — **nunca regenerada, corrigida ou otimizada** em runtime (determinismo = verdade não-alucinada). Falha de execução vira `status = "erro_gabarito"`, **não** reprovação do candidato.
- A `gabarito_sql` **NUNCA** entra no prompt do `kb-evaluator`. O candidato chega ao número só pela KB — senão a avaliação vira cópia. (Reforça o Invariante #1: o gabarito vem de fonte independente da KB; KB errada não "casa" com gabarito errado.)
- `valor_gabarito` é gravado no snapshot (auditável via `gabarito_job_id`) mas **varia entre runs** por design. A comparação longitudinal é por **`status` por pergunta**, não por valor absoluto — por isso o status fica estável apesar do drift de dados.
- O `question-creator` gera `gabarito_sql` (extraída da SQL real das fontes — `query.sql` do Looker/Metabase nativo — e **validada no BigQuery read-only**, Passo 5.5; gabarito que não valida é descartado). Os commands ainda toleram o formato legado (`resposta_esperada_valor`) **na leitura**, mas a geração nova já é dinâmica — `--regenerate-questions` produz gabaritos dinâmicos. Para isso o `question-creator` ganhou `mcp__bq_local__execute_sql_readonly` (read-only — não fere o Invariante #5) só para validação; continua **sem ler `kb.md`** (Invariante #1 intacto).

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
- `knowledge-bases/*/results/` — snapshots de avaliação (`{ meta, results }`) + `_index.json` (índice append-only, derivado)
- `knowledge-bases/*/reports/` — HTML gerado por `/eval-report` (derivado, regenerável)
- `.env` — secrets

**Backups (no disco, sem rotação):**
- `kb.md.bak.<ts>` ao promover candidate
- `questions.json.bak.<ts>` ao `--regenerate-questions`
- `kb-candidate.md` é efêmero — em execução interrompida fica órfão; `/create-kb` no Passo 1a trata.

## Convenções

- **Slug de KB**: `[a-z0-9-]+` (minúsculas, dígitos, hífens). Sem espaços, acentos, underscores. Validado no Passo 1 de `/create-kb`.
- **Idioma**: tudo em português (commands, agents, README, mensagens). Manter consistência.
- **Snapshots `results/`** (formato `{ meta, results }`; `meta` carrega `kb`, `run_id`, `kb_hash`, `questions_hash`, `mode`, agregados `aprovados`/`reprovados`/`erros_gabarito`/`total`/`confianca_media` e `bytes_total`):
  - `<ts>.json` = canônico (`mode` `full`/`quick`; de `/run-eval` ou pós-promoção)
  - `<ts>.champion.json` / `<ts>.candidate.json` = staging do champion-vs-candidate (`mode` `champion`/`candidate`); na consolidação viram `<ts>.json` com `mode` reescrito p/ `full`
  - `_index.json` = índice append-only (uma entrada `meta` por run canônica; staging **não** entra). Derivado: reconstruível; falha de escrita nunca aborta
  - Hashes = sha256 (16 chars) de `kb.md`/`questions.json`; `"unknown"` se falhar
  - Cada item de `results` tem 3 `status` possíveis: `aprovado` / `reprovado` / `erro_gabarito` (gabarito não executou). Campos de gabarito por item: `gabarito_sql`, `valor_gabarito`, `gabarito_job_id`, `gabarito_bytes`, `gabarito_ok`. `bytes_total` soma candidato **+** gabarito.
  - Snapshots antigos (array nu, ou com `resposta_esperada_valor` em vez de `gabarito_sql`) são tolerados na leitura e **nunca** reescritos
- **Datas relativas** em prompts/AskUserQuestion: sempre converter para absoluto antes de gravar em `kb.md`.

## Workflow de mudanças comuns

| Quero mudar… | Onde mexer |
|---|---|
| Comportamento de `/create-kb`, `/run-eval` ou `/eval-report` | `.claude/commands/<cmd>.md` |
| Visual/layout do relatório HTML | template (CSS+JS inline) no corpo de `.claude/commands/eval-report.md` |
| Comportamento de um subagent | `.claude/agents/<agent>.md` |
| Schema/lógica de um MCP | `.claude-plugin/mcps/<name>/server.py` → depois rodar `./setup-mcp.sh` |
| Dependências de um MCP | `.claude-plugin/mcps/<name>/requirements.txt` → `./setup-mcp.sh` |
| Lista de repos sincronizados | `.env` (`KB_GITHUB_ORG`, `KB_GITHUB_REPOS`) |
| Permissões pré-aprovadas | `.claude/settings.json` (compartilhadas) · `.claude/settings.local.json` (locais da máquina, gitignored — paths absolutos, liberadas p/ multi-KB) |
| Manifesto do plugin (commands/agents/mcps declarados) | `.claude-plugin/plugin.json` |

Após editar MCP source, **sempre** rode `./setup-mcp.sh` — instâncias em `mcp-*/` são cópias.

Após mudar `.claude/commands/`, `.claude/agents/` ou `.claude-plugin/plugin.json`: o usuário precisa **reiniciar o Claude Code** para o plugin recarregar. Avise quando for o caso.

## Armadilhas conhecidas

- **MCPs não respondem**: 9/10 vezes é credencial vazia no `.env` ou `gcloud auth application-default login` expirada. Não tente "corrigir" o código do MCP antes de verificar credenciais.
- **`gh repo clone` falha em `sync-repos.sh`**: SSO da org não autorizado. `gh repo view <ORG>/<repo>` aciona o prompt. Não é bug do script.
- **Pergunta histórica que sempre passou reprovou**: pode ser drift de dados no BigQuery (legítimo — atualize `kb.md`) ou tolerância apertada demais. Não relaxe tolerância sem confirmar.
- **`kb-candidate.md` órfão**: execução anterior interrompida. `/create-kb` Passo 1a trata com AskUserQuestion (descartar/usar/abortar). Não delete preventivamente.
- **Editar `mcp-bq/server.py` direto**: será sobrescrito no próximo `setup-mcp.sh`. Sempre `.claude-plugin/mcps/bq/server.py`.
- **Alerta de regressão sumiu / aparece `ℹ alvo móvel`**: se `questions_hash` mudou entre runs (ex.: `--regenerate-questions`), a comparação por pergunta é suprimida **de propósito** (alvo móvel) — não é bug. Para voltar a comparar, mantenha `questions.json` fixo entre runs.
- **`/eval-report` diz "Nenhuma avaliação encontrada"**: não há snapshots em `results/`. Rode `/run-eval <kb>` primeiro. Apagar `_index.json` **não** perde histórico — ele é reconstruído varrendo os snapshots.

## Como começar a trabalhar aqui

Antes de mexer em algo, leia na ordem:
1. [README.md](README.md) — uso e arquitetura geral
2. [.claude-plugin/plugin.json](.claude-plugin/plugin.json) — o que é exposto e como
3. O command/agent específico que vai tocar — eles têm o contrato completo no próprio frontmatter + corpo

Convenção do projeto: commands e agents são **auto-contidos e prescritivos** (não dependem de docs externas para funcionar). Se precisar adicionar contexto que vale para todos, é candidato a este CLAUDE.md — não a redundar em cada agente.
