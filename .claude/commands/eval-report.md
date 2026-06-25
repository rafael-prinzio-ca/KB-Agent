---
description: Relatório histórico de qualidade de uma KB — leitura pura (sem agentes, sem BigQuery). Lê os snapshots/índice em results/, imprime tabela de tendência no terminal e gera um HTML standalone (offline, sem dependências) em reports/<kb>-history.html para compartilhar com gestores. Uso `/eval-report <kb>` (ex.: `/eval-report suporte`).
---

# Relatório histórico da KB (leitura pura)

Você (Claude principal) é o orquestrador. Este command **não avalia nada** — não dispara `kb-evaluator`, não chama BigQuery, não toca `kb.md`/`questions.json`. Ele só **lê** o histórico já gravado em `results/` e produz duas saídas: uma tabela no terminal e um HTML standalone para gestores não-técnicos.

É barato e idempotente: rodar 2× regenera o mesmo HTML (sobrescreve `reports/<kb>-history.html`) sem tocar em snapshots.

## Passo 0 — Validar `<kb>`

1. Capture `<kb>`.
2. **Se ausente/vazio**: liste KBs via Bash e pare:
   ```
   Uso: /eval-report <kb>
   KBs disponíveis: <lista de knowledge-bases/*/>
   ```
3. **Se `knowledge-bases/<kb>/` não existe**: imprima `KB "<kb>" não encontrada. Rode /create-kb <kb> primeiro.` Pare.
4. Defina:
   - `KB_DIR = knowledge-bases/<kb>`
   - `RESULTS_DIR = <KB_DIR>/results`
   - `INDEX_PATH = <RESULTS_DIR>/_index.json`
   - `REPORTS_DIR = <KB_DIR>/reports`
   - `HTML_PATH = <REPORTS_DIR>/<kb>-history.html`

## Passo 1 — Carregar o histórico (índice, com fallback de reconstrução)

Objetivo: montar `RUNS` = lista de entradas `meta` (uma por run **canônica**), em ordem cronológica crescente por `run_id`.

### 1a. Caminho rápido — índice existe

Se `INDEX_PATH` existe (`test -e`): Read + `JSON.parse`. Cada elemento já é um bloco `meta`. Ordene por `run_id` crescente. Esse é o `RUNS`.

### 1b. Fallback — reconstruir varrendo snapshots

Se o índice **não** existe (ou o parse falhou): reconstrua a partir dos snapshots.

1. `Glob("<RESULTS_DIR>/*.json")`.
2. **Exclua**: `_index.json` e qualquer `*.champion.json` / `*.candidate.json` (staging A/B — decisão A: não entram na linha do tempo).
3. Para cada arquivo restante (`<run_id>.json`): Read + parse e **tolere os dois formatos**:
   - **Novo** (`{ meta, results }`): use `meta` direto.
   - **Antigo** (array nu, sem `meta`): derive um `meta` parcial:
     - `kb = "<kb>"`, `run_id` = nome do arquivo sem `.json`, `kb_hash = "unknown"`, `questions_hash = "unknown"`, `mode = "full"`.
     - `total` = `len(array)`; `aprovados`/`reprovados` = contagem por `status`; `confianca_media` = média de `confianca_score` onde `parse_error != true` (2 casas; 0.0 se nenhuma); `bytes_total` = soma de `bytes_processed` (null→0).
4. Ordene por `run_id` crescente → `RUNS`.

> Reconstruir é seguro: o índice é **derivado**. Não regrave o índice aqui (isso é responsabilidade do `/run-eval` e `/create-kb`). Apenas use os dados em memória.

### 1c. Sem histórico

Se `RUNS` ficou vazio: imprima e pare (não gere HTML):
```
Nenhuma avaliação encontrada para "<kb>". Rode /run-eval <kb> primeiro.
```

## Passo 2 — Detalhe da última run

Seja `LAST = RUNS[-1]` (run mais recente).

