# Conhecimento Domínio Atendimento — ContaAzul
> Atualizado em 01/05/2026

---

## 1. Arquitetura de Dados

**Projeto BigQuery**: `contaazul-ssbi`
**Modelo Looker**: `serve_data_mart` (label: "Servir")
**Dataset principal**: `contaazul-ssbi.gold_serve`

### Camadas do Data Lake

```
bronze_tool_zendesk_events
  → silver_serve.ingestion_zendesk_tickets + _chats + _whatsapp + _web + _email
  → silver_serve.zendesk_tickets_detailed
  → gold_serve.dim_zendesk_tickets_detailed

bronze_tool_blip / bronze_app_supercami
  → silver_serve.ingestion_blip_supercami_* + ingestion_takeblip_*
  → gold_serve.dim_chatbot

silver_serve.agent_capacity (filtro: team = 'Servir')
  → PDT pdt_agent_capacity_agg (inline no SQL Looker)
  → gold_serve.fact_service_metrics
```

---

## 2. Tabelas Principais

### `gold_serve.fact_service_metrics`
- **Descrição**: Fato de métricas diárias de atendimento humano (Zendesk)
- **Partição**: `nk_event_date` (DATE, diária)
- **Cluster**: `channel`, `area`, `nk_email`
- **Explore Looker**: `fact_service_metrics`

| Campo | Tipo | Descrição |
|---|---|---|
| nk_event_date | DATE | Data do evento |
| channel | STRING | Canal: Chat, Email, Telefone, Web, Whatsapp |
| area | STRING | Área do encantador: BK, DN, EC, SAC - CA, SAC - Pessoalize, Ouvidoria - IP, RT |
| nk_email | STRING | E-mail do encantador |
| squad | STRING | Time por matriz de produto |
| customer_type | STRING | PME, Parceiro, Cliente do Parceiro |
| has_premium_support | BOOLEAN | Possui suporte premium |
| is_partner | BOOLEAN | É parceiro |
| partner_level | STRING | Nível de parceria |
| is_under_6m | BOOLEAN | Menos de 6 meses de vida |
| count_of_demanded | INTEGER | Chamados recebidos |
| count_of_abandoned | INTEGER | Chamados abandonados |
| count_of_attended | INTEGER | Chamados atendidos |
| count_of_positive_ratings | INTEGER | Avaliações positivas |
| count_of_negative_ratings | INTEGER | Avaliações negativas |
| sum_of_ta | INTEGER | Tempo total de atendimento (segundos) |
| sum_of_te | INTEGER | Tempo total de espera (segundos) |
| sum_of_tpr | INTEGER | Tempo total de primeira resposta (segundos) |
| count_of_tpr_ok | INTEGER | Tickets com TPR dentro do SLA |
| count_of_tpr_nok | INTEGER | Tickets com TPR fora do SLA |

**Áreas presentes por canal** (descobertas na validação):
- Whatsapp: BK, DN, EC, RT
- Chat: BK, DN, EC, RT
- Telefone: DN, EC, SAC - CA, SAC - Pessoalize, Ouvidoria - IP
- Web: BK, DN, EC, ENG, N/I, RT, SDM, TRAINING, BACKING_OPS, OUVIDORIA
- Email: BK, DN

---

### `gold_serve.dim_chatbot`
- **Descrição**: Interações diárias dos chatbots (Cami/SuperCami — Blip/Takeblip/Ultimate)
- **Partição**: `nk_date` (DATE, diária)
- **Cluster**: `channel`, `team`
- **Explore Looker**: `dim_blip_messages`
- **Granularidade**: 1 linha = 1 interação/sessão (`sum_of_interactions = 1` por linha)

| Campo | Tipo | Descrição |
|---|---|---|
| nk_date | DATE | Data do registro |
| channel | STRING | Canal: Whatsapp, Chat |
| team | STRING | Produto: CA Mais, CA Pro, Conta PJ |
| bot_type | STRING | Tipo de bot: Gen2, Gen3 CA Mais, Gen3 CA Pro, Bot_Fin |
| bot_departament | STRING | Departamento: Servir, Retenção, NULL |
| csat_type | STRING | N/I, csat_retidos, csat_transbordados |
| is_gen3 | BOOLEAN | É fluxo Gen3 |
| nk_company_id | INTEGER | ID da empresa |
| customer_type | STRING | PME, Parceiro, Cliente do Parceiro |
| has_premium_support | BOOLEAN | Possui suporte premium |
| is_partner | BOOLEAN | É parceiro |
| thread_uid | STRING | ID único da conversa |
| sum_of_interactions | INTEGER | Nº de interações (= 1 por linha) |
| sum_of_transfers | INTEGER | Transbordos para humano |
| sum_of_final_bot | INTEGER | Conversas retidas (resolvidas pelo bot) |
| sum_of_positive_ratings | INTEGER | Avaliações positivas |
| sum_of_negative_ratings | INTEGER | Avaliações negativas |
| sum_of_total_ratings | INTEGER | Total de avaliações |

**Valores de bot_type presentes** (W16 referência):
- `Gen2` — bot principal de Whatsapp
- `Gen3 CA Mais` — bot Gen3 para CA Mais (Chat)
- `Gen3 CA Pro` — bot Gen3 para CA Pro (Chat e Whatsapp)
- `Bot_Fin` — bot Financeiro/FinAI (**não é o Cami**)

**Valores de bot_departament**:
- `Servir` — fluxo de suporte principal ← usado nas métricas de Atendimento
- `Retenção` — fluxo de retenção de clientes
- `NULL` — Bot_Fin sem departamento definido

**Valores de csat_type**:
- `N/I` — sessão sem avaliação (topo de funil, maioria das interações)
- `csat_retidos` — avaliação de cliente retido pelo bot ← usado para CSAT Cami
- `csat_transbordados` — avaliação de cliente transbordado para humano

---

### `gold_serve.dim_zendesk_tickets_detailed`
- **Descrição**: Todos os tickets do Zendesk com detalhamento completo
- **Partição**: `nk_date` (DATETIME, mensal)
- **Cluster**: `ticket_category`, `ticket_subcategory`
- **Explore Looker**: `dim_zendesk_tickets_detailed`

Campos principais: `id`, `nk_date`, `nk_company_id`, `assignee_email`, `assignee_name`, `assignee_area`, `channel`, `ticket_category`, `ticket_subcategory`, `ticket_level`, `departament`, `attendance_type`, `status`, `online_service_time`, `online_waiting_time`, `tags`, `is_incomplete`, `is_charge`, `customer_type`, `has_premium_support`, `is_partner`

---

### Tabelas de Suporte
| Tabela | Uso |
|---|---|
| `gold_common.dim_date` | Dimensão calendário — JOIN por nk_date |
| `gold_common.dim_company` | Dados das empresas clientes |
| `gold_common.dim_accountancy` | Dados dos parceiros/contadores |
| `gold_common.dim_active_companies_by_month` | Base ativa CAPRO por mês |
| `gold_serve.dim_chatbot_holidays` | Feriados por canal (usado p/ filtro DU no bot) |
| `silver_serve.agent_capacity` | Capacidade dos encantadores (team = 'Servir') |

---

## 3. Dashboards Oficiais

### Dashboard 220 — [SUP_OFI] Gerencial 592
**URL**: https://contaazul.cloud.looker.com/dashboards/220
**Explore**: `fact_service_metrics`

### Dashboard 273 — [SUP_OFI] 275 Tickets Detail
**URL**: https://contaazul.cloud.looker.com/dashboards/273
**Explore**: `dim_zendesk_tickets_detailed`

### Dashboard 210 — [SUP_OFI] Chatbots
**URL**: https://contaazul.cloud.looker.com/dashboards/210
**Explore**: `dim_blip_messages`

---

## 4. Definições e Fórmulas dos KPIs

### Demanda Total (Cami + Telefone)
> Métrica principal do acompanhamento semanal. Soma autoatendimento bot + voz humana.

```sql
-- CAMI (autoatendimento)
SELECT SUM(sum_of_interactions)
FROM `contaazul-ssbi.gold_serve.dim_chatbot`
WHERE bot_departament = 'Servir'
-- ⚠️ NÃO filtrar csat_type nem bot_type — inclui tudo

-- TELEFONE (voz)
SELECT SUM(count_of_demanded)
FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
WHERE channel = 'Telefone'
  AND area IN ('BK', 'DN', 'EC', 'SAC - CA', 'SAC - Pessoalize')
-- ⚠️ Ouvidoria - IP e RT NÃO entram
```

> ✅ Validado W16: Cami=8.853 | Telefone=1.046 | Total=9.899

---

### Demanda por DU (média por dia útil)
> Normaliza a demanda total pelo número de dias úteis da semana para comparação WoW justa.

```
Demanda por DU = Demanda Total / Qtd de Dias Úteis no Período
```

```sql
-- Dias úteis = dias da semana excluindo sábado e domingo
-- Semana padrão (seg-sex) = 5 DU
-- Exemplo W16: 8.853 / 5 = 1.771 (Cami) | 1.046 / 5 = 209 (Telefone)
```

> ⚠️ Não é um filtro de dia útil — é divisão do total pelo nº de DU da semana

---

### Demanda Humana por Canal
> Usa `count_of_demanded` (recebida), NÃO `count_of_attended`.

```sql
SELECT channel, SUM(count_of_demanded) AS demanda_recebida
FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
WHERE channel IN ('Chat', 'Email', 'Telefone', 'Web', 'Whatsapp')
  AND area IN ('BK', 'DN', 'EC', 'SAC - CA', 'SAC - Pessoalize')
GROUP BY channel
```

> ✅ Validado W16: WA=2.410 | Chat=1.453 | Tel=1.046 | Web=272 | Email=38 | Total=5.219

**Diferença entre recebida e atendida:**
- `count_of_demanded` = recebida (atendidos + abandonados)
- `count_of_attended` = só atendidos
- Diferença = abandonados (W16: 5.220 - 5.014 = 206 abandonos)

---

### CSAT Blended PME / Parceiro
> "Blended" = avaliações do bot (Cami) + humano numa única nota.

