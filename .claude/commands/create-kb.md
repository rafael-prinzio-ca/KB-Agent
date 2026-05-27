---
description: Cria ou atualiza uma KB. Sincroniza repos GitHub, coleta inputs (período + URLs Looker/Metabase + definições), dispara kb-builder + question-creator em PARALELO (cada um chama os MCPs independente). Em KB com kb.md existente, gera kb-candidate.md, roda eval contra ambos com as mesmas questions e oferece promoção via diff. Uso `/create-kb <kb> [--regenerate-questions]`.
---

# Criar/atualizar KB (champion-vs-candidate)

Você (Claude principal) é o orquestrador. Sua missão é construir ou atualizar a KB `<kb>`. Você **é o único ponto de interação com o usuário** — sub-agents não fazem AskUserQuestion. Coleta tudo upfront e passa via prompt estruturado.

**Princípio fundamental**: `kb-builder` e `question-creator` rodam em paralelo, cada um chamando os MCPs Looker/Metabase **independente**. O `question-creator` **NÃO** lê o `kb.md` gerado pelo `kb-builder` — isso evita "alvo móvel" (KB e perguntas que evoluem juntas, mascarando se a melhoria é real).

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
   - `QUESTIONS_PATH = <KB_DIR>/questions.json`
   - `RESULTS_DIR = <KB_DIR>/results`
6. Inspecione (via Bash `test -e`):
   - `KB_EXISTS`
   - `QUESTIONS_EXISTS`
   - `CANDIDATE_ORPHAN = test -e <CANDIDATE_PATH>` (de execução anterior interrompida)

### 1a. Tratar candidate órfão

Se `CANDIDATE_ORPHAN == true`: AskUserQuestion `"kb-candidate.md órfão encontrado de execução anterior. Como proceder?"` — header `"Candidate órfão"` — opções:
- `"Descartar e gerar candidate novo"` → `rm <CANDIDATE_PATH>` via Bash; siga.
- `"Usar como ponto de partida (não regenera)"` → marque `SKIP_BUILD = true`; pule Passo 4a (kb-builder).
- `"Abortar /create-kb"` → pare imediatamente.

### 1b. Imprimir status