1. Leia o snapshot `<RESULTS_DIR>/<LAST.run_id>.json` (tolere os dois formatos: `{meta,results}` → use `results`; array nu → use o próprio array).
2. Para cada item de `results`, monte um objeto enxuto para o relatório:
   - `id`, `pergunta` (string; pode truncar para ~80 chars na exibição), `status`.
   - `esperava_encontrar`.
   - `esperado` = `valor_gabarito` (verdade-corrente da run; **fallback** `resposta_esperada_valor` em snapshots legados), `obtido` = `valor_obtido`, `unidade` = `unidade_obtida` (ou `resposta_esperada_unidade`).
   - `delta_relativo`, `tolerancia` = `tolerancia_relativa`.
   - `motivo`: vazio se `status == "aprovado"`; se `status == "erro_gabarito"` → `gabarito_falhou` (benchmark não executou — não é falha do candidato); senão o motivo curto na ordem de prioridade: `parse_error` › `encontrada esperada=X obtida=Y` › `unidade esperada=X obtida=Y` › `delta_relativo=Z (tol=T)` › `execucao_ausente`.

> O template renderiza qualquer `status != "aprovado"` (incluindo `erro_gabarito`) com a pill vermelha "reprovado" e a observação no `motivo` — não altere o template por isso. O `esperado` (=`valor_gabarito`) varia entre runs por design (gabarito dinâmico); não é regressão.
3. Se o arquivo de `LAST` não existir (índice aponta para snapshot removido): use o snapshot existente mais recente; se nenhum, deixe `questions = []` e siga.

## Passo 3 — Computar Δ e marcadores entre runs

Para cada run `i` em `RUNS` (comparando com `i-1`), compute campos derivados que serão exibidos:

- `kb_changed` = `RUNS[i].kb_hash != RUNS[i-1].kb_hash` (e ambos != `"unknown"`).
- `questions_changed` = `RUNS[i].questions_hash != RUNS[i-1].questions_hash` (e ambos != `"unknown"`).
- `delta` (string curta):
  - `i == 0` → `"—"`.
  - `questions_changed` → `"perguntas mudaram"` (comparação de aprovados perde sentido).
  - senão, compare `aprovados`:
    - `> anterior` → `"✨ melhorou (+<k>)"`.
    - `< anterior` → `"⚠ regrediu (−<k>)"`.
    - `==` → `"estável"`.
  - Se `kb_changed`, anexe ` (kb mudou)`.
- **Detalhe por pergunta (best-effort, só enriquece o `delta`)**: se quiser identificar *quais* ids regrediram entre `i-1` e `i`, e ambos os snapshots existem e têm o mesmo `questions_hash`, carregue os dois `results` e liste os ids com `aprovado→reprovado` (ex.: `"⚠ regrediu #4 (kb mudou)"`). Se algum snapshot faltar ou for alvo móvel, fique só no Δ agregado. Não falhe por isso.

Guarde `kb_changed`, `questions_changed` e `delta` em cada entrada de `RUNS`.

## Passo 4 — Tabela de tendência no terminal

```
KB: <kb> — histórico de avaliações

run                    modo    aprovados  conf.média  kb_hash   Δ
<run_id>               <mode>  <ap>/<tot> <conf>      <hash6>   <delta>
...

HTML: <HTML_PATH>
```

- `kb_hash` curto = 6 primeiros chars + `…` (ou `—` se `"unknown"`).
- Alinhe as colunas. Liste em ordem cronológica (mais antiga no topo).
- Se algum snapshot é formato antigo (hash `unknown`), tudo bem — exibe `—` na coluna `kb_hash`.

## Passo 5 — Gerar o HTML standalone

1. `mkdir -p "<REPORTS_DIR>"` via Bash.
2. Data de geração: `date +%Y-%m-%d` → `GENERATED_AT`.
3. Monte o objeto `DATA` (será embutido como JSON inline no HTML):

```json
{
  "kb": "<kb>",
  "generated_at": "<GENERATED_AT>",
  "runs": [
    {
      "run_id": "...", "mode": "full|quick",
      "kb_hash": "...", "questions_hash": "...",
      "aprovados": 0, "reprovados": 0, "total": 0,
      "confianca_media": 0.0, "bytes_total": 0,
      "delta": "...", "kb_changed": false, "questions_changed": false
    }
  ],
  "last_run": {
    "run_id": "...", "mode": "...",
    "aprovados": 0, "total": 0, "confianca_media": 0.0, "bytes_total": 0,
    "questions": [
      { "id": 1, "pergunta": "...", "status": "aprovado|reprovado",
        "esperava_encontrar": true, "esperado": 0, "obtido": 0, "unidade": "count",
        "delta_relativo": 0.0, "tolerancia": 0.05, "motivo": "" }
    ]
  }
}
```