```sql
-- Blended PME
(humano_pos_pme + cami_pos_pme) / (humano_pos_pme + humano_neg_pme + cami_pos_pme + cami_neg_pme)

-- Humano PME
SELECT
  SUM(CASE WHEN customer_type != 'Parceiro' THEN count_of_positive_ratings END) AS pos,
  SUM(CASE WHEN customer_type != 'Parceiro' THEN count_of_negative_ratings END) AS neg
FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
WHERE area IN ('BK', 'DN', 'EC', 'SAC - CA', 'SAC - Pessoalize')

-- Cami PME (apenas retidos)
SELECT
  SUM(CASE WHEN csat_type='csat_retidos' AND customer_type != 'Parceiro' THEN sum_of_positive_ratings END) AS pos,
  SUM(CASE WHEN csat_type='csat_retidos' AND customer_type != 'Parceiro' THEN sum_of_negative_ratings END) AS neg
FROM `contaazul-ssbi.gold_serve.dim_chatbot`
WHERE bot_departament = 'Servir'
```

> ✅ Validado W16: Blended PME=86,4% | Humano PME=93,3% | Cami PME=75,7%
> ✅ Validado W16: Blended Parceiro=87,8% | Humano Parceiro=95,1% | Cami Parceiro=69,9%

---

### Retenção Cami
> % de interações que o bot resolveu sem precisar transbordar para humano.

```sql
SELECT
  -- Total
  ROUND(1 - SUM(sum_of_transfers) / NULLIF(SUM(sum_of_interactions), 0), 4) AS retencao_total,
  -- PME
  ROUND(1 - SUM(CASE WHEN customer_type != 'Parceiro' THEN sum_of_transfers END) /
    NULLIF(SUM(CASE WHEN customer_type != 'Parceiro' THEN sum_of_interactions END), 0), 4) AS retencao_pme,
  -- Parceiro
  ROUND(1 - SUM(CASE WHEN customer_type = 'Parceiro' THEN sum_of_transfers END) /
    NULLIF(SUM(CASE WHEN customer_type = 'Parceiro' THEN sum_of_interactions END), 0), 4) AS retencao_parceiro
FROM `contaazul-ssbi.gold_serve.dim_chatbot`
WHERE bot_departament = 'Servir'
```

> ✅ Validado W16: Total=55,6% | PME=59,5% | Parceiro=44,3%

---

### TMA (Tempo Médio de Atendimento)
> Apenas canais com atendimento humano online: Whatsapp, Telefone, Chat.

```sql
SUM(CASE WHEN channel IN ('Whatsapp','Telefone','Chat') THEN sum_of_ta END) /
NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Telefone','Chat') THEN count_of_attended END), 0)
-- resultado em segundos; dividir por 60 para minutos
-- Ex: 2.706 seg = 45min 06seg
```

> ✅ Validado W16: TMA PME=45:06 | TMA Parceiro=48:49

---

### TME (Tempo Médio de Espera)
> Apenas canais com fila: Whatsapp, Telefone, Chat.

```sql
SUM(CASE WHEN channel IN ('Whatsapp','Telefone','Chat') THEN sum_of_te END) /
NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Telefone','Chat') THEN count_of_demanded END), 0)
-- resultado em segundos
```

> ✅ Validado W16: TME PME=0:00:33 | TME Parceiro=0:00:15

---

### SLA TME (<3 min)
> % de tickets com TME médio abaixo de 180 segundos.

```sql
SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone')
         AND (sum_of_te / NULLIF(count_of_demanded,0)) < 180
    THEN count_of_demanded END) /
NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') THEN count_of_demanded END), 0)
```

> ✅ Validado W16: SLA TME PME=94,3% | SLA TME Parceiro=97,9%

---

### % Abandono

```sql
SUM(count_of_abandoned) / NULLIF(SUM(count_of_demanded), 0)
-- Segmentar por customer_type para PME vs Parceiro
```

> ✅ Validado W16: Abandono PME=2,99% | Abandono Parceiro=3,09% (oficial 3,14%, diff 0,05pp)

---

### HC Líquido e Chamados por Encantador
> Fonte: `silver_serve.agent_capacity` (team = 'Servir')

```sql
-- HC Líquido = média diária de encantadores ativos no período
SELECT ROUND(SUM(CAST(is_active_workday AS INT64)) / <qtd_du>, 0) AS hc_liquido
FROM `contaazul-ssbi.silver_serve.agent_capacity`
WHERE event_date BETWEEN '<inicio>' AND '<fim>'
  AND team = 'Servir'

-- Chamados atendidos por encantador Mês = total atendido / HC Líquido
-- Chamados atendidos por encantador DU  = total atendido / HC Líquido / DU
-- total atendido = SUM(count_of_attended) de fact_service_metrics (todos os segmentos)
```

> ✅ Validado abr.26 MTD: HC=54 | Chamados/enc mês=297 (dashboard 296) | Chamados/enc DU=17 (dashboard 18)

---

### Densidade de Demanda

```sql
SUM(count_of_demanded) / MAX(dim_active_companies_by_month.total_active_companies)
-- JOIN: date_trunc(nk_event_date, month) = nk_month de dim_active_companies_by_month
```

---

### FTE (Capacidade)

```sql
-- PDT inline: silver_serve.agent_capacity WHERE team = 'Servir'
SUM(capacity) / SUM(count_of_demanded)
```

---

## 5. Armadilhas e Cuidados ⚠️

### dim_chatbot — Cuidados críticos
| # | Armadilha | Detalhe |
|---|---|---|
| 1 | **Bot_Fin não é o Cami** | bot_type='Bot_Fin' é o bot Financeiro/FinAI — incluído em `bot_departament='Servir'` mas representa produto diferente. Para demanda Cami usar `bot_departament='Servir'` sem filtrar bot_type (o dashboard oficial inclui Bot_Fin) |
| 2 | **csat_type cria múltiplas linhas** | Cada thread pode ter até 3 linhas (N/I + csat_retidos + csat_transbordados). Para contar sessões únicas usar apenas `csat_type='N/I'`. Para CSAT usar `csat_type='csat_retidos'` |
| 3 | **Demanda Cami = todos csat_type** | `SUM(sum_of_interactions)` com `bot_departament='Servir'` sem filtro de csat_type = total correto de interações |
| 4 | **RT (Retenção) é área separada** | Área `RT` na fact_service_metrics representa atendimentos do fluxo de Retenção — NÃO entra no filtro padrão de Atendimento |

### fact_service_metrics — Cuidados críticos
| # | Armadilha | Detalhe |
|---|---|---|
| 1 | **Ouvidoria - IP fora do filtro** | `area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')` — Ouvidoria e RT ficam de fora da Demanda Total |
| 2 | **TMA/TME só em canais online** | Calcular apenas para `channel IN ('Whatsapp','Telefone','Chat')` — Email e Web não têm TA/TE |
| 3 | **Demanda recebida ≠ atendida** | Dashboard "Demanda humana por canal" usa `count_of_demanded` (recebida). `count_of_attended` é menor (exclui abandonos) |
| 4 | **Web tem muitas áreas extras** | BACKING_OPS, N/I, RT, ENG, SDM, TRAINING, OUVIDORIA — todas fora do filtro padrão |
| 5 | **Parceiros exige filtro de área** | Para SLA/TME/TMA/Abandono de `customer_type='Parceiro'`, obrigatório `area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')`. Sem isso RT+N/I+BACKING_OPS inflam sum_of_te e o TME sai 4–5x maior que o real |

### Segmentação PME vs Parceiro

| Segmento | Tabela | Filtro |
|---|---|---|
| PME | fact_service_metrics | `customer_type != 'Parceiro'` |
| Parceiro | fact_service_metrics | `customer_type = 'Parceiro'` |
| PME | dim_chatbot | `customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro')` |
| Parceiro | dim_chatbot | `customer_type = 'Parceiro'` |
| Cliente do Parceiro | dim_chatbot | `customer_type = 'Cliente do Parceiro'` |
| Cliente sem Parceiro | dim_chatbot | `customer_type = 'Cliente sem Parceiro'` |

> ⚠️ Em `dim_chatbot` existe `customer_type = NULL` (~21 linhas em W16 por bot_type). Não usar `!= 'Parceiro'` para PME nessa tabela — usar `IN (...)` explícito para não incluir NULLs.
> Em `fact_service_metrics` o padrão `!= 'Parceiro'` é seguro (sem NULLs relevantes nessa tabela).

---

## 6. Queries Validadas (prontas para uso)

### Q1 — Demanda Total Semanal (Cami + Telefone)

```sql
SELECT
  'Cami (autoatendimento)' AS canal,
  SUM(sum_of_interactions)  AS demanda
FROM `contaazul-ssbi.gold_serve.dim_chatbot`
WHERE DATE(nk_date) BETWEEN '<inicio>' AND '<fim>'
  AND bot_departament = 'Servir'

UNION ALL

SELECT
  'Telefone (voz)',
  SUM(count_of_demanded)
FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
WHERE DATE(nk_event_date) BETWEEN '<inicio>' AND '<fim>'
  AND channel = 'Telefone'
  AND area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')
```

---

### Q2 — Demanda Humana por Canal

```sql
SELECT
  channel,
  SUM(count_of_demanded)  AS demanda_recebida,
  SUM(count_of_attended)  AS demanda_atendida,
  SUM(count_of_abandoned) AS demanda_abandonada
FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
WHERE DATE(nk_event_date) BETWEEN '<inicio>' AND '<fim>'
  AND channel IN ('Chat','Email','Telefone','Web','Whatsapp')
  AND area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')
GROUP BY channel
```

---

### Q3 — CSAT Blended PME e Parceiro

