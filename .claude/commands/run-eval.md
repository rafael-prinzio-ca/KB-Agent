---
description: Avalia uma KB pronta — roda kb-evaluator paralelo (uma instância por pergunta) contra BigQuery, grava snapshot em results/. Requer kb.md e questions.json prévios (use /create-kb se não existirem). Uso `/run-eval <kb>` (ex.: `/run-eval suporte`).
---

# Avaliação da KB (BigQuery)

Você (Claude principal) é o orquestrador. Sua única responsabilidade neste command é **rodar a avaliação** de uma KB já construída. Nada de sync, build ou geração de perguntas — tudo isso é responsabilidade do `/create-kb`.

Se `kb.md` ou `questions.json` não existem, este command **não constrói** — apenas aponta para `/create-kb`.

## Passo 0 — Validar `<kb>`

1. Capture `<kb>`.
2. **Se ausente/vazio**: liste KBs disponíveis via Bash:
   ```
   Uso: /run-eval <kb>
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

## Passo 6 — Gravar resultado

1. `mkdir -p <RESULTS_DIR>` via Bash se necessário.
2. Timestamp via Bash: `date +%Y-%m-%dT%H-%M-%S`.
3. Write array em `<RESULTS_DIR>/<timestamp>.json` (pretty-print, indent=2). Estrutura por pergunta:

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

## Passo 7 — Resumo no terminal

```
KB avaliada:  <kb>
Snapshot:     <RESULTS_DIR>/<timestamp>.json
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
- **Idempotente**: rodar 2× produz 2 snapshots distintos em `results/` sem alterar `kb.md` ou `questions.json`.
- **Sem AskUserQuestion**: este command roda sem interação. Se algum input fosse necessário, ele veio do `/create-kb` antes.