```
Status da KB "<kb>":
  kb.md          : [✓ existe | ✗ ausente]
  questions.json : [✓ existe | ✗ ausente]
  --regenerate-questions : [sim | não]

Plano:
  kb-builder       → escrever em [kb.md (KB nova) | kb-candidate.md (KB existente)]
  question-creator → [executado | pulado (mantém questions atuais)]
  kb-evaluator     → [executado contra candidate+champion | pulado (KB nova; rode /run-eval depois)]
```

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
- `QUESTIONS_EXISTS == false` → `true` (sem questions não há como avaliar)
- `QUESTIONS_EXISTS == true` E `--regenerate-questions` → `true`
- `QUESTIONS_EXISTS == true` E sem flag → `false` (mantém — alvo fixo)

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
  description="Gera questions.json para <kb>",
  prompt="""
KB_NAME: <kb>
KB_DIR: <KB_DIR>
QUESTIONS_PATH: <QUESTIONS_PATH>
MODE: <create se !QUESTIONS_EXISTS; senão overwrite>
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

> Note: `question-creator` recebe as MESMAS URLs que o `kb-builder`. Cada um vai chamar os MCPs Looker/Metabase próprios — duplicação intencional para garantir isolamento (question-creator não vê o que kb-builder fez).

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
✓ questions.json: <QUESTIONS_PATH> (<num_total> perguntas)
[se SYNC_STALE: "⚠ ATENÇÃO: repos GitHub não foram sincronizados — KB pode estar com código defasado."]

Próximo: rode `/run-eval <kb>` para avaliar a qualidade.
```

Fim do command. Não roda eval automaticamente.

## Passo 6 — Modo candidate: avaliar ambos (TARGET_PATH == kb-candidate.md)

### 6a. Ler questions e KBs

1. Leia `<QUESTIONS_PATH>` (1 Read) e parseie como array.
2. Leia `<KB_PATH>` (champion) em 2 Reads sequenciais (KBs podem exceder 25K tokens):
   - `Read(file_path="<KB_PATH>", limit=650)`
   - `Read(file_path="<KB_PATH>", offset=650)`
   Concatene em `KB_CONTENT_CHAMPION`.
3. Leia `<CANDIDATE_PATH>` (candidate) em 2 Reads sequenciais. Concatene em `KB_CONTENT_CANDIDATE`.

### 6b. Disparar 2N kb-evaluator em paralelo

Em **uma única mensagem**, dispare `2 * N` (N = número de perguntas) `Agent(subagent_type="kb-evaluator")`:

- N instâncias com `KB_CONTENT_CHAMPION` + cada uma das perguntas.
- N instâncias com `KB_CONTENT_CANDIDATE` + cada uma das perguntas.

Template do prompt (mesmo de `/run-eval`):

```
BASE DE CONHECIMENTO:
<KB_CONTENT_(CHAMPION|CANDIDATE)>

PERGUNTA:
<PERGUNTA>

Responda apenas com o objeto JSON especificado na sua definição. Sem texto antes, sem texto depois.
```

Use `description` distinto para rastrear: `"Champion #<id>"` e `"Candidate #<id>"`.

### 6c. Coletar respostas (parse tolerante)

Para cada resposta:
1. Strip de markdown wrappers (` ```json `, ` ``` `).
2. Extrair entre primeiro `{` e último `}`.
3. `JSON.parse`.
4. Falhou → `parse_error: true`.
5. OK → capture `encontrada`, `valor`, `unidade`, `confianca`, `confianca_score`, `explicacao`, `sql_executado`, `bytes_processed`, `job_id`.

### 6d. Avaliar (idêntico ao /run-eval)

Para cada pergunta (champion e candidate separadamente):
- `encontrada_ok` = `encontrada_obtida == esperava_encontrar`
- `unidade_ok` (case-insensitive; `count`/`""`/`#` equivalentes; moedas estrito)
- Quando `esperava_encontrar == true` e `encontrada == true`:
  - `delta_absoluto = abs(valor_obtido - resposta_esperada_valor)`
  - `delta_relativo = delta_absoluto / abs(resposta_esperada_valor)` (ou 0/1 se esperado=0)
  - `dentro_tolerancia = delta_relativo <= tolerancia_relativa`
- `execucao_ok`: SQL contém SELECT, bytes >= 0, job_id len >= 8 alfanumérico.
- `status = "aprovado"` se todas: `encontrada_ok && (unidade_ok || !esperava) && dentro_tolerancia && !parse_error && (execucao_ok || !esperava)`.

### 6e. Gravar 2 snapshots

Timestamp via `date +%Y-%m-%dT%H-%M-%S`.

Grave 2 arquivos (mesmo schema do `/run-eval`):
- `<RESULTS_DIR>/<ts>.champion.json` (array dos N resultados champion)
- `<RESULTS_DIR>/<ts>.candidate.json` (array dos N resultados candidate)

`mkdir -p <RESULTS_DIR>` se ausente.

## Passo 7 — Diff + decisão

### 7a. Computar diff

Para cada pergunta, determine `transicao`:
- `mantém_aprovado` (aprovado → aprovado)
- `mantém_reprovado` (reprovado → reprovado)
- `melhorou` (reprovado → aprovado)
- `regrediu` (aprovado → reprovado)

Compute totals:
- `aprovados_champion`, `aprovados_candidate`
- `confianca_media_champion`, `confianca_media_candidate`

### 7b. Imprimir tabela

```
Champion (kb.md) vs Candidate (kb-candidate.md):
  Aprovados:       X/N → Y/N    (Δ +/-Z)
  Reprovados:      (N-X)/N → (N-Y)/N
  Confiança média: A → B

Mudanças por pergunta:
  #1 mantém aprovado
  #2 mantém aprovado
  #3 mantém aprovado
  #4 reprovado → aprovado  ✨ melhorou
  #5 mantém aprovado
  #6 aprovado → reprovado  ⚠ regrediu  (motivo: <curto>)
```

Motivo curto para regressão/melhoria:
- `parse_error`
- `encontrada esperada=X obtida=Y`
- `unidade esperada=X obtida=Y`
- `delta_relativo=Z (tol=T)`
- `execucao_ausente`

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

Imprima:
```
✓ Candidate descartado. kb.md permanece como estava.
  Snapshot do champion atual: knowledge-bases/<kb>/results/<ts>.json
```

### Opção: Manter para inspeção

Não move/deleta nada. Os 2 arquivos `.champion.json` e `.candidate.json` permanecem como staging.

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
⚠ NOTA: questions.json foi regenerado. Backup em knowledge-bases/<kb>/questions.json.bak.<ts>.
   Comparações com snapshots anteriores em results/ ficam menos significativas (alvo móvel).
```

## Regras invioláveis

- **Você é o único que conversa com o usuário** — sub-agents não fazem AskUserQuestion.
- **Inputs upfront**: todas as perguntas nos Passos 1a/2/7c, antes de invocar agents (exceto a decisão de promoção, que naturalmente vem depois do eval).
- **Pulo binário de question-creator**: questions.json existe E sem `--regenerate-questions` → não invoca question-creator (mantém alvo fixo).
- **TARGET_PATH é binário**: `kb.md` para KB nova, `kb-candidate.md` para KB existente. Sem exceções.
- **Agents em paralelo**: kb-builder + question-creator no mesmo turno via 2 tool_uses na mesma mensagem.
- **kb-evaluator é sempre paralelo no candidate flow**: 2N tool_uses em uma única mensagem.
- **Nunca ajuste manualmente as respostas dos subagentes**: registre o que retornaram.
- **Nunca leia kb.md no orquestrador para tomar decisões**: você lê só para passar ao kb-evaluator no Passo 6a. A decisão de promoção é baseada em diff de resultados, não em diff de markdown.