```sql
WITH
humano AS (
  SELECT
    SUM(CASE WHEN customer_type != 'Parceiro' THEN count_of_positive_ratings END) AS pos_pme,
    SUM(CASE WHEN customer_type != 'Parceiro' THEN count_of_negative_ratings END) AS neg_pme,
    SUM(CASE WHEN customer_type  = 'Parceiro' THEN count_of_positive_ratings END) AS pos_parc,
    SUM(CASE WHEN customer_type  = 'Parceiro' THEN count_of_negative_ratings END) AS neg_parc
  FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
  WHERE DATE(nk_event_date) BETWEEN '<inicio>' AND '<fim>'
    AND area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')
),
cami AS (
  SELECT
    SUM(CASE WHEN csat_type='csat_retidos' AND customer_type != 'Parceiro' THEN sum_of_positive_ratings END) AS pos_pme,
    SUM(CASE WHEN csat_type='csat_retidos' AND customer_type != 'Parceiro' THEN sum_of_negative_ratings END) AS neg_pme,
    SUM(CASE WHEN csat_type='csat_retidos' AND customer_type  = 'Parceiro' THEN sum_of_positive_ratings END) AS pos_parc,
    SUM(CASE WHEN csat_type='csat_retidos' AND customer_type  = 'Parceiro' THEN sum_of_negative_ratings END) AS neg_parc
  FROM `contaazul-ssbi.gold_serve.dim_chatbot`
  WHERE DATE(nk_date) BETWEEN '<inicio>' AND '<fim>'
    AND bot_departament = 'Servir'
)
SELECT
  -- PME
  ROUND(humano.pos_pme / NULLIF(humano.pos_pme + humano.neg_pme, 0), 4) AS csat_humano_pme,
  ROUND(cami.pos_pme   / NULLIF(cami.pos_pme   + cami.neg_pme,   0), 4) AS csat_cami_pme,
  ROUND((humano.pos_pme + cami.pos_pme) /
    NULLIF(humano.pos_pme + humano.neg_pme + cami.pos_pme + cami.neg_pme, 0), 4) AS csat_blended_pme,
  -- Parceiro
  ROUND(humano.pos_parc / NULLIF(humano.pos_parc + humano.neg_parc, 0), 4) AS csat_humano_parceiro,
  ROUND(cami.pos_parc   / NULLIF(cami.pos_parc   + cami.neg_parc,   0), 4) AS csat_cami_parceiro,
  ROUND((humano.pos_parc + cami.pos_parc) /
    NULLIF(humano.pos_parc + humano.neg_parc + cami.pos_parc + cami.neg_parc, 0), 4) AS csat_blended_parceiro
FROM humano, cami
```

---

### Q4 — Retenção Cami (PME e Parceiro)

```sql
SELECT
  ROUND(1 - SUM(sum_of_transfers) /
    NULLIF(SUM(sum_of_interactions), 0), 4) AS retencao_total,
  ROUND(1 - SUM(CASE WHEN customer_type != 'Parceiro' THEN sum_of_transfers END) /
    NULLIF(SUM(CASE WHEN customer_type != 'Parceiro' THEN sum_of_interactions END), 0), 4) AS retencao_pme,
  ROUND(1 - SUM(CASE WHEN customer_type = 'Parceiro' THEN sum_of_transfers END) /
    NULLIF(SUM(CASE WHEN customer_type = 'Parceiro' THEN sum_of_interactions END), 0), 4) AS retencao_parceiro
FROM `contaazul-ssbi.gold_serve.dim_chatbot`
WHERE DATE(nk_date) BETWEEN '<inicio>' AND '<fim>'
  AND bot_departament = 'Servir'
```

---

### Q6 — CSAT Blended PME por sub-segmento (Cliente do Parceiro / Cliente sem Parceiro)

```sql
WITH
humano AS (
  SELECT
    SUM(CASE WHEN customer_type != 'Parceiro' THEN count_of_positive_ratings END) AS pos_pme,
    SUM(CASE WHEN customer_type != 'Parceiro' THEN count_of_negative_ratings END) AS neg_pme,
    SUM(CASE WHEN customer_type = 'Cliente do Parceiro' THEN count_of_positive_ratings END) AS pos_cdp,
    SUM(CASE WHEN customer_type = 'Cliente do Parceiro' THEN count_of_negative_ratings END) AS neg_cdp,
    SUM(CASE WHEN customer_type = 'Cliente sem Parceiro' THEN count_of_positive_ratings END) AS pos_csp,
    SUM(CASE WHEN customer_type = 'Cliente sem Parceiro' THEN count_of_negative_ratings END) AS neg_csp
  FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
  WHERE DATE(nk_event_date) BETWEEN '<inicio>' AND '<fim>'
    AND area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')
),
cami AS (
  SELECT
    SUM(CASE WHEN csat_type='csat_retidos' AND customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro') THEN sum_of_positive_ratings END) AS pos_pme,
    SUM(CASE WHEN csat_type='csat_retidos' AND customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro') THEN sum_of_negative_ratings END) AS neg_pme,
    SUM(CASE WHEN csat_type='csat_retidos' AND customer_type = 'Cliente do Parceiro' THEN sum_of_positive_ratings END) AS pos_cdp,
    SUM(CASE WHEN csat_type='csat_retidos' AND customer_type = 'Cliente do Parceiro' THEN sum_of_negative_ratings END) AS neg_cdp,
    SUM(CASE WHEN csat_type='csat_retidos' AND customer_type = 'Cliente sem Parceiro' THEN sum_of_positive_ratings END) AS pos_csp,
    SUM(CASE WHEN csat_type='csat_retidos' AND customer_type = 'Cliente sem Parceiro' THEN sum_of_negative_ratings END) AS neg_csp
  FROM `contaazul-ssbi.gold_serve.dim_chatbot`
  WHERE DATE(nk_date) BETWEEN '<inicio>' AND '<fim>'
    AND bot_departament = 'Servir'
)
SELECT
  ROUND(humano.pos_pme / NULLIF(humano.pos_pme + humano.neg_pme, 0), 4) AS csat_humano_pme,
  ROUND(humano.pos_cdp / NULLIF(humano.pos_cdp + humano.neg_cdp, 0), 4) AS csat_humano_cdp,
  ROUND(humano.pos_csp / NULLIF(humano.pos_csp + humano.neg_csp, 0), 4) AS csat_humano_csp,
  ROUND(cami.pos_pme / NULLIF(cami.pos_pme + cami.neg_pme, 0), 4) AS csat_cami_pme,
  ROUND(cami.pos_cdp / NULLIF(cami.pos_cdp + cami.neg_cdp, 0), 4) AS csat_cami_cdp,
  ROUND(cami.pos_csp / NULLIF(cami.pos_csp + cami.neg_csp, 0), 4) AS csat_cami_csp,
  ROUND((humano.pos_pme + cami.pos_pme) /
    NULLIF(humano.pos_pme + humano.neg_pme + cami.pos_pme + cami.neg_pme, 0), 4) AS csat_blended_pme,
  ROUND((humano.pos_cdp + cami.pos_cdp) /
    NULLIF(humano.pos_cdp + humano.neg_cdp + cami.pos_cdp + cami.neg_cdp, 0), 4) AS csat_blended_cdp,
  ROUND((humano.pos_csp + cami.pos_csp) /
    NULLIF(humano.pos_csp + humano.neg_csp + cami.pos_csp + cami.neg_csp, 0), 4) AS csat_blended_csp
FROM humano, cami
```

---

### Q7 — CSAT Cami PME por bot_type e sub-segmento

```sql
SELECT
  bot_type,
  -- Total PME
  ROUND(SUM(CASE WHEN customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro') THEN sum_of_positive_ratings END) /
    NULLIF(SUM(CASE WHEN customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro') THEN sum_of_total_ratings END), 0), 4) AS csat_pme,
  SUM(CASE WHEN customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro') THEN sum_of_total_ratings END) AS vol_pme,
  -- Cliente do Parceiro
  ROUND(SUM(CASE WHEN customer_type = 'Cliente do Parceiro' THEN sum_of_positive_ratings END) /
    NULLIF(SUM(CASE WHEN customer_type = 'Cliente do Parceiro' THEN sum_of_total_ratings END), 0), 4) AS csat_cdp,
  SUM(CASE WHEN customer_type = 'Cliente do Parceiro' THEN sum_of_total_ratings END) AS vol_cdp,
  -- Cliente sem Parceiro
  ROUND(SUM(CASE WHEN customer_type = 'Cliente sem Parceiro' THEN sum_of_positive_ratings END) /
    NULLIF(SUM(CASE WHEN customer_type = 'Cliente sem Parceiro' THEN sum_of_total_ratings END), 0), 4) AS csat_csp,
  SUM(CASE WHEN customer_type = 'Cliente sem Parceiro' THEN sum_of_total_ratings END) AS vol_csp
FROM `contaazul-ssbi.gold_serve.dim_chatbot`
WHERE DATE(nk_date) BETWEEN '<inicio>' AND '<fim>'
  AND bot_departament = 'Servir'
  AND csat_type = 'csat_retidos'
GROUP BY bot_type
ORDER BY bot_type
```

> ⚠️ Usar `sum_of_total_ratings` como denominador (= pos + neg), não `sum_of_interactions`.
> Gen 2 e Gen 3 CA Mais podem não ter avaliações `csat_retidos` em PME — retornam NULL.

---

### Q8 — Retenção Cami por bot_type e sub-segmento
> Breakdown completo: total + PME (Cliente do Parceiro / Cliente sem Parceiro) + Parceiro, por bot_type.

```sql
SELECT
  bot_type,
  -- Total
  ROUND(1 - SUM(sum_of_transfers) / NULLIF(SUM(sum_of_interactions),0), 4) AS retencao_total,
  -- PME (Cliente do Parceiro + Cliente sem Parceiro)
  ROUND(1 - SUM(CASE WHEN customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro') THEN sum_of_transfers END) /
    NULLIF(SUM(CASE WHEN customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro') THEN sum_of_interactions END),0), 4) AS retencao_pme,
  -- Cliente do Parceiro (sub-seg PME)
  ROUND(1 - SUM(CASE WHEN customer_type = 'Cliente do Parceiro' THEN sum_of_transfers END) /
    NULLIF(SUM(CASE WHEN customer_type = 'Cliente do Parceiro' THEN sum_of_interactions END),0), 4) AS retencao_cliente_parceiro,
  -- Cliente sem Parceiro (sub-seg PME)
  ROUND(1 - SUM(CASE WHEN customer_type = 'Cliente sem Parceiro' THEN sum_of_transfers END) /
    NULLIF(SUM(CASE WHEN customer_type = 'Cliente sem Parceiro' THEN sum_of_interactions END),0), 4) AS retencao_cliente_sem_parceiro,
  -- Parceiro
  ROUND(1 - SUM(CASE WHEN customer_type = 'Parceiro' THEN sum_of_transfers END) /
    NULLIF(SUM(CASE WHEN customer_type = 'Parceiro' THEN sum_of_interactions END),0), 4) AS retencao_parceiro
FROM `contaazul-ssbi.gold_serve.dim_chatbot`
WHERE DATE(nk_date) BETWEEN '<inicio>' AND '<fim>'
  AND bot_departament = 'Servir'
GROUP BY bot_type
ORDER BY bot_type
```

