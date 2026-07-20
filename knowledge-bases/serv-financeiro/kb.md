# Serviços Financeiros — Banking Mensal (serv-financeiro)
> Gerado em 2026-07-16
> Período de referência: 2026-06-01 a 2026-06-30 (junho/2026 — último mês fechado)
> Fontes:
> - Looker: dashboard 1180 " Serviços Financeiros - Overview Banking Mensal" (abas MDR, Clientes, Crédito) — explore `financial_services_data_mart :: sf_banking_mensal` [WIP]
> - Metabase: —

## 1. Visão Geral

Esta KB cobre os indicadores de **Serviços Financeiros (Banking)** exibidos no dashboard Looker 1180 e suas métricas de apoio: **MDR** (receita por meio, clientes ativos, churn, ARPU, LTV), **Payments** (TPV, Take Rate, Gross Revenue), **Float**, **Crédito** e **MDP**.

Duas camadas de fonte:
- **contaazul-ssbi** — tabelas `gold_mdr.fact_actual` e `gold_mdr.fact_track_backend` materializadas pelo Dataform (`repos/gcp-dataform-contaazul`). São a base autoritativa dos indicadores de **MDR e Payments** — para esses há queries validadas abaixo.
- **banking-ssbi** — tabelas `gold_core_banking.*`, `gold_credit.*` e `silver_wall_street.*`. Sustentam **Float, Float Revenue, Saldo EOD, Crédito, MDP e TPV Cash In/Out**. O Dataform desse projeto (`repos/gcp-dataform-banking`) **está sincronizado**: o **Saldo Positivo (EOD) / Clientes Ativos Float** (3.12) foi aterrado em código e tem **query validada**. Os demais itens banking (TPV Cash In/Out, Float Revenue, Crédito, MDP) seguem documentados por definição + FQN + medida no Looker, **sem query validada** (a serem aterrados em seus próprios intents).

> ⚠️ **DOIS PROJETOS GCP.** As fontes vivem em `banking-ssbi` **e** `contaazul-ssbi`. O default do sistema é `contaazul-ssbi`. **Toda** query/tabela DEVE usar FQN completo com o projeto **explícito** (ex.: `` `banking-ssbi.gold_core_banking.fact_transactions` ``). Uma query sem projeto resolveria para `contaazul-ssbi` e quebraria nas tabelas de `banking-ssbi`.

## 2. Tabelas e Schemas

### `contaazul-ssbi.gold_mdr.fact_actual`
- Registro dos documentos de Meios de Recebimento (MDR) **agrupado** por data, cliente, método de pagamento e comissão da cobrança. Fonte da maioria das medidas MDR do explore (`receita_*`, `clientes_ativos_mdr`, `arpu_mdr`, `novos`/`reativados`/`sairam`, `churn_*`, `ltv_mdr`).
- Campos principais: `nk_date` (DATE — data de **criação** nas linhas de emissão OU de **liquidação/compensação** nas linhas de compensação), `nk_customer_id`, `nk_method` (= `original_method_type`, ex.: `PIXLETO`), `nk_billet_commission`, `total_issuance`, `total_compensations`, `sum_of_value` (valor cobrado), `sum_of_amount_paid` (valor pago), `sum_of_fee_value` (valor de taxa), `sum_of_revenue_ca` (**receita CA — só em docs compensados**), `sum_of_gross_profit` (lucro após custos).
- Definição em código: `repos/gcp-dataform-contaazul/definitions/gold/mdr/tables/fact_actual.sqlx`
- Nota de lineage: `sum_of_revenue_ca` e demais agregados de compensação só são preenchidos onde `nk_acquit_date != '0001-01-01'`; linhas de emissão pura têm esses campos = 0.

### `contaazul-ssbi.gold_mdr.fact_track_backend`
- Registro **granular** (por cobrança) dos documentos de Meios de Recebimento (fonte: `silver_mdr.payments_track_backend`). Base do `fact_actual` e origem direta de **TPV / Take Rate / Gross Revenue** (Payments).
- Campos principais: `nk_customer_id`, `nk_status`, `nk_method` (método adaptado, ex.: `BANK_SLIP`), `original_method_type` (sem adaptação, ex.: `PIXLETO`), `billet_commission`, `nk_created_date`, `nk_acquit_date` (DATE da liquidação; sentinela `'0001-01-01'` = não liquidado), `nk_due_date`, `sum_of_value`, `sum_of_amount_paid`, `sum_of_fee_value`, `sum_of_revenue_ca`, `sum_of_gross_profit`.
- Definição em código: `repos/gcp-dataform-contaazul/definitions/gold/mdr/tables/fact_track_backend.sqlx`

