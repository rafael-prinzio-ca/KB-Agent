---
description: Avalia uma KB pronta — roda kb-evaluator paralelo (uma instância por pergunta) contra BigQuery, grava snapshot em results/. Requer kb.md e questions.json prévios (use /create-kb se não existirem). Uso `/run-eval <kb> [--quick]` (ex.: `/run-eval suporte`; `--quick` = check diário binário vs última run verde).
---

# Avaliação da KB (BigQuery)

Você (Claude principal) é o orquestrador. Sua única responsabilidade neste command é **rodar a avaliação** de uma KB já construída. Nada de sync, build ou geração de perguntas — tudo isso é responsabilidade do `/create-kb`.

Se `kb.md` ou `questions.json` não existem, este command **não constrói** — apenas aponta para `/create-kb`.

## Passo 0 — Validar `<kb>` + flags

1. Capture `<kb>` e detecte `--quick` em ARGUMENTS → `QUICK_MODE = true|false`. (`--quick` = check diário binário: mesma avaliação, baseline = última run verde, saída curta. Ver Passos 7 e 8.)
2. **Se `<kb>` ausente/vazio**: liste KBs disponíveis via Bash:
   ```
   Uso: /run-eval <kb> [--quick]
   KBs disponíveis: <lista>
   ```
   Pare.
3. **Se `knowledge-bases/<kb>/` não existe**: imprima `KB "<kb>" não encontrada. Rode /create-kb <kb> primeiro.` Pare.
4. Defina:
   - `KB_DIR = knowledge-bases/<kb>`
   - `KB_PATH = <KB_DIR>/kb.md`
   - `QUESTIONS_PATH = <KB_DIR>/questions.json`
   - `RESULTS_DIR = <KB_DIR>/results`

## Passo 1 — Validar artefatos

Via Bash `test -e`:
- **Se `<KB_PATH>` não existe**: imprima `kb.md ausente em <KB_PATH>. Rode /create-kb <kb> primeiro.` Pare.
- **Se `<QUESTIONS_PATH>` não existe**: imprima `questions.json ausente em <QUESTIONS_PATH>. Rode /create-kb <kb> primeiro.` Pare.

Sem sync de repos. Sem AskUserQuestion. Sem agents de build. Este command é deliberadamente enxuto.

## Passo 2 — Carregar inputs

1. Leia `<KB_PATH>` em **2 chamadas Read sequenciais** (KBs podem exceder 25K tokens):
   - `Read(file_path="<KB_PATH>", limit=650)` — primeira metade
   - `Read(file_path="<KB_PATH>", offset=650)` — segunda metade

   Concatene em `KB_CONTENT`.

2. Leia `<QUESTIONS_PATH>` e parseie. Esperado: array de objetos com:
   - `id` (number), `pergunta` (string), `resposta_esperada_valor` (number | null), `resposta_esperada_unidade` (string), `esperava_encontrar` (boolean), `tolerancia_relativa` (number), `_nota` (string, ignorada).

## Passo 3 — Disparar N kb-evaluator em paralelo

Para **cada** pergunta no array, invoque `Agent` com:

- `subagent_type`: `kb-evaluator`
- `description`: `"Avalia pergunta #<id>"`
- `prompt`: template abaixo, substituindo `<KB_CONTENT>` e `<PERGUNTA>`.

Template:
```
BASE DE CONHECIMENTO:
<KB_CONTENT>

PERGUNTA:
<PERGUNTA>

Responda apenas com o objeto JSON especificado na sua definição. Sem texto antes, sem texto depois.
```

### Regras críticas

- **Todas as N chamadas em uma única mensagem** com múltiplos `tool_use` no mesmo turno → execução paralela.
- Cada subagente recebe **somente uma pergunta**. Nunca passe múltiplas.
- KB completa em **cada** prompt (canal único de informação textual).
- **Nunca passe `KB_PATH:` no prompt** do subagente — passe o conteúdo literal.

## Passo 4 — Coletar respostas (parse tolerante)

Para cada resposta:

1. **Strip de markdown wrappers**: se começa com ` ```json ` ou ` ``` `, remova wrapper inicial e fechamento final.
2. **Strip de texto fora do JSON**: extraia entre primeiro `{` e último `}`.
3. `JSON.parse` no candidato.
4. Se falhar, registre `parse_error: true`, `_raw_output: "<truncado>"`, siga.
5. Se OK, capture: `encontrada`, `valor`, `unidade`, `confianca`, `confianca_score`, `explicacao`, `sql_executado`, `bytes_processed`, `job_id`. Sinalize `parse_lenient: true` quando precisou de strip.