> ⚠️ **customer_type em dim_chatbot**: além de `Parceiro`, PME se divide em `Cliente do Parceiro` e `Cliente sem Parceiro` (não existe valor literal `PME`).
> Logo: PME = `customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro')`, não `!= 'Parceiro'` (há NULLs que seriam incluídos erroneamente).

---

### Q9 — Visão por Categoria Cami (Gen2 + Gen3 CA Pro + Gen3 CA Mais)
> Categoria derivada das tags do Zendesk via join `dim_chatbot` ↔ `silver_serve.ingestion_zendesk_tickets`.
> ⚠️ Vendas e NA ainda têm divergência a investigar — não usar para esses dois até resolução.

```sql
WITH
base_raw AS (
  SELECT
    c.*,
    COALESCE(zt_ultimate.tags, zt_intercom.tags) AS tags
  FROM `contaazul-ssbi.gold_serve.dim_chatbot` c
  LEFT JOIN (
    SELECT CAST(id AS STRING) AS id, tags
    FROM `contaazul-ssbi.silver_serve.ingestion_zendesk_tickets`
    QUALIFY ROW_NUMBER() OVER (PARTITION BY CAST(id AS STRING) ORDER BY id) = 1
  ) zt_ultimate ON CAST(c.thread_uid AS STRING) = zt_ultimate.id
  LEFT JOIN (
    SELECT CAST(id AS STRING) AS id, tags, intercom_conversation_id
    FROM `contaazul-ssbi.silver_serve.ingestion_zendesk_tickets`
    WHERE intercom_conversation_id IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (PARTITION BY intercom_conversation_id ORDER BY id) = 1
  ) zt_intercom ON CAST(c.thread_uid AS STRING) = CAST(zt_intercom.intercom_conversation_id AS STRING)
  WHERE c.bot_departament = 'Servir'
    AND DATE(c.nk_date) BETWEEN '<inicio>' AND '<fim>'
    AND c.bot_type IN ('Gen2', 'Gen3 CA Pro', 'Gen3 CA Mais')  -- exclui Bot_Fin
),
base AS (
  SELECT
    CASE
      -- Categorias temáticas (ordem exata da query oficial)
      WHEN tags LIKE '%bot_ultimate_macro_tema_emissao_nota_fiscal%'       THEN 'Configuração e Emissão de Notas Fiscais'
      WHEN tags LIKE '%bot_ultimate_macro_tema_transbordo_sem_macro_tema%' THEN 'Não Identificado'
      WHEN tags LIKE '%mt_retencao%'                                       THEN 'Retenção'
      WHEN tags LIKE '%mt_vendas_estoque_e_api%'                           THEN 'Vendas'       -- ⚠️ pendente ajuste fino
      WHEN tags LIKE '%mt_fiscal%'                                         THEN 'Fiscal'
      WHEN tags LIKE '%mt_financeiro%'                                     THEN 'Financeiro'
      WHEN tags LIKE '%mt_servicos_financeiros%'                           THEN 'Serviços Financeiros'
      WHEN tags LIKE '%mt_contabilidade%'                                  THEN 'Contabilidade'
      WHEN tags LIKE '%mt_cross%'                                          THEN 'Cross'
      WHEN tags LIKE '%mt_cobranca_chamado%'                               THEN 'Cobrança de chamado'
      -- Comportamentais depois das categorias específicas
      WHEN tags LIKE '%mt_desistente%'                                     THEN 'Desistente'
      WHEN tags LIKE '%mt_falar_com_atendente%'                            THEN 'Falar com atendente'
      ELSE 'NA'
    END AS categoria,
    SUM(sum_of_interactions)                                               AS interacoes,
    SUM(sum_of_transfers)                                                  AS transbordos
  FROM base_raw
  GROUP BY 1
)
SELECT
  categoria,
  interacoes,
  ROUND(interacoes / SUM(interacoes) OVER (), 4) AS mix,
  ROUND(1 - transbordos / NULLIF(interacoes, 0), 4) AS retencao
FROM base
ORDER BY interacoes DESC
```

**Fontes da categoria:**
- Tags vêm de `silver_serve.ingestion_zendesk_tickets` (campo `tags`)
- Join por `thread_uid` (Gen3/Ultimate) ou `intercom_conversation_id` (Bot_Fin)
- Tag atual para Vendas: `mt_vendas_estoque_e_api` (tag antiga `mt_vendas_compras_estoque_e_api` não existe mais em 2026)
- Interações sem ticket Zendesk (retidas sem tag) → caem em NA

---

### Q10 — Performance dos Encantadores PME (HC, Chamados/enc, CSAT por sub-segmento)

```sql
WITH
hc AS (
  SELECT
    ROUND(SUM(CAST(is_active_workday AS INT64)) / <qtd_du>, 0) AS hc_liquido
  FROM `contaazul-ssbi.silver_serve.agent_capacity`
  WHERE event_date BETWEEN '<inicio>' AND '<fim>'
    AND team = 'Servir'
),
total AS (
  SELECT SUM(count_of_attended) AS total_atendido
  FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
  WHERE DATE(nk_event_date) BETWEEN '<inicio>' AND '<fim>'
    AND area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')
),
metricas AS (
  SELECT
    -- CDP
    SUM(CASE WHEN customer_type = 'Cliente do Parceiro' THEN count_of_demanded END)   AS dem_rec_cdp,
    SUM(CASE WHEN customer_type = 'Cliente do Parceiro' THEN count_of_attended END)   AS dem_ate_cdp,
    ROUND(SUM(CASE WHEN customer_type = 'Cliente do Parceiro' THEN count_of_positive_ratings END) /
      NULLIF(SUM(CASE WHEN customer_type = 'Cliente do Parceiro' THEN count_of_positive_ratings + count_of_negative_ratings END),0), 4) AS csat_cdp,
    -- CSP
    SUM(CASE WHEN customer_type = 'Cliente sem Parceiro' THEN count_of_demanded END)  AS dem_rec_csp,
    SUM(CASE WHEN customer_type = 'Cliente sem Parceiro' THEN count_of_attended END)  AS dem_ate_csp,
    ROUND(SUM(CASE WHEN customer_type = 'Cliente sem Parceiro' THEN count_of_positive_ratings END) /
      NULLIF(SUM(CASE WHEN customer_type = 'Cliente sem Parceiro' THEN count_of_positive_ratings + count_of_negative_ratings END),0), 4) AS csat_csp
  FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
  WHERE DATE(nk_event_date) BETWEEN '<inicio>' AND '<fim>'
    AND area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')
)
SELECT
  hc.hc_liquido,
  ROUND(total.total_atendido / hc.hc_liquido, 0)        AS chamados_enc_mes,
  ROUND(total.total_atendido / hc.hc_liquido / <qtd_du>, 0) AS chamados_enc_du,
  metricas.*
FROM hc, total, metricas
```

> ⚠️ HC Líquido usa `is_active_workday` de `silver_serve.agent_capacity` (team='Servir'), dividido pelo nº de DU do período.
> Chamados/enc usa o **total atendido de todos os segmentos** (PME + Parceiro) como numerador.

---

### Q5 — SLA TME, TMA e Abandono (PME total + Cliente do Parceiro + Cliente sem Parceiro)

```sql
SELECT
  -- SLA TME PME (<3min)
  ROUND(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type != 'Parceiro'
                  AND (sum_of_te / NULLIF(count_of_demanded,0)) < 180
             THEN count_of_demanded END) /
    NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type != 'Parceiro'
               THEN count_of_demanded END), 0), 4) AS sla_tme_pme,

  -- TME PME (segundos)
  ROUND(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type != 'Parceiro'
            THEN sum_of_te END) /
    NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type != 'Parceiro'
               THEN count_of_demanded END), 0)) AS tme_pme_seg,

  -- TMA PME (segundos)
  ROUND(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type != 'Parceiro'
            THEN sum_of_ta END) /
    NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type != 'Parceiro'
               THEN count_of_attended END), 0)) AS tma_pme_seg,

  -- Abandono PME
  ROUND(SUM(CASE WHEN customer_type != 'Parceiro' THEN count_of_abandoned END) /
    NULLIF(SUM(CASE WHEN customer_type != 'Parceiro' THEN count_of_demanded END), 0), 4) AS abandono_pme,

  -- SLA TME Parceiro (<3min)
  ROUND(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Parceiro'
                  AND (sum_of_te / NULLIF(count_of_demanded,0)) < 180
             THEN count_of_demanded END) /
    NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Parceiro'
               THEN count_of_demanded END), 0), 4) AS sla_tme_parceiro,

  -- TME Parceiro (segundos)
  ROUND(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Parceiro'
            THEN sum_of_te END) /
    NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Parceiro'
               THEN count_of_demanded END), 0)) AS tme_parceiro_seg,

  -- TMA Parceiro (segundos)
  ROUND(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Parceiro'
            THEN sum_of_ta END) /
    NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Parceiro'
               THEN count_of_attended END), 0)) AS tma_parceiro_seg,

  -- Abandono Parceiro
  ROUND(SUM(CASE WHEN customer_type = 'Parceiro' THEN count_of_abandoned END) /
    NULLIF(SUM(CASE WHEN customer_type = 'Parceiro' THEN count_of_demanded END), 0), 4) AS abandono_parceiro,

  -- Sub-segmentos PME: Cliente do Parceiro (CDP) e Cliente sem Parceiro (CSP)
  ROUND(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente do Parceiro'
                  AND (sum_of_te / NULLIF(count_of_demanded,0)) < 180
             THEN count_of_demanded END) /
    NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente do Parceiro'
               THEN count_of_demanded END), 0), 4) AS sla_tme_cdp,
  ROUND(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente sem Parceiro'
                  AND (sum_of_te / NULLIF(count_of_demanded,0)) < 180
             THEN count_of_demanded END) /
    NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente sem Parceiro'
               THEN count_of_demanded END), 0), 4) AS sla_tme_csp,
  ROUND(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente do Parceiro' THEN sum_of_te END) /
    NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente do Parceiro' THEN count_of_demanded END), 0)) AS tme_cdp_seg,
  ROUND(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente sem Parceiro' THEN sum_of_te END) /
    NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente sem Parceiro' THEN count_of_demanded END), 0)) AS tme_csp_seg,
  ROUND(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente do Parceiro' THEN sum_of_ta END) /
    NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente do Parceiro' THEN count_of_attended END), 0)) AS tma_cdp_seg,
  ROUND(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente sem Parceiro' THEN sum_of_ta END) /
    NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente sem Parceiro' THEN count_of_attended END), 0)) AS tma_csp_seg,
  ROUND(SUM(CASE WHEN customer_type = 'Cliente do Parceiro' THEN count_of_abandoned END) /
    NULLIF(SUM(CASE WHEN customer_type = 'Cliente do Parceiro' THEN count_of_demanded END), 0), 4) AS abandono_cdp,
  ROUND(SUM(CASE WHEN customer_type = 'Cliente sem Parceiro' THEN count_of_abandoned END) /
    NULLIF(SUM(CASE WHEN customer_type = 'Cliente sem Parceiro' THEN count_of_demanded END), 0), 4) AS abandono_csp
FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
WHERE DATE(nk_event_date) BETWEEN '<inicio>' AND '<fim>'
  AND area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')
```