### `contaazul-ssbi.gold_mdr.dim_track_backend_method`
- Lista de métodos de recebimento: `nk_method` (código) + `method_label` (rótulo). Populada de `silver_mdr.param_backend_method_type` (valores vêm da fonte, não hardcoded).
- Definição em código: `repos/gcp-dataform-contaazul/definitions/gold/mdr/tables/dim_track_backend_method.sqlx`

### `contaazul-ssbi.gold_common.dim_date`
- Dimensão de datas. `nk_date` é **DATE** (padrão `yyyy-mm-dd`) — por isso os `nk_*_date` das fatos são comparáveis diretamente com `@inicio`/`@fim` (DATE), sem cast.
- Definição em código: `repos/gcp-dataform-contaazul/definitions/gold/common/tables/dim_date.sqlx`

### `banking-ssbi.gold_core_banking.dim_company_float_by_day`
- Saldo/float diário por empresa. Base da medida "Clientes Ativos Float" / Saldo Positivo (EOD) — ver 3.12.
- Campos (**confirmados em código**): `nk_company_id` (identificador do cliente/empresa — vem de `contaazul_company_id`, **sem sentinela `-1`**), `nk_balance_date` (DATE — data do saldo), `float_value` (**receita de float atribuída ao cliente** em BRL, rateada pelo share de saldo — **não** é o saldo bruto nem o Float Revenue total da companhia), `provider` (`'iugu'` | `'ip'`).
- Granularidade: `nk_company_id × nk_balance_date × provider` (até 2 linhas/cliente/dia). Grão misto: `ip` diário, `iugu` mensal (data carimbada no 1º do mês). Ver 3.12.
- Definição em código: `repos/gcp-dataform-banking/definitions/gold/core_banking/tables/dim_company_float_by_day.sqlx` → silver `.../balance_and_float/company_float_by_day.sqlx` (union `company_float_iugu.sqlx` + `company_float_ip.sqlx`).

### Tabelas `banking-ssbi` — origem declarada, **sem cross-reference em código neste patch**
Documentadas a partir do glossário (seção 4); o repo `gcp-dataform-banking` **já está** em `repos/`, mas as tabelas abaixo **ainda não foram cruzadas em código** (fora do escopo do intent 9 — a serem aterradas em seus próprios intents). Colunas **não verificadas**:
- `banking-ssbi.gold_core_banking.fact_transactions` — transações Banking. Suporta TPV Cash In/Out, Float e MDP (Pagamentos via Conta PJ) e LTV MDR (per glossário).
- `banking-ssbi.gold_credit.fact_credit_advance` — solicitações de antecipação de crédito. Suporta Clientes Ativos Crédito.
- `banking-ssbi.silver_wall_street.business_performance_metrics` — suporta **Float Revenue (Floating)**. ⚠️ Não confundir com `contaazul-ssbi.silver_board_material.business_performance_metrics` (repo sincronizado), que é o **book de resultados da companhia** (EBITDA/CAC/LTV/ARR) — tabela homônima, projeto/schema diferentes, **não** é a fonte de Float Revenue.

## 3. KPIs e Queries Validadas

Convenção: cada bloco é **uma query executável** parametrizada por `@inicio`/`@fim` (DATE). Para junho/2026, `@inicio = DATE '2026-06-01'`, `@fim = DATE '2026-06-30'`.

### 3.1 Receita MDR — Total
> Fonte: Looker `sf_banking_mensal.receita_total` ("Receita MDR Total (R$)") · Dataform: `repos/gcp-dataform-contaazul/definitions/gold/mdr/tables/fact_actual.sqlx`
> Receita arrecadada pela CA via MDR (taxas de boleto, pix e link de pagamento). Fórmula: **soma de `sum_of_revenue_ca`** (receita CA, reconhecida só na compensação) no período, tomando `nk_date` como a data de liquidação.

```sql
SELECT
  ROUND(SUM(sum_of_revenue_ca), 2) AS receita_mdr_total_brl
FROM `contaazul-ssbi.gold_mdr.fact_actual`
WHERE nk_date BETWEEN @inicio AND @fim
```

### 3.2 Receita MDR — por meio (boleto / pix / link de pagamento)
> Fonte: Looker `receita_boleto` / `receita_pix` / `receita_link` · mesma tabela.
> Split da receita por método. O meio fica em `nk_method` (que no `fact_actual` carrega `original_method_type`). Agrupe por `nk_method`; os *shares* (`share_*_pct`) são `receita_do_meio / receita_total`.

```sql
SELECT
  nk_method,
  ROUND(SUM(sum_of_revenue_ca), 2) AS receita_brl
FROM `contaazul-ssbi.gold_mdr.fact_actual`
WHERE nk_date BETWEEN @inicio AND @fim
GROUP BY nk_method
ORDER BY receita_brl DESC
```