## Passo 5 — Avaliar (comparação numérica)

Para cada pergunta:

### 5.1 `encontrada_ok`
- `encontrada_ok = (encontrada_obtida == esperava_encontrar)`
- Se `esperava_encontrar == false`:
  - Subagente retornou `encontrada: false` → passou; `dentro_tolerancia: true`, `delta_absoluto: null`, `delta_relativo: null`.
  - Subagente retornou `encontrada: true` → **reprovado** (alucinou).

### 5.2 `unidade_ok`
- Match case-insensitive. Tolere `"count"` ≡ `""` ≡ `"#"`. Moedas estrito (`"USD"` ≠ `"BRL"`).

### 5.3 Comparação numérica
Quando `esperava_encontrar == true` e `encontrada_obtida == true`:
- `delta_absoluto = abs(valor_obtido - resposta_esperada_valor)`
- Se `resposta_esperada_valor != 0`: `delta_relativo = delta_absoluto / abs(resposta_esperada_valor)`
- Senão: `delta_relativo = (valor_obtido == 0) ? 0.0 : 1.0`
- `dentro_tolerancia = delta_relativo <= tolerancia_relativa`

### 5.4 `execucao_ok`
Aplique quando `encontrada_obtida == true`. `execucao_ok = true` se **todos**:
1. `sql_executado` é string não-vazia contendo `SELECT` (case-insensitive).
2. `bytes_processed` é integer `>= 0`.
3. `job_id` é string não-vazia, alfanumérica, `len >= 8`.

Quando `encontrada_obtida == false`, `execucao_ok = null`.

### 5.5 `status`
`status = "aprovado"` se **todas**:
1. `encontrada_ok == true`
2. `unidade_ok == true` (ou `esperava_encontrar == false`)
3. `dentro_tolerancia == true`
4. `parse_error == false`
5. `execucao_ok == true` (ou `esperava_encontrar == false`)

Senão, `status = "reprovado"`.

## Passo 6 — Gravar resultado (snapshot com `meta` + índice)

O snapshot deixa de ser um array nu e passa a ser um objeto `{ meta, results }`. O array por-pergunta (`results`) é **idêntico ao formato atual** — nada muda dentro de cada objeto. O bloco `meta` carimba identidade e agregados da run; ele alimenta o `_index.json` (Passo 6.5), o alerta de regressão e o `/eval-report`.

### 6.1 Diretório e timestamp

1. `mkdir -p <RESULTS_DIR>` via Bash se necessário.
2. `RUN_ID = $(date +%Y-%m-%dT%H-%M-%S)` via Bash. O arquivo será `<RESULTS_DIR>/<RUN_ID>.json`.

### 6.2 Hashes de identidade (16 chars; nunca abortam)

São identidade, não segurança — colisão é irrelevante. Compute o sha256 (primeiros 16 chars) de `kb.md` e `questions.json`:

```bash
sha256sum "<KB_PATH>" 2>/dev/null | head -c 16          # → kb_hash
sha256sum "<QUESTIONS_PATH>" 2>/dev/null | head -c 16    # → questions_hash
```

Se `sha256sum` não existir, use o fallback PowerShell (resultado idêntico):
```
(Get-FileHash "<KB_PATH>" -Algorithm SHA256).Hash.Substring(0,16).ToLower()
```
Se **ambos** falharem, grave `"unknown"` no campo e siga. **Nunca aborte a run por causa do hash.**

### 6.3 Agregados

A partir do array `results` já avaliado (Passo 5):
- `aprovados` = nº de perguntas com `status == "aprovado"`.
- `reprovados` = nº com `status == "reprovado"`.
- `total` = tamanho de `results`.
- `confianca_media` = média de `confianca_score` sobre perguntas com `parse_error == false`, arredondada a 2 casas decimais. Se nenhuma elegível, `0.0`.
- `bytes_total` = soma de `bytes_processed` de todas as perguntas, tratando `null` como `0`. (Prepara acompanhamento de custo BigQuery.)

### 6.4 Gravar `{ meta, results }`

Defina `meta.mode = "quick"` se `QUICK_MODE`, senão `"full"`. Write em `<RESULTS_DIR>/<RUN_ID>.json` (pretty-print, indent=2):

```json
{
  "meta": {
    "kb": "<kb>",
    "run_id": "<RUN_ID>",
    "kb_hash": "<kb_hash ou unknown>",
    "questions_hash": "<questions_hash ou unknown>",
    "mode": "full",
    "aprovados": 5,
    "reprovados": 1,
    "total": 6,
    "confianca_media": 0.88,
    "bytes_total": 1264080
  },
  "results": [ /* array do Passo 5 — um objeto por pergunta, schema abaixo, INALTERADO */ ]
}
```