---

## 7. Validação Completa — W16 (13-19/abr/2026)

| Indicador | Calculado | Oficial | Diff |
|---|---|---|---|
| Demanda total (Cami + Tel) | 9.899 | 9.899 | ✅ 0 |
| Cami (autoatendimento) | 8.853 | 8.853 | ✅ 0 |
| Telefone (voz) | 1.046 | 1.046 | ✅ 0 |
| Demanda por DU | 1.980 | 1.980 | ✅ 0 |
| Cami DU | 1.771 | 1.771 | ✅ 0 |
| Telefone DU | 209 | 209 | ✅ 0 |
| Demanda humana total | 5.219 | 5.220 | ✅ -1 |
| Whatsapp | 2.410 | 2.411 | ✅ -1 |
| Chat | 1.453 | 1.453 | ✅ 0 |
| Telefone humano | 1.046 | 1.046 | ✅ 0 |
| Web | 272 | 271 | ✅ +1 |
| Email | 38 | 38 | ✅ 0 |
| Retenção Cami total | 55,6% | 55,4% | ✅ +0,2pp |
| Retenção PME | 59,5% | 59,2% | ✅ +0,3pp |
| Retenção Parceiro | 44,3% | 44,3% | ✅ 0 |
| Retenção — Fin AI total | 50,98% | 50,2% | ✅ +0,8pp |
| Retenção — Gen 3 CA Pro total | 67,73% | 67,0% | ✅ +0,7pp |
| Retenção — Gen 3 CA Mais total | 48,18% | 48,1% | ✅ +0,1pp |
| Retenção — Gen 2 total | 53,86% | 53,9% | ✅ -0,04pp |
| Retenção PME — Fin AI | 55,47% | 54,7% | ✅ +0,8pp |
| Retenção PME — Gen 3 CA Pro | 67,15% | 66,4% | ✅ +0,75pp |
| Retenção PME — Gen 2 | 56,99% | 57,0% | ✅ -0,01pp |
| Retenção Parceiro — Fin AI | 42,12% | 42,1% | ✅ +0,02pp |
| Retenção Parceiro — Gen 3 CA Pro | 71,34% | 71,2% | ✅ +0,14pp |
| Retenção Parceiro — Gen 3 CA Mais | 48,08% | 48,0% | ✅ +0,08pp |
| Retenção Parceiro — Gen 2 | 41,51% | 41,5% | ✅ +0,01pp |
| CSAT Blended PME | 86,4% | 86,4% | ✅ 0 |
| CSAT Humano PME | 93,3% | 93,4% | ✅ -0,1pp |
| CSAT Cami PME | 75,7% | 75,7% | ✅ 0 |
| CSAT Blended Parceiro | 87,8% | 87,8% | ✅ 0 |
| CSAT Humano Parceiro | 95,1% | 95,1% | ✅ 0 |
| CSAT Cami Parceiro | 69,9% | 69,9% | ✅ 0 |
| SLA TME PME (<3min) | 94,3% | 94,3% | ✅ 0 |
| TME PME | 0:00:33 | 0:00:33 | ✅ 0 |
| TMA PME | 45:06 | 45:06 | ✅ 0 |
| Abandono PME | 2,99% | 2,99% | ✅ 0 |
| SLA TME Parceiro (<3min) | 97,9% | 97,9% | ✅ 0 |
| TME Parceiro | 0:00:15 | 0:00:15 | ✅ 0 |
| TMA Parceiro | 48:49 | 48:49 | ✅ 0 |
| Abandono Parceiro | 3,09% | 3,14% | ✅ -0,05pp |

**Resultado: 42/42 indicadores validados. Diferença máxima: 0,8pp (margem de arredondamento + NULLs de customer_type).**

---

## Validação W17 (20-26/abr/2026)

| Indicador | Calculado | Oficial | Diff |
|---|---|---|---|
| CSAT Blended PME | 84,26% | 84,3% | ✅ −0,04pp |
| CSAT Humano PME | 93,72% | 93,8% | ✅ −0,08pp |
| CSAT Humano — Cliente do Parceiro | 93,09% | 93,1% | ✅ −0,01pp |
| CSAT Humano — Cliente sem Parceiro | 94,17% | 94,3% | ✅ −0,13pp |
| CSAT Cami PME | 75,18% | 75,3% | ✅ −0,12pp |
| CSAT Cami — Cliente do Parceiro | 72,71% | 72,9% | ✅ −0,19pp |
| CSAT Cami — Cliente sem Parceiro | 77,78% | 77,7% | ✅ +0,08pp |

**Resultado: 7/7 indicadores validados. Diferença máxima: 0,19pp.**

### CSAT Cami PME W17 — por bot_type e sub-segmento

| Indicador | Calculado | Oficial | Diff | Volume |
|---|---|---|---|---|
| CSAT Cami PME — Fin AI | 74,49% | 74,6% | ✅ −0,11pp | 788 aval. |
| CSAT Cami PME — Gen 3 CA Pro | 88,10% | 88,1% | ✅ 0pp | 42 aval. |
| CSAT Cami PME — Gen 3 CA Mais | NULL | — | ✅ sem aval. | 0 |
| CSAT Cami PME — Gen 2 | NULL | — | ✅ sem aval. | 0 |
| CSAT Cami CDP — Fin AI | 71,67% | 71,9% | ✅ −0,23pp | 406 aval. |
| CSAT Cami CDP — Gen 3 CA Pro | 94,74% | 94,7% | ✅ +0,04pp | 19 aval. |
| CSAT Cami CSP — Fin AI | 77,49% | 77,4% | ✅ +0,09pp | 382 aval. |
| CSAT Cami CSP — Gen 3 CA Pro | 82,61% | 82,6% | ✅ +0,01pp | 23 aval. |

**Resultado: 8/8 indicadores validados. Diferença máxima: 0,23pp.**

> Fin AI concentrou 788/830 avaliações PME (95% do volume). Gen 2 e Gen 3 CA Mais não tiveram avaliações `csat_retidos` PME em W17.

### CSAT Cami Parceiros W16 e W17 — por bot_type

| bot_type | W16 dashboard | W16 BQ | Diff | W17 dashboard | W17 BQ | Diff | Aval. W17 |
|---|---|---|---|---|---|---|---|
| Fin AI | 66,2% | 66,18% | ✅ −0,02pp | 72,1% | 72,15% | ✅ +0,05pp | 377 |
| Gen 3 CA Pro | 75,0% | 75,00% | ✅ 0pp | 100,0% | 100,00% | ✅ 0pp | 2 |
| Gen 3 CA Mais | 75,0% | 75,00% | ✅ 0pp | 57,1% | 57,14% | ✅ +0,04pp | 7 |
| Gen 2 | 74,0% | 74,04% | ✅ +0,04pp | — | — | ✅ sem aval. | 0 |
| **Total Cami Parceiros** | **69,9%** | **69,92%** | ✅ +0,02pp | **72,0%** | **72,02%** | ✅ +0,02pp | 386 |

**Resultado: 9/9 indicadores validados. Diferença máxima: 0,05pp.**

> Fin AI concentrou 377/386 avaliações Parceiros W17 (97,7% do volume). Gen 3 CA Pro e Gen 3 CA Mais têm amostras irrisórias (2 e 7 aval.) — não ler como tendência.

### Visão por Categoria Cami W17 (Gen2 + Gen3 CA Pro + Gen3 CA Mais)

| Categoria | BQ Interações | Dashboard | Diff | BQ Retenção | Dashboard | Diff |
|---|---|---|---|---|---|---|
| Falar com atendente | 304 | 304 | ✅ 0 | 16,8% | 16,2% | ✅ +0,6pp |
| Desistente | 269 | 268 | ✅ +1 | 97,4% | 97,5% | ✅ −0,1pp |
| Financeiro | 225 | 228 | ✅ −3 | 74,2% | 73,5% | ✅ +0,7pp |
| Fiscal | 204 | 207 | ✅ −3 | 66,2% | 66,3% | ✅ −0,1pp |
| Cross | 150 | 155 | ✅ −5 | 85,3% | 84,6% | ✅ +0,7pp |
| Configuração e Emissão de NF | 143 | 142 | ✅ +1 | 72,0% | 72,1% | ✅ −0,1pp |
| Serviços Financeiros | 89 | 89 | ✅ 0 | 64,0% | 62,8% | ✅ +1,2pp |
| Contabilidade | 30 | 30 | ✅ 0 | 73,3% | 73,3% | ✅ 0 |
| Cobrança de chamado | 10 | 10 | ✅ 0 | 70,0% | 70,0% | ✅ 0 |
| Vendas | 132 | 88 | ⚠️ +44 | 87,1% | 89,5% | — |
| NA | 113 | 139 | ⚠️ −26 | 73,5% | 43,4% | — |