### 3.3 Clientes Ativos MDR
> Fonte: Looker `sf_banking_mensal.clientes_ativos_mdr` · `fact_actual.sqlx`
> Clientes com **ao menos uma transação compensada/liquidada** (Pix, Boleto ou Link) no período. Fórmula: contagem distinta de `nk_customer_id` com `total_compensations > 0`. `nk_customer_id > -1` exclui o membro "desconhecido".

```sql
SELECT
  COUNT(DISTINCT nk_customer_id) AS clientes_ativos_mdr
FROM `contaazul-ssbi.gold_mdr.fact_actual`
WHERE nk_date BETWEEN @inicio AND @fim
  AND total_compensations > 0
  AND nk_customer_id > -1
```

### 3.4 Churn MDR — Novos, Reativados, Saíram e Churn Líquido (%)
> Fonte: Looker `novos` / `reativados` / `sairam` / `churn_liq_pct` · `fact_actual.sqlx`
> Compara o conjunto de clientes ativos (compensados) do **mês de `@inicio`** com o **mês anterior** e com o histórico anterior a ele. **Novos** = ativos no mês e nunca ativos antes; **Reativados** = ativos no mês, ausentes no mês anterior, mas ativos em algum mês antes disso; **Saíram** = ativos no mês anterior e ausentes no mês atual. **Churn Líquido %** = `(saíram − entradas) / ativos_mês_anterior × 100`, onde `entradas = novos + reativados`.

```sql
WITH ativos AS (
  SELECT DISTINCT DATE_TRUNC(nk_date, MONTH) AS mes, nk_customer_id
  FROM `contaazul-ssbi.gold_mdr.fact_actual`
  WHERE total_compensations > 0 AND nk_customer_id > -1
),
params AS (
  SELECT DATE_TRUNC(@inicio, MONTH) AS mes_atual,
         DATE_SUB(DATE_TRUNC(@inicio, MONTH), INTERVAL 1 MONTH) AS mes_ant
),
atual     AS (SELECT nk_customer_id FROM ativos a, params WHERE a.mes = params.mes_atual),
anterior  AS (SELECT nk_customer_id FROM ativos a, params WHERE a.mes = params.mes_ant),
historico AS (SELECT DISTINCT nk_customer_id FROM ativos a, params WHERE a.mes < params.mes_ant)
SELECT
  (SELECT COUNT(*) FROM anterior) AS ativos_mes_anterior,
  (SELECT COUNT(*) FROM atual)    AS ativos_mes_atual,
  (SELECT COUNT(*) FROM atual WHERE nk_customer_id NOT IN (SELECT nk_customer_id FROM anterior)
                               AND nk_customer_id NOT IN (SELECT nk_customer_id FROM historico)) AS novos,
  (SELECT COUNT(*) FROM atual WHERE nk_customer_id NOT IN (SELECT nk_customer_id FROM anterior)
                               AND nk_customer_id IN (SELECT nk_customer_id FROM historico))     AS reativados,
  (SELECT COUNT(*) FROM anterior WHERE nk_customer_id NOT IN (SELECT nk_customer_id FROM atual)) AS sairam,
  ROUND(100 * SAFE_DIVIDE(
      (SELECT COUNT(*) FROM anterior WHERE nk_customer_id NOT IN (SELECT nk_customer_id FROM atual))
    - (SELECT COUNT(*) FROM atual    WHERE nk_customer_id NOT IN (SELECT nk_customer_id FROM anterior)),
      (SELECT COUNT(*) FROM anterior)), 2) AS churn_liquido_pct
FROM params
```

### 3.5 ARPU MDR
> Fonte: Looker `sf_banking_mensal.arpu_mdr` ("ARPU MDR (R$)") · `fact_actual.sqlx`
> Average Revenue Per User = **receita total / clientes ativos** no período. Numerador = `SUM(sum_of_revenue_ca)`; denominador = clientes ativos MDR (3.3).

```sql
SELECT
  ROUND(
    SUM(sum_of_revenue_ca)
    / NULLIF(COUNT(DISTINCT IF(total_compensations > 0 AND nk_customer_id > -1, nk_customer_id, NULL)), 0),
  2) AS arpu_mdr_brl
FROM `contaazul-ssbi.gold_mdr.fact_actual`
WHERE nk_date BETWEEN @inicio AND @fim
```