Cada elemento de `results` mantém **exatamente** o schema atual (nada removido, nada renomeado):

```json
{
  "id": 1,
  "pergunta": "...",
  "resposta_esperada_valor": 100000,
  "resposta_esperada_unidade": "count",
  "esperava_encontrar": true,
  "tolerancia_relativa": 0.05,
  "valor_obtido": 100000,
  "unidade_obtida": "count",
  "encontrada": true,
  "confianca": "alta",
  "confianca_score": 0.95,
  "explicacao": "...",
  "sql_executado": "SELECT COUNT(*) FROM `...`",
  "bytes_processed": 0,
  "job_id": "bquxjob_1a2b3c4d_18f9e0a7b21",
  "encontrada_ok": true,
  "unidade_ok": true,
  "delta_absoluto": 0,
  "delta_relativo": 0.0,
  "dentro_tolerancia": true,
  "parse_error": false,
  "execucao_ok": true,
  "status": "aprovado"
}
```

> `mode` é `"quick"` quando rodado com `--quick`; senão `"full"`. (Os modos `"champion"`/`"candidate"` pertencem ao `/create-kb` e viram `"full"` na promoção.)

### 6.5 Appendar ao índice (`_index.json` — append-only, tolerante a falha)

O índice `<RESULTS_DIR>/_index.json` é um array onde cada run appenda uma entrada **igual ao bloco `meta`** do Passo 6.4. É a fonte rápida do `/eval-report` e do alerta de regressão — **derivado, não fonte de verdade** (reconstruível varrendo os `meta` dos snapshots).

1. Se `_index.json` **não** existe (`test -e`): crie com `[<meta>]`.
2. Se existe: Read → parse do array → **append** de `<meta>` ao fim → Write (indent=2). **Nunca** reescreva, reordene ou edite entradas anteriores.
3. **Falha de escrita do índice nunca aborta a run.** Se qualquer passo falhar (parse inválido, permissão, etc.), imprima e siga:
   ```
   ⚠ aviso: _index.json não atualizado (<motivo curto>). Snapshot gravado normalmente; índice é reconstruível via /eval-report.
   ```

## Passo 7 — Comparação longitudinal (custo zero)

Apenas cruza dados já presentes nos snapshots/índice — **nenhuma chamada nova ao BigQuery**. Se nada aplicar, siga ao Passo 8.

### 7.1 Localizar baseline

Leia `<RESULTS_DIR>/_index.json` (já contém a entrada da run atual, appendada no Passo 6.5). O índice da KB só tem entradas canônicas (`mode` ∈ {`full`,`quick`}; champion/candidate nunca entram).

- **Modo normal (`full`):** `BASELINE` = entrada **imediatamente anterior** à run atual (penúltima). Sem anterior (1ª run da KB) → pule o Passo 7 e vá ao resumo.
- **Modo `--quick`:** `BASELINE` = entrada mais recente com `reprovados == 0`, excluindo a atual (decisão B). Se nenhuma run 100% verde existir → use a anterior mais recente e marque `BASELINE_FALLBACK = true`. Sem nenhuma anterior → sem baseline (saída quick reporta só o estado atual).

Índice ausente/corrompido → **não aborte**: trate como "sem baseline" e siga (o snapshot já foi gravado).

### 7.2 Checar alvo móvel

Compare `questions_hash` da run atual com o do `BASELINE`:
- **Diferentes** → as perguntas mudaram; comparar por `id` perde validade. Marque `ALVO_MOVEL = true`, **não** reporte regressão, pule 7.3.
- **Iguais** → siga para 7.3.

### 7.3 Transições por pergunta

Carregue o snapshot do baseline (`<RESULTS_DIR>/<BASELINE.run_id>.json`) e leia seu `results`. **Tolere o formato antigo**: se o topo for array nu (sem `meta`), use o próprio array como `results`.

Para cada `id` presente nos dois, compare `status`:
- `aprovado → reprovado` = **regressão** → adicione a `REGRESSOES`.
- `reprovado → aprovado` = **melhoria** → adicione a `MELHORIAS`.
- igual = estável.

Para cada item, derive o `motivo curto` da run atual (mesma prioridade do Passo 8).

## Passo 8 — Saída no terminal

### 8a. Modo `--quick` — saída binária

Data de hoje via `date +%Y-%m-%d`. Imprima:

```
<kb> — check diário (<YYYY-MM-DD>)
  baseline: <data do BASELINE.run_id> (<BASELINE.aprovados>/<BASELINE.total> aprovado)
  agora:    <aprovados>/<total>
  [para cada item em REGRESSOES: "⚠ #<id> regrediu: <motivo curto>"]

  KB ainda condiz? <SIM|NÃO> — <justificativa>
```

Regras:
- `SIM` se `REGRESSOES` vazio **e** `aprovados == total`; senão `NÃO`.
- Justificativa: `SIM` → `<total>/<total> dentro da tolerância.` · `NÃO` com regressões → `<len(REGRESSOES)> pergunta(s) fora de tolerância.` · `NÃO` sem regressão vs baseline → `<reprovados> reprovada(s).`.
- `BASELINE_FALLBACK == true` → acrescente `  (sem run 100% verde anterior — baseline = run mais recente)`.
- `ALVO_MOVEL == true` → troque as linhas baseline/regressão por `  ⚠ questions.json mudou desde a última run — comparação não aplicável.`; reporte só `agora:` e decida `SIM/NÃO` pelo estado atual (`aprovados == total`).
- Sem baseline (1ª run) → `  baseline: — (primeira run)`; decida pelo estado atual.

No modo quick, **encerre aqui** (não imprima 8b).

### 8b. Modo normal (`full`)

Se `REGRESSOES` não vazio e `ALVO_MOVEL != true`, imprima o alerta **antes** do resumo:

```
⚠ REGRESSÃO vs run anterior (<BASELINE.run_id>)
  #<id>  aprovado → reprovado
         <motivo curto>
  [se kb_hash atual != kb_hash do baseline: "contexto: kb_hash mudou (<base> → <atual>) — provável causa: kb.md editado/promovido."]
  [para cada item em MELHORIAS: "✨ #<id> reprovado → aprovado"]
  (questions_hash igual → comparação válida)
────────────────────────────────────────
```

Se `ALVO_MOVEL == true`, em vez do bloco acima:
```
ℹ alvo móvel: questions.json mudou desde a run anterior — regressão não comparável.
```
Primeira run (sem baseline): nada antes do resumo.

Em seguida, o resumo padrão:

```
KB avaliada:  <kb>
Snapshot:     <RESULTS_DIR>/<RUN_ID>.json
Aprovados:    X/N
Reprovados:   Y/N
Confiança média: Z

Reprovados:
  #<id> — <motivo curto>
  ...
```

Motivo curto (em ordem de prioridade):
- `parse_error` se JSON malformado.
- `encontrada esperada=X, obtida=Y` se discrepância de encontrada.
- `unidade esperada=X, obtida=Y` se discrepância de unidade.
- `delta_relativo=Z (tolerância=T)` se fora da tolerância.
- `execucao_ausente (sql=<missing|empty>, bytes=<...>, job_id=<...>)` se `execucao_ok=false`.

## Regras invioláveis

- **Não constrói nada**: se kb.md ou questions.json estão ausentes, este command aponta para `/create-kb` e termina. Não tenta sync, não invoca kb-builder, não invoca question-creator.
- **kb-evaluator é sempre paralelo**: N tool_uses em uma única mensagem.
- **Nunca ajuste manualmente as respostas dos subagentes**: registre o que retornaram.
- **Idempotente**: rodar 2× produz 2 snapshots distintos em `results/` (e 2 entradas no `_index.json`, append-only) sem alterar `kb.md` ou `questions.json`.
- **Sem AskUserQuestion**: este command roda sem interação. Se algum input fosse necessário, ele veio do `/create-kb` antes.
- **Snapshot é `{ meta, results }`**: nunca volte ao array nu; o array por-pergunta vai dentro de `results`, byte a byte inalterado. Snapshots antigos (array nu, sem `meta`) são tolerados na leitura e **nunca** reescritos.
- **Índice é append-only e não-crítico**: `_index.json` nunca reescreve entradas anteriores; falha ao gravá-lo emite aviso mas **não** aborta a run.
- **Hash nunca aborta**: se o sha256 de `kb.md`/`questions.json` falhar, grave `"unknown"` e siga.
- **`--quick` é só apresentação**: usa a MESMA avaliação (N kb-evaluator paralelos no BigQuery) e grava+indexa snapshot normalmente (`mode:"quick"`). Muda apenas o baseline (última run verde, decisão B) e o formato de saída (binário). Sem `--quick`: comportamento idêntico ao anterior + os carimbos novos.
- **Comparação longitudinal é custo zero**: regressão/baseline cruzam só snapshots/índice — nunca disparam BigQuery extra. Ausência de baseline/índice degrada para "sem comparação", nunca aborta.