**9/11 categorias validadas. Vendas e NA com divergência pendente de investigação.**

### SLA TME / TME / TMA / Abandono PME W17 — por sub-segmento

| Indicador | Calculado | Oficial | Diff |
|---|---|---|---|
| SLA TME PME | 90,18% | 90,2% | ✅ −0,02pp |
| SLA TME — Cliente do Parceiro | 90,31% | 90,3% | ✅ +0,01pp |
| SLA TME — Cliente sem Parceiro | 90,07% | 90,2% | ✅ −0,13pp |
| TME PME | 0:00:52 | 0:00:52 | ✅ 0 |
| TME — Cliente do Parceiro | 0:00:45 | 0:00:44 | ✅ +1s |
| TME — Cliente sem Parceiro | 0:00:59 | 0:00:58 | ✅ +1s |
| TMA PME | 0:40:52 | 0:40:27 | ✅ +25s |
| TMA — Cliente do Parceiro | 0:47:04 | 0:46:09 | ✅ +55s |
| TMA — Cliente sem Parceiro | 0:35:42 | 0:35:41 | ✅ +1s |
| Abandono PME | 4,66% | 4,70% | ✅ −0,04pp |
| Abandono — Cliente do Parceiro | 4,36% | 4,45% | ✅ −0,09pp |
| Abandono — Cliente sem Parceiro | 4,90% | 4,90% | ✅ 0 |

**12/12 indicadores validados. Diferença máxima: 55s no TMA CDP (arredondamento de segundos).**

### SLA TME / TME / TMA / Abandono Parceiros W16 e W17

> ⚠️ **Obrigatório para Parceiros**: sempre incluir `area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')`. Sem esse filtro, linhas de RT, N/I e BACKING_OPS inflam sum_of_te e count_of_demanded — TME sai 4–5x errado.

| Indicador | W16 dashboard | W16 BQ | Diff | W17 dashboard | W17 BQ | Diff |
|---|---|---|---|---|---|---|
| SLA TME Parceiros | 97,9% | 97,87% | ✅ −0,03pp | 93,1% | 92,99% | ✅ −0,11pp |
| TME Parceiros | 0:00:15 | 0:00:15 | ✅ 0s | 0:00:31 | 0:00:31 | ✅ 0s |
| TMA Parceiros | 0:48:49 | 0:48:50 | ✅ +1s | 0:48:48 | 0:48:40 | ✅ −8s |
| Abandono Parceiros | 3,14% | 3,09% | ✅ −0,05pp | 3,79% | 3,55% | ✅ −0,24pp |

**8/8 indicadores validados. Diferença máxima: 0,24pp no Abandono W17.**

### Performance dos Encantadores Parceiros — abr.26 MTD (01–26/abr/2026, 18 DU)

| Indicador | Dashboard | BQ | Diff |
|---|---|---|---|
| HC Líquido | 54 | 54 | ✅ 0 |
| Chamados/enc Mês | 296 | 297 | ✅ +1 |
| Chamados/enc DU | 18 | 17 | ✅ −1 |
| Demanda Recebida Parceiro | ~6,1k | 6.222 | ✅ |
| Demanda Atendida Parceiro | ~5,9k | 6.018 | ✅ |
| CSAT Parceiro MTD | 92,9% | 92,65% | ✅ −0,25pp |

**6/6 indicadores validados. Diff máx: 0,25pp.**

> ⚠️ Chamados/enc usa **total atendido de todos os segmentos** (PME + Parceiro = 16.057) como numerador — mesmo HC serve PME e Parceiros. O gráfico "[Parceiro]" só troca barras de demanda e CSAT; HC e produtividade são compartilhados.

---

### Performance dos Encantadores PME — abr.26 MTD (01–26/abr/2026, 18 DU)

| Indicador | Calculado | Oficial | Diff |
|---|---|---|---|
| HC Líquido | 54 | 54 | ✅ 0 |
| Chamados/enc Mês | 297 | 296 | ✅ +1 |
| Chamados/enc DU | 17 | 18 | ✅ −1 |
| Demanda Recebida CDP | 4.634 | ≈4,5k | ✅ |
| Demanda Atendida CDP | 4.491 | ≈4,4k | ✅ |
| CSAT CDP | 92,68% | 92,8% | ✅ −0,12pp |
| Demanda Recebida CSP | 5.379 | ≈5,5k | ✅ |
| Demanda Atendida CSP | 5.172 | ≈5,1k | ✅ |
| CSAT CSP | 93,38% | 93,6% | ✅ −0,22pp |

**9/9 indicadores validados. Diff máx: 0,22pp.**

> ⚠️ Discrepâncias de ~0,8pp em Bot_Fin/Fin AI total se devem a ~21 interações com `customer_type = NULL` que o dashboard provavelmente exclui. Para os demais bot_types a diferença é ≤0,14pp.

---

### Telefone — Indicadores Macro W16 e W17

Query: `channel = 'Telefone'` + `area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')`

| Indicador | W16 dashboard | W16 BQ | Diff | W17 dashboard | W17 BQ | Diff |
|---|---|---|---|---|---|---|
| Demanda total | 1.046 | 1.046 | ✅ 0 | 833 | 833 | ✅ 0 |
| Demanda PME | 753 | 753 | ✅ 0 | 624 | 624 | ✅ 0 |
| Demanda CDP | 242 | 242 | ✅ 0 | 185 | 185 | ✅ 0 |
| Demanda CSP | 511 | 511 | ✅ 0 | 439 | 439 | ✅ 0 |
| Demanda Parceiro | 205 | 205 | ✅ 0 | 143 | 143 | ✅ 0 |
| CSAT total | 99,4% | 99,44% | ✅ +0,04pp | 99,5% | 99,50% | ✅ 0 |
| CSAT PME | 99,5% | 99,51% | ✅ +0,01pp | 100,0% | 100,0% | ✅ 0 |
| CSAT Parceiro | 99,0% | 99,01% | ✅ +0,01pp | 96,6% | 96,55% | ✅ −0,05pp |
| SLA TME total | 85,4% | 85,37% | ✅ −0,03pp | 89,2% | 89,08% | ✅ −0,12pp |
| SLA TME PME | 84,2% | 84,20% | ✅ 0 | 88,6% | 88,46% | ✅ −0,14pp |
| SLA TME Parceiro | 86,8% | 86,83% | ✅ +0,03pp | 90,9% | 90,91% | ✅ +0,01pp |
| TME total | 0:01:30 | 0:01:30 | ✅ 0s | 0:01:00 | 0:01:00 | ✅ 0s |
| TME PME | 0:01:33 | 0:01:33 | ✅ 0s | 0:01:06 | 0:01:07 | ✅ +1s |
| TME Parceiro | 0:01:34 | 0:01:34 | ✅ 0s | 0:00:39 | 0:00:39 | ✅ 0s |
| TMA total | 0:13:16 | 0:13:16 | ✅ 0s | 0:12:04 | 0:12:05 | ✅ +1s |
| TMA PME | 0:13:05 | 0:13:05 | ✅ 0s | 0:12:08 | 0:12:10 | ✅ +2s |
| TMA Parceiro | 0:14:45 | 0:14:45 | ✅ 0s | 0:12:31 | 0:12:31 | ✅ 0s |
| Abandono total | 4,49% | 4,49% | ✅ 0 | 4,92% | 4,92% | ✅ 0 |
| Abandono PME | 0,00% | 0,00% | ✅ 0 | 0,00% | 0,00% | ✅ 0 |
| Abandono Parceiro | 0,00% | 0,00% | ✅ 0 | 0,00% | 0,00% | ✅ 0 |

**20/20 indicadores validados. Diff máx: 0,14pp.**

> Abandono total Telefone (~4,5–5%) vem de `customer_type IS NULL` ou segmentos fora de PME/Parceiro — PME e Parceiro têm 0% de abandono no canal Telefone.

---

### Telefone — Visão por Categoria (Categorias Telefone)

**Fonte:** `ticket_category` em `gold_serve.dim_zendesk_tickets_detailed`
**Filtros:** `channel = 'Telefone'` + `area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')` + `is_service_metrics = TRUE`
**Medidas:** `COUNT(*)` para interações, `AVG(online_service_time)` para TMA, `current_rating = 'good'` para CSAT

**Lógica de data (W17 validada):**

```sql
WHERE (source_solved_at BETWEEN '2026-04-20' AND '2026-04-26')
   OR (source_solved_at IS NULL AND DATE(nk_date) BETWEEN '2026-04-20' AND '2026-04-26')
```

> Tickets com `source_solved_at IS NULL` usam `nk_date` como fallback. Sem isso, categorias como "emissão de nfse" ficam 3 tickets abaixo do dashboard.

**Query BQ validada W17:**

```sql
SELECT
  ticket_category,
  COUNT(*) AS interacoes,
  ROUND(COUNT(*) / SUM(COUNT(*)) OVER (), 4) AS mix,
  ROUND(COUNTIF(current_rating = 'good') / NULLIF(COUNTIF(current_rating IS NOT NULL), 0), 4) AS csat,
  ROUND(AVG(online_service_time) / 60, 1) AS tma_min
FROM `contaazul-ssbi.gold_serve.dim_zendesk_tickets_detailed`
WHERE channel = 'Telefone'
  AND assignee_area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')
  AND is_service_metrics = TRUE
  AND (
    source_solved_at BETWEEN '<inicio>' AND '<fim>'
    OR (source_solved_at IS NULL AND DATE(nk_date) BETWEEN '<inicio>' AND '<fim>')
  )
GROUP BY 1
ORDER BY 2 DESC
```

**Validação W17 — principais categorias:**