### 3.6 LTV MDR
> Fonte: Looker `sf_banking_mensal.ltv_mdr` ("LTV MDR (R$)") · `fact_actual.sqlx`
> Valor arrecadado em MDR ao longo da vida do cliente. Fórmula do explore: **ARPU × (ativos_mês_anterior / saíram)** = `ARPU / churn_bruto`, onde `churn_bruto = saíram / ativos_mês_anterior`. ⚠️ Usa **churn bruto** (não líquido): net churn pode ser negativo e tornaria o LTV infinito. Correto apenas na granularidade **mensal**.

```sql
WITH ativos AS (
  SELECT DISTINCT DATE_TRUNC(nk_date, MONTH) AS mes, nk_customer_id
  FROM `contaazul-ssbi.gold_mdr.fact_actual`
  WHERE total_compensations > 0 AND nk_customer_id > -1
),
params AS (
  SELECT DATE_TRUNC(@inicio, MONTH) AS mes_atual,
         DATE_SUB(DATE_TRUNC(@inicio, MONTH), INTERVAL 1 MONTH) AS mes_ant
),
atual    AS (SELECT nk_customer_id FROM ativos a, params WHERE a.mes = params.mes_atual),
anterior AS (SELECT nk_customer_id FROM ativos a, params WHERE a.mes = params.mes_ant),
base   AS (SELECT COUNT(*) AS n FROM anterior),
sairam AS (SELECT COUNT(*) AS n FROM anterior WHERE nk_customer_id NOT IN (SELECT nk_customer_id FROM atual)),
arpu AS (
  SELECT SUM(sum_of_revenue_ca) / NULLIF(COUNT(DISTINCT nk_customer_id), 0) AS v
  FROM `contaazul-ssbi.gold_mdr.fact_actual`
  WHERE nk_date BETWEEN @inicio AND @fim AND total_compensations > 0 AND nk_customer_id > -1
)
SELECT ROUND(arpu.v * SAFE_DIVIDE(base.n, sairam.n), 2) AS ltv_mdr_brl
FROM arpu, base, sairam
```

### 3.7 TPV (Payments)
> Fonte: Looker `Payments > TPV` · Dataform: `repos/gcp-dataform-contaazul/definitions/gold/mdr/tables/fact_track_backend.sqlx`
> Volume total de pagamentos **processados** (liquidados) pela CA no período. Fórmula: `SUM(sum_of_amount_paid)` filtrando pela data de liquidação (`nk_acquit_date`). O `BETWEEN` com datas válidas já exclui o sentinela `'0001-01-01'` (não liquidados).

```sql
SELECT
  ROUND(SUM(sum_of_amount_paid), 2) AS tpv_brl
FROM `contaazul-ssbi.gold_mdr.fact_track_backend`
WHERE nk_acquit_date BETWEEN @inicio AND @fim
```

### 3.8 Take Rate
> Fonte: Looker `Payments > Take Rate` · `fact_track_backend.sqlx`
> Percentual financeiro arrecadado sobre o volume processado, em pontos percentuais. Fórmula: **Gross Revenue / TPV × 100** = `SUM(sum_of_revenue_ca) / SUM(sum_of_amount_paid) × 100`.

```sql
SELECT
  ROUND(100 * SAFE_DIVIDE(SUM(sum_of_revenue_ca), SUM(sum_of_amount_paid)), 4) AS take_rate_pct
FROM `contaazul-ssbi.gold_mdr.fact_track_backend`
WHERE nk_acquit_date BETWEEN @inicio AND @fim
```

### 3.9 Gross Revenue (Payments)
> Fonte: Looker `Finance Services > Payments` · `fact_track_backend.sqlx`
> Faturamento bruto de Serviços Financeiros (Payments) — total faturado **sem** dedução de custos. Fórmula: `SUM(sum_of_revenue_ca)` no período de liquidação. ⚠️ Não confundir com `sum_of_gross_profit` (lucro **após** custos como `iugu_cost`). Reconcilia com a Receita MDR Total (3.1) no mesmo período — são a mesma receita CA vista em bases distintas (`fact_track_backend` granular vs `fact_actual` por método/compensação).

```sql
SELECT
  ROUND(SUM(sum_of_revenue_ca), 2) AS gross_revenue_brl
FROM `contaazul-ssbi.gold_mdr.fact_track_backend`
WHERE nk_acquit_date BETWEEN @inicio AND @fim
```

### 3.10 TPV Cash In / Cash Out — Banking (sem query validada)
> Fonte: Looker `Corporate Account > TPV > Cash In [R$ MM]` / `Cash Out [R$ MM]` · Origem: `banking-ssbi.gold_core_banking.fact_transactions`.
> Cash In = volume total de pagamentos de **entrada**; Cash Out = de **saída**; TPV (total) = entrada + saída. **Não há query validada** — a tabela vive em `banking-ssbi` e seu Dataform não está sincronizado em `repos/` (colunas não verificadas). Ver seção 4.

