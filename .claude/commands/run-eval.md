---
description: Avalia uma KB pronta — roda kb-evaluator paralelo (uma instância por pergunta) contra BigQuery, grava snapshot em results/. Requer kb.md e as faces de perguntas prévios (use /create-kb se não existirem). Uso `/run-eval <kb> [--quick]` (ex.: `/run-eval suporte`; `--quick` = check diário binário vs última run verde).
---

# Avaliação da KB (BigQuery)

Você (Claude principal) é o orquestrador. Sua única responsabilidade neste command é **rodar a avaliação** de uma KB já construída. Nada de sync, build ou geração de perguntas — tudo isso é responsabilidade do `/create-kb`.

Se `kb.md` ou as faces de perguntas não existem, este command **não constrói** — apenas aponta para `/create-kb`.

> **Isolamento do gabarito (a razão de ser deste fluxo).** As perguntas vivem em **duas faces** (Invariante #1 do CLAUDE.md): a **pública** (`questions.public.json` — `id`+`pergunta`) e a **secreta** (`questions.secret.json` — `gabarito_sql`+unidade+esperava+tolerância). **Você (orquestrador) lê SÓ a face pública.** A face secreta é lida exclusivamente pelo subagente `golden-runner`, que executa o gabarito e nunca monta prompt de avaliador. Por isso a ordem importa: você dispara os avaliadores a partir da face pública **antes** de qualquer gabarito existir no seu contexto — assim a fórmula da resposta é fisicamente incapaz de vazar para o prompt do candidato.

## Passo 0 — Validar `<kb>` + flags

1. Capture `<kb>` e detecte `--quick` em ARGUMENTS → `QUICK_MODE = true|false`. (`--quick` = check diário binário: mesma avaliação, baseline = última run verde, saída curta. Ver Passos 8 e 9.)
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
   - `PUBLIC_PATH = <KB_DIR>/questions.public.json`
   - `SECRET_PATH = <KB_DIR>/questions.secret.json`
   - `RESULTS_DIR = <KB_DIR>/results`

## Passo 1 — Validar artefatos

Via Bash `test -e`:
- **Se `<KB_PATH>` não existe**: imprima `kb.md ausente em <KB_PATH>. Rode /create-kb <kb> primeiro.` Pare.
- **Se `<PUBLIC_PATH>` não existe**: imprima `questions.public.json ausente em <PUBLIC_PATH>. Rode /create-kb <kb> primeiro.` Pare.
- **Se `<SECRET_PATH>` não existe**: imprima `questions.secret.json ausente em <SECRET_PATH>. Rode /create-kb <kb> --regenerate-questions para gerar as faces.` Pare.

> **Formato legado (`questions.json` único, sem faces).** Se `questions.public.json` não existe mas existe um `questions.json` antigo no diretório, imprima:
> `Detectado questions.json legado (formato antigo, sem faces). Rode /create-kb <kb> --regenerate-questions para migrar para as duas faces, ou migre manualmente.` e pare. Este command **não** lê o formato antigo — a separação em faces é pré-requisito do isolamento do gabarito.

Sem sync de repos. Sem AskUserQuestion. Sem agents de build. Este command é deliberadamente enxuto.

## Passo 2 — Preparar cópia isolada da KB + carregar face pública (NUNCA a secreta)

1. **Cópia isolada da KB (o avaliador a lê sozinho).** Você **não** lê mais o `kb.md` para embutir no prompt. Em vez disso, faça uma **cópia byte-exata** num diretório de scratch da sessão e passe aos avaliadores **apenas o caminho** dela.

   a. Defina `SCRATCH_DIR` = um diretório de scratch **opaco e único** da sessão (**fora** de `knowledge-bases/`), criado com `SCRATCH_DIR=$(python -c "import tempfile; print(tempfile.mkdtemp())")` — **não** `mktemp -d` (devolve caminho POSIX `/tmp/...` que a tool `Read` não abre no Windows/Git Bash). **O nome do `SCRATCH_DIR` NÃO pode conter o slug `<kb>` nem derivar dele** — senão o slug vaza embutido no `KB_FILE` (ver nota de isolamento abaixo). Se quiser registrar o caminho para debug, faça-o **só na sua saída**, nunca no prompt do avaliador.
   b. Via Bash: `cp "<KB_PATH>" "<SCRATCH_DIR>/kb.md"` (o `SCRATCH_DIR` já foi criado no passo a). Defina `KB_FILE = <SCRATCH_DIR>/kb.md`. O arquivo-cópia é sempre `kb.md` (nome genérico, sem slug).
   c. Meça o tamanho real para a verificação de integridade (Passo 7.2): `KB_LINHAS = $(wc -l < "<KB_PATH>")` via Bash.
   d. Compute o **marcador de EOF** para a prova de leitura íntegra (Passo 7.2): `KB_ULTIMA_LINHA` = a **última linha não-vazia** do `<KB_PATH>`, com `strip()` e truncada em **120 caracteres**. Use Python (mesma convenção do avaliador) — ex.: `python -c "import sys;ls=[l.rstrip('\n') for l in open(sys.argv[1],encoding='utf-8')];nb=[l for l in ls if l.strip()];print(nb[-1].strip()[:120] if nb else '')" "<KB_PATH>"`. Guarde o resultado como `KB_ULTIMA_LINHA`. **Este valor NUNCA entra no prompt do avaliador** — é só para conferência posterior (Passo 7.2).

   > **Cópia, não ditado.** Use `cp` (cópia byte-a-byte) — **nunca** reescreva, resuma, edite, filtre ou regere a KB, e **nunca** cole conteúdo de KB no prompt do avaliador. O avaliador tem de ler o `kb.md` **cru**.

   > **Isolamento — passe só o caminho da cópia.** Ao avaliador vai **apenas** `KB_FILE` (o caminho em scratch). **NUNCA** passe `KB_DIR`, o slug `<kb>`, nem qualquer caminho sob `knowledge-bases/`. **Isso inclui o próprio `KB_FILE`: o slug não pode aparecer em nenhuma parte do caminho — nem no nome do diretório de scratch, nem no do arquivo.** É isso que impede o avaliador de **localizar** a face secreta (`questions.secret.json`), que permanece só no `KB_DIR`.

2. Leia **somente** `<PUBLIC_PATH>` e parseie. Esperado: array de objetos `{ id (number), pergunta (string) }`. Guarde como `PERGUNTAS`. **Não leia `<SECRET_PATH>`** — ela não entra no seu contexto neste passo nem em nenhum momento da montagem dos prompts. Quem a lê é o `golden-runner` (Passo 5).

## Passo 3 — Disparar N kb-evaluator em paralelo (só com a face pública)

Para **cada** item de `PERGUNTAS`, invoque `Agent` com:

- `subagent_type`: `kb-evaluator`
- `description`: `"Avalia pergunta #<id>"`
- `prompt`: template abaixo, substituindo `<KB_FILE>` (o caminho da cópia, idêntico em todas as N chamadas) e `<PERGUNTA>` (a `pergunta` da face pública).

Template:
```
KB_FILE: <KB_FILE>

PERGUNTA:
<PERGUNTA>

Responda apenas com o objeto JSON especificado na sua definição. Sem texto antes, sem texto depois.
```

### Regras críticas

- **Todas as N chamadas em uma única mensagem** com múltiplos `tool_use` no mesmo turno → execução paralela. (Agora cabe: o prompt é enxuto — só caminho + pergunta.)
- Cada subagente recebe **somente uma pergunta** (a pública). Nunca passe múltiplas.
- Todos os prompts apontam para a **mesma** cópia (`KB_FILE`); o avaliador lê a KB **inteira** sozinho via `Read` (canal único de informação — ele mesmo busca).
- **`<PERGUNTA>` é copiada verbatim da face pública.** **PROIBIDO** reescrever a pergunta ou injetar dicas/fórmulas/conversões. Você não monta conteúdo de KB nenhum — não há o que resumir.
- **Passe SÓ `KB_FILE` (o caminho da cópia em scratch).** **NUNCA** passe `KB_DIR`, o slug `<kb>`, nem o caminho real do `kb.md` em `knowledge-bases/` — senão o avaliador poderia localizar a face secreta. **O slug também não pode estar embutido no `KB_FILE`** (nome do diretório de scratch ou do arquivo) — use `SCRATCH_DIR` opaco (Passo 2.1a). O canal é o **caminho da cópia**, não o texto da KB.
- Neste momento seu contexto **não tem nenhuma `gabarito_sql` nem valor de gabarito** — e é exatamente assim que tem de ser. Não leia a face secreta "para adiantar".

## Passo 4 — Coletar respostas dos avaliadores (parse tolerante)

Para cada resposta:

1. **Strip de markdown wrappers**: se começa com ` ```json ` ou ` ``` `, remova wrapper inicial e fechamento final.
2. **Strip de texto fora do JSON**: extraia entre primeiro `{` e último `}`.
3. `JSON.parse` no candidato.
4. Se falhar, registre `parse_error: true`, `_raw_output: "<truncado>"`, siga.
5. Se OK, capture: `encontrada`, `valor`, `unidade`, `confianca`, `confianca_score`, `explicacao`, `sql_executado`, `bytes_processed`, `job_id`, `kb_linhas_lidas`, `kb_ultima_linha`. Sinalize `parse_lenient: true` quando precisou de strip.

## Passo 5 — Estabelecer a verdade via `golden-runner` (depois que os avaliadores já responderam)

A verdade de cada pergunta **não é estática** — é o resultado de rodar a `gabarito_sql` **agora**, contra o BigQuery ao vivo. Isso absorve atualização retroativa dos dados: o número certo de ontem pode não ser o de hoje, e o gabarito acompanha automaticamente. **E o gabarito é executado por um ator isolado** (`golden-runner`), não por você — você nunca lê a `gabarito_sql`.

Para **cada** item de `PERGUNTAS`, invoque `Agent` com:

- `subagent_type`: `golden-runner`
- `description`: `"Gabarito #<id>"`
- `prompt`:
  ```
  KB_DIR: <KB_DIR>
  QUESTION_ID: <id>
  ```

### Regras críticas

- **Todas as N chamadas em uma única mensagem** (paralelo), igual aos avaliadores.
- **Só dispare os `golden-runner` depois de coletar as respostas dos avaliadores (Passo 4).** A ordem é o que garante o isolamento: quando o gabarito entra no seu contexto (como retorno do `golden-runner`), os prompts dos avaliadores já foram enviados e respondidos — não há mais onde vazar.
- Você **não** monta a SQL nem a passa no prompt: passa só `KB_DIR` + `id`. O `golden-runner` lê a face secreta sozinho.

Colete de cada `golden-runner` (parse tolerante igual ao Passo 4): `id`, `esperava_encontrar`, `gabarito_sql`, `resposta_esperada_unidade`, `tolerancia_relativa`, `valor_gabarito`, `gabarito_job_id`, `gabarito_bytes`, `gabarito_ok`. Esses campos são a sua **única** fonte de verdade e de parâmetros de tolerância/unidade — você não relê a face secreta.

> **Anti-alucinação do orquestrador (CRÍTICO).** Você **NUNCA** reescreve, "corrige", otimiza ou regenera a `gabarito_sql` (você nem a montou — veio do `golden-runner`). `valor_gabarito` vem **exclusivamente** do retorno do `golden-runner`; sem execução real → `gabarito_ok = false`/`null`. Se um `golden-runner` falhar, **não conserte a query nesta run**: a pergunta vira `status = "erro_gabarito"` na conferência — não é culpa do candidato.

## Passo 6 — Conferência (scoring canônico)

> Este é o **scoring canônico do projeto**. O `/create-kb` (Passo de avaliação champion-vs-candidate) aplica **exatamente estas mesmas regras** — referencie este passo, não duplique a lógica.

A conferência recebe, por pergunta, apenas: **a resposta do avaliador** (Passo 4) + **o resultado do `golden-runner`** (Passo 5). Não há nenhum outro caminho de informação. Para cada pergunta:

### 6.0 `valor_referencia` (precede tudo)

Define a verdade contra a qual o candidato será comparado:

- **`esperava_encontrar == true` e `gabarito_ok == false`** (do `golden-runner`): a verdade não pôde ser estabelecida nesta run → `status = "erro_gabarito"`. **Pule 6.1–6.5.** Registre `valor_referencia = null`, `delta_absoluto = null`, `delta_relativo = null`, `dentro_tolerancia = false`. Não é culpa do candidato — é o benchmark que quebrou.
- **`esperava_encontrar == true` e `gabarito_ok == true`**: `valor_referencia = valor_gabarito`. Siga para 6.1.
- **`esperava_encontrar == false`** (`gabarito_ok == null`): sem verdade numérica; `valor_referencia = null` (a avaliação é só sobre `encontrada`, ver 6.1).

### 6.1 `encontrada_ok`
- `encontrada_ok = (encontrada_obtida == esperava_encontrar)`
- Se `esperava_encontrar == false`:
  - Subagente retornou `encontrada: false` → passou; `dentro_tolerancia: true`, `delta_absoluto: null`, `delta_relativo: null`.
  - Subagente retornou `encontrada: true` → **reprovado** (alucinou).

### 6.2 `unidade_ok`
- Compare `unidade_obtida` (avaliador) com `resposta_esperada_unidade` (do `golden-runner`). Match case-insensitive. Tolere `"count"` ≡ `""` ≡ `"#"`. Moedas estrito (`"USD"` ≠ `"BRL"`).

### 6.3 Comparação numérica
Quando `esperava_encontrar == true`, `encontrada_obtida == true` e o `status` **não** foi fixado em `"erro_gabarito"` (6.0):
- `delta_absoluto = abs(valor_obtido - valor_referencia)`
- Se `valor_referencia != 0`: `delta_relativo = delta_absoluto / abs(valor_referencia)`
- Senão: `delta_relativo = (valor_obtido == 0) ? 0.0 : 1.0`
- `dentro_tolerancia = delta_relativo <= tolerancia_relativa` (a `tolerancia_relativa` veio do `golden-runner`).

### 6.4 `execucao_ok`
Aplique quando `encontrada_obtida == true`. `execucao_ok = true` se **todos**:
1. `sql_executado` é string não-vazia contendo `SELECT` (case-insensitive).
2. `bytes_processed` é integer `>= 0`.
3. `job_id` é string não-vazia com `len >= 8` casando `^[A-Za-z0-9_-]+$` (aceita UUID com hífen — **formato real** do `queryId` retornado pelo BigQuery Python client — e também o formato `bquxjob_...` do Console). **Não** exija "alfanumérico puro": o `queryId` real (`job.job_id`) tem hífens, e essa regra ao pé da letra reprovaria toda run.

Quando `encontrada_obtida == false`, `execucao_ok = null`.

### 6.5 `status`
- Se o `status` já foi fixado em `"erro_gabarito"` no 6.0, **mantenha** (tem precedência — a run não conseguiu estabelecer a verdade).
- Senão, `status = "aprovado"` se **todas**:
  1. `encontrada_ok == true`
  2. `unidade_ok == true` (ou `esperava_encontrar == false`)
  3. `dentro_tolerancia == true`
  4. `parse_error == false`
  5. `execucao_ok == true` (ou `esperava_encontrar == false`)
- Senão, `status = "reprovado"`.

Os três status são mutuamente exclusivos: `aprovado` (candidato bateu a verdade), `reprovado` (candidato errou), `erro_gabarito` (benchmark não rodou — candidato não foi julgado).

## Passo 7 — Gravar resultado (snapshot com `meta` + índice)

O snapshot é um objeto `{ meta, results }`. O array por-pergunta (`results`) traz um objeto por pergunta (schema no 7.3). O bloco `meta` carimba identidade e agregados da run; ele alimenta o `_index.json` (7.4), o alerta de regressão e o `/eval-report`.

### 7.1 Diretório e timestamp

1. `mkdir -p <RESULTS_DIR>` via Bash se necessário.
2. `RUN_ID = $(date +%Y-%m-%dT%H-%M-%S)` via Bash. O arquivo será `<RESULTS_DIR>/<RUN_ID>.json`.

### 7.2 Hashes de identidade + integridade da KB enviada (16 chars; nunca abortam)

São identidade, não segurança — colisão é irrelevante. Compute o sha256 (primeiros 16 chars):

```bash
sha256sum "<KB_PATH>" 2>/dev/null | head -c 16          # → kb_hash (kb.md em disco)
sha256sum "<SECRET_PATH>" 2>/dev/null | head -c 16       # → questions_hash (face secreta = identidade do benchmark)
```

Se `sha256sum` não existir, use o fallback PowerShell (resultado idêntico): `(Get-FileHash "<path>" -Algorithm SHA256).Hash.Substring(0,16).ToLower()`. Se **ambos** falharem, grave `"unknown"` e siga. **Nunca aborte a run por causa do hash.**

> `questions_hash` agora é o hash da **face secreta** (`questions.secret.json`) — é ela que define a identidade do benchmark (gabaritos + tolerâncias). A face pública por si só não distingue duas versões de gabarito.

**Verificação de KB íntegra (`kb_prompt_hash` + `kb_integra`).** Como o avaliador lê a KB de uma cópia byte-exata (`cp`, Passo 2.1b) e o orquestrador não manipula o conteúdo, use três checagens, todas baratas e nunca-abortantes:

1. **`kb_prompt_hash`** = sha256 (16 chars) da **cópia** que os avaliadores leram (`KB_FILE`):
   ```bash
   sha256sum "<KB_FILE>" 2>/dev/null | head -c 16   # → kb_prompt_hash (a cópia em scratch que o avaliador leu)
   ```
   Como veio de `cp "<KB_PATH>"`, confirma que a cópia é byte-a-byte o `kb.md` do disco. `kb_integra_arquivo = (kb_prompt_hash == kb_hash)` — `false` só se o `cp` corrompeu ou foi para um arquivo errado. Hashear a cópia aqui é o correto: é literalmente o que o avaliador leu.
2. **Prova de tamanho lido (sinal grosso)** — o hash não prova que o avaliador leu a KB toda, só que o arquivo está inteiro. Use o campo de prova `kb_linhas_lidas` (Passo 4) de cada avaliador contra `KB_LINHAS` (Passo 2.1c): se **algum** avaliador reportar `kb_linhas_lidas` fora de ±1 de `KB_LINHAS`, houve **leitura parcial** → run **suspeita**. (A tolerância ±1 é *slop* de convenção: `wc -l` conta `\n`, o `Read` pode numerar uma linha final sem `\n`. É dissuasor de recorte grosseiro, não prova de EOF — para isso serve a checagem 3.)
3. **Prova de leitura até o EOF (marcador de conteúdo)** — a prova forte de que o avaliador chegou ao **fim** da KB. Compare o campo `kb_ultima_linha` (Passo 4) de cada avaliador com `KB_ULTIMA_LINHA` (Passo 2.1d): se **algum** divergir (comparação exata das strings já normalizadas — `strip`, ≤120 chars), a leitura **não chegou ao fim** → run **suspeita**. Este marcador vem do `kb.md` (conteúdo público, não a face secreta) e o valor esperado **nunca** foi ao prompt do avaliador — por isso um agente que não tivesse lido o fim não teria como acertá-lo.
4. `kb_integra = (kb_integra_arquivo == true) E (todos os avaliadores com kb_linhas_lidas dentro de ±1 de KB_LINHAS) E (todos os avaliadores com kb_ultima_linha == KB_ULTIMA_LINHA)`. `true` → cópia íntegra, lida por inteiro **e** até o EOF por todos. `false` → **suspeita** (cópia corrompida, leitura parcial, ou não chegou ao fim); ainda assim **grave o snapshot normalmente** e reporte no Passo 9. Se `kb_prompt_hash`/`KB_LINHAS`/`KB_ULTIMA_LINHA` não computarem, grave `"unknown"` naquela sub-checagem (não a force para `false`) e, se nenhuma sub-checagem for conclusiva, `kb_integra = null` — **nunca aborte**.

### 7.3 Agregados

A partir do array `results` já avaliado (Passo 6):
- `aprovados` = nº com `status == "aprovado"`.
- `reprovados` = nº com `status == "reprovado"`.
- `erros_gabarito` = nº com `status == "erro_gabarito"`. (Benchmark não executou — **não** é reprovação do candidato. `aprovados + reprovados + erros_gabarito == total`.)
- `total` = tamanho de `results`.
- `confianca_media` = média de `confianca_score` sobre perguntas com `parse_error == false`, arredondada a 2 casas. Se nenhuma elegível, `0.0`.
- `bytes_total` = soma de `bytes_processed` (candidato) **+** `gabarito_bytes` (gabarito) de todas as perguntas, tratando `null` como `0`.

### 7.4 Gravar `{ meta, results }`

Defina `meta.mode = "quick"` se `QUICK_MODE`, senão `"full"`. Write em `<RESULTS_DIR>/<RUN_ID>.json` (pretty-print, indent=2):

```json
{
  "meta": {
    "kb": "<kb>",
    "run_id": "<RUN_ID>",
    "kb_hash": "<kb_hash ou unknown>",
    "kb_prompt_hash": "<kb_prompt_hash ou unknown>",
    "kb_integra": true,
    "kb_ultima_linha_esperada": "<KB_ULTIMA_LINHA ou unknown>",
    "questions_hash": "<questions_hash ou unknown>",
    "mode": "full",
    "aprovados": 5,
    "reprovados": 1,
    "erros_gabarito": 0,
    "total": 6,
    "confianca_media": 0.88,
    "bytes_total": 1264080
  },
  "results": [ /* array do Passo 6 — um objeto por pergunta, schema abaixo */ ]
}
```

Cada elemento de `results` segue este schema. O `valor_gabarito` e a `gabarito_sql` vêm do `golden-runner` (auditável depois via `gabarito_job_id`) e são gravados para auditoria — eles entram no seu contexto **só após** os avaliadores terem respondido:

```json
{
  "id": 1,
  "pergunta": "...",
  "resposta_esperada_unidade": "count",
  "esperava_encontrar": true,
  "tolerancia_relativa": 0.05,
  "gabarito_sql": "SELECT COALESCE(SUM(...), 0) FROM `...`",
  "valor_gabarito": 100000,
  "gabarito_job_id": "9f8e7d6c-4b2a-41e0-8c3d-1e2f3a4b5c6d",
  "gabarito_bytes": 252816,
  "gabarito_ok": true,
  "valor_obtido": 100000,
  "unidade_obtida": "count",
  "encontrada": true,
  "confianca": "alta",
  "confianca_score": 0.95,
  "explicacao": "...",
  "sql_executado": "SELECT COUNT(*) FROM `...`",
  "bytes_processed": 0,
  "job_id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
  "kb_linhas_lidas": 1407,
  "kb_ultima_linha": "| sum_of_interactions | INTEGER | total de interações do bot |",
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

> A `pergunta` no `results` vem da face pública. Os campos de gabarito vêm do `golden-runner`. Em `status == "erro_gabarito"`: `gabarito_ok = false`, `valor_gabarito = null`, e os campos do candidato ainda são preenchidos com o que ele retornou — mas `delta_*` ficam `null` e `dentro_tolerancia = false`.

> Os valores no schema acima são **exemplos ilustrativos** (como `valor_gabarito: 100000` e o `kb_ultima_linha` de exemplo), não fixos. Em especial, **`kb_linhas_lidas` e `kb_ultima_linha` são dinâmicos**: são a contagem real de linhas e a última linha não-vazia que o avaliador leu naquela run — **variam por KB e por versão**. O orquestrador compara `kb_linhas_lidas` com `KB_LINHAS` (`wc -l`) e `kb_ultima_linha` com `KB_ULTIMA_LINHA` (marcador de EOF do `kb.md` da própria run); se uma KB crescer/encolher, os dois lados acompanham juntos. Nada é hardcoded — divergência de linhas sinaliza leitura parcial; divergência do marcador sinaliza que a leitura não chegou ao fim. Os `job_id`/`gabarito_job_id` de exemplo são UUIDs (formato real do BigQuery Python client).

> `mode` é `"quick"` quando rodado com `--quick`; senão `"full"`. (Os modos `"champion"`/`"candidate"` pertencem ao `/create-kb` e viram `"full"` na promoção.)

### 7.5 Appendar ao índice (`_index.json` — append-only, tolerante a falha)

O índice `<RESULTS_DIR>/_index.json` é um array onde cada run appenda uma entrada **igual ao bloco `meta`** do 7.4. É a fonte rápida do `/eval-report` e do alerta de regressão — **derivado, não fonte de verdade** (reconstruível varrendo os `meta` dos snapshots).

1. Se `_index.json` **não** existe (`test -e`): crie com `[<meta>]`.
2. Se existe: Read → parse do array → **append** de `<meta>` ao fim → Write (indent=2). **Nunca** reescreva, reordene ou edite entradas anteriores.
3. **Falha de escrita do índice nunca aborta a run.** Se qualquer passo falhar (parse inválido, permissão, etc.), imprima e siga:
   ```
   ⚠ aviso: _index.json não atualizado (<motivo curto>). Snapshot gravado normalmente; índice é reconstruível via /eval-report.
   ```

## Passo 8 — Comparação longitudinal (custo zero)

Apenas cruza dados já presentes nos snapshots/índice — **nenhuma chamada nova ao BigQuery**. Se nada aplicar, siga ao Passo 9.

### 8.1 Localizar baseline

Leia `<RESULTS_DIR>/_index.json` (já contém a entrada da run atual, appendada no 7.5). O índice da KB só tem entradas canônicas (`mode` ∈ {`full`,`quick`}; champion/candidate nunca entram).

- **Modo normal (`full`):** `BASELINE` = entrada **imediatamente anterior** à run atual (penúltima). Sem anterior (1ª run da KB) → pule o Passo 8 e vá ao resumo.
- **Modo `--quick`:** `BASELINE` = entrada mais recente com `reprovados == 0`, excluindo a atual. Se nenhuma run 100% verde existir → use a anterior mais recente e marque `BASELINE_FALLBACK = true`. Sem nenhuma anterior → sem baseline (saída quick reporta só o estado atual).

Índice ausente/corrompido → **não aborte**: trate como "sem baseline" e siga (o snapshot já foi gravado).

### 8.2 Checar alvo móvel

Compare `questions_hash` da run atual com o do `BASELINE`:
- **Diferentes, OU qualquer um == `"unknown"`** → as perguntas mudaram (ou não dá para provar que são as mesmas); comparar por `id` perde validade. Marque `ALVO_MOVEL = true`, **não** reporte regressão, pule 8.3. (Dois `"unknown"` **não** contam como "iguais".)
- **Iguais e != `"unknown"`** → siga para 8.3.

### 8.3 Transições por pergunta

Carregue o snapshot do baseline (`<RESULTS_DIR>/<BASELINE.run_id>.json`) e leia seu `results`. **Tolere o formato antigo**: se o topo for array nu (sem `meta`), use o próprio array como `results`.

Para cada `id` presente nos dois, compare `status`:
- `aprovado → reprovado` = **regressão** → adicione a `REGRESSOES`.
- `reprovado → aprovado` = **melhoria** → adicione a `MELHORIAS`.
- igual = estável.
- Qualquer transição **de ou para `erro_gabarito`** = **não comparável** → **não** conta como regressão nem melhoria. Os itens em `erro_gabarito` na run atual são reportados à parte (Passo 9).

Para cada item, derive o `motivo curto` da run atual (mesma prioridade do Passo 9).

## Passo 9 — Saída no terminal

### 9a. Modo `--quick` — saída binária

Data de hoje via `date +%Y-%m-%d`. Imprima:

```
<kb> — check diário (<YYYY-MM-DD>)
  baseline: <data do BASELINE.run_id> (<BASELINE.aprovados>/<BASELINE.total> aprovado)
  agora:    <aprovados>/<total>
  [para cada item em REGRESSOES: "⚠ #<id> regrediu: <motivo curto>"]
  [se erros_gabarito > 0: "✖ <erros_gabarito> gabarito(s) não executaram (benchmark) — #<ids>"]
  [se kb_integra == false: "⚠ KB suspeita: conteúdo enviado ≠ kb.md em disco (kb_prompt_hash != kb_hash)"]

  KB ainda condiz? <SIM|NÃO> — <justificativa>
```

Regras:
- `SIM` se `REGRESSOES` vazio **e** `erros_gabarito == 0` **e** `aprovados == total` **e** `kb_integra != false`; senão `NÃO`.
- Justificativa: `SIM` → `<total>/<total> dentro da tolerância.` · `NÃO` com regressões → `<len(REGRESSOES)> pergunta(s) fora de tolerância.` · `NÃO` com `erros_gabarito > 0` → `<erros_gabarito> gabarito(s) não executaram — verifique o questions.secret.json / conexão BigQuery.` · `NÃO` com `kb_integra == false` → `KB enviada ao avaliador diverge do kb.md em disco — resultado não confiável.` · `NÃO` sem regressão vs baseline → `<reprovados> reprovada(s).`.
- `BASELINE_FALLBACK == true` → acrescente `  (sem run 100% verde anterior — baseline = run mais recente)`.
- `ALVO_MOVEL == true` → troque as linhas baseline/regressão por `  ⚠ benchmark mudou desde a última run — comparação não aplicável.`; reporte só `agora:` e decida `SIM/NÃO` pelo estado atual.
- Sem baseline (1ª run) → `  baseline: — (primeira run)`; decida pelo estado atual.

No modo quick, **encerre aqui** (não imprima 9b).

### 9b. Modo normal (`full`)

Se `kb_integra == false`, imprima **antes de tudo** o alerta de integridade:
```
⚠ KB SUSPEITA: a KB que os avaliadores usaram não corresponde ao kb.md íntegro em disco, ou não foi lida até o fim.
  kb_hash (disco):      <kb_hash>
  kb_prompt_hash (cópia): <kb_prompt_hash>
  KB_LINHAS (disco): <KB_LINHAS>  ·  kb_linhas_lidas divergentes: #<ids>
  KB_ULTIMA_LINHA (disco): "<KB_ULTIMA_LINHA>"  ·  kb_ultima_linha divergentes: #<ids>
  Provável causa: cópia de scratch corrompida/errada (hash difere) OU leitura parcial (linhas divergem) OU leitura não chegou ao EOF (última linha diverge).
  Trate os resultados desta run com desconfiança e rode novamente.
────────────────────────────────────────
```

Se `REGRESSOES` não vazio e `ALVO_MOVEL != true`, imprima o alerta de regressão **antes** do resumo:

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
ℹ alvo móvel: benchmark (questions.secret.json) mudou desde a run anterior — regressão não comparável.
```
Primeira run (sem baseline): nada antes do resumo.

Em seguida, o resumo padrão:

```
KB avaliada:  <kb>
Snapshot:     <RESULTS_DIR>/<RUN_ID>.json
Integridade KB: <OK | SUSPEITA (kb_prompt_hash != kb_hash)>
Aprovados:    X/N
Reprovados:   Y/N
Erros de gabarito: G/N   [omita a linha se G == 0]
Confiança média: Z

Reprovados:
  #<id> — <motivo curto>
  ...

[se G > 0:]
Erros de gabarito (benchmark não executou — NÃO é falha do candidato; corrija a gabarito_sql na face secreta ou a conexão BigQuery):
  #<id> — gabarito_falhou
  ...
```

Motivo curto (em ordem de prioridade):
- `gabarito_falhou` se `status == "erro_gabarito"` (a `gabarito_sql` não executou — listado no bloco próprio acima).
- `parse_error` se JSON malformado.
- `encontrada esperada=X, obtida=Y` se discrepância de encontrada.
- `unidade esperada=X, obtida=Y` se discrepância de unidade.
- `delta_relativo=Z (tolerância=T)` se fora da tolerância.
- `execucao_ausente (sql=<missing|empty>, bytes=<...>, job_id=<...>)` se `execucao_ok=false`.

## Regras invioláveis

- **Você lê SÓ a face pública**: o orquestrador nunca abre `questions.secret.json`. A `gabarito_sql` e o `valor_gabarito` chegam exclusivamente como **retorno do `golden-runner`**, e só depois que os avaliadores já responderam. Ler a face secreta no orquestrador recria o vazamento que a separação física existe para impedir.
- **Ordem é isolamento**: avaliadores (Passo 3) **antes** dos `golden-runner` (Passo 5). Em nenhum momento da montagem do prompt do avaliador o seu contexto contém o gabarito.
- **Não constrói nada**: se kb.md ou as faces estão ausentes, este command aponta para `/create-kb` e termina.
- **kb-evaluator e golden-runner são sempre paralelos**: N tool_uses em uma única mensagem, cada grupo no seu turno.
- **Gabarito é executado verbatim pelo `golden-runner`**: a `gabarito_sql` roda como está, nunca regenerada/corrigida na run, nunca incluída no prompt do `kb-evaluator`. Falha vira `erro_gabarito` (não reprovação). Determinismo é garantido por validação de prova (`gabarito_job_id`/`gabarito_bytes`), não por "quem executou".
- **Verdade é dinâmica**: a referência de comparação é `valor_gabarito` (resultado da run atual), não um número fixo. Dois runs com o mesmo `questions_hash` podem ter `valor_gabarito` diferente (drift de dados) — e isso é correto: o `status` por pergunta permanece estável apesar do drift.
- **Conferência é o scoring canônico**: o `/create-kb` referencia o Passo 6, não reimplementa.
- **Nunca ajuste manualmente as respostas dos subagentes**: registre o que retornaram.
- **Idempotente**: rodar 2× produz 2 snapshots distintos (e 2 entradas no `_index.json`, append-only) sem alterar `kb.md` nem as faces.
- **Sem AskUserQuestion**: este command roda sem interação.
- **Snapshot é `{ meta, results }`**: o array por-pergunta vai dentro de `results`. Snapshots antigos (array nu, sem `meta`) são tolerados na leitura e **nunca** reescritos.
- **Índice e hashes nunca abortam**: `_index.json` é append-only e não-crítico; sha256 que falhar grava `"unknown"`. `kb_integra == false` **sinaliza** (run suspeita) mas **não** aborta.
- **Prova de leitura íntegra é conferida, nunca ditada**: o `KB_ULTIMA_LINHA` (marcador de EOF) e o `KB_LINHAS` são computados pelo orquestrador a partir do `kb.md` e **nunca** entram no prompt do avaliador. O avaliador produz `kb_ultima_linha`/`kb_linhas_lidas` cego, a partir do que leu; o orquestrador só compara **depois** de coletar. O marcador vem da KB (conteúdo público), nunca da face secreta — não afeta o isolamento do gabarito.
- **`--quick` é só apresentação**: usa a MESMA avaliação e grava+indexa snapshot normalmente (`mode:"quick"`). Muda apenas o baseline (última run verde) e o formato de saída.
- **Comparação longitudinal é custo zero**: regressão/baseline cruzam só snapshots/índice — nunca disparam BigQuery extra.