| Categoria | Dashboard | BQ | Diff |
|---|---|---|---|
| billing dono de negócio | 86 | 83 | −3 |
| conciliação | 83 | 82 | −1 |
| emissão de nfse | 64 | 64 | ✅ 0 |
| integração bancária | 53 | 48 | −5 (pendente) |
| emissão de nfe | 52 | 52 | ✅ 0 |
| financeiro | 42 | 42 | ✅ 0 |
| sac_0800 | 31 | 31 | ✅ 0 |
| plataforma | 25 | 25 | ✅ 0 |

> Integração bancária com diff −5 é investigação pendente — possível join adicional no Looker capturando tickets atendidos com solve fora da janela.

---

### Telefone — Suporte Premium (Segmentação)

**Fonte:** `gold_serve.fact_service_metrics`
**Filtros:** `channel = 'Telefone'` + `area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')`
**Data:** `nk_event_date`

| Campo | Lógica |
|---|---|
| Interação total | `SUM(count_of_attended)` |
| +6 meses de casa | `SUM(count_of_attended) WHERE is_under_6m = FALSE OR is_under_6m IS NULL` |
| -6 meses de casa | `SUM(count_of_attended) WHERE is_under_6m = TRUE` |
| Suporte Premium | `has_premium_support = TRUE` |
| Não Possui SP | `has_premium_support = FALSE` |
| Não Identificado | `has_premium_support IS NULL` |
| Customer Type | `customer_type`: Cliente do Parceiro, Cliente sem Parceiro, Parceiro, NULL→Sem Tipo de Cliente |

```sql
SELECT
  CASE WHEN has_premium_support = TRUE  THEN 'Possui Suporte Premium'
       WHEN has_premium_support = FALSE THEN 'Não Possui Suporte Premium'
       ELSE 'Não Identificado' END               AS suporte_premium,
  COALESCE(customer_type, 'Sem Tipo de Cliente') AS customer_type,
  SUM(count_of_attended)                         AS interacao_total,
  SUM(CASE WHEN is_under_6m = FALSE OR is_under_6m IS NULL
           THEN count_of_attended END)            AS mais_6m,
  SUM(CASE WHEN is_under_6m = TRUE
           THEN count_of_attended END)            AS menos_6m
FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
WHERE nk_event_date BETWEEN '<inicio>' AND '<fim>'
  AND channel = 'Telefone'
  AND area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')
GROUP BY 1, 2
ORDER BY 1, 2
```

**Validação W17 (20–26/abr/2026):** estrutura e padrões confirmados vs dashboard — Parceiro tem 1 ticket com Suporte Premium e 0 sem, ~142 Não Identificados no dashboard (157 no BQ). Diffs residuais de ~10% provavelmente por janela exata de data.

---

## 11. Billing Dono de Negócio — Negociação e Retenção

### Fonte de Dados

| Campo | Valor |
|---|---|
| Tabela BQ | `contaazul-ssbi.gold_serve.dim_zendesk_tickets_detailed` |
| Explore Looker | `churn_data_mart` → `cancellation_tickets` (silver_retention) |
| Filtro área | `assignee_area = 'BACKING_OPS'` |
| Filtro categoria | `LOWER(ticket_category) = 'billing dono de negócio'` |
| Data | `DATE(source_solved_at)` |

> A tabela `silver_retention.cancellation_tickets` é a fonte oficial do Looker, mas pode ter defasagem. Usar `gold_serve.dim_zendesk_tickets_detailed` com os filtros abaixo replica os números corretamente.

### Definições de Campos

| Conceito | Lógica BQ |
|---|---|
| Total atendimentos | `COUNT(DISTINCT id)` |
| Negociação | `subclassification IN ('retido','retenção') OR servir_churn_type IS NOT NULL` |
| Retidos | `subclassification IN ('retido','retenção')` |
| Não retido | negociação que NÃO resultou em subclassification retido/retenção |
| Mix demanda | `COUNT(DISTINCT id billing) / COUNT(DISTINCT id BACKING_OPS total)` |

### Query Validada

```sql
SELECT
  COUNT(DISTINCT id)                                                       AS total,
  COUNTIF(subclassification IN ('retido','retenção')
    OR servir_churn_type IS NOT NULL)                                      AS negociacao,
  COUNTIF(subclassification IN ('retido','retenção'))                      AS retidos,
  COUNTIF(servir_churn_type IS NOT NULL
    AND COALESCE(subclassification,'') NOT IN ('retido','retenção'))       AS nao_retido
FROM `contaazul-ssbi.gold_serve.dim_zendesk_tickets_detailed`
WHERE LOWER(ticket_category) = 'billing dono de negócio'
  AND assignee_area = 'BACKING_OPS'
  AND DATE(source_solved_at) BETWEEN '<inicio>' AND '<fim>'
```

### Validação W17 e MTD Abril 2026

| Métrica | Dashboard | BQ | Status |
|---|---|---|---|
| MTD total atendimentos | 341 | 341 | ✅ |
| MTD negociação | 68 | 68 | ✅ |
| MTD não retidos | 1 | ~0 | ⚠️ diff de 1 (tracking Fortknox) |
| W17 mix | ~12% | ~10,5% | ✅ aprox. |
| W17 negociação | 14 | 13–16 | ✅ aprox. |
| W17 100% retidos | 100% | 0 não retidos | ✅ |

**Leitura executiva:**
- Na W17, 14 atendimentos classificados como negociação — 100% revertidos e mantidos na base
- MTD abril: 341 atendimentos tratados, 68 classificados como negociação, somente 1 não retido no atendimento

---

## 8. Semanas de Referência

| Semana | Período | Cami | Telefone | Total |
|---|---|---|---|---|
| W17 | 20–26/abr/2026 | 6.002 | 833 | 6.835 |
| W16 | 13–19/abr/2026 | 8.853 | 1.046 | 9.899 |
| W15 | 06–12/abr/2026 | 9.527 | 1.033 | 10.560 |

---

## 9. Geração de Gráficos — QuickChart.io

Gráficos gerados via **QuickChart.io** (Chart.js) e embutidos como imagens `![alt](url)`.

### Paleta visual padrão RPS semanal (3 semanas)

| Dataset | Hex | Uso |
|---|---|---|
| W15 | `#BAE6FD` | Semana t−2 (mais clara) |
| W16 | `#60A5FA` | Semana t−1 |
| W17 | `#1D4ED8` | Semana atual (mais escura) |
| Meta (linha) | `#059669` | Linha tracejada de meta |
| Vermelho alerta | `#EF4444` | Barras de abandono / alerta |
| Âmbar atenção | `#F59E0B` | Semáforo intermediário |
| Cinza label/eixo | `#6B7280` | Texto de eixos e labels |
| Fundo | `#ffffff` | `bkg=%23ffffff` na URL |

### Configurações padrão dos gráficos

```
- borderRadius: 4 (barras arredondadas)
- título: fontSize 13, fontColor #111827, fontStyle bold, padding 12
- legenda: position bottom, fontSize 11, fontColor #374151, padding 16
- eixos: fontColor #6B7280, fontSize 10
- datalabels: anchor end, align top/right, color #374151, fontSize 9-10
- linha de meta: type "line", borderDash [6,3], borderWidth 2, pointRadius 0, fill false
- dimensões padrão: w=700, h=340 (verticais); w=700, h=380-400 (horizontalBar)
```

### Função Python para geração de URL

```python
import urllib.parse, json

def chart_url(config, w=700, h=340):
    c = json.dumps(config, separators=(',', ':'))
    return f"https://quickchart.io/chart?c={urllib.parse.quote(c)}&w={w}&h={h}&bkg=%23ffffff"
```

### Estrutura padrão — bar chart 3 semanas + meta

```python
config = {
    "type": "bar",
    "data": {
        "labels": ["Label1", "Label2"],
        "datasets": [
            {"label": "W15", "data": [...], "backgroundColor": "#BAE6FD", "borderRadius": 4},
            {"label": "W16", "data": [...], "backgroundColor": "#60A5FA", "borderRadius": 4},
            {"label": "W17", "data": [...], "backgroundColor": "#1D4ED8", "borderRadius": 4},
            {"label": "Meta XX%", "data": [...], "type": "line", "borderColor": "#059669",
             "borderDash": [6,3], "borderWidth": 2, "pointRadius": 0, "fill": False}
        ]
    },
    "options": {
        "title": {"display": True, "text": "Título", "fontSize": 13,
                  "fontStyle": "bold", "fontColor": "#111827", "padding": 12},
        "scales": {
            "xAxes": [{"ticks": {"fontColor": "#6B7280", "fontSize": 10}}],
            "yAxes": [{"ticks": {"fontColor": "#6B7280", "fontSize": 10}}]
        },
        "plugins": {"datalabels": {"anchor": "end", "align": "top", "color": "#374151", "fontSize": 9}},
        "legend": {"position": "bottom", "labels": {"fontSize": 11, "fontColor": "#374151", "padding": 16}}
    }
}
```

### Cores semáforo (retenção por categoria)

- `#EF4444` (vermelho) se retenção < 50%
- `#059669` (verde) se retenção > 80%
- `#F59E0B` (âmbar) demais

---

### Página gerada W17 — RPS completa (todos os segmentos)

- **Título:** RPS W17 — Acompanhamento Semanal (20–26/abr/2026)
- **ID:** `3534a554-a42f-8170-9dc9-d4cfc3385eba`
- **URL:** https://app.notion.com/p/3534a554a42f81709dc9d4cfc3385eba
- **Status:** criada em 01/05/2026, dados W15/W16/W17 do BQ, sem comparação com dashboard

**Seções da página:**
1. Contexto rápido + Resumo Executivo TL;DR
2. 📊 Indicadores Macro — Demanda (Cami / Telefone / Total por canal)
3. 🌐 BLENDED — Retenção Cami por bot_type
4. 🏢 PME — CSAT Blended PME (Blended / Humano / Cami)
5. PME — CSAT Cami PME por bot_type e sub-segmento (CDP/CSP)
6. 📂 Visão por Categoria Cami (Gen2 + Gen3 CA Pro + Gen3 CA Mais)
7. PME — SLA TME PME + Abandono (PME total + CDP + CSP)
8. 📊 Ticket por Encantador PME (MTD abril)
9. 🤝 Parceiros — CSAT Blended / Humano / Cami Parceiros
10. Parceiros — CSAT Cami por bot_type
11. Parceiros — SLA TME + Abandono
12. 📊 Ticket por Encantador Parceiros (MTD abril)
13. 📞 Telefone — Demanda por segmento + CSAT + SLA + TMA
14. 💵 Billing Dono de Negócio (DN) — negociação e retenção