### 3.11 Float e Float Revenue (Floating) — Banking (sem query validada)
> Fonte: Looker `Finance Services > Floating`. Origem Float Revenue: `banking-ssbi.silver_wall_street.business_performance_metrics`. Origem Float (saldo): `banking-ssbi.gold_core_banking.dim_company_float_by_day`.
> **Float** = montante sob custódia da CA (dinheiro do pagador que fica D+n parado antes do repasse ao parceiro — boleto, cartão, serviços de pagamento). **Float Revenue** = receita da aplicação do float antes do repasse. **Sem query validada** (fonte `banking-ssbi` não sincronizada).

### 3.12 Saldo Positivo — EOD / Clientes Ativos Float — Banking
> Fonte: Looker dashboard 1180 → Banking — Float → "Clientes Ativos Float" (medida `sf_banking_mensal.clientes_float`, tipo `sum`) · Dataform: `repos/gcp-dataform-banking/definitions/gold/core_banking/tables/dim_company_float_by_day.sqlx` (silver: `.../silver/core_banking/tables/balance_and_float/company_float_by_day.sqlx`).
> **Conceito:** nº de **clientes (empresas) distintos que terminaram ao menos um dia do período com saldo positivo** (Saldo `> 0` no fim do dia → positivo; `< 0` → negativo; `= 0` → equilíbrio). Na `dim_company_float_by_day` isso equivale a ter **`float_value > 0`** em ≥1 dia do período — ver a disambiguação abaixo e a armadilha na seção 5.

**Colunas (confirmadas em código — `dim_company_float_by_day.sqlx`):**
- `nk_company_id` — identificador do cliente (empresa); vem direto de `contaazul_company_id`. **Sem membro sentinela/"desconhecido"** (ao contrário de `fact_actual.nk_customer_id`, que usa `-1`): não há join com dimensão de cliente na linhagem, então **não** se aplica filtro `> -1` aqui.
- `nk_balance_date` — DATE, data do saldo. Comparável direto com `@inicio`/`@fim`, sem cast.
- `float_value` — **receita de float atribuída ao cliente** (BRL), rateada pelo share do saldo do cliente. **Não é o saldo bruto** (ver disambiguação).
- `provider` — provedor da conta: `'iugu'` ou `'ip'`.

**Granularidade e provedor:**
- Grão = `nk_company_id × nk_balance_date × provider` → **até 2 linhas por cliente/dia** (uma por provedor). `COUNT(DISTINCT nk_company_id)` **absorve** essa duplicação — não é preciso consolidar por cliente/dia antes do teste `> 0`, porque (a) contamos clientes distintos e (b) as duas fontes silver já filtram `float_value > 0` (não há linhas ≤ 0 para "cancelar" numa soma). Somar por cliente/dia e testar `SUM(...) > 0` daria exatamente o mesmo conjunto de clientes.
- **Grão misto por provedor:** `ip` é **diário** (`nk_balance_date` = data do dia); `iugu` é **mensal** — `nk_balance_date` vem de `DATE_TRUNC(..., MONTH)`, carimbado no **1º dia do mês** (rateio mensal). ⚠ Por isso o período deve **começar no dia 1º** para capturar os clientes IUGU: um `@inicio` a partir do dia 2 deixaria a linha IUGU (carimbada em `-01`) fora do `BETWEEN`. Para mês fechado (junho, `@inicio = DATE '2026-06-01'`) ambos os provedores entram.

**Disambiguação (fecha a ambiguidade da rodada 1):**
- `dim_company_float_by_day.float_value` **≠ saldo bruto da conta**. O saldo bruto mora em `banking-ssbi.silver_core_banking.company_banking_balance_by_day.balance` (não exposto por esta medida). Aqui o valor é a **receita de float** derivada desse saldo.
- `dim_company_float_by_day.float_value` **≠ Float Revenue total da 3.11**. O `float_value` per-cliente é a **decomposição** da receita total de float da companhia (`banking-ssbi.silver_wall_street.business_performance_metrics.floating_revenue`, seção 3.11) rateada por cliente: mesmo conceito (receita de float), grão diferente (cliente×dia/mês vs companhia×mês).
- **Por que `float_value > 0` ≡ "Saldo > 0 EOD":** a linhagem só atribui float a quem teve **saldo positivo** no período (IP filtra `balance > 0` antes do rateio; IUGU filtra `sum_balance_iugu_month > 0`) e depois filtra `float_value > 0`. Logo um cliente aparece com `float_value > 0` num dia **exatamente porque** fechou aquele dia com saldo positivo — é a operacionalização, no data mart, da medida "Clientes Ativos Float".

