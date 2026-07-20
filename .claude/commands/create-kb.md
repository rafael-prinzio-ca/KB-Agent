---
description: Cria ou atualiza uma KB. Sincroniza repos GitHub, coleta inputs (período + URLs Looker/Metabase + definições), dispara kb-builder + question-creator em PARALELO (cada um chama os MCPs independente). Em KB com kb.md existente, gera kb-candidate.md, roda eval contra ambos com as mesmas questions e oferece promoção via diff. Uso `/create-kb <kb> [--regenerate-questions]`.
---

# Criar/atualizar KB (Nascimento + Atualização)

Você (Claude principal) é o orquestrador. Sua missão é construir ou atualizar a KB `<kb>`. Você **é o único ponto de interação com o usuário** — sub-agents não fazem AskUserQuestion. Coleta tudo upfront e passa via prompt estruturado.

**Princípio fundamental**: `kb-builder` e `question-creator` rodam em paralelo, cada um chamando os MCPs Looker/Metabase **independente**. O `question-creator` **NÃO** lê o `kb.md` gerado pelo `kb-builder` — isso evita "alvo móvel" (KB e perguntas que evoluem juntas, mascarando se a melhoria é real).

> **Isolamento do gabarito.** As perguntas vivem em **duas faces** (Invariante #1 do CLAUDE.md): pública (`questions.public.json` — `id`+`pergunta`+`split`) e secreta (`questions.secret.json` — gabarito + unidade + esperava + tolerância + `split`). Você **lê só a face pública** para montar os prompts; a verdade é estabelecida pela tool MCP `execute_gabarito` (isolada, server-side), **depois** que os avaliadores/probers já responderam. O orquestrador nunca abre a face secreta.

## Dois modos (fork por `KB_EXISTS`)

- **Nascimento** (`KB_EXISTS == false`, escreve em `kb.md`): guiado + **loop test-driven**. Ementa (Passo 2.5) → build → varredura + loop com `kb-prober` sobre as perguntas `split=="estudo"` → checkpoint humano. A verdade nunca chega a quem escreve a KB; o conserto vem das **fontes** (Passo 5).
- **Atualização** (`KB_EXISTS == true`, escreve em `kb-candidate.md`): **champion-vs-candidate** (Passo 6-8, como sempre). Antes do A/B: candidate = champion + **patch** do delta (não regenera) + delta-loop só nas perguntas novas (Passo 5.5). O portão de regressão cobre **toda pergunta pré-existente** (held-out + estudo antiga); o held-out segue como o número honesto de certificação.

> **Papéis (não confundir):** dentro do `/create-kb`, o `kb-prober` faz a avaliação **do loop de afinação** (Passo 5/5.5) — é ele que devolve `lacunas` para dirigir o conserto. O **A/B champion-vs-candidate** (Passo 6) usa o `kb-evaluator` — o mesmo avaliador oficial do `/run-eval` —, porque a decisão de promoção deve usar o instrumento mais confiável e consistente com a certificação. Ou seja: **prober afina, evaluator julga.** `kb-builder`/`question-creator`/`kb-prober`/`kb-evaluator` **nunca** veem o gabarito.

## Passo 0 — Sync de repos GitHub

Antes de qualquer coisa, rode o sync para garantir que os clones em `repos/` estejam frescos. Os agents `kb-builder` e `question-creator` podem cruzar com LookML/SQLX desses repos.

1. Via Bash: `./scripts/sync-repos.sh`.
2. **Se exit code == 0**: imprima o output e siga para Passo 1.
3. **Se exit code != 0**: AskUserQuestion `"Sync de repos GitHub falhou. Como proceder?"` — header `"Sync falhou"` — opções:
   - `"Abortar build"` → pare; imprima `"/create-kb cancelado: sync falhou. Resolva (gh auth status, conexão) e rode novamente."` (debug com `./scripts/sync-repos.sh` direto).
   - `"Continuar com clones existentes (pode estar defasado)"` → siga; marque `SYNC_STALE = true` (usado no resumo final).

## Passo 1 — Validar `<kb>` + parsing de flags + estado prévio

1. Capture argumentos: `<kb>` e detecte `--regenerate-questions` em ARGUMENTS.
2. **Se `<kb>` ausente/vazio**: liste `knowledge-bases/` via Bash:
   ```
   Uso: /create-kb <kb> [--regenerate-questions]
   KBs existentes: <lista>
   ```
   Pare.
3. **Validar slug**: `<kb>` deve ser `[a-z0-9-]+`. Caracteres inválidos → mostre regra e pare.
4. Crie pasta se ausente: `mkdir -p knowledge-bases/<kb>`.
5. Defina:
   - `KB_DIR = knowledge-bases/<kb>`
   - `KB_PATH = <KB_DIR>/kb.md`
   - `CANDIDATE_PATH = <KB_DIR>/kb-candidate.md`
   - `PUBLIC_PATH = <KB_DIR>/questions.public.json`
   - `SECRET_PATH = <KB_DIR>/questions.secret.json`
   - `RESULTS_DIR = <KB_DIR>/results`
6. Inspecione (via Bash `test -e`):
   - `KB_EXISTS`
   - `FACES_EXIST = (test -e <PUBLIC_PATH>) E (test -e <SECRET_PATH>)` — as **duas** faces presentes.
   - `CANDIDATE_ORPHAN = test -e <CANDIDATE_PATH>` (de execução anterior interrompida)

### 1a. Tratar candidate órfão

Se `CANDIDATE_ORPHAN == true`: AskUserQuestion `"kb-candidate.md órfão encontrado de execução anterior. Como proceder?"` — header `"Candidate órfão"` — opções:
- `"Descartar e gerar candidate novo"` → `rm <CANDIDATE_PATH>` via Bash; siga.
- `"Usar como ponto de partida (não regenera)"` → marque `SKIP_BUILD = true`; pule Passo 4a (kb-builder).
- `"Abortar /create-kb"` → pare imediatamente.

### 1b. Imprimir status

```
Status da KB "<kb>":
  kb.md             : [✓ existe | ✗ ausente]
  faces de perguntas: [✓ existem (public+secret) | ✗ ausentes | ⚠ incompletas]
  --regenerate-questions : [sim | não]

Plano:
  kb-builder       → [build em kb.md (Nascimento) | patch em kb-candidate.md (Atualização)]
  question-creator → [executado | pulado (mantém faces atuais)]
  kb-prober        → [loop de construção (Nascimento) | delta-loop (Atualização)]
  kb-evaluator     → [A/B champion-vs-candidate (Atualização) | certificação via /run-eval]
```

> Se exatamente **uma** das faces existir (estado inconsistente, ex.: migração interrompida), trate como `FACES_EXIST = false` e force regeneração: marque `WILL_GENERATE_QUESTIONS = true` no Passo 2 e avise no resumo final que as faces foram regeneradas por estarem incompletas.

## Passo 2 — Coletar inputs upfront via AskUserQuestion

### Bloco 1 (sempre)

Faça **uma chamada AskUserQuestion** com 4 perguntas:

1. `"Período de referência da KB?"` — header `"Período"`:
   - "Última semana fechada"
   - "Último mês fechado"
   - "Trimestre atual"
   - (Other para texto livre, ex.: `"2026-04-01 a 2026-04-30"`)

2. `"Fontes Looker — cole URLs separadas por espaço"` — header `"Looker"`:
   - "Pular Looker"
   - (Other com URLs)

3. `"Fontes Metabase — cole URLs separadas por espaço"` — header `"Metabase"`:
   - "Pular Metabase"
   - (Other com URLs)

4. `"Definições adicionais — texto livre (regras de negócio, glossário, contexto)?"` — header `"Definições"`:
   - "Pular"
   - (Other com texto livre)

Defina:
- `DATE_RANGE` = texto da resposta 1 (ou "(none)" se vazio).
- `LOOKER_URLS` = texto da resposta 2 (ou "(none)" se "Pular Looker").
- `METABASE_URLS` = texto da resposta 3 (ou "(none)" se "Pular Metabase").
- `DEFINITIONS` = texto da resposta 4 (ou "(none)" se "Pular").

### Sanity check de fontes

Se `LOOKER_URLS == "(none)"` E `METABASE_URLS == "(none)"` E `DEFINITIONS == "(none)"`:
```
Nenhuma fonte fornecida (Looker, Metabase e Definições todos vazios). Pipeline cancelado — não há material para construir/atualizar a KB.
```
Pare.

### Bloco 2 (só se vai rodar question-creator)

Determine `WILL_GENERATE_QUESTIONS`:
- `FACES_EXIST == false` → `true` (sem faces não há como avaliar)
- `FACES_EXIST == true` E `--regenerate-questions` → `true` (`MODE=overwrite`)
- `FACES_EXIST == true` E **Modo 2 com assunto novo** (a ementa do Passo 2.5 adiciona intents) → `true` (`MODE=append` — gera só as perguntas dos intents novos; preserva as existentes). *Finalizado após o Passo 2.5, que revela o "assunto novo".*
- `FACES_EXIST == true` E sem flag E sem assunto novo → `false` (mantém — alvo fixo / refresh puro)

Se `WILL_GENERATE_QUESTIONS == true`, faça **uma chamada AskUserQuestion** com 4 perguntas:

5. `"Quantas perguntas gerar?"` — header `"Qtd"`:
   - "5 (recomendado)"
   - "6 a 7"
   - "8 a 10"
   - (Other)

6. `"Nível de dificuldade?"` — header `"Dificuldade"`:
   - "Misto (recomendado)"
   - "Fácil"
   - "Médio"
   - "Difícil"

7. `"Tipos de pergunta?"` — header `"Tipos"` — **multiSelect**:
   - "Contagem (COUNT)"
   - "Soma (SUM)"
   - "Média (AVG)"
   - "Proporção/ratio"

8. `"Foco temático?"` — header `"Foco"`:
   - "Cobertura ampla (recomendado)"
   - (Other para tópico, ex.: "CSAT PME")

Mapeie respostas:
- `NUM_QUESTIONS` = inteiro (5 / 6 / 8 / Other parseado; default 6 para "6 a 7", 8 para "8 a 10").
- `DIFFICULTY` = `facil | medio | dificil | misto`.
- `QUESTION_TYPES` = CSV das opções marcadas (ex.: `contagem,soma,media`). Default `contagem,soma` se nenhuma.
- `FOCUS` = texto da resposta 8 (ou `"(none)"`).

## Passo 2.5 — Ementa (`intents.json`)

Roda **quando `WILL_GENERATE_QUESTIONS == true`** (KB nova; `--regenerate-questions`; ou Modo 2 com assunto novo). A ementa é a lista de **assuntos que a KB deve saber responder** — o requisito que escopa `kb-builder` e `question-creator`, e o termômetro de cobertura do checkpoint. **Você propõe; o usuário aprova** (Invariante #3).

1. **Rascunhe** 5–12 intents em **linguagem de negócio** a partir do que já tem: `DEFINITIONS` + títulos/URLs de Looker/Metabase + (se úteis) nomes de tabela/métrica achados com `Grep` em `repos/` (você **pode** ler `repos/`; **não** chame MCPs aqui). Intent = um assunto/métrica, **não** uma pergunta específica (ex.: "Demanda de atendimento por canal e segmento", não "demanda no dia X"). Sem citar coluna/tabela.
2. **Imprima** a lista numerada e faça **UMA** `AskUserQuestion` header `"Ementa"`:
   - `"Aprovar como está"` → usa o rascunho.
   - `"Editar"` (Other: o usuário lista ajustes/adições/remoções) → aplique.
   - `"Refazer"` → rascunhe de novo com o feedback (máx. 2 voltas; depois siga com o melhor rascunho e avise).
3. **Grave** `intents.json` na **raiz** de `KB_DIR` (não em `results/` — invisível ao `/eval-report`):
   ```json
   { "kb": "<kb>", "gerado_em": "<date +%Y-%m-%d>", "intents": [ { "id": 1, "intent": "<assunto>", "notas": "<opcional>" } ] }
   ```
   Em **Modo 2 (assunto novo)**: **append** os intents novos ao `intents.json` existente (Read → adiciona → Write; não reescreve os antigos; ids continuam).
4. Guarde o texto da ementa como `INTENTS` (passado aos agents no Passo 4). Em Modo 2, guarde também `INTENTS_DELTA` = só os intents novos.

> Ementa imperfeita é OK: o loop + o checkpoint a refinam (um intent que as fontes não suportam vira falha visível no checkpoint, não um erro fatal aqui).

## Passo 3 — Determinar TARGET_PATH e modo de build

- `KB_EXISTS == false` → **Nascimento**: `TARGET_PATH = <KB_PATH>`; `BUILD_MODE = build`.
- `KB_EXISTS == true` → **Atualização**: `TARGET_PATH = <CANDIDATE_PATH>`; `BUILD_MODE = patch`. **Prepare o candidate a partir do champion** (não regenera): se `SKIP_BUILD != true`, via Bash `cp "<KB_PATH>" "<CANDIDATE_PATH>"`. (Se o usuário escolheu "usar candidate órfão como ponto de partida" no Passo 1a → `SKIP_BUILD == true` → **não** faça o `cp`, mantenha o órfão.)

## Passo 4 — Disparar agents em paralelo

Em **uma única mensagem**, dispare até 2 `Agent` tool_uses simultaneamente.

### 4a. kb-builder (a menos que SKIP_BUILD)

Se `SKIP_BUILD != true`:

```
Agent(
  subagent_type="kb-builder",
  description="<kb>: <BUILD_MODE> em <TARGET_PATH>",
  prompt="""
KB_NAME: <kb>
KB_DIR: <KB_DIR>
TARGET_PATH: <TARGET_PATH>
MODE: <BUILD_MODE>
OVERWRITE: true
INTENTS: <INTENTS>
DATE_RANGE: <DATE_RANGE>
LOOKER_URLS: <LOOKER_URLS>
METABASE_URLS: <METABASE_URLS>
DEFINITIONS: <DEFINITIONS>
LACUNAS: (none)
"""
)
```

> **Modo 1** → `MODE=build` (escreve `kb.md` do zero, escopado por `INTENTS`, queries em `@inicio`/`@fim`). **Modo 2** → `MODE=patch` (o `<CANDIDATE_PATH>` já é cópia do champion no Passo 3; o kb-builder **adiciona** os intents novos de `INTENTS` e re-aterra nas fontes, **sem regenerar**). `LACUNAS` na chamada inicial é `(none)` — as lacunas só aparecem no loop (Passo 5/5.5). Em nenhum caso o `kb-builder` recebe gabarito.

### 4b. question-creator (a menos que WILL_GENERATE_QUESTIONS=false)

Se `WILL_GENERATE_QUESTIONS == true`:

```
Agent(
  subagent_type="question-creator",
  description="Gera faces de perguntas para <kb>",
  prompt="""
KB_NAME: <kb>
KB_DIR: <KB_DIR>
MODE: <create se !FACES_EXIST | append se Modo 2 com assunto novo (só perguntas dos intents novos) | overwrite se --regenerate-questions>
INTENTS: <INTENTS>
HOLDOUT_RATIO: 0.3
NUM_QUESTIONS: <NUM_QUESTIONS>
DIFFICULTY: <DIFFICULTY>
QUESTION_TYPES: <QUESTION_TYPES>
FOCUS: <FOCUS>
DATE_RANGE: <DATE_RANGE>
LOOKER_URLS: <LOOKER_URLS>
METABASE_URLS: <METABASE_URLS>
DEFINITIONS: <DEFINITIONS>
"""
)
```

> O `question-creator` deriva `questions.public.json` e `questions.secret.json` de `KB_DIR` e grava as **duas faces** (a `gabarito_sql` só na secreta). Ele recebe as MESMAS URLs que o `kb-builder` e chama os MCPs próprios — duplicação intencional para garantir isolamento.

### Validar resultados

Aguarde ambos. Parseie a última linha da resposta de cada como JSON.

- Se `kb-builder` retornou `status: "error"`: imprima `kb-builder falhou: <reason>`. Aborte.
- Se `question-creator` retornou `status: "error"`: imprima `question-creator falhou: <reason>`. Aborte.
- Se ambos `status: "ok"`: anote `kb_builder_status = "executado"` e `question_creator_status = "executado"` (ou "pulado" se não foi invocado).

## Passo 5 — Modo Nascimento: loop de construção + checkpoint (TARGET_PATH == kb.md)

Só quando `TARGET_PATH == <KB_PATH>` (KB nova). Afina a KB contra as perguntas `split=="estudo"` até o placar parar de melhorar. O `kb-evaluator` **não** entra aqui — ele é a certificação oficial, sua, via `/run-eval`.

### 5a. Preparar

1. Leia `<PUBLIC_PATH>` (1 Read) → array `PERGUNTAS` (`id`+`pergunta`+`split`). **Não leia `<SECRET_PATH>`.**
2. `ESTUDO_IDS` = ids com `split == "estudo"`. Se vazio (ex.: face legada sem split) → **pule o loop**, vá ao 5c com aviso "sem população de estudo — nada a afinar".
3. `mkdir -p <KB_DIR>/build-log` (staging do loop; fora de `results/`, nunca no `_index.json`).

### 5b. Primitiva `LOOP(KB_ALVO, ESTUDO_IDS, K=3)` — usada aqui e no Passo 5.5

Para `r = 1..K`:

1. **Varredura**: (1ª vez) `ToolSearch(query="select:mcp__bq_local__validate_kb_queries", max_results=1)`; então `mcp__bq_local__validate_kb_queries(kb_file="<KB_ALVO>")`. Grave o retorno em `build-log/varredura-r<r>.json`. Blocos `falhou`/`nao_query` entram nas FAILURES.
2. **Cópia opaca**: `SCRATCH_DIR=$(python -c "import tempfile; print(tempfile.mkdtemp())")` (opaco, **sem** o slug); `cp "<KB_ALVO>" "<SCRATCH_DIR>/kb.md"` → `KB_FILE`. Passe só `KB_FILE` (nunca `KB_DIR`/slug), igual ao `/run-eval` Passo 2.1.
3. **Probers**: em **uma mensagem**, `Agent(subagent_type="kb-prober")` para **cada** `ESTUDO_IDS` — prompt = `KB_FILE:` + `PERGUNTA:` (a pública). Seu contexto **não tem gabarito** neste momento.
4. **Coleta** (parse tolerante do `/run-eval` Passo 4): campos-núcleo + `lacunas`.
5. **Gabarito** — só **depois** do passo 3: `ToolSearch(query="select:mcp__bq_local__execute_gabarito", max_results=1)`; em **uma mensagem**, `mcp__bq_local__execute_gabarito(kb_dir="<KB_DIR>", question_id=id)` para cada `ESTUDO_IDS`.
6. **Scoring**: aplique o **`/run-eval` Passo 6** (fonte canônica — não reimplemente) → `status` por pergunta.
7. `FAILURES` = perguntas `reprovado` ∪ blocos `falhou`/`nao_query` da varredura. `erro_gabarito` **não** é falha do candidato (é o benchmark).
8. **Parada**: `FAILURES` vazio → PARA (sucesso). Nenhum novo `aprovado` vs a rodada anterior → PARA (platô).
9. **FIX_PROMPT (sanitizado)**: monte para o `kb-builder` — as `FAILURES` (a pergunta pública + as `lacunas` do prober) + as queries ⚠ + `INTENTS` + URLs para re-aterrar. **AUDITE antes de enviar**: o prompt **NÃO pode** conter `gabarito_sql`, `valor_gabarito` nem valor de referência (você os tem no contexto desde o passo 5 desta rodada, mas eles **nunca** vão ao patch — o conserto vem das fontes, ver Regra inviolável). Se algum aparecer, remova.
10. **Patch**: `Agent(subagent_type="kb-builder")` com `MODE: patch`, `TARGET_PATH: <KB_ALVO>`, `LACUNAS: <FIX_PROMPT>`, `INTENTS`, `LOOKER_URLS`/`METABASE_URLS`, `DEFINITIONS`. Ele lê `<KB_ALVO>`, aplica merge dirigido (re-aterrando **primeiro nos `repos/`**), re-grava.
11. Grave `build-log/loop-r<r>.json` (staging: respostas dos probers + scores + resumo do patch). **NUNCA** appenda ao `_index.json`.

Retorna: placar de estudo da última rodada (`X/N`) + nº de queries ⚠.

### 5c. Checkpoint (você decide)

Rode `LOOP(<KB_PATH>, ESTUDO_IDS, 3)`. Depois, **AskUserQuestion** header `"Construção"`, mostrando `"<r> rodadas · estudo <X>/<N> aprovado · <Q> queries ⚠"`:
- `"Aceitar KB"` → siga para 5d.
- `"Continuar (+3 rodadas)"` → rode `LOOP` de novo e repita o checkpoint.
- `"Abortar"` → pare; imprima que a KB ficou no estado atual (não certificada).

### 5d. Fim (KB aceita)

```
✓ KB criada: <KB_PATH>  (estudo: <X>/<N> aprovado após <r> rodadas)
✓ Faces de perguntas: <PUBLIC_PATH> + <SECRET_PATH> (<num_total>; <num_holdout> held-out reservadas)
✓ Ementa: <KB_DIR>/intents.json  ·  Log de construção: <KB_DIR>/build-log/
[se SYNC_STALE: "⚠ repos GitHub não sincronizados — KB pode ter código defasado."]

Próximo: rode `/run-eval <kb>` para CERTIFICAR no held-out (o kb-evaluator oficial, que não participou da construção).
```

Fim do command (Modo Nascimento). A certificação é sua, via `/run-eval`.

## Passo 5.5 — Modo Atualização: delta-loop no candidate (só se houve assunto novo)

Só quando `TARGET_PATH == <CANDIDATE_PATH>` **e** o `question-creator` rodou em `append` (gerou perguntas novas para os intents do delta). Caso contrário (refresh puro, sem perguntas novas) → **pule para o Passo 6**.

1. Leia `<PUBLIC_PATH>` → `PERGUNTAS`. `ESTUDO_NOVOS` = ids `split=="estudo"` **entre as perguntas novas** desta run (o `num_new` do retorno do `question-creator` delimita — são os ids mais altos). Vazio → pule ao Passo 6.
2. `mkdir -p <KB_DIR>/build-log`.
3. Rode **`LOOP(<CANDIDATE_PATH>, ESTUDO_NOVOS, 3)`** (a primitiva do Passo 5b): afina **só** o delta no candidate; o champion **não** é tocado. Artefatos em `build-log/`.

Sem checkpoint aqui — o portão de qualidade do Modo 2 é o champion-vs-candidate (Passo 6-8) com o portão de regressão pré-existente (Passo 7c). Siga para o Passo 6.

## Passo 6 — Modo candidate: avaliar ambos (TARGET_PATH == kb-candidate.md)

> Mesmo isolamento do `/run-eval`: avaliadores a partir da face pública **primeiro**, `execute_gabarito` **depois**. O gabarito (computado **uma vez**) julga champion e candidate contra o **mesmo** `valor_gabarito` — é isso que torna o A/B justo.

### 6a. Ler face pública + preparar cópias isoladas das duas KBs (NUNCA a secreta)

1. Leia `<PUBLIC_PATH>` (1 Read) e parseie como array `PERGUNTAS` (`id`+`pergunta`+`split`). **Não leia `<SECRET_PATH>`.** (O `split` acompanha cada pergunta para o sub-placar held-out do snapshot e para o delta-loop do Passo 5.5; o portão do Passo 7c é **agnóstico ao `split`** — bloqueia qualquer `regrediu`.)
2. **Não** leia mais o `kb.md`/`kb-candidate.md` para embutir no prompt. Em vez disso, faça **cópias byte-exatas** num diretório de scratch da sessão (**fora** de `knowledge-bases/`) e passe aos avaliadores **apenas os caminhos**. Via Bash:
   - `SCRATCH_DIR=$(python -c "import tempfile; print(tempfile.mkdtemp())")` — diretório **opaco e único** (**não** `mktemp -d`: caminho POSIX que o `Read` não abre no Windows). **O nome do `SCRATCH_DIR` NÃO pode conter o slug `<kb>` nem derivar dele** (senão o slug vaza embutido no `KB_FILE` — ver nota de isolamento abaixo). Os arquivos-filho são `champion.md`/`candidate.md` (nomes genéricos, sem slug). Se logar o caminho para debug, só na sua saída, nunca no prompt do avaliador.
   - `cp "<KB_PATH>" "<SCRATCH_DIR>/champion.md"` → `KB_FILE_CHAMPION = <SCRATCH_DIR>/champion.md`
   - `cp "<CANDIDATE_PATH>" "<SCRATCH_DIR>/candidate.md"` → `KB_FILE_CANDIDATE = <SCRATCH_DIR>/candidate.md`
   - `KB_LINHAS_CHAMPION = $(wc -l < "<KB_PATH>")` e `KB_LINHAS_CANDIDATE = $(wc -l < "<CANDIDATE_PATH>")` (para a verificação de integridade no 6f).
   - **Marcador de EOF por lado** (para a prova de leitura íntegra no 6f): `KB_ULTIMA_LINHA_CHAMPION` / `KB_ULTIMA_LINHA_CANDIDATE` = a **última linha não-vazia** de cada arquivo, com `strip()` e truncada em **120 caracteres** (mesma convenção do `/run-eval` Passo 2.1d — ex.: `python -c "import sys;ls=[l.rstrip(chr(10)) for l in open(sys.argv[1],encoding='utf-8')];nb=[l for l in ls if l.strip()];print(nb[-1].strip()[:120] if nb else '')" "<path>"`). **Esses valores NUNCA entram no prompt do avaliador** — só servem para conferência no 6f.

> **Cópia, não ditado.** As cópias vêm de `cp` (byte-a-byte); **nunca** reescreva, resuma, edite ou filtre nenhuma KB — além de contaminar a medição, isso favoreceria artificialmente um dos lados do champion-vs-candidate. As perguntas vão **verbatim** da face pública.

> **Isolamento — passe só os caminhos das cópias.** Cada avaliador recebe **apenas** `KB_FILE` (o caminho da cópia do lado correto). **NUNCA** passe `KB_DIR`, o slug `<kb>`, nem caminhos sob `knowledge-bases/` — é isso que impede o avaliador de localizar a face secreta. **Isso inclui o próprio `KB_FILE`: o slug não pode aparecer em nenhuma parte do caminho** (nome do `SCRATCH_DIR` ou do arquivo) — use `SCRATCH_DIR` opaco (6a.2). O avaliador lê a KB **inteira** sozinho via `Read`; a prova de leitura íntegra vem de `kb_linhas_lidas` (6c/6f).

### 6b. Disparar 2N kb-evaluator em paralelo (só com a face pública)

Em **uma única mensagem**, dispare `2 * N` (N = número de perguntas) `Agent(subagent_type="kb-evaluator")` — o **mesmo** avaliador oficial do `/run-eval` (mesmo JSON-núcleo consumido pelo scoring; sem o campo `lacunas`, que só o loop de afinação usa). Usa-se o `kb-evaluator` aqui — e não o `kb-prober` — porque a decisão de promoção deve usar o instrumento mais confiável e consistente com a certificação:

- N instâncias com `KB_FILE_CHAMPION` + cada `pergunta` (pública).
- N instâncias com `KB_FILE_CANDIDATE` + cada `pergunta` (pública).

Template do prompt (mesmo do `/run-eval`, enxuto — só caminho + pergunta):

```
KB_FILE: <KB_FILE_(CHAMPION|CANDIDATE)>

PERGUNTA:
<PERGUNTA>

Responda apenas com o objeto JSON especificado na sua definição. Sem texto antes, sem texto depois.
```

**Passe SÓ o `KB_FILE` do lado correto** (nunca `KB_DIR`/slug/caminho em `knowledge-bases/`, e o slug não pode estar embutido no próprio `KB_FILE` — use `SCRATCH_DIR` opaco, 6a.2). Use `description` distinto: `"Champion #<id>"` e `"Candidate #<id>"`. Neste momento seu contexto **não tem nenhum gabarito** — e tem de continuar assim.

### 6c. Coletar respostas (parse tolerante)

Para cada uma das 2N respostas: strip de markdown (` ```json `, ` ``` `); extrair entre primeiro `{` e último `}`; `JSON.parse`; falhou → `parse_error: true`; OK → capture `encontrada`, `valor`, `unidade`, `confianca`, `confianca_score`, `explicacao`, `sql_executado`, `bytes_processed`, `job_id`, `kb_linhas_lidas`, `kb_ultima_linha`.

### 6d. Estabelecer a verdade via `execute_gabarito` (depois dos avaliadores; uma vez, vale p/ os dois lados)

A tool MCP chega como **deferred**; carregue-a uma vez: `ToolSearch(query="select:mcp__bq_local__execute_gabarito", max_results=1)`.

Em **uma única mensagem**, chame `N` vezes `mcp__bq_local__execute_gabarito` — **uma por pergunta** (não por lado; a verdade independe da KB):

```
mcp__bq_local__execute_gabarito(kb_dir="<KB_DIR>", question_id=<id>)
```

Colete de cada retorno: `id`, `esperava_encontrar`, `gabarito_sql`, `resposta_esperada_unidade`, `tolerancia_relativa`, `valor_gabarito`, `gabarito_job_id`, `gabarito_bytes`, `gabarito_ok` — **mesma anti-alucinação do `/run-eval` Passo 5**: você nunca reescreve a SQL (nem a montou), `valor_gabarito` vem só do retorno, falha vira `erro_gabarito`. O mesmo `valor_gabarito` julga **os dois** lados.

### 6e. Conferência (scoring canônico do `/run-eval` Passo 6)

Para cada pergunta, aplique **as regras do `/run-eval` Passo 6** (6.0–6.5) **duas vezes** — uma com a resposta do champion, outra com a do candidate — sempre contra o **mesmo** resultado de `execute_gabarito`:

- `valor_referencia` = `valor_gabarito` de `execute_gabarito` (ou `null` se `gabarito_ok == false`).
- Se `esperava_encontrar == true` e `gabarito_ok == false`: `status = "erro_gabarito"` para **ambos** os lados (a verdade não existe nesta run) — `delta_* = null`, `dentro_tolerancia = false`.
- `encontrada_ok`, `unidade_ok` (usando `resposta_esperada_unidade` de `execute_gabarito`), comparação numérica (`tolerancia_relativa` de `execute_gabarito`), `execucao_ok` e `status` exatamente como no Passo 6 do `/run-eval`.

Não reimplemente as fórmulas aqui — o Passo 6 do `/run-eval` é a fonte canônica.

### 6f. Gravar 2 snapshots (formato `{ meta, results }`, modo champion/candidate)

`ts = $(date +%Y-%m-%dT%H-%M-%S)`. `mkdir -p <RESULTS_DIR>` se ausente.

Hashes (16 chars; nunca abortam — fallback PowerShell, depois `"unknown"`):
- `questions_hash` = sha256(16) de **`<SECRET_PATH>`** (identidade do benchmark; igual nos dois snapshots).
- **champion**: `kb_hash` = sha256(16) de `kb.md`; `kb_prompt_hash` = sha256(16) da **cópia** `KB_FILE_CHAMPION` que os avaliadores leram; `kb_integra` = (`kb_prompt_hash == kb_hash`) **E** (todos os N avaliadores champion com `kb_linhas_lidas` dentro de ±1 de `KB_LINHAS_CHAMPION`) **E** (todos com `kb_ultima_linha == KB_ULTIMA_LINHA_CHAMPION`). Grave `KB_ULTIMA_LINHA_CHAMPION` em `meta.kb_ultima_linha_esperada`.
- **candidate**: `kb_hash` = sha256(16) de `kb-candidate.md`; `kb_prompt_hash` = sha256(16) da cópia `KB_FILE_CANDIDATE`; `kb_integra` = comparação correspondente contra `KB_LINHAS_CANDIDATE` **e** `KB_ULTIMA_LINHA_CANDIDATE`. Grave `KB_ULTIMA_LINHA_CANDIDATE` em `meta.kb_ultima_linha_esperada`.

> **Integridade — hash da cópia + prova de leitura (mesma tripla do `/run-eval` Passo 7.2).** Hasheie a **cópia de scratch** (`KB_FILE_*`) — é o que o avaliador leu. Depois cheque, por lado: (1) `kb_prompt_hash == kb_hash` (cópia íntegra); (2) `kb_linhas_lidas` vs `KB_LINHAS_*` (±1, leu inteiro); (3) `kb_ultima_linha` vs `KB_ULTIMA_LINHA_*` (chegou ao EOF). Qualquer divergência → aquele lado é **suspeito** (`kb_integra = false`); nunca aborta. O marcador vem da KB de cada lado (conteúdo público), nunca da face secreta, e o esperado nunca vai ao prompt do avaliador — isolamento intacto.

Grave 2 arquivos no formato `{ meta, results }` — **mesmo bloco `meta` do Passo 7.4 do `/run-eval`** (com `kb_hash`, `kb_prompt_hash`, `kb_integra`, `questions_hash`, agregados `aprovados`/`reprovados`/`erros_gabarito`/`total`/`confianca_media`/`bytes_total`; `bytes_total` inclui os bytes do gabarito):

- `<RESULTS_DIR>/<ts>.champion.json` — `results` = N do champion; `meta.mode = "champion"`; hashes do champion; `meta.run_id = "<ts>"`.
- `<RESULTS_DIR>/<ts>.candidate.json` — `results` = N do candidate; `meta.mode = "candidate"`; hashes do candidate; `meta.run_id = "<ts>"`.

Cada elemento de `results` segue o **schema do Passo 7.4 do `/run-eval`** (com os campos de gabarito vindos de `execute_gabarito`). O `valor_gabarito` é idêntico nos dois arquivos (mesma verdade da run). A `pergunta` vem da face pública.

> **Não** appende ao `_index.json` aqui. Champion/candidate são *staging* de A/B, não pontos da linha do tempo. A entrada canônica é appendada **só na consolidação** (Passo 8).

## Passo 7 — Diff + decisão

### 7a. Computar diff

Para cada pergunta, determine `transicao`:
- `mantém_aprovado` (aprovado → aprovado)
- `mantém_reprovado` (reprovado → reprovado)
- `melhorou` (reprovado → aprovado)
- `regrediu` (aprovado → reprovado)
- `erro_gabarito` (status `erro_gabarito` nos dois lados — não comparável; não entra no Δ de aprovados)

Compute totals: `aprovados_champion`, `aprovados_candidate`, `confianca_media_champion`, `confianca_media_candidate`.

### 7b. Imprimir tabela

```
Champion (kb.md) vs Candidate (kb-candidate.md):
  Aprovados:       X/N → Y/N    (Δ +/-Z)
  Reprovados:      (N-X)/N → (N-Y)/N
  Confiança média: A → B
  [se champion.kb_integra == false OU candidate.kb_integra == false: "⚠ integridade KB suspeita em <champion|candidate> — kb_prompt_hash != kb_hash"]

Mudanças por pergunta:
  #1 mantém aprovado
  #4 reprovado → aprovado  ✨ melhorou
  #6 aprovado → reprovado  ⚠ regrediu  (motivo: <curto>)
```

Motivo curto: `gabarito_falhou` | `parse_error` | `encontrada esperada=X obtida=Y` | `unidade esperada=X obtida=Y` | `delta_relativo=Z (tol=T)` | `execucao_ausente`.

### 7c. Decisão — portão de regressão + auto-promoção

Antes de perguntar, avalie o **portão** (usando o diff do 7a + o conjunto de perguntas **novas** desta run, via `num_new`):
- `REGRESSAO_PREEXISTENTE` = existe **alguma** pergunta com transição `aprovado→reprovado` (champion→candidate), **em qualquer `split`**? (Cobre held-out **e** estudo antiga. Perguntas novas raramente regridem — o champion não cobria o tópico novo, então tende a reprová-las (transição `melhorou`/`mantém_reprovado`) — e uma nova que ainda assim regredisse já é barrada por `NOVAS_OK`. `erro_gabarito` **não** conta como regressão.)
- `NOVAS_OK` = todas as perguntas **novas** desta run (se houve `append`) estão `aprovado` no candidate?

**Auto-promoção**: se `REGRESSAO_PREEXISTENTE == false` **E** (`NOVAS_OK == true` ou não houve perguntas novas) **E** `candidate.kb_integra != false` → **promova automaticamente** (execute a opção "Promover" do Passo 8), imprimindo o diff (7b) + `"✓ auto-promovido: sem regressão em nenhuma pergunta pré-existente"`. **Não** pergunte.

Senão (regressão em alguma pergunta pré-existente, ou alguma nova falhou, ou `kb_integra == false`) → **escale** com AskUserQuestion:

```
AskUserQuestion(
  question="Promover candidate → kb.md? (portão de regressão não passou limpo)",
  header="Promoção",
  options=[
    "Sim, promover (backup do atual em kb.md.bak.<ts>)",
    "Não, descartar candidate",
    "Manter candidate para inspeção (não promove, não apaga)"
  ]
)
```

## Passo 8 — Aplicar decisão

### Opção: Promover

```bash
mv <KB_PATH> <KB_DIR>/kb.md.bak.<ts>
mv <CANDIDATE_PATH> <KB_PATH>
rm <RESULTS_DIR>/<ts>.champion.json
mv <RESULTS_DIR>/<ts>.candidate.json <RESULTS_DIR>/<ts>.json
```

Consolide a identidade no índice (a decisão A/B virou o ponto canônico da linha do tempo):
1. Em `<RESULTS_DIR>/<ts>.json`, reescreva `meta.mode` de `"candidate"` para `"full"` (Read → ajuste só esse campo → Write; `results` e os demais campos de `meta` — inclusive `kb_prompt_hash`/`kb_integra` do candidate, que já é o novo `kb.md` — ficam intactos).
2. Appende esse `meta` (com `mode:"full"`) ao `<RESULTS_DIR>/_index.json` — append-only, **mesma regra tolerante do Passo 7.5 do `/run-eval`** (falha emite aviso, não aborta).

Imprima:
```
✓ Candidate promovido.
  Champion anterior:  knowledge-bases/<kb>/kb.md.bak.<ts>
  Snapshot pós-promoção: knowledge-bases/<kb>/results/<ts>.json
  Aprovados: <aprovados_candidate>/<N>
```

### Opção: Descartar

```bash
rm <CANDIDATE_PATH>
rm <RESULTS_DIR>/<ts>.candidate.json
mv <RESULTS_DIR>/<ts>.champion.json <RESULTS_DIR>/<ts>.json
```

Consolide a identidade no índice (o champion continua canônico, mas registramos o ponto na linha do tempo):
1. Em `<RESULTS_DIR>/<ts>.json`, reescreva `meta.mode` de `"champion"` para `"full"`.
2. Appende esse `meta` (com `mode:"full"`) ao `<RESULTS_DIR>/_index.json` — append-only, tolerante (Passo 7.5 do `/run-eval`).

Imprima:
```
✓ Candidate descartado. kb.md permanece como estava.
  Snapshot do champion atual: knowledge-bases/<kb>/results/<ts>.json
```

### Opção: Manter para inspeção

Não move/deleta nada. Os 2 arquivos `.champion.json` e `.candidate.json` permanecem como staging.

> Como **nenhuma consolidação ocorreu**, nada é appendado ao `_index.json` — os snapshots de staging não entram na linha do tempo. Se você promover manualmente depois, rode `/run-eval <kb>` para registrar o ponto canônico no índice.

Imprima:
```
✓ Candidate mantido em knowledge-bases/<kb>/kb-candidate.md para análise manual.
  Snapshots em knowledge-bases/<kb>/results/<ts>.{champion,candidate}.json
  Para promover manualmente:
    mv knowledge-bases/<kb>/kb.md knowledge-bases/<kb>/kb.md.bak.<ts>
    mv knowledge-bases/<kb>/kb-candidate.md knowledge-bases/<kb>/kb.md
  Para descartar:
    rm knowledge-bases/<kb>/kb-candidate.md
```

## Passo 9 — Aviso SYNC_STALE (se aplicável)

Se `SYNC_STALE == true`, **após o resumo do Passo 5 ou 8**, imprima:
```
⚠ ATENÇÃO: repos GitHub não foram sincronizados antes desta run.
   KB pode ter sido construída com código defasado.
   Rode `./scripts/sync-repos.sh` e refaça `/create-kb <kb>` se isso for crítico.
```

## Passo 9b — Aviso de alvo móvel (se aplicável)

Se `--regenerate-questions` foi usado, imprima também:
```
⚠ NOTA: as faces de perguntas foram regeneradas. Backup em knowledge-bases/<kb>/questions.{public,secret}.json.bak.<ts>.
   Comparações com snapshots anteriores em results/ ficam menos significativas (alvo móvel — questions_hash muda).
```

## Regras invioláveis

- **Você é o único que conversa com o usuário** — sub-agents não fazem AskUserQuestion.
- **Você lê SÓ a face pública**: o orquestrador nunca abre `questions.secret.json`. O gabarito chega como retorno de `execute_gabarito`, e só depois que os avaliadores responderam (Passo 6b antes do 6d). Ler a face secreta no orquestrador recria o vazamento que a separação física existe para impedir.
- **Inputs upfront**: todas as perguntas nos Passos 1a/2/7c, antes de invocar agents (exceto a decisão de promoção, que vem depois do eval).
- **Pulo binário de question-creator**: faces existem E sem `--regenerate-questions` → não invoca question-creator (mantém alvo fixo).
- **TARGET_PATH é binário**: `kb.md` para KB nova, `kb-candidate.md` para KB existente. Sem exceções.
- **Agents/tools em paralelo**: kb-builder + question-creator no mesmo turno; 2N kb-evaluator no mesmo turno (A/B); N chamadas de `execute_gabarito` no mesmo turno; no loop de afinação, N kb-prober e depois N `execute_gabarito`, cada grupo no seu turno.
- **Gabarito é computado uma vez por `execute_gabarito`, verbatim, e compartilhado**: nunca regenerado, nunca no prompt do candidato; o mesmo `valor_gabarito` julga champion e candidate. Falha vira `erro_gabarito` nos dois lados — não vira regressão/melhoria.
- **Conferência usa o scoring canônico do `/run-eval` Passo 6**: não reimplemente as fórmulas.
- **Nunca ajuste manualmente as respostas dos subagentes**: registre o que retornaram.
- **Nunca leia kb.md no orquestrador para tomar decisões**: no 6a você só faz `cp` das duas KBs para scratch e passa os caminhos ao kb-evaluator (nunca embute o conteúdo, nunca inspeciona para julgar). A decisão de promoção é baseada em diff de resultados, não em diff de markdown.
- **Snapshots carregam `meta`**: champion/candidate são `{ meta, results }` com `mode` correspondente + `kb_prompt_hash`/`kb_integra` por lado. Só a consolidação (Passo 8) appenda a entrada canônica (`mode:"full"`) ao `_index.json`. Staging **nunca** entra na linha do tempo. Falha de índice/hash emite aviso, nunca aborta; `kb_integra == false` sinaliza, não aborta.
- **Ementa: você propõe, o usuário aprova** (Passo 2.5). `intents.json` na **raiz** de `KB_DIR` (nunca em `results/`). Sub-agents não decidem a ementa.
- **Avaliação por fase**: o **loop de afinação** (Passo 5/5.5) usa `kb-prober` (devolve `lacunas` para o conserto); o **A/B** (Passo 6) usa `kb-evaluator` (o mesmo avaliador da certificação, mais confiável e consistente com o `/run-eval`). O `kb-prober` **nunca** certifica nem julga o A/B; o `kb-evaluator` **nunca** entra no loop de afinação. Nenhum dos dois vê o gabarito.
- **Gabarito nunca no prompt de quem escreve a KB**: no loop, o `FIX_PROMPT` do `kb-builder` MODE=patch é **auditado** (sem `gabarito_sql`/`valor_gabarito`/valor de referência). Você tem o gabarito no contexto para pontuar, mas o conserto vem das **fontes** (`repos/`/Looker/Metabase).
- **Loop é staging**: artefatos em `<KB_DIR>/build-log/` (fora de `results/`), **nunca** appendados ao `_index.json`. Só o A/B consolidado (Passo 8) ou o `/run-eval` gravam na linha do tempo.
- **kb-builder tem dois modos**: `build` (Nascimento, do zero) e `patch` (Atualização + loop, **merge** — nunca regenera). Queries seguem a convenção `@inicio`/`@fim`.
