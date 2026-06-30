---
description: Cria ou atualiza uma KB. Sincroniza repos GitHub, coleta inputs (período + URLs Looker/Metabase + definições), dispara kb-builder + question-creator em PARALELO (cada um chama os MCPs independente). Em KB com kb.md existente, gera kb-candidate.md, roda eval contra ambos com as mesmas questions e oferece promoção via diff. Uso `/create-kb <kb> [--regenerate-questions]`.
---

# Criar/atualizar KB (champion-vs-candidate)

Você (Claude principal) é o orquestrador. Sua missão é construir ou atualizar a KB `<kb>`. Você **é o único ponto de interação com o usuário** — sub-agents não fazem AskUserQuestion. Coleta tudo upfront e passa via prompt estruturado.

**Princípio fundamental**: `kb-builder` e `question-creator` rodam em paralelo, cada um chamando os MCPs Looker/Metabase **independente**. O `question-creator` **NÃO** lê o `kb.md` gerado pelo `kb-builder` — isso evita "alvo móvel" (KB e perguntas que evoluem juntas, mascarando se a melhoria é real).

> **Isolamento do gabarito.** As perguntas vivem em **duas faces** (Invariante #1 do CLAUDE.md): pública (`questions.public.json` — `id`+`pergunta`) e secreta (`questions.secret.json` — gabarito + unidade + esperava + tolerância). Na avaliação champion-vs-candidate, **você lê só a face pública** para montar os prompts; a verdade é estabelecida por subagentes `golden-runner` isolados, **depois** que os avaliadores já responderam. O orquestrador nunca abre a face secreta.

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
  kb-builder       → escrever em [kb.md (KB nova) | kb-candidate.md (KB existente)]
  question-creator → [executado | pulado (mantém faces atuais)]
  kb-evaluator     → [executado contra candidate+champion | pulado (KB nova; rode /run-eval depois)]
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
- `FACES_EXIST == true` E `--regenerate-questions` → `true`
- `FACES_EXIST == true` E sem flag → `false` (mantém — alvo fixo)

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

## Passo 3 — Determinar TARGET_PATH

- Se `KB_EXISTS == false` → `TARGET_PATH = <KB_PATH>` (KB nova, escreve direto em `kb.md`).
- Se `KB_EXISTS == true` → `TARGET_PATH = <CANDIDATE_PATH>` (KB existente, modo candidate).

## Passo 4 — Disparar agents em paralelo

Em **uma única mensagem**, dispare até 2 `Agent` tool_uses simultaneamente.

### 4a. kb-builder (a menos que SKIP_BUILD)

Se `SKIP_BUILD != true`:

```
Agent(
  subagent_type="kb-builder",
  description="Compila <TARGET_PATH> para <kb>",
  prompt="""
KB_NAME: <kb>
KB_DIR: <KB_DIR>
TARGET_PATH: <TARGET_PATH>
OVERWRITE: true
DATE_RANGE: <DATE_RANGE>
LOOKER_URLS: <LOOKER_URLS>
METABASE_URLS: <METABASE_URLS>
DEFINITIONS: <DEFINITIONS>
"""
)
```

### 4b. question-creator (a menos que WILL_GENERATE_QUESTIONS=false)

Se `WILL_GENERATE_QUESTIONS == true`:

```
Agent(
  subagent_type="question-creator",
  description="Gera faces de perguntas para <kb>",
  prompt="""
KB_NAME: <kb>
KB_DIR: <KB_DIR>
MODE: <create se !FACES_EXIST; senão overwrite>
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

## Passo 5 — Modo "KB nova" (TARGET_PATH == kb.md)

Se `TARGET_PATH == <KB_PATH>`:

Imprima:
```
✓ KB criada: <KB_PATH>
✓ Faces de perguntas: <PUBLIC_PATH> + <SECRET_PATH> (<num_total> perguntas)
[se SYNC_STALE: "⚠ ATENÇÃO: repos GitHub não foram sincronizados — KB pode estar com código defasado."]

Próximo: rode `/run-eval <kb>` para avaliar a qualidade.
```

Fim do command. Não roda eval automaticamente.

## Passo 6 — Modo candidate: avaliar ambos (TARGET_PATH == kb-candidate.md)

> Mesmo isolamento do `/run-eval`: avaliadores a partir da face pública **primeiro**, `golden-runner` **depois**. O gabarito (computado **uma vez**) julga champion e candidate contra o **mesmo** `valor_gabarito` — é isso que torna o A/B justo.

### 6a. Ler face pública + as duas KBs (NUNCA a secreta)

1. Leia `<PUBLIC_PATH>` (1 Read) e parseie como array `PERGUNTAS` (`id`+`pergunta`). **Não leia `<SECRET_PATH>`.**
2. Leia `<KB_PATH>` (champion) **integralmente**, guiando-se pela contagem real de linhas (KBs variam de tamanho e podem exceder 25K tokens; o número de chamadas **não é fixo**):
   a. `TOTAL_CHAMPION = $(wc -l < "<KB_PATH>")` via Bash.
   b. Leia em janelas sequenciais de `offset=1` até `TOTAL_CHAMPION`, ex.: `Read(limit=650)`, `Read(offset=650, limit=650)`… **até o EOF**.
   c. Concatene **todas** as janelas (conteúdo limpo), na ordem, em `KB_CONTENT_CHAMPION`.
3. Leia `<CANDIDATE_PATH>` (candidate) da mesma forma — meça `TOTAL_CANDIDATE` e leia em janelas até o EOF. Concatene em `KB_CONTENT_CANDIDATE`.

> **Anti-truncamento (invariante I2b — KB completa por avaliador).** Champion e candidate vão **inteiros** para os respectivos `kb-evaluator`. A leitura é dirigida pela contagem (`wc -l`), não por um número fixo de chamadas. Entregar KB **parcial** viola o I2b tão gravemente quanto recortá-la por pergunta. **Nunca dispare os `kb-evaluator` com champion ou candidate truncado.** (O 6f carimba `kb_prompt_hash` de cada lado, tornando isso auditável.)

### 6b. Disparar 2N kb-evaluator em paralelo (só com a face pública)

Em **uma única mensagem**, dispare `2 * N` (N = número de perguntas) `Agent(subagent_type="kb-evaluator")`:

- N instâncias com `KB_CONTENT_CHAMPION` + cada `pergunta` (pública).
- N instâncias com `KB_CONTENT_CANDIDATE` + cada `pergunta` (pública).

Template do prompt (mesmo do `/run-eval`):

```
BASE DE CONHECIMENTO:
<KB_CONTENT_(CHAMPION|CANDIDATE)>

PERGUNTA:
<PERGUNTA>

Responda apenas com o objeto JSON especificado na sua definição. Sem texto antes, sem texto depois.
```

Use `description` distinto: `"Champion #<id>"` e `"Candidate #<id>"`. Neste momento seu contexto **não tem nenhum gabarito** — e tem de continuar assim.

### 6c. Coletar respostas (parse tolerante)

Para cada uma das 2N respostas: strip de markdown (` ```json `, ` ``` `); extrair entre primeiro `{` e último `}`; `JSON.parse`; falhou → `parse_error: true`; OK → capture `encontrada`, `valor`, `unidade`, `confianca`, `confianca_score`, `explicacao`, `sql_executado`, `bytes_processed`, `job_id`.

### 6d. Estabelecer a verdade via `golden-runner` (depois dos avaliadores; uma vez, vale p/ os dois lados)

Em **uma única mensagem**, dispare `N` `Agent(subagent_type="golden-runner")` — **um por pergunta** (não por lado; a verdade independe da KB):

```
Agent(
  subagent_type="golden-runner",
  description="Gabarito #<id>",
  prompt="""
KB_DIR: <KB_DIR>
QUESTION_ID: <id>
"""
)
```

Colete de cada um: `id`, `esperava_encontrar`, `gabarito_sql`, `resposta_esperada_unidade`, `tolerancia_relativa`, `valor_gabarito`, `gabarito_job_id`, `gabarito_bytes`, `gabarito_ok` — **mesma anti-alucinação do `/run-eval` Passo 5**: você nunca reescreve a SQL (nem a montou), `valor_gabarito` vem só do retorno, falha vira `erro_gabarito`. O mesmo `valor_gabarito` julga **os dois** lados.

### 6e. Conferência (scoring canônico do `/run-eval` Passo 6)

Para cada pergunta, aplique **as regras do `/run-eval` Passo 6** (6.0–6.5) **duas vezes** — uma com a resposta do champion, outra com a do candidate — sempre contra o **mesmo** resultado do `golden-runner`:

- `valor_referencia` = `valor_gabarito` do `golden-runner` (ou `null` se `gabarito_ok == false`).
- Se `esperava_encontrar == true` e `gabarito_ok == false`: `status = "erro_gabarito"` para **ambos** os lados (a verdade não existe nesta run) — `delta_* = null`, `dentro_tolerancia = false`.
- `encontrada_ok`, `unidade_ok` (usando `resposta_esperada_unidade` do `golden-runner`), comparação numérica (`tolerancia_relativa` do `golden-runner`), `execucao_ok` e `status` exatamente como no Passo 6 do `/run-eval`.

Não reimplemente as fórmulas aqui — o Passo 6 do `/run-eval` é a fonte canônica.

### 6f. Gravar 2 snapshots (formato `{ meta, results }`, modo champion/candidate)

`ts = $(date +%Y-%m-%dT%H-%M-%S)`. `mkdir -p <RESULTS_DIR>` se ausente.

Hashes (16 chars; nunca abortam — fallback PowerShell, depois `"unknown"`):
- `questions_hash` = sha256(16) de **`<SECRET_PATH>`** (identidade do benchmark; igual nos dois snapshots).
- **champion**: `kb_hash` = sha256(16) de `kb.md`; `kb_prompt_hash` = sha256(16) do `KB_CONTENT_CHAMPION` enviado (grave-o num arquivo de scratch e hasheie — não escreva em `knowledge-bases/`); `kb_integra = (kb_prompt_hash == kb_hash)`.
- **candidate**: `kb_hash` = sha256(16) de `kb-candidate.md`; `kb_prompt_hash` = sha256(16) do `KB_CONTENT_CANDIDATE` enviado; `kb_integra` = comparação correspondente.

Grave 2 arquivos no formato `{ meta, results }` — **mesmo bloco `meta` do Passo 7.4 do `/run-eval`** (com `kb_hash`, `kb_prompt_hash`, `kb_integra`, `questions_hash`, agregados `aprovados`/`reprovados`/`erros_gabarito`/`total`/`confianca_media`/`bytes_total`; `bytes_total` inclui os bytes do gabarito):

- `<RESULTS_DIR>/<ts>.champion.json` — `results` = N do champion; `meta.mode = "champion"`; hashes do champion; `meta.run_id = "<ts>"`.
- `<RESULTS_DIR>/<ts>.candidate.json` — `results` = N do candidate; `meta.mode = "candidate"`; hashes do candidate; `meta.run_id = "<ts>"`.

Cada elemento de `results` segue o **schema do Passo 7.4 do `/run-eval`** (com os campos de gabarito vindos do `golden-runner`). O `valor_gabarito` é idêntico nos dois arquivos (mesma verdade da run). A `pergunta` vem da face pública.

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

### 7c. AskUserQuestion: decisão

```
AskUserQuestion(
  question="Promover candidate → kb.md?",
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
- **Você lê SÓ a face pública**: o orquestrador nunca abre `questions.secret.json`. O gabarito chega como retorno do `golden-runner`, e só depois que os avaliadores responderam (Passo 6b antes do 6d). Ler a face secreta no orquestrador recria o vazamento que a separação física existe para impedir.
- **Inputs upfront**: todas as perguntas nos Passos 1a/2/7c, antes de invocar agents (exceto a decisão de promoção, que vem depois do eval).
- **Pulo binário de question-creator**: faces existem E sem `--regenerate-questions` → não invoca question-creator (mantém alvo fixo).
- **TARGET_PATH é binário**: `kb.md` para KB nova, `kb-candidate.md` para KB existente. Sem exceções.
- **Agents em paralelo**: kb-builder + question-creator no mesmo turno; 2N kb-evaluator no mesmo turno; N golden-runner no mesmo turno.
- **Gabarito é computado uma vez pelo `golden-runner`, verbatim, e compartilhado**: nunca regenerado, nunca no prompt do candidato; o mesmo `valor_gabarito` julga champion e candidate. Falha vira `erro_gabarito` nos dois lados — não vira regressão/melhoria.
- **Conferência usa o scoring canônico do `/run-eval` Passo 6**: não reimplemente as fórmulas.
- **Nunca ajuste manualmente as respostas dos subagentes**: registre o que retornaram.
- **Nunca leia kb.md no orquestrador para tomar decisões**: você lê só para passar ao kb-evaluator no 6a. A decisão de promoção é baseada em diff de resultados, não em diff de markdown.
- **Snapshots carregam `meta`**: champion/candidate são `{ meta, results }` com `mode` correspondente + `kb_prompt_hash`/`kb_integra` por lado. Só a consolidação (Passo 8) appenda a entrada canônica (`mode:"full"`) ao `_index.json`. Staging **nunca** entra na linha do tempo. Falha de índice/hash emite aviso, nunca aborta; `kb_integra == false` sinaliza, não aborta.