**Agregação mensal:** "≥1 dia com `float_value > 0` no período" = `COUNT(DISTINCT nk_company_id)` sobre as linhas do período; cada cliente conta uma vez, independentemente de quantos dias/provedores positivos teve.

```sql
SELECT
  COUNT(DISTINCT nk_company_id) AS clientes_saldo_positivo_eod
FROM `banking-ssbi.gold_core_banking.dim_company_float_by_day`
WHERE nk_balance_date BETWEEN @inicio AND @fim
  AND float_value > 0
```

### 3.13 Antecipação de Crédito — Clientes Ativos Crédito — Banking (sem query validada)
> Fonte: Looker `Banking — Crédito > Clientes Ativos Crédito` (medida `clientes_credito`); detalhamento em `credito_qtd_ops`, `credito_vol_bruto`, `credito_vol_liquido`, `credito_receita_esperada`, `credito_receita_contabil`, `credito_prazo_medio`. Origem: `banking-ssbi.gold_credit.fact_credit_advance`.
> Clientes que fizeram **ao menos uma solicitação de antecipação**, ainda não deram churn e não tiveram a solicitação recusada. **Sem query validada** (fonte `banking-ssbi` não sincronizada).

### 3.14 Pagamentos via Conta PJ (MDP) — Banking (sem query validada)
> Fonte: Looker `Banking — MDP > Clientes Ativos MDP` (medida `clientes_mdp`). Origem: `banking-ssbi.gold_core_banking.fact_transactions`.
> Clientes **não bloqueados** que fizeram movimentação monetária do tipo "pagamento" em que o destino **não** é nenhuma de suas outras contas e o método ∈ {`PIX_CASH_OUT`, `CASH_OUT_BOLETO`, `TED_CASH_IN`, `TRANSFER`, `MANUALLY`}. **Sem query validada** (fonte `banking-ssbi` não sincronizada).

## 4. Notas e Definições

### Definições fornecidas pelo usuário
GLOSSÁRIO — Serviços Financeiros (fonte: Notion "Glossário de Dados", filtrado por área = "Serviços Financeiros").

⚠️ ATENÇÃO — DOIS PROJETOS GCP nas origens: `banking-ssbi` E `contaazul-ssbi`. O default do sistema é `contaazul-ssbi`, portanto TODAS as tabelas e queries DEVEM usar FQN completo com o projeto EXPLÍCITO (ex.: `banking-ssbi.gold_core_banking.fact_transactions`). Nunca omita o projeto — uma query sem projeto explícito resolveria para contaazul-ssbi e quebraria nas tabelas de banking-ssbi.