4. Gere `<HTML_PATH>` com **Write**, copiando o TEMPLATE abaixo **verbatim** e substituindo o marcador `__DATA_JSON__` (única ocorrência) pelo `DATA` serializado como JSON. Não altere o CSS/JS do template — só injete o JSON.

### TEMPLATE (copiar literal; trocar `__DATA_JSON__` pelo JSON do DATA)

```html
<!DOCTYPE html>
<!-- Relatório self-contained. Funciona offline, sem dependências externas (gráfico = SVG desenhado por JS inline). -->
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Histórico de Qualidade — KB</title>
<style>
  :root{
    --bg:#ffffff; --fg:#1f2937; --muted:#6b7280; --line:#e5e7eb; --card:#f9fafb;
    --ok:#16a34a; --bad:#dc2626; --accent:#2563eb; --accent2:#d97706; --warn:#b45309;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    font-size:14px;line-height:1.5;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .wrap{max-width:960px;margin:0 auto;padding:32px 24px 64px}
  header h1{font-size:22px;margin:0 0 4px}
  header .sub{color:var(--muted);font-size:13px}
  h2{font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
    margin:36px 0 12px;font-weight:600}
  .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:20px}
  .card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
  .card .lbl{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
  .card .val{font-size:24px;font-weight:700;margin-top:6px}
  .card .note{font-size:12px;color:var(--muted);margin-top:2px}
  .card .note.bad{color:var(--bad)} .card .note.ok{color:var(--ok)}
  .chart{border:1px solid var(--line);border-radius:10px;padding:12px}
  svg{display:block;width:100%;height:auto}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
  th{color:var(--muted);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
  td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
  .pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600}
  .pill.ok{background:#dcfce7;color:#166534} .pill.bad{background:#fee2e2;color:#991b1b}
  .tag{font-size:11px;color:var(--warn);background:#fef3c7;border-radius:6px;padding:1px 6px;margin-left:6px}
  .delta-bad{color:var(--bad);font-weight:600} .delta-ok{color:var(--ok);font-weight:600}
  .delta-mut{color:var(--muted)}
  code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;color:var(--muted)}
  .legend{display:flex;gap:18px;font-size:12px;color:var(--muted);margin:4px 2px 0}
  .legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:middle}
  footer{margin-top:48px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:12px}
  .qtrunc{max-width:420px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  @media print{ .wrap{max-width:none;padding:0} .chart,.card{break-inside:avoid} }
  @media (max-width:680px){ .cards{grid-template-columns:repeat(2,1fr)} }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1 id="title">KB — Histórico de Qualidade</h1>
    <div class="sub" id="subtitle"></div>
  </header>

  <div class="cards" id="cards"></div>

  <h2>Aprovados e confiança ao longo do tempo</h2>
  <div class="chart">
    <div id="chart"></div>
    <div class="legend">
      <span><i style="background:#2563eb"></i>Aprovados (% do total)</span>
      <span><i style="background:#d97706"></i>Confiança média</span>
      <span><i style="background:#b45309;border-radius:50%"></i>KB alterada nesta run</span>
    </div>
  </div>

  <h2>Por run</h2>
  <table id="runs"><thead><tr>
    <th>Run</th><th>Modo</th><th class="num">Aprovados</th><th class="num">Conf.</th>
    <th>kb_hash</th><th>Δ vs anterior</th>
  </tr></thead><tbody></tbody></table>

  <h2>Detalhe da última run</h2>
  <div class="sub" id="lastinfo" style="margin-bottom:10px"></div>
  <table id="questions"><thead><tr>
    <th class="num">#</th><th>Pergunta</th><th class="num">Esperado</th>
    <th class="num">Obtido</th><th>Status</th><th>Observação</th>
  </tr></thead><tbody></tbody></table>

  <footer>
    Gerado por <code>/eval-report</code> · arquivo único, funciona offline (sem dependências externas).
    Dados embutidos no momento da geração; reabrir não recalcula nada.
  </footer>
</div>

<script>
const DATA = __DATA_JSON__;

const $ = (id)=>document.getElementById(id);
const pct = (a,t)=> t>0 ? a/t : 0;
const fmtPct = (x)=> (x*100).toFixed(0)+"%";
const shortHash = (h)=> (!h||h==="unknown") ? "—" : h.slice(0,6)+"…";
const shortDate = (rid)=> (rid||"").slice(0,10);
const gb = (b)=> (b/1e9);

// ---- header ----
$("title").textContent = "KB: "+DATA.kb+" — Histórico de Qualidade";
$("subtitle").textContent = "Gerado em "+DATA.generated_at+" · "+DATA.runs.length+
  " avaliação(ões) · fonte: BigQuery";

// ---- cards ----
(function(){
  const L = DATA.last_run || {aprovados:0,total:0,confianca_media:0,bytes_total:0};
  const runs = DATA.runs;
  let deltaNote = "—", cls = "";
  if(runs.length>=2){
    const prev = runs[runs.length-2], cur = runs[runs.length-1];
    const d = cur.aprovados - prev.aprovados;
    if(cur.questions_changed){ deltaNote="perguntas mudaram"; }
    else if(d<0){ deltaNote="▼ "+d+" vs run anterior"; cls="bad"; }
    else if(d>0){ deltaNote="▲ +"+d+" vs run anterior"; cls="ok"; }
    else { deltaNote="estável vs run anterior"; }
  }
  const gbv = gb(L.bytes_total||0);
  const cost = (L.bytes_total||0)/1e12 * 5; // ~US$5/TB on-demand (estimativa)
  const cards = [
    {lbl:"Aprovados (última run)", val:(L.aprovados||0)+" / "+(L.total||0), note:deltaNote, cls:cls},
    {lbl:"Confiança média", val:(L.confianca_media!=null?L.confianca_media.toFixed(2):"—"), note:""},
    {lbl:"Última run", val:shortDate(L.run_id||"—"), note:(L.mode||"")},
    {lbl:"Custo BigQuery", val:gbv.toFixed(2)+" GB", note:"≈ US$ "+cost.toFixed(2)+" (a US$5/TB)"},
  ];
  $("cards").innerHTML = cards.map(c=>
    `<div class="card"><div class="lbl">${c.lbl}</div><div class="val">${c.val}</div>`+
    `<div class="note ${c.cls||""}">${c.note||""}</div></div>`).join("");
})();

// ---- SVG line chart (aprovados% + confiança) ----
(function(){
  const runs = DATA.runs;
  const W=860,H=320,P={t:20,r:24,b:54,l:42};
  const iw=W-P.l-P.r, ih=H-P.t-P.b;
  const n=runs.length;
  const X = (i)=> n<=1 ? P.l+iw/2 : P.l + iw*i/(n-1);
  const Y = (v)=> P.t + ih*(1-v);
  const NS="http://www.w3.org/2000/svg";
  const svg=document.createElementNS(NS,"svg");
  svg.setAttribute("viewBox","0 0 "+W+" "+H);
  svg.setAttribute("role","img");
  const add=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);svg.appendChild(e);return e;};

  // gridlines + y labels
  [0,0.25,0.5,0.75,1].forEach(g=>{
    add("line",{x1:P.l,y1:Y(g),x2:W-P.r,y2:Y(g),stroke:"#eef2f7","stroke-width":1});
    const tx=add("text",{x:P.l-8,y:Y(g)+4,"text-anchor":"end","font-size":11,fill:"#9ca3af"});
    tx.textContent=fmtPct(g);
  });

  const series=(getter,color)=>{
    const pts=runs.map((r,i)=>[X(i),Y(getter(r))]);
    if(pts.length>1){
      add("polyline",{points:pts.map(p=>p.join(",")).join(" "),fill:"none",stroke:color,"stroke-width":2.5,"stroke-linejoin":"round"});
    }
    runs.forEach((r,i)=>{
      add("circle",{cx:X(i),cy:Y(getter(r)),r:3.5,fill:color});
    });
  };
  series(r=>pct(r.aprovados,r.total),"#2563eb");
  series(r=>r.confianca_media||0,"#d97706");

  // mark kb_changed points (ring on the aprovados line)
  runs.forEach((r,i)=>{
    if(r.kb_changed){
      add("circle",{cx:X(i),cy:Y(pct(r.aprovados,r.total)),r:6.5,fill:"none",stroke:"#b45309","stroke-width":2});
    }
  });

  // x labels (thin out if many)
  const step = Math.ceil(n/8);
  runs.forEach((r,i)=>{
    if(i%step!==0 && i!==n-1) return;
    const tx=add("text",{x:X(i),y:H-P.b+20,"text-anchor":"middle","font-size":11,fill:"#9ca3af"});
    tx.textContent=shortDate(r.run_id);
  });

  $("chart").appendChild(svg);
})();

// ---- runs table ----
(function(){
  const tb=$("runs").querySelector("tbody");
  tb.innerHTML = DATA.runs.map(r=>{
    let dcls="delta-mut";
    if(/regrediu|▼/.test(r.delta)) dcls="delta-bad";
    else if(/melhorou|▲|✨/.test(r.delta)) dcls="delta-ok";
    const tags = (r.kb_changed?'<span class="tag">kb_hash mudou</span>':"")+
                 (r.questions_changed?'<span class="tag">perguntas mudaram</span>':"");
    return `<tr>
      <td><code>${shortDate(r.run_id)}</code>${tags}</td>
      <td>${r.mode||""}</td>
      <td class="num">${r.aprovados}/${r.total}</td>
      <td class="num">${r.confianca_media!=null?r.confianca_media.toFixed(2):"—"}</td>
      <td><code>${shortHash(r.kb_hash)}</code></td>
      <td class="${dcls}">${r.delta||"—"}</td>
    </tr>`;
  }).join("");
})();

// ---- questions table ----
(function(){
  const L=DATA.last_run||{questions:[]};
  $("lastinfo").textContent = "Run "+shortDate(L.run_id||"—")+" · "+(L.aprovados||0)+"/"+(L.total||0)+" aprovados";
  const tb=$("questions").querySelector("tbody");
  tb.innerHTML = (L.questions||[]).map(q=>{
    const ok = q.status==="aprovado";
    const esp = q.esperava_encontrar===false ? "—" : (q.esperado!=null?q.esperado:"—");
    const obt = q.obtido!=null?q.obtido:"—";
    return `<tr>
      <td class="num">${q.id}</td>
      <td><div class="qtrunc" title="${(q.pergunta||"").replace(/"/g,'&quot;')}">${q.pergunta||""}</div></td>
      <td class="num">${esp}</td>
      <td class="num">${obt}</td>
      <td><span class="pill ${ok?"ok":"bad"}">${ok?"aprovado":"reprovado"}</span></td>
      <td><span class="${ok?"delta-mut":"delta-bad"}">${q.motivo||(ok?"ok":"")}</span></td>
    </tr>`;
  }).join("");
})();
</script>
</body>
</html>
```