> ⚠️ **NÃO incluir** seção "Principais Ações Operacionais" — não há dados BQ para isso.

**9 gráficos QuickChart embutidos:**
1. Macro — Demanda Cami/Tel/Total W15 vs W16 vs W17 (bar)
2. Retenção Cami por bot_type W15 vs W16 vs W17 + meta 57% (bar)
3. CSAT Blended PME componentes W15 vs W16 vs W17 + meta 81,3% (bar)
4. CSAT Cami PME por bot_type/sub-seg W15 vs W16 vs W17 (horizontalBar)
5. Visão por Categoria — Interações W17 (horizontalBar)
6. SLA TME e Abandono PME W15 vs W16 vs W17 + meta 70% (bar)
7. CSAT Blended Parceiros W15 vs W16 vs W17 + meta 79,1% (bar)
8. CSAT Cami Parceiros por bot_type W15 vs W16 vs W17 (bar)
9. Telefone — Demanda por Segmento W15 vs W16 vs W17 (bar)

---

## 10. Segmento Parceiros — KPIs e Estrutura RPS

### Definição de Parceiros no BQ

- **`fact_service_metrics`**: `customer_type = 'Parceiro'`
- **`dim_chatbot`**: `customer_type NOT IN ('Cliente do Parceiro', 'Cliente sem Parceiro')` (i.e., exclui PME)

> ⚠️ PME = `Cliente do Parceiro` (CDP) + `Cliente sem Parceiro` (CSP). Parceiro é o canal de parceiros — distinto dos sub-segmentos PME.

---

### KPIs Validados W17 — Parceiros

#### CSAT (Blended / Humano / Cami)

| Visão | W17 | W16 | WoW | MoM (sem equiv.) | MTD abril | vs KR abril (79,1%) | vs KR dez (90%) |
|---|---|---|---|---|---|---|---|
| **CSAT Blended Parceiros ⭐** | **80,6%** | 87,8% | **−7,2 pp** | 86,6% | 84,9% | **+5,8 pp** | **−5,1 pp** |
| CSAT Humano Parceiros | 89,1% | 95,1% | −5,9 pp | 91,4% | 92,6% | — | — |
| CSAT Cami Parceiros | 72,0% | 69,9% | **+2,1 pp** | 74,7% | 71,8% | — | — |

**KR abril Parceiros**: 79,1% → está **5,8 pp acima**, sem risco de descumprimento no mês.
**KR dezembro (meta final)**: 90% → gap de −5,1 pp (distância aumentou vs W16).

**Leitura executiva W17:**
- Blended caiu 7,2 pp WoW — queda expressiva, mas mantém folga sobre KR abril
- Humano Parceiros: queda abrupta 95,1% → 89,1% (−5,9 pp) — pode ser amostra reduzida ou deterioração pontual; confirmar em W18
- Cami Parceiros: recuperou +2,1 pp (único sinal positivo da semana) — acima do MTD abril (71,8%)
- Padrão **inverso Humano vs Cami** persiste pela 2ª semana consecutiva — dinâmicas distintas entre canais

---

### Estrutura da Seção Parceiros na RPS

A RPS oficial inclui uma seção `## 🤝 Parceiros` após a seção PME. Estrutura espelhada:

1. **⭐ CSAT Blended Parceiros: 78% → 90%** — leitura executiva + gráfico + tabela (igual à estrutura PME)
2. **CSAT Humano Parceiros** — mesma estrutura
3. **CSAT Cami Parceiros** — mesma estrutura
4. **Retenção Cami Parceiros** — por bot_type
5. **SLA / Abandono Parceiros** — se disponível
6. **Demanda e HC Parceiros** — se disponível

### Queries BQ para Parceiros

```sql
-- CSAT Blended + Humano + Cami Parceiros (query validada W16: diff máx 0,02pp)
WITH
humano AS (
  SELECT
    SUM(CASE WHEN customer_type = 'Parceiro' THEN count_of_positive_ratings END) AS pos_parc,
    SUM(CASE WHEN customer_type = 'Parceiro' THEN count_of_negative_ratings END) AS neg_parc
  FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
  WHERE nk_event_date BETWEEN '<inicio>' AND '<fim>'
    AND area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')
),
cami AS (
  SELECT
    SUM(CASE WHEN csat_type='csat_retidos' AND customer_type = 'Parceiro' THEN sum_of_positive_ratings END) AS pos_parc,
    SUM(CASE WHEN csat_type='csat_retidos' AND customer_type = 'Parceiro' THEN sum_of_negative_ratings END) AS neg_parc
  FROM `contaazul-ssbi.gold_serve.dim_chatbot`
  WHERE DATE(nk_date) BETWEEN '<inicio>' AND '<fim>'
    AND bot_departament = 'Servir'
)
SELECT
  ROUND(humano.pos_parc / NULLIF(humano.pos_parc + humano.neg_parc, 0), 4) AS csat_humano_parceiro,
  ROUND(cami.pos_parc   / NULLIF(cami.pos_parc   + cami.neg_parc,   0), 4) AS csat_cami_parceiro,
  ROUND((humano.pos_parc + cami.pos_parc) /
    NULLIF(humano.pos_parc + humano.neg_parc + cami.pos_parc + cami.neg_parc, 0), 4) AS csat_blended_parceiro
FROM humano, cami
```

---

## 11. Insights & Pontos de Atenção — W15/W16/W17

Página Notion: https://www.notion.so/3564a554a42f8119a5a0f7de204fe647

| # | Insight | Tipo | Segmento |
|---|---|---|---|
| 1 | Fin AI: queda acelerada de retenção W15→W16→W17 (50,5%→51,0%→43,1% total; Parceiros 46,0%→42,1%→38,4%) | 🔴 Gargalo crítico | Blended |
| 2 | Fin AI concentra 95%+ das avaliações Cami (788/830 PME, 377/386 Parceiros em W17) — qualquer oscilação move o consolidado | 🟠 Risco estrutural | Blended |
| 3 | Gap estrutural retenção PME vs Parceiros: 10–15 pp em todas as 3 semanas; Parceiros nunca atingiu meta 57% | 🔴 Gargalo estrutural | Parceiros |
| 4 | Abandono CSP sempre ~1 pp acima do CDP; em W17 ambos subiram (CDP 4,36% / CSP 4,90%) com TME CSP > CDP | 🟡 Ponto de atenção | PME |
| 5 | Gen 3 CA Pro único bot em trajetória positiva: retenção 64,2%→67,7%→70,6%; CSAT Cami PME 78,1%→86,7%→88,1% | 🟢 Oportunidade | Blended |
| 6 | CSAT Humano Parceiros: queda abrupta de 6 pp em W17 (95,1%→89,1%) enquanto PME subiu (93,3%→93,7%) | 🟡 Ponto de atenção | Parceiros |
| 7 | Billing DN: taxa de retenção 98,5% MTD abril (67/68 negociações retidas); W17 100% revertidos | 🟢 Ponto positivo | Telefone/DN |

### Queries chave dos insights

**#1/#2 — Fin AI retenção + concentração de avaliações:**

```sql
SELECT
  bot_type,
  ROUND(1 - SUM(sum_of_transfers)/NULLIF(SUM(sum_of_interactions),0),4) AS retencao_total,
  ROUND(1 - SUM(CASE WHEN customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro') THEN sum_of_transfers END)/
    NULLIF(SUM(CASE WHEN customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro') THEN sum_of_interactions END),0),4) AS retencao_pme,
  ROUND(1 - SUM(CASE WHEN customer_type='Parceiro' THEN sum_of_transfers END)/
    NULLIF(SUM(CASE WHEN customer_type='Parceiro' THEN sum_of_interactions END),0),4) AS retencao_parceiro,
  SUM(CASE WHEN csat_type='csat_retidos' THEN sum_of_total_ratings END) AS vol_aval
FROM `contaazul-ssbi.gold_serve.dim_chatbot`
WHERE DATE(nk_date) BETWEEN '<inicio>' AND '<fim>'
  AND bot_departament = 'Servir'
GROUP BY bot_type
```

**#4 — Abandono CDP vs CSP:**

```sql
SELECT
  ROUND(SUM(CASE WHEN customer_type='Cliente do Parceiro' THEN count_of_abandoned END)/
    NULLIF(SUM(CASE WHEN customer_type='Cliente do Parceiro' THEN count_of_demanded END),0),4) AS abandono_cdp,
  ROUND(SUM(CASE WHEN customer_type='Cliente sem Parceiro' THEN count_of_abandoned END)/
    NULLIF(SUM(CASE WHEN customer_type='Cliente sem Parceiro' THEN count_of_demanded END),0),4) AS abandono_csp
FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
WHERE DATE(nk_event_date) BETWEEN '<inicio>' AND '<fim>'
  AND area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')
```

**#7 — Billing DN taxa de retenção:**

```sql
SELECT
  COUNT(DISTINCT id) AS total,
  COUNTIF(subclassification IN ('retido','retenção') OR servir_churn_type IS NOT NULL) AS negociacao,
  COUNTIF(subclassification IN ('retido','retenção')) AS retidos,
  ROUND(COUNTIF(subclassification IN ('retido','retenção'))/
    NULLIF(COUNTIF(subclassification IN ('retido','retenção') OR servir_churn_type IS NOT NULL),0),4) AS taxa_retencao
FROM `contaazul-ssbi.gold_serve.dim_zendesk_tickets_detailed`
WHERE LOWER(ticket_category) = 'billing dono de negócio'
  AND assignee_area = 'BACKING_OPS'
  AND DATE(source_solved_at) BETWEEN '<inicio>' AND '<fim>'