Métricas/conceitos (nome — definição — origem no BigQuery — variável no Looker):
- LTV MDR: soma de todo valor arrecadado em MDR por cliente durante seu período como assinante da CA (taxa de maquininha, valor repassado por boleto, taxa no pix). Origem: banking-ssbi.gold_core_banking.fact_transactions. Looker: Sf Banking Mensal > MDR — Clientes > LTV MDR (R$).
- %Churn Líquido: o quanto o churn líquido representa do total de usuários ativos. Origem: contaazul-ssbi.gold_mdr.fact_actual. Looker: Sf Banking Mensal > Churn MDR > Churn Líquido (%).
- Clientes Ativos (MDR): clientes com pelo menos uma transação compensada/liquidada via Pix, Boleto ou Link de Pagamento. Origem: contaazul-ssbi.gold_mdr.fact_actual. Looker: Sf Banking Mensal > MDR — Clientes > Clientes Ativos MDR.
- Churn: quantidade de clientes que deixaram de assinar algum dos planos da CA. Origem: contaazul-ssbi.gold_mdr.fact_actual. Looker: Sf Banking Mensal > Churn MDR > Novos Clientes / Reativados / Saíram; MDR — Clientes > Clientes Ativos MDR.
- Receita MDR: receita acumulada por meio do MDR (taxas de boleto, pix ou link de pagamento). Origem: contaazul-ssbi.gold_mdr.fact_actual. Looker: Sf Banking Mensal > MDR — Receita > Receita Boleto / Receita Pix / Receita Link de Pagamento / Receita MDR Total.
- Saldo Positivo (Saldo > 0 EOD): clientes que terminaram o dia positivo (saldo>0 → positivo; <0 → negativo; =0 → equilíbrio). Origem: banking-ssbi.gold_core_banking.dim_company_float_by_day. Looker: Sf Banking Mensal > Banking — Float > Clientes Ativos Float.
- Clientes com antecipação: clientes que realizaram ao menos uma solicitação de antecipação de crédito, ainda não deram churn e não tiveram a solicitação recusada. Origem: banking-ssbi.gold_credit.fact_credit_advance. Looker: Sf Banking Mensal > Banking — Crédito > Clientes Ativos Crédito.
- Pagamentos via Conta PJ (MDP): clientes não bloqueados que fizeram movimentação monetária do tipo "pagamento" onde o destino não é nenhuma de suas outras contas e o método ∈ {PIX_CASH_OUT, CASH_OUT_BOLETO, TED_CASH_IN, TRANSFER, MANUALLY}. Origem: banking-ssbi.gold_core_banking.fact_transactions. Looker: Sf Banking Mensal > Banking — MDP > Clientes Ativos MDP.
- ARPU: Average Revenue Per User = razão entre a soma da receita total e a quantidade de clientes ativos. Origem: contaazul-ssbi.gold_mdr.fact_actual. Looker: Sf Banking Mensal > MDR — Clientes > ARPU MDR (R$).
- TPV Cash In: volume total de pagamentos de entrada processados pela Conta Azul. Origem: banking-ssbi.gold_core_banking.fact_transactions. Looker: Corporate Account > TPV > Cash In [R$ MM].
- TPV Cash Out: volume total de pagamentos de saída processados pela Conta Azul. Origem: banking-ssbi.gold_core_banking.fact_transactions. Looker: Corporate Account > TPV > Cash Out [R$ MM].
- TPV: volume total de pagamentos processados pela Conta Azul. Origem: contaazul-ssbi.gold_mdr.fact_track_backend. Looker: Payments > TPV.
- Take Rate: valor financeiro que a CA arrecada a partir do processamento de pagamentos, em pontos percentuais. Origem: contaazul-ssbi.gold_mdr.fact_track_backend. Looker: Payments > Take Rate.
- Gross Revenue: faturamento bruto (total faturado sem descontos de custos/gastos). Origem: contaazul-ssbi.gold_mdr.fact_track_backend. Looker: Finance Services > Payments.
- Float: montante parado sob custódia da CA (quando o cliente do parceiro paga, o dinheiro passa pela CA — boleto, cartão, serviços de pagamento — e fica D+n parado conosco). Origem: (não especificada no glossário — investigue nas fontes/repos; ligada a dim_company_float_by_day e à silver_wall_street).
- Float Revenue (Floating): dinheiro arrecadado a partir da aplicação do float antes do repasse para o parceiro. Origem: banking-ssbi.silver_wall_street.business_performance_metrics. Looker: Finance Services > Floating.

### Avisos de build (aterramento)
- ⚠ **Explore Looker `financial_services_data_mart :: sf_banking_mensal` ([WIP] Banking Mensal) NÃO está em `repos/looker`.** O SQL/`sql:` das medidas do dashboard não pôde ser cruzado com LookML; as medidas foram aterradas via schema do explore (`get_explore`) + as tabelas Dataform `gold_mdr`. A view auxiliar `sf_banking_yoy` (receita por ano, para o gráfico YoY) é *joined* nesse explore, não é explore próprio.
- ⚠ **SQL por-tile do dashboard 1180 indisponível** (a API retornou "Bad json" para os 14 tiles). Fields e medidas foram capturados normalmente; o aterramento das queries veio das definições Dataform em `repos/gcp-dataform-contaazul`.
- ⚠ **Repositório Dataform de `banking-ssbi` (`repos/gcp-dataform-banking`) sincronizado.** O intent 9 (Saldo Positivo / Clientes Ativos Float) foi aterrado em código (ver 3.12 e a entrada de `dim_company_float_by_day` na seção 2). As demais tabelas banking (`gold_core_banking.fact_transactions`, `gold_credit.fact_credit_advance`, `silver_wall_street.business_performance_metrics`) **ainda não foram cruzadas em código** neste patch — Float Revenue, Crédito, MDP e TPV Cash In/Out seguem sem query validada até serem aterrados em seus próprios intents.
- ✔ **[patch 2026-07-16] Intent 9 (Saldo Positivo / Clientes Ativos Float) aterrado e resolvido.** Com o Dataform de `banking-ssbi` sincronizado, as colunas de `dim_company_float_by_day` (`nk_company_id`, `nk_balance_date`, `float_value`, `provider`) foram confirmadas na fonte (`.../gold/core_banking/tables/dim_company_float_by_day.sqlx` + silver `.../balance_and_float/company_float_by_day.sqlx`). A linhagem revelou que `float_value` é **receita de float atribuída ao cliente** (rateio do saldo), e que o filtro `float_value > 0` operacionaliza "Saldo > 0 EOD" (só quem teve saldo positivo recebe rateio). A seção 3.12 recebeu query `@inicio`/`@fim` executável com FQN explícito, e a disambiguação Saldo × Float × Float Revenue foi documentada (3.12 + seção 5). Marcador "sem query validada" removido.
- Metabase: nenhuma URL fornecida (fonte não usada neste build).