## Passo 6 — Confirmar no terminal

Após gravar, imprima:
```
✓ Relatório gerado: <HTML_PATH>
  Runs no histórico: <N>   |   Última: <LAST.run_id> (<aprovados>/<total>)
  Abra no navegador (arquivo único, funciona offline).
```

## Regras invioláveis

- **Leitura pura**: nunca dispara `kb-evaluator`, nunca chama BigQuery, nunca edita `kb.md`/`questions.json`/snapshots/índice. Só lê `results/` e escreve em `reports/`.
- **Tolera os dois formatos de snapshot**: `{ meta, results }` novo e array nu antigo. Hash ausente vira `—`/`"unknown"`, nunca quebra.
- **Staging fora da linha do tempo**: ao reconstruir, ignore `*.champion.json`/`*.candidate.json` (decisão A).
- **Índice é derivado**: pode reconstruir a partir dos snapshots, mas **não regrava** `_index.json` (isso é do `/run-eval` e `/create-kb`).
- **HTML self-contained**: um único arquivo, sem dependências externas (gráfico é SVG desenhado por JS inline). Nunca referencie CDN/URL externa.
- **Idempotente**: rodar 2× sobrescreve `reports/<kb>-history.html` com os mesmos dados; nada mais muda.
- **Sem AskUserQuestion**: roda direto a partir de `<kb>`.