## 5. Glossário / Armadilhas

- **FQN com projeto explícito, sempre.** `banking-ssbi` e `contaazul-ssbi` coexistem; omitir o projeto resolve para `contaazul-ssbi` e quebra nas tabelas de banking.
- **Receita = `sum_of_revenue_ca`, não taxa nem lucro.** Receita MDR / Gross Revenue usam `sum_of_revenue_ca` (receita CA). Não confundir com `sum_of_fee_value` (valor de taxa cobrada) nem `sum_of_gross_profit` (lucro **após** custos). Receita só é reconhecida na **compensação** (`nk_acquit_date`/`nk_date` de liquidação), não na emissão.
- **`fact_actual.nk_method` carrega `original_method_type`** (ex.: `PIXLETO`), enquanto `dim_track_backend_method.nk_method` usa o método **adaptado** (ex.: `BANK_SLIP` = boleto, visto no `CASE` de `fact_track_backend.sqlx`). O JOIN direto `fact_actual.nk_method = dim.nk_method` pode **não casar**. Para o split por meio, agrupe por `fact_actual.nk_method` e mapeie os códigos (boleto = `BANK_SLIP`; pix ≈ `PIX`/`PIXLETO`; link de pagamento = método próprio) conferindo os valores presentes no período.
- **`nk_date` no `fact_actual` é ambíguo por natureza:** vale a data de **criação** nas linhas de emissão e a de **liquidação** nas de compensação. Para receita/clientes ativos/ARPU filtre com `total_compensations > 0` (ou some `sum_of_revenue_ca`, que já é zero fora da compensação).
- **Sentinela de data `'0001-01-01'`** em `nk_acquit_date` = documento **não** liquidado. `BETWEEN @inicio AND @fim` com datas válidas já o exclui.
- **`nk_customer_id > -1`**: `-1` é o membro "desconhecido" da dimensão de clientes; exclua-o em contagens de clientes.
- **LTV usa churn BRUTO, não líquido.** `LTV = ARPU × (ativos_anterior / saíram)`. Net churn pode ser negativo → LTV infinito. Métrica válida só na granularidade **mensal**.
- **Churn Líquido vs Bruto.** Bruto = `saíram / ativos_mês_anterior`. Líquido = `(saíram − novos − reativados) / ativos_mês_anterior`. "Novos" (nunca ativos antes) ≠ "Reativados" (ativos em algum mês antes do anterior) — a distinção exige histórico completo, não só o mês anterior.
- **Gross Revenue (Payments) ≈ Receita MDR Total** no mesmo período (mesma receita CA, bases distintas: granular vs por método). Se divergirem muito, investigue diferença de data-base (criação vs liquidação) ou de escopo de método.
- **Duas `business_performance_metrics` homônimas:** `banking-ssbi.silver_wall_street.*` (Float Revenue) ≠ `contaazul-ssbi.silver_board_material.*` (book de resultados da companhia — EBITDA/CAC/ARR). Não troque uma pela outra.
- **Saldo EOD × Float × Float Revenue — três coisas diferentes (intent 9 / Clientes Ativos Float).** `dim_company_float_by_day.float_value` **não** é o saldo bruto da conta (esse é `banking-ssbi.silver_core_banking.company_banking_balance_by_day.balance`) **nem** a receita total de float da companhia (essa é `silver_wall_street...floating_revenue`, seção 3.11). É a **receita de float atribuída a cada cliente**, rateada pelo share do saldo diário/mensal. Como a linhagem só atribui float a quem teve **saldo > 0** (IP filtra `balance > 0`; IUGU filtra `sum_balance_iugu_month > 0`) e ainda filtra `float_value > 0`, **`float_value > 0` ≡ "fechou o dia com saldo positivo (EOD)"** — é assim que "Clientes Ativos Float" é operacionalizada. Conte com `COUNT(DISTINCT nk_company_id)` (absorve a dimensão `provider`, que gera até 2 linhas/cliente/dia; e não há linhas ≤ 0 para consolidar). **Grão misto:** `ip` é diário, `iugu` é mensal (linha carimbada no **1º do mês**) — para capturar IUGU o período tem de **começar no dia 1º**. **Sem sentinela `-1`** aqui (ao contrário de MDR `nk_customer_id > -1`): o id vem direto de `contaazul_company_id`, sem join com dimensão.
- TODO: preencher com aprendizados de uso real e valores de referência de junho/2026 quando disponíveis.
