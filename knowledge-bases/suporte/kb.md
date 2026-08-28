# Conhecimento Domínio Atendimento — ContaAzul
> Atualizado em 28/08/2026 · construído em 01/05/2026

> **Revisão de 28/08/2026** — auditoria contra o LookML em `repos/looker/` e o Book Pré-RMR.
>
> **Definições corrigidas** (agora batem com o LookML): retenção Cami com `GREATEST` + dia útil;
> SLA TME `<= 180`; HC Líquido sem `CAST`; densidade com `total_active_companies_by_day`;
> DU derivado de `dim_date.national_work_day`; contatos únicos com `CONCAT(company, accountancy)`.
>
> **Fatos errados corrigidos**: `customer_type != 'Parceiro'` **não** é PME (existe `'N/I'`, até 11%
> do volume); o HC histórico de 54 estava errado (era 61,63 — o período tem 16 DU, não 18);
> `sum_of_final_bot` é campo morto (sempre 0); `bot_departament` NULL não é Bot_Fin;
> Gen2 praticamente extinto; `dim_chatbot_holidays` não tem linhas de 2026.
>
> **Dicionário completado**: `subcategory`, `partner_profile`, `nk_accountancy_id`, canais
> `Ios`/`Android`, `sac_theme`, `leader`, `sub_leader`, `tool`, campos Gen3 — ~20 no total.
>
> **Armadilha transversal nova**: labels e descriptions do LookML contradizem o `sql:` — ver §5.
>
> **Cobertura nova (28/08/2026)**: **FCR** (`tmp_servir.vw_rps_fcr_semanal`) e **pNPS/rNPS**
> (`gold_nps.fact_nps_survey`) — definições, séries de 2026 e 8 armadilhas próprias, incluindo a
> contaminação do pNPS de CA Pro em agosto e a troca de ferramenta IndeCX→Survicate em 31/12/2025.
>
> Tabelas de validação da §7 recalculadas — **leia o aviso no topo daquela seção antes de usar
> qualquer número de abril/2026**.

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
| event_hour | INTEGER | Hora do evento |
| channel | STRING | Canal: Chat, Email, Telefone, Web, Whatsapp — **e `''` (string vazia), ver armadilha §5** |
| area | STRING | Área do encantador: BK, DN, EC, SAC - CA, SAC - Pessoalize, Ouvidoria - IP, RT |
| nk_email | STRING | E-mail do encantador |
| squad | STRING | Time por matriz de produto |
| leader | STRING | Líder do encantador |
| sub_leader | STRING | Sub-líder do encantador |
| sac_theme | STRING | Tema que o cliente selecionou para falar com o SAC |
| tool | STRING | Ferramenta de origem da demanda |
| customer_type | STRING | `Parceiro`, `Cliente do Parceiro`, `Cliente sem Parceiro` (não existe valor literal `PME`) |
| **partner_profile** | STRING | **Perfil do parceiro contábil**: `CONTADOR`, `BPO`, `MISTO`. NULL quando não é Parceiro |
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
- `''` (string vazia): existe **dentro** do filtro de área padrão. Em jul/26 são 61 chamados
  demandados e **61 abandonados** (100% de abandono). Ver armadilha §5.

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
| event_hour | INTEGER | Hora do evento |
| channel | STRING | Canal: `Whatsapp`, `Chat`, `Ios`, `Android` |
| team | STRING | Produto: CA Mais, CA Pro, Conta PJ |
| subject | STRING | Assunto da interação |
| **subcategory** | STRING | **Subcategoria temática da interação** — categorização nativa, ver §5 |
| bot_type | STRING | Tipo de bot: Gen2, Gen3 CA Mais, Gen3 CA Pro, Bot_Fin |
| bot_departament | STRING | Departamento: `Servir`, `Retenção` |
| csat_type | STRING | N/I, csat_retidos, csat_transbordados |
| csat_bot_comment | STRING | Comentário deixado na avaliação do bot |
| open_offline | BOOLEAN | Conversa abriu ticket offline (só interações vindas do Intercom) |
| is_gen3 | BOOLEAN | É fluxo Gen3 |
| nk_company_id | INTEGER | ID da empresa (−1 se indisponível) |
| **nk_accountancy_id** | INTEGER | **ID do escritório contábil** (−1 se indisponível) — parte da chave de contatos únicos |
| customer_type | STRING | `Parceiro`, `Cliente do Parceiro`, `Cliente sem Parceiro` (não existe valor literal `PME`) |
| **partner_profile** | STRING | **Perfil do parceiro contábil**: `CONTADOR`, `BPO`, `MISTO`. NULL quando não é Parceiro |
| partner_level | STRING | Nível do parceiro no Programa de Parceria |
| has_premium_support | BOOLEAN | Possui suporte premium |
| is_partner | BOOLEAN | É parceiro |
| is_under_6m | BOOLEAN | Cliente com menos de 6 meses de vida na abertura |
| thread_uid | STRING | ID único da conversa |
| sum_of_interactions | INTEGER | Nº de interações (= 1 por linha) |
| sum_of_transfers | INTEGER | Transbordos para humano |
| sum_of_final_bot | INTEGER | ⚠️ **Sempre 0** — campo morto, ver armadilha §5 |
| sum_of_positive_ratings | INTEGER | Avaliações positivas |
| sum_of_negative_ratings | INTEGER | Avaliações negativas |
| sum_of_total_ratings | INTEGER | Total de avaliações (**= positivas + negativas**, verificado) |
| sum_of_positive_ratings_gen3 | INTEGER | Avaliações positivas geradas pela IA Gen3 |
| sum_of_negative_ratings_gen3 | INTEGER | Avaliações negativas geradas pela IA Gen3 |
| sum_of_total_ratings_gen3 | INTEGER | Total de avaliações Gen3 |

**Valores de channel** (grafia exata — comparação em SQL é *case-sensitive*):
- `Whatsapp` e `Chat` — os dois canais principais
- `Ios` e `Android` — app CA de Bolso. **É `Ios`, com I maiúsculo e "os" minúsculo** — escrever
  `'iOS'` não casa com nada e descarta o canal silenciosamente.
- O filtro oficial do canal está no tile 20110 do dashboard 220: `Android, Chat, Ios, Whatsapp`.
- Volume de app é pequeno mas não-nulo (jul/26: 430 `Ios` + 240 `Android` de 42.135 interações Servir).

**Valores de bot_type presentes**:
- `Bot_Fin` — bot Financeiro/FinAI (**não é o Cami**) — hoje é **99% do volume**
  (jul/26: 41.772 de 42.135 interações do departamento Servir)
- `Gen3 CA Pro` — bot Gen3 para CA Pro (Chat e Whatsapp) — jul/26: 299 interações
- `Gen3 CA Mais` — bot Gen3 para CA Mais (Chat) — jul/26: 60 interações
- `Gen2` — ⚠️ **praticamente extinto**: 4 interações em jul/26 no Servir. A descrição histórica
  ("bot principal de Whatsapp") vale para o período W16/abr-2026, não para hoje.

**Valores de bot_departament**:
- `Servir` — fluxo de suporte principal ← usado nas métricas de Atendimento
- `Retenção` — fluxo de retenção de clientes
- ⚠️ **NULL não é "Bot_Fin sem departamento"** — as linhas com `bot_departament IS NULL` têm
  **0 interações**. O Bot_Fin está distribuído entre `Servir` (41.772) e `Retenção` (6.712) em jul/26.
  (A description do schema menciona um valor `Ouvidoria`, que não aparece nos dados dos últimos 12 meses.)

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
| `gold_serve.dim_chatbot_holidays` | Feriados por canal — ⚠️ **sem linhas de 2026**, ver §4 Retenção |
| `silver_serve.agent_capacity` | Capacidade dos encantadores (team = 'Servir') |
| `tmp_servir.vw_rps_fcr_semanal` | **FCR semanal** — é uma *view*, escaneia 2,13 GB por execução |
| `gold_nps.fact_nps_survey` | **pNPS / rNPS** — 1 linha = 1 resposta de pesquisa |

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
-- Dias úteis = COUNT DISTINCT das datas com national_work_day na dim_date.
-- É assim que o Looker conta (dim_date.total_work_days, filtrado por dim_date.is_work_day,
-- que por sua vez é gold_common.dim_date.national_work_day) —
-- ver repos/looker/0-Common/views/dim_date.view.lkml:195 e :210.
SELECT COUNT(DISTINCT nk_date) AS qtd_dias_uteis
FROM `contaazul-ssbi.gold_common.dim_date`
WHERE nk_date BETWEEN '<inicio>' AND '<fim>'
  AND national_work_day
-- Exemplo: julho/2026 = 23 DU · semana padrão seg-sex sem feriado = 5 DU
-- Exemplo W16: 8.853 / 5 = 1.771 (Cami) | 1.046 / 5 = 209 (Telefone)
```

> ⚠️ Não é um filtro de dia útil — é divisão do total pelo nº de DU do período.
> **Derive o DU da `dim_date`, não conte "seg a sex" na mão**: o `national_work_day` já exclui
> feriado nacional. Numa janela mensal a diferença é real (jul/26 tem 23 DU, não 23 dias seg-sex).

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

### Retenção Cami (= "Deflexão Cami") — KPI oficial
> % de interações que o bot resolveu sem precisar transbordar para humano.
> **Sinônimo**: o Book Pré-RMR chama esta métrica de **Deflexão Cami**. É a mesma coisa.
>
> Definição autoritativa: measure `dim_chatbot.pct_retention` em
> `repos/looker/1-SERVE/views/dim_chatbot.view.lkml:240` →
> `greatest(1 - transbordos/interações, 0)`, **como consumida pelo tile "Retenção" (id 5691)
> do dashboard 210**, que filtra `dim_date.day_name: -Sábado,-Domingo` +
> `dim_chatbot_holidays.is_holiday: Yes`.
>
> Três coisas que a fórmula ingênua erra: (1) falta o `GREATEST(...,0)`; (2) conta fim de semana;
> (3) não exclui feriado **por canal**.

```sql
-- KPI de Retenção (Deflexão) da Cami — regra do tile "Retenção" do dashboard 210
WITH base AS (
  SELECT
    c.customer_type,
    c.sum_of_interactions,
    c.sum_of_transfers,
    -- dia útil E não-feriado NAQUELE canal (join em channel + data)
    ((dd.day_name NOT IN ('Domingo','Sábado') OR dd.day_name IS NULL)
      AND h.nk_date IS NULL)                                        AS is_business_day
  FROM `contaazul-ssbi.gold_serve.dim_chatbot` c
  LEFT JOIN `contaazul-ssbi.gold_common.dim_date` dd
    ON c.nk_date = dd.nk_date
  LEFT JOIN `contaazul-ssbi.gold_serve.dim_chatbot_holidays` h
    ON h.channel = c.channel AND DATE(h.nk_date) = c.nk_date
  WHERE c.nk_date BETWEEN '<inicio>' AND '<fim>'
    AND c.bot_departament = 'Servir'
)
SELECT
  ROUND(GREATEST(0, 1 - SAFE_DIVIDE(
    SUM(IF(is_business_day, sum_of_transfers, 0)),
    SUM(IF(is_business_day, sum_of_interactions, 0)))), 4)          AS retencao_total,
  ROUND(GREATEST(0, 1 - SAFE_DIVIDE(
    SUM(IF(is_business_day AND customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro'), sum_of_transfers, 0)),
    SUM(IF(is_business_day AND customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro'), sum_of_interactions, 0)))), 4) AS retencao_pme,
  ROUND(GREATEST(0, 1 - SAFE_DIVIDE(
    SUM(IF(is_business_day AND customer_type = 'Parceiro', sum_of_transfers, 0)),
    SUM(IF(is_business_day AND customer_type = 'Parceiro', sum_of_interactions, 0)))), 4) AS retencao_parceiro
FROM base
```

> ⚠️ **Existem DUAS retenções oficiais no dashboard 210** — não são erro, são recortes diferentes:
> | Tiles | Filtro de dia | Quando usar |
> |---|---|---|
> | `Retenção` (5691), `Retenção Diária` (5688) | dia útil + exclui feriado | **KPI** — é a resposta padrão |
> | `Acumulado Mensal` (12073/12074/12086), `Detalhado *`, `Retenção por hora` | sem filtro de dia | retenção **observada** no período |
>
> Para a visão sem filtro, use a mesma query sem o `IF(is_business_day, ...)`.
> Diferença medida: **0,5 a 1,2pp** ao mês (a versão sem filtro é sempre mais alta).
> Motivo: no fim de semana não há encantador para receber transbordo, então a retenção
> fica artificialmente em ~96% (vs ~57% em dia útil, mai–jul/26) — o KPI exclui esse período
> justamente porque a métrica não significa nada ali.

> ℹ️ Numa janela **segunda a sexta** as duas regras dão exatamente o mesmo número
> (o filtro não remove nada). A diferença só aparece em janela que inclui fim de semana
> — atenção: as "semanas" desta KB (W15/W16/W17) são de **7 dias**, segunda a domingo.

> 🔴 **`dim_chatbot_holidays` está desatualizada — o join de feriado é INERTE em 2026.**
> A tabela tem **32 linhas**, de 12/02/2024 a **20/11/2025**, só nos canais `Chat`, `Web` e `Whatsapp`.
> Não há nenhuma linha de 2026. Consequência prática:
> - o `h.nk_date IS NULL` é sempre verdadeiro para datas de 2026 → **na prática só o filtro de
>   fim de semana está atuando**;
> - a diferença de 0,5–1,2pp que se observa entre KPI e retenção observada vem **inteiramente
>   do fim de semana**, não de feriado;
> - feriados nacionais de 2026 (ex.: Tiradentes 21/04, Sexta-feira Santa 03/04) **contam como
>   dia útil** na retenção — tanto na sua query quanto no tile do Looker.
>
> Mantenha o join mesmo assim: é o que o tile faz, e volta a ter efeito se a tabela for
> repovoada. Mas **não confunda com o `national_work_day` da `dim_date`**, que cobre 2026
> normalmente e é quem deve contar dias úteis (ver "Demanda por DU").

---

### Contatos Únicos do Chatbot (clientes distintos)
> Quantos clientes distintos falaram com a Cami no período.
> Definição: measure `dim_chatbot.count_of_distinct_customers` em
> `repos/looker/1-SERVE/views/dim_chatbot.view.lkml:274`.

```sql
SELECT COUNT(DISTINCT CONCAT(nk_company_id, nk_accountancy_id)) AS contatos_unicos
FROM `contaazul-ssbi.gold_serve.dim_chatbot`
WHERE nk_date BETWEEN '<inicio>' AND '<fim>'
  AND bot_departament = 'Servir'
```

> ⚠️ A chave é o **CONCAT de `nk_company_id` com `nk_accountancy_id`** — não é
> `COUNT(DISTINCT nk_company_id)` nem contagem de `thread_uid`. Um mesmo `nk_company_id`
> atendido por escritórios contábeis diferentes conta como contatos distintos.
> Medido em 08–12/jun/2026 (Servir, canais Chat/Web/Whatsapp): **4.309** pela regra correta,
> contra 3.077 se usar só `nk_company_id` e 8.242 se contar `thread_uid` (= nº de interações).

> ℹ️ O `CONCAT` sem separador tem colisão teórica (empresa `1` + contabilidade `23` gera a mesma
> string que empresa `12` + contabilidade `3`). **Reproduza assim mesmo** — é exatamente o que a
> measure do Looker faz, e o objetivo aqui é bater com o dashboard. Não "conserte" com separador:
> o número deixaria de casar.

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
> % de tickets com TME médio **menor ou igual a** 180 segundos.
> Definição: dimensão `fact_service_metrics.sla_tme_3min` em
> `repos/looker/1-SERVE/views/fact_service_metrics.view.lkml:276`.

```sql
SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone')
         AND (sum_of_te / NULLIF(count_of_demanded,0)) <= 180
    THEN count_of_demanded END) /
NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') THEN count_of_demanded END), 0)
```

> ⚠️ É `<= 180`, **não** `< 180`. O label e a description do LookML dizem "menor do que 180 segundos",
> mas o SQL da dimensão usa `<=`. Vale a regra geral da §5: **confiar no SQL, não no nome**.
> (Existe também `sla_tme_5min`, com `<= 300`.)

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
-- ⚠️ is_active_workday é NUMERIC (decimal), NÃO booleano — nunca use CAST(... AS INT64)
SELECT ROUND(SUM(is_active_workday) / <qtd_du>, 2) AS hc_liquido
FROM `contaazul-ssbi.silver_serve.agent_capacity`
WHERE event_date BETWEEN '<inicio>' AND '<fim>'
  AND team = 'Servir'

-- Chamados atendidos por encantador Mês = total atendido / HC Líquido
-- Chamados atendidos por encantador DU  = total atendido / HC Líquido / DU
-- total atendido = SUM(count_of_attended) de fact_service_metrics (todos os segmentos)
```

> 🔴 **O valor histórico "HC=54" desta KB estava errado** — veio de dividir por 18 dias úteis,
> mas 01–26/abr/2026 tem **16** (03/abr Sexta-feira Santa e 21/abr Tiradentes são feriados
> nacionais). Recalculado em 28/08/2026: **HC = 61,63 · Chamados/enc mês = 260 · Chamados/enc DU = 16,2**.
> Sempre derive o `<qtd_du>` da `dim_date` (ver "Demanda por DU"), nunca contando dias de semana.

---

### Densidade de Demanda
> Definição: measure `fact_service_metrics.density_tickets` em
> `repos/looker/1-SERVE/views/fact_service_metrics.view.lkml:133`.

```sql
SAFE_DIVIDE(SUM(count_of_demanded), MAX(dim_active_companies_by_month.total_active_companies_by_day))
-- JOIN: date_trunc(nk_event_date, month) = nk_month de dim_active_companies_by_month
```

> ⚠️ O denominador é `total_active_companies_by_day`, **não** `total_active_companies`.

---

### FTE (Capacidade)

```sql
-- PDT inline: silver_serve.agent_capacity WHERE team = 'Servir'
SUM(capacity) / SUM(count_of_demanded)
```

---

### FCR — Resolução no Primeiro Contato
> % dos atendimentos resolvidos sem o cliente precisar voltar.
> Fonte: `contaazul-ssbi.tmp_servir.vw_rps_fcr_semanal` — é uma **view semanal**, não tabela.
> Grão: uma linha por (semana × `tipo` × `categoria`). Cobertura: 27/04/2025 a 16/08/2026.

```sql
SELECT
  FORMAT_DATE('%Y-%m', DATE_TRUNC(semana_inicio, MONTH))              AS mes,
  SUM(numerador)                                                      AS resolvidos_1o_contato,
  SUM(denominador)                                                    AS total_atendimentos,
  ROUND(100 * SAFE_DIVIDE(SUM(numerador), SUM(denominador)), 2)       AS fcr_pct
FROM `contaazul-ssbi.tmp_servir.vw_rps_fcr_semanal`
WHERE semana_inicio BETWEEN '<inicio>' AND '<fim>'
  AND tipo = 'humano'
GROUP BY 1
ORDER BY 1
```

**Campos**: `semana_inicio`, `semana_fim`, `semana_label` (DATE/STRING) · `tipo` (`humano` \| `bot`) ·
`categoria` (28 valores no humano; aceita NULL) · `numerador`, `denominador` (INT) ·
`fcr_pct`, `nao_fcr_pct` (FLOAT, já calculados por linha).

**Série FCR humano 2026** (medida em 28/08/2026):

| jan | fev | mar | abr | mai | jun | jul | ago |
|---|---|---|---|---|---|---|---|
| 65,31% | 69,19% | 70,25% | 72,13% | 69,03% | 70,45% | 68,22% | 71,04% |

> ⚠️ **`tipo = 'humano'` é obrigatório.** Sem o filtro, o agregado vai a **76,7%**; o bot sozinho
> dá **81,2%**. São métricas de coisas diferentes — o FCR de atendimento é o humano.
>
> ⚠️ **Use `SUM(numerador)/SUM(denominador)`, nunca `AVG(fcr_pct)`** — média de proporção pesa
> semanas pequenas igual a semanas grandes.
>
> ⚠️ **Custo: 2,13 GB por execução.** A view não é particionada nem clusterizada, e o `WHERE` em
> `semana_inicio` **não** reduz o scan. Rode uma vez e reaproveite; nunca em loop.
>
> ⚠️ **Semanas atravessam o mês.** `DATE_TRUNC(semana_inicio, MONTH)` atribui a semana inteira ao
> mês em que ela começou — é aproximação, não recorte exato de mês.
>
> 🔴 **O FCR do bot mudou de patamar**: ~87% até abril, **98,2% em junho e 98,96% em julho**.
> Salto grande demais para ser real. Investigue antes de reportar qualquer FCR de bot.

---

### pNPS e rNPS
> Fonte: `contaazul-ssbi.gold_nps.fact_nps_survey` — dataset **`gold_nps`**, não `tmp`.
> Grão: 1 linha = 1 resposta de pesquisa.
> `NPS = (Promotores − Detratores) / total de respostas × 100`

```sql
SELECT
  FORMAT_DATE('%Y-%m', DATE(nk_date))                                 AS mes,
  segment,
  COUNT(*)                                                            AS respostas,
  COUNT(DISTINCT nk_company)                                          AS empresas,
  COUNTIF(nps_classification = 'Promotor')                            AS promotores,
  COUNTIF(nps_classification = 'Neutro')                              AS neutros,
  COUNTIF(nps_classification = 'Detrator')                            AS detratores,
  ROUND(100 * SAFE_DIVIDE(
    COUNTIF(nps_classification = 'Promotor') - COUNTIF(nps_classification = 'Detrator'),
    COUNT(*)), 1)                                                     AS nps
FROM `contaazul-ssbi.gold_nps.fact_nps_survey`
WHERE DATE(nk_date) BETWEEN '<inicio>' AND '<fim>'
  AND nps_type = 'pNPS'
GROUP BY 1, 2
ORDER BY 1 DESC, 2
```

**Campos-chave**:

| Campo | Valores / uso |
|---|---|
| `nps_classification` | **em português**: `Promotor` (nota 9–10), `Neutro` (7–8), `Detrator` (0–6) |
| `nps_type` | `pNPS`, `rNPS`, `Não identificado` |
| `segment` | `CA Mais` = parceiros contadores · `CA Pro` = donos de negócio (PME) |
| `survey_name_standard` | campanha, ex.: `[Oficial_Pro] 2026 pNPS Ciclo 2` |
| `nps_tool` | `Survicate` (viva) · `Tracksale`, `IndeCX` (descontinuadas) |
| `nk_company` | COALESCE de empresa e escritório contábil — depende do `segment` |
| `sk_nps_survey` | **a chave de unicidade** — `nk_answer` só é único por ferramenta |
| `nps_answer`, `nps_comment` | nota 0–10 e comentário livre |

**Série pNPS 2026** (medida em 28/08/2026):

| Mês | CA Pro | CA Mais |
|---|---|---|
| mai | 54,5 | 66,3 |
| jun | 54,5 | 64,2 |
| jul | 55,1 | 59,8 |
| ago | **22,5** ⚠️ | 65,4 |

> 🔴 **NÃO reporte o pNPS de CA Pro de agosto/2026 sem tratar.** A campanha
> `[Oficial_Pro] 2026 pNPS Ciclo 2` reenviou para quem já havia respondido: **15.742 respostas de
> 5.290 empresas = 2,98 por empresa**, contra ~1,05 em maio/junho/julho. A nota cai de 55,1 para
> 22,5 sem que nada tenha piorado. Não é duplicação de linha — `sk_nps_survey` e `nk_answer` são
> únicos; a pesquisa foi mesmo respondida várias vezes. **CA Mais não foi afetado.**
> Mitigação: deduplique por empresa (ex.: última resposta por `nk_company` no período) ou
> filtre a campanha.
>
> 🔴 **Troca de ferramenta em 31/12/2025 — IndeCX → Survicate.** Todo dado anterior a 2026 tem
> `nps_type = 'Não identificado'` (a IndeCX não marcava o ciclo no nome da campanha).
> **Filtrar `nps_type = 'pNPS'` descarta silenciosamente todo o histórico de 2025**
> (16.011 respostas de CA Pro + 2.293 de CA Mais). Para série longa, use `segment` + `nk_date`
> e **não** filtre `nps_type`.
>
> ⚠️ **rNPS é praticamente inexistente**: 20 respostas no total (CA Mais, mar–abr/2026).
> Se a pergunta for sobre rNPS, responda que não há base suficiente.

---

## 5. Armadilhas e Cuidados ⚠️

### ⚠️ Regra geral: os nomes do LookML mentem — confie no `sql:`

Três casos confirmados em `repos/looker/`, todos capazes de inverter uma query:

| Campo | O nome/description sugere | O `sql:` faz |
|---|---|---|
| `dim_chatbot_holidays.is_holiday`<br>(`dim_chatbot_holidays.view.lkml:21`) | label "Desconsiderar Feriados?" — parece **marcar** feriados | `${TABLE}.nk_date is null` → `Yes` significa **NÃO é feriado**. O filtro `is_holiday: "Yes"` **exclui** feriados |
| `fact_service_metrics.sla_tme_3min`<br>(`fact_service_metrics.view.lkml:276`) | "tickets que possuem TE médio **menor do que** 180 segundos" | `<= 180` |
| `dim_chatbot.rated_demands`<br>(`dim_chatbot.view.lkml:266`) | "em relação aos clientes que chegaram no **chatbot Final**" | divide por `count_of_interactions`, não por `count_of_final_bot` |

Ao traduzir um tile do Looker para SQL, **abra o `.lkml` e leia o `sql:`**.

### ⚠️ Um dashboard pode ter duas definições da mesma métrica

O dashboard 210 expõe `pct_retention` com filtro de dia útil nos tiles de KPI e **sem** filtro nos
tiles de detalhe. Não é bug — são perguntas diferentes ("KPI de retenção" vs "retenção observada").
Antes de responder, identifique **qual tile** a pergunta quer. Ver "Retenção Cami" na §4.

### dim_chatbot — Cuidados críticos
| # | Armadilha | Detalhe |
|---|---|---|
| 1 | **Bot_Fin não é o Cami** | bot_type='Bot_Fin' é o bot Financeiro/FinAI — incluído em `bot_departament='Servir'` mas representa produto diferente. Para demanda Cami usar `bot_departament='Servir'` sem filtrar bot_type (o dashboard oficial inclui Bot_Fin) |
| 2 | **csat_type cria múltiplas linhas** | Cada thread pode ter até 3 linhas (N/I + csat_retidos + csat_transbordados). Para contar sessões únicas usar apenas `csat_type='N/I'`. Para CSAT usar `csat_type='csat_retidos'` |
| 3 | **Demanda Cami = todos csat_type** | `SUM(sum_of_interactions)` com `bot_departament='Servir'` sem filtro de csat_type = total correto de interações |
| 4 | **RT (Retenção) é área separada** | Área `RT` na fact_service_metrics representa atendimentos do fluxo de Retenção — NÃO entra no filtro padrão de Atendimento |
| 5 | **`sum_of_final_bot` é sempre 0** | Campo morto: soma **0** nos 12 meses (ago/25–jul/26), em `Servir` e `Retenção`. A descrição "conversas retidas" engana — **retenção NÃO se calcula com ele**, e sim `1 − transbordos/interações`. A measure `count_of_final_bot` do LookML herda o problema |
| 6 | **`subcategory` é a categorização nativa** | Traz o tema já classificado (`Emissão de Nota Fiscal`, `Lançamentos Financeiros`, `Conciliação bancária`, `Transferência sem Contexto`, `Desistente`, `Abandono Chatbot`, `N/I`, …). Muito mais barato que o join com tags do Zendesk da Q9 — **prefira `subcategory`** quando a pergunta for por tema |
| 7 | **`partner_profile` não particiona a base** | Só existe para Parceiro: `CONTADOR`, `BPO`, `MISTO` — e é **NULL em ~68% das linhas** (todo cliente que não é parceiro). É subconjunto de `customer_type = 'Parceiro'`, não uma segmentação alternativa da base inteira. Ver §5 "Perfil de parceiro" |
| 8 | **Contatos únicos usa duas colunas** | `COUNT(DISTINCT CONCAT(nk_company_id, nk_accountancy_id))` — não `nk_company_id` sozinho (diferença de ~40%) |

### fact_service_metrics — Cuidados críticos
| # | Armadilha | Detalhe |
|---|---|---|
| 1 | **Ouvidoria - IP fora do filtro** | `area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')` — Ouvidoria e RT ficam de fora da Demanda Total |
| 2 | **TMA/TME só em canais online** | Calcular apenas para `channel IN ('Whatsapp','Telefone','Chat')` — Email e Web não têm TA/TE |
| 3 | **Demanda recebida ≠ atendida** | Dashboard "Demanda humana por canal" usa `count_of_demanded` (recebida). `count_of_attended` é menor (exclui abandonos) |
| 4 | **Web tem muitas áreas extras** | BACKING_OPS, N/I, RT, ENG, SDM, TRAINING, OUVIDORIA — todas fora do filtro padrão |
| 5 | **Parceiros exige filtro de área** | Para SLA/TME/TMA/Abandono de `customer_type='Parceiro'`, obrigatório `area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')`. Sem isso RT+N/I+BACKING_OPS inflam sum_of_te e o TME sai 4–5x maior que o real |
| 6 | **`channel = ''` entra no abandono — e isso está certo** | Existem linhas com canal vazio **dentro** do filtro de área padrão, e elas são **100% abandono** (jul/26: 61 demandados, 61 abandonados). A measure oficial `percent_of_abandoned` (`fact_service_metrics.view.lkml:401`) **não filtra canal** — logo o abandono oficial **inclui** essas linhas. Não adicione filtro de canal ao abandono "para limpar": você se afasta do Looker. Efeito: ~0,23pp a mais na taxa. (O Book Pré-RMR filtra canal e por isso reporta abandono menor.) |

### Segmentação PME vs Parceiro

| Segmento | Tabela | Filtro |
|---|---|---|
| PME | fact_service_metrics | `customer_type != 'Parceiro'` |
| Parceiro | fact_service_metrics | `customer_type = 'Parceiro'` |
| PME | dim_chatbot | `customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro')` |
| Parceiro | dim_chatbot | `customer_type = 'Parceiro'` |
| Cliente do Parceiro | dim_chatbot | `customer_type = 'Cliente do Parceiro'` |
| Cliente sem Parceiro | dim_chatbot | `customer_type = 'Cliente sem Parceiro'` |

> 🔴 **`!= 'Parceiro'` NÃO é PME — nas duas tabelas.** Existe um quarto valor literal,
> **`'N/I'`**, e ele é volumoso. Medido em jun–jul/2026:
>
> | Tabela | Parceiro | Cliente do Parceiro | Cliente sem Parceiro | **`N/I`** | NULL |
> |---|---|---|---|---|---|
> | `dim_chatbot` (Servir) | 25.337 | 22.274 | 22.602 | **5.095** | 0 |
> | `fact_service_metrics` | 16.074 | 12.978 | 14.528 | **1.702** | 6 |
>
> Usar `customer_type != 'Parceiro'` como PME **infla o PME em ~11% no `dim_chatbot`** (49.971 em
> vez de 44.876) e ~4% na `fact_service_metrics`. Para PME use sempre
> `customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro')`.
>
> ⚠️ Isso corrige duas afirmações antigas desta KB: (a) o problema **não** é `NULL` — o
> `dim_chatbot` não tem nenhum `NULL` em `customer_type`; (b) `!= 'Parceiro'` **não** é seguro na
> `fact_service_metrics`. Várias queries da §6 ainda usam `!= 'Parceiro'` e por isso reproduzem os
> números históricos — se a pergunta for sobre PME de verdade, prefira o `IN (...)` explícito e
> espere um número ~4% menor.

### Perfil de parceiro (`partner_profile`)

Segunda dimensão de segmento, **dentro** do universo Parceiro. Existe nas duas tabelas
transacionais (`fact_service_metrics` e `dim_chatbot`) com os mesmos valores:

| Valor | Significado |
|---|---|
| `CONTADOR` | Empresa contábil / contador |
| `BPO` | Financial BPO |
| `MISTO` | Consultoria ou empresa contábil com BPO (o Book chama de "Contador BPO & Consultor") |
| `NULL` | Cliente **não é** Parceiro, ou não houve match com uma accountancy |

Distribuição jul/26 em `dim_chatbot`: NULL 33.105 · CONTADOR 7.535 · MISTO 4.276 · BPO 3.967.

> ⚠️ **Não confundir com a tabela de perfil mensal.** Em
> `tmp_data_analytics.fact_customer_partner_profile_nova_regra` o mesmo conceito aparece
> em **minúsculas e com nomes diferentes**: `contador`, `bpo`, `contador_bpo`, `sem_uso`.
> Um `JOIN`/`IN` entre as duas grafias devolve vazio silenciosamente.

---

### FCR e NPS — cuidados críticos

| # | Armadilha | Detalhe |
|---|---|---|
| 1 | **FCR sem `tipo='humano'`** | O agregado sobe de 67,8% para 76,7%; o bot sozinho dá 81,2%. O FCR de atendimento é o **humano** |
| 2 | **FCR com `AVG(fcr_pct)`** | Média de proporção. Use `SUM(numerador)/SUM(denominador)` |
| 3 | **FCR custa 2,13 GB por execução** | View sem partição; o `WHERE` em `semana_inicio` não reduz o scan. Nunca em loop |
| 4 | **FCR do bot saltou para 98%** | ~87% até abr/26, 98,2% em jun e 98,96% em jul. Suspeito — não reporte sem investigar |
| 5 | **pNPS de CA Pro em ago/26 está contaminado** | 2,98 respostas por empresa (vs ~1,05). Nota cai de 55,1 para 22,5 sem piora real. CA Mais não afetado |
| 6 | **`nps_type='pNPS'` descarta 2025 inteiro** | Antes de 31/12/2025 a ferramenta era IndeCX e o tipo é `Não identificado`. Para série longa, filtre por `segment` + data, não por `nps_type` |
| 7 | **Unicidade do NPS é `sk_nps_survey`** | `nk_answer` só é único dentro de uma ferramenta — pode colidir entre IndeCX/Survicate |
| 8 | **rNPS não tem base** | 20 respostas no total. Se perguntarem, diga que não há volume |

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

### Q4 — Retenção Cami / Deflexão (PME e Parceiro) — KPI oficial

> Regra do tile "Retenção" do dashboard 210: `GREATEST(...,0)` + só dia útil + exclui feriado por canal.

```sql
WITH base AS (
  SELECT
    c.customer_type,
    c.sum_of_interactions,
    c.sum_of_transfers,
    ((dd.day_name NOT IN ('Domingo','Sábado') OR dd.day_name IS NULL)
      AND h.nk_date IS NULL)                                        AS is_business_day
  FROM `contaazul-ssbi.gold_serve.dim_chatbot` c
  LEFT JOIN `contaazul-ssbi.gold_common.dim_date` dd
    ON c.nk_date = dd.nk_date
  LEFT JOIN `contaazul-ssbi.gold_serve.dim_chatbot_holidays` h
    ON h.channel = c.channel AND DATE(h.nk_date) = c.nk_date
  WHERE c.nk_date BETWEEN '<inicio>' AND '<fim>'
    AND c.bot_departament = 'Servir'
)
SELECT
  ROUND(GREATEST(0, 1 - SAFE_DIVIDE(
    SUM(IF(is_business_day, sum_of_transfers, 0)),
    SUM(IF(is_business_day, sum_of_interactions, 0)))), 4)          AS retencao_total,
  ROUND(GREATEST(0, 1 - SAFE_DIVIDE(
    SUM(IF(is_business_day AND customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro'), sum_of_transfers, 0)),
    SUM(IF(is_business_day AND customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro'), sum_of_interactions, 0)))), 4) AS retencao_pme,
  ROUND(GREATEST(0, 1 - SAFE_DIVIDE(
    SUM(IF(is_business_day AND customer_type = 'Parceiro', sum_of_transfers, 0)),
    SUM(IF(is_business_day AND customer_type = 'Parceiro', sum_of_interactions, 0)))), 4) AS retencao_parceiro
FROM base
```

> Para a **retenção observada** (tiles `Acumulado Mensal` / `Detalhado`, sem filtro de dia),
> troque `IF(is_business_day, x, 0)` por `x` em todos os termos. Numa janela seg–sex sem feriado
> as duas devolvem o mesmo número.

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
WITH base AS (
  SELECT
    c.bot_type,
    c.customer_type,
    c.sum_of_interactions,
    c.sum_of_transfers,
    ((dd.day_name NOT IN ('Domingo','Sábado') OR dd.day_name IS NULL)
      AND h.nk_date IS NULL)                                        AS is_business_day
  FROM `contaazul-ssbi.gold_serve.dim_chatbot` c
  LEFT JOIN `contaazul-ssbi.gold_common.dim_date` dd
    ON c.nk_date = dd.nk_date
  LEFT JOIN `contaazul-ssbi.gold_serve.dim_chatbot_holidays` h
    ON h.channel = c.channel AND DATE(h.nk_date) = c.nk_date
  WHERE c.nk_date BETWEEN '<inicio>' AND '<fim>'
    AND c.bot_departament = 'Servir'
)
SELECT
  bot_type,
  -- Total
  ROUND(GREATEST(0, 1 - SAFE_DIVIDE(
    SUM(IF(is_business_day, sum_of_transfers, 0)),
    SUM(IF(is_business_day, sum_of_interactions, 0)))), 4)          AS retencao_total,
  -- PME (Cliente do Parceiro + Cliente sem Parceiro)
  ROUND(GREATEST(0, 1 - SAFE_DIVIDE(
    SUM(IF(is_business_day AND customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro'), sum_of_transfers, 0)),
    SUM(IF(is_business_day AND customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro'), sum_of_interactions, 0)))), 4) AS retencao_pme,
  -- Cliente do Parceiro (sub-seg PME)
  ROUND(GREATEST(0, 1 - SAFE_DIVIDE(
    SUM(IF(is_business_day AND customer_type = 'Cliente do Parceiro', sum_of_transfers, 0)),
    SUM(IF(is_business_day AND customer_type = 'Cliente do Parceiro', sum_of_interactions, 0)))), 4) AS retencao_cliente_parceiro,
  -- Cliente sem Parceiro (sub-seg PME)
  ROUND(GREATEST(0, 1 - SAFE_DIVIDE(
    SUM(IF(is_business_day AND customer_type = 'Cliente sem Parceiro', sum_of_transfers, 0)),
    SUM(IF(is_business_day AND customer_type = 'Cliente sem Parceiro', sum_of_interactions, 0)))), 4) AS retencao_cliente_sem_parceiro,
  -- Parceiro
  ROUND(GREATEST(0, 1 - SAFE_DIVIDE(
    SUM(IF(is_business_day AND customer_type = 'Parceiro', sum_of_transfers, 0)),
    SUM(IF(is_business_day AND customer_type = 'Parceiro', sum_of_interactions, 0)))), 4) AS retencao_parceiro
FROM base
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
    -- is_active_workday é NUMERIC (decimal): somar direto, NUNCA CAST AS INT64
    SUM(is_active_workday) / <qtd_du> AS hc_liquido
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
                  AND (sum_of_te / NULLIF(count_of_demanded,0)) <= 180
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
                  AND (sum_of_te / NULLIF(count_of_demanded,0)) <= 180
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
                  AND (sum_of_te / NULLIF(count_of_demanded,0)) <= 180
             THEN count_of_demanded END) /
    NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente do Parceiro'
               THEN count_of_demanded END), 0), 4) AS sla_tme_cdp,
  ROUND(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') AND customer_type = 'Cliente sem Parceiro'
                  AND (sum_of_te / NULLIF(count_of_demanded,0)) <= 180
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

## 7. Validação — W16/W17 (abr/2026), recalculada em 28/08/2026

> ### ⚠️ Leia antes de usar estes números
>
> **Estes valores NÃO reproduzem mais o que o dashboard mostrava em abril de 2026.** Três causas,
> todas reais e verificadas:
>
> **1. As tabelas são reprocessadas.** `gold_serve.fact_service_metrics` e `gold_serve.dim_chatbot`
> mudam retroativamente. A retenção Cami da W16, registrada como 55,6% em abril, hoje devolve 57,08%
> com a mesma query. O CSAT Cami PME moveu 8pp (75,7% → 83,9%). Não é erro de cálculo: é o dado
> que mudou embaixo. **Não persiga décimos contra alvo móvel.**
>
> **2. Abril/2026 tem uma anomalia de dados em `channel = ''`.** Naquele mês há **3.966 chamados
> com canal vazio, 100% abandonados** — contra 1 a 336 em qualquer outro mês do ano. Isso sozinho
> leva o abandono de abril de 4,84% para 19,81%. A measure oficial `percent_of_abandoned`
> **não filtra canal**, então os números abaixo **incluem** o artefato — é o que o Looker devolveria.
> Para leitura operacional de abril, use a coluna "sem artefato".
>
> **3. O DU de abril estava errado no cálculo original.** O MTD 01–26/abr tem **16 dias úteis**,
> não 18: 03/abr (Sexta-feira Santa) e 21/abr (Tiradentes) são feriados nacionais. O HC Líquido
> registrado (54) saiu de dividir por 18; pela `dim_date` o correto é **61,63**.
>
> **Coluna "Registro abr/26"** = o que foi conferido contra o dashboard na época, preservado como
> auditoria histórica. **Não é possível atualizá-la**: o MCP do Looker devolve a definição do tile,
> não o dado.

### W16 (13–19/abr/2026) — 5 dias úteis

| Indicador | BQ recalc. 28/08/26 | Registro abr/26 | Δ |
|---|---|---|---|
| Demanda total (Cami + Tel) | 10.168 | 9.899 | +269 |
| Cami (autoatendimento) | 9.115 | 8.853 | +262 |
| Telefone (voz) | 1.053 | 1.046 | +7 |
| Demanda por DU | 2.034 | 1.980 | +54 |
| Cami DU | 1.823 | 1.771 | +52 |
| Telefone DU | 211 | 209 | +2 |
| Demanda humana total | 6.189 | 5.220 | +969 ⚠️ artefato |
| — sem o artefato `channel=''` | 5.255 | 5.220 | +35 |
| Whatsapp | 2.431 | 2.411 | +20 |
| Chat | 1.460 | 1.453 | +7 |
| Telefone humano | 1.053 | 1.046 | +7 |
| Web | 273 | 271 | +2 |
| Email | 38 | 38 | 0 |
| `(vazio)` — **anomalia**, 100% abandono | 934 | (não existia) | +934 |
| **Retenção Cami total — KPI (dia útil)** | **56,74%** | 55,4% | +1,3pp |
| Retenção Cami total — observada (s/ filtro) | 57,08% | 55,4% | +1,7pp |
| Retenção PME — KPI | 60,27% | 59,2% | +1,1pp |
| Retenção Parceiro — KPI | 46,56% | 44,3% | +2,3pp |
| Retenção — Bot_Fin (Fin AI) total | 60,56% | 50,2% | +10,4pp |
| Retenção — Gen 3 CA Pro total | 67,00% | 67,0% | 0 |
| Retenção — Gen 3 CA Mais total | 48,08% | 48,1% | 0 |
| Retenção — Gen 2 total | 53,45% | 53,9% | −0,5pp |
| Retenção PME — Bot_Fin | 63,61% | 54,7% | +8,9pp |
| Retenção PME — Gen 3 CA Pro | 66,50% | 66,4% | +0,1pp |
| Retenção PME — Gen 2 | 56,26% | 57,0% | −0,7pp |
| Retenção Parceiro — Bot_Fin | 55,65% | 42,1% | +13,6pp |
| Retenção Parceiro — Gen 3 CA Pro | 70,00% | 71,2% | −1,2pp |
| Retenção Parceiro — Gen 3 CA Mais | 47,57% | 48,0% | −0,4pp |
| Retenção Parceiro — Gen 2 | 41,33% | 41,5% | −0,2pp |
| CSAT Blended PME | 90,44% | 86,4% | +4,0pp |
| CSAT Humano PME | 93,03% | 93,4% | −0,4pp |
| CSAT Cami PME | 83,93% | 75,7% | +8,2pp |
| CSAT Blended Parceiro | 90,83% | 87,8% | +3,0pp |
| CSAT Humano Parceiro | 94,93% | 95,1% | −0,2pp |
| CSAT Cami Parceiro | 74,17% | 69,9% | +4,3pp |
| SLA TME PME (≤3min) | 93,85% | 94,3% | −0,5pp |
| TME PME | 0:00:33 | 0:00:33 | 0 |
| TMA PME | 0:44:04 | 0:45:06 | −62s |
| **Abandono PME** | **20,03%** ⚠️ | 2,99% | +17,0pp ⚠️ artefato |
| — sem o artefato `channel=''` | 4,85% | 2,99% | +1,9pp |
| SLA TME Parceiro (≤3min) | 97,87% | 97,9% | 0 |
| TME Parceiro | 0:00:11 | 0:00:15 | −4s |
| TMA Parceiro | 0:48:31 | 0:48:49 | −18s |
| **Abandono Parceiro** | **16,40%** ⚠️ | 3,14% | +13,3pp ⚠️ artefato |

> **Leitura:** dos 40 indicadores, ~20 continuam dentro de 1pp do registro original. Os desvios
> grandes se concentram em (a) abandono — inteiramente explicado pelo artefato de abril; e
> (b) Bot_Fin/CSAT Cami — reprocessamento genuíno da `dim_chatbot`.

---

### W17 (20–26/abr/2026) — 4 dias úteis (21/abr é Tiradentes)

| Indicador | BQ recalc. 28/08/26 | Registro abr/26 | Δ |
|---|---|---|---|
| CSAT Blended PME | 88,19% | 84,3% | +3,9pp |
| CSAT Humano PME | 92,92% | 93,8% | −0,9pp |
| CSAT Humano — Cliente do Parceiro | 92,97% | 93,1% | −0,1pp |
| CSAT Humano — Cliente sem Parceiro | 93,63% | 94,3% | −0,7pp |
| CSAT Cami PME | 74,74% | 75,3% | −0,6pp |
| CSAT Cami — Cliente do Parceiro | 70,95% | 72,9% | −2,0pp |
| CSAT Cami — Cliente sem Parceiro | 78,62% | 77,7% | +0,9pp |
| CSAT Blended — Cliente do Parceiro | 86,11% | — | — |
| CSAT Blended — Cliente sem Parceiro | 90,00% | — | — |
| Retenção Cami total — KPI (dia útil) | 57,02% | — | — |
| Retenção Cami total — observada | 57,82% | — | — |
| Demanda total (Cami + Tel) | 7.888 | 6.835 | +1.053 |

> ⚠️ **A W17 contém um feriado nacional (21/abr, Tiradentes)** — pela `dim_date` ela tem
> **4 dias úteis, não 5**. O registro original dividia por 5 DU, então toda métrica "por DU"
> da W17 no registro está subestimada em ~20%.
>
> Cuidado para não misturar dois conceitos: o **DU da `dim_date`** exclui Tiradentes; a
> **retenção KPI** não, porque ela usa `dim_chatbot_holidays`, que não tem linhas de 2026
> (ver o aviso na §4). A diferença KPI vs observada aqui (0,8pp) vem só do fim de semana —
> é maior que na W16 (0,3pp) por causa do mix de volume do sábado/domingo, não do feriado.

### CSAT Cami PME W17 — por bot_type e sub-segmento

| Indicador | BQ recalc. 28/08/26 | Aval. hoje | Registro abr/26 | Aval. na época |
|---|---|---|---|---|
| CSAT Cami PME — Bot_Fin (Fin AI) | 72,51% | 251 | 74,6% | 788 |
| CSAT Cami PME — Gen 3 CA Pro | 88,10% | 42 | 88,1% | 42 |
| CSAT Cami PME — Gen 3 CA Mais | — | 0 | — | 0 |
| CSAT Cami PME — Gen 2 | — | 0 | — | 0 |

> ⚠️ **O volume de avaliações do Bot_Fin caiu de 788 para 251** com o reprocessamento — a nota
> ainda é parecida (−2,1pp), mas a base não. A quebra por sub-segmento (CDP/CSP × bot_type),
> que existia no registro original, **não foi recalculada neste ciclo**.
>
> Bot_Fin segue concentrando praticamente todas as avaliações PME. Gen 2 e Gen 3 CA Mais não
> tiveram avaliações `csat_retidos` PME na W17 nem na época nem hoje.

### CSAT Cami Parceiros W16 e W17 — por bot_type

| bot_type | W16 recalc. | Aval. W16 | W16 registro | W17 recalc. | Aval. W17 | W17 registro |
|---|---|---|---|---|---|---|
| Bot_Fin (Fin AI) | 73,33% | 30 | 66,2% | 68,35% | 139 | 72,1% |
| Gen 3 CA Pro | 75,00% | 4 | 75,0% | 100,00% | 2 | 100,0% |
| Gen 3 CA Mais | 70,00% | 10 | 75,0% | 57,14% | 7 | 57,1% |
| Gen 2 | 74,77% | 107 | 74,0% | — | 0 | — |
| **Total Cami Parceiros** | **74,17%** | **151** | 69,9% | **68,24%** | **148** | 72,0% |

> ⚠️ **O volume de avaliações mudou muito com o reprocessamento**: a W17 de Parceiros tinha
> 386 avaliações no registro original e hoje tem 148; a distribuição por bot_type também mudou
> (Bot_Fin era 377, hoje é 139). Com amostras desse tamanho, **não leia bot_type como tendência**
> — Gen 3 CA Pro tem 2 avaliações na W17.

### Visão por Categoria Cami W17 (Gen2 + Gen3 CA Pro + Gen3 CA Mais)

> ⏸️ **Não recalculado neste ciclo** — os números abaixo são de abr/2026 e estão sujeitos ao
> mesmo reprocessamento das demais tabelas.
>
> 💡 **Prefira `dim_chatbot.subcategory`** a este join com as tags do Zendesk. A coluna traz o tema
> já classificado, sem join, sem custo e sem a divergência pendente de Vendas/NA. Ver §5, armadilha 6.
> Exemplo do que `subcategory` devolve (jul/26, departamento Servir): `Transferência sem Contexto`
> 5.730 · `Desistente` 5.456 · `Emissão de Nota Fiscal` 3.777 · `Falha na Emissão de Nota Fiscal`
> 2.438 · `Lançamentos Financeiros` 2.263 · `Conciliação bancária` 2.054 — mais de 25 categorias.

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

| Indicador | BQ recalc. 28/08/26 | Registro abr/26 | Δ |
|---|---|---|---|
| SLA TME PME (≤3min) | 89,37% | 90,2% | −0,8pp |
| SLA TME — Cliente do Parceiro | 89,89% | 90,3% | −0,4pp |
| SLA TME — Cliente sem Parceiro | 89,64% | 90,2% | −0,6pp |
| TME PME | 0:00:55 | 0:00:52 | +3s |
| TME — Cliente do Parceiro | 0:00:49 | 0:00:44 | +5s |
| TME — Cliente sem Parceiro | 0:00:52 | 0:00:58 | −6s |
| TMA PME | 0:42:24 | 0:40:27 | +117s |
| TMA — Cliente do Parceiro | 0:47:01 | 0:46:09 | +52s |
| TMA — Cliente sem Parceiro | 0:39:31 | 0:35:41 | +230s |
| **Abandono PME** | **28,33%** ⚠️ | 4,70% | +23,6pp ⚠️ artefato |
| **Abandono — Cliente do Parceiro** | **30,85%** ⚠️ | 4,45% | +26,4pp ⚠️ artefato |
| **Abandono — Cliente sem Parceiro** | **27,38%** ⚠️ | 4,90% | +22,5pp ⚠️ artefato |

> ⚠️ Os três abandonos estão dominados pela anomalia de `channel = ''` de abril/2026
> (1.077 chamados na W17, todos abandonados) — ver o aviso no topo da §7. A measure oficial
> não filtra canal, então estes são os valores fiéis à definição; **não são leitura operacional.**

### SLA TME / TME / TMA / Abandono Parceiros W16 e W17

> ⚠️ **Obrigatório para Parceiros**: sempre incluir `area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')`. Sem esse filtro, linhas de RT, N/I e BACKING_OPS inflam sum_of_te e count_of_demanded — TME sai 4–5x errado.

| Indicador | W16 recalc. | W16 registro | W17 recalc. | W17 registro |
|---|---|---|---|---|
| SLA TME Parceiros (≤3min) | 97,87% | 97,9% | 92,97% | 93,1% |
| TME Parceiros | 0:00:11 | 0:00:15 | 0:00:32 | 0:00:31 |
| TMA Parceiros | 0:48:31 | 0:48:49 | 0:56:54 | 0:48:48 |
| **Abandono Parceiros** | **16,40%** ⚠️ | 3,14% | **25,46%** ⚠️ | 3,79% |
| Demanda recebida Parceiro | 2.323 | — | 1.634 | — |
| Retenção Cami Parceiro — KPI | 46,56% | 44,3% | 52,36% | — |
| CSAT Cami Parceiro | 74,17% | 69,9% | 68,24% | 72,0% |
| CSAT Blended Parceiro | 90,83% | 87,8% | 83,67% | 80,6% |

> SLA e TME seguem estáveis (≤0,4pp / ≤4s). O TMA da W17 subiu 8 minutos com o reprocessamento.
> Os abandonos estão dominados pela anomalia de abril — ver o aviso no topo da §7.

### Performance dos Encantadores Parceiros — abr.26 MTD (01–26/abr/2026, 18 DU)

> 🔴 **ERRO ENCONTRADO no cálculo original: o período tem 16 dias úteis, não 18.**
> 01–26/abr/2026 tem 18 dias de semana, mas **dois são feriados nacionais** — 03/abr
> (Sexta-feira Santa) e 21/abr (Tiradentes). A `gold_common.dim_date` devolve `national_work_day`
> para 16 datas. O HC Líquido registrado (54) veio de dividir a soma de `is_active_workday` por 18.
> Dividindo pelos 16 corretos, o HC é **61,63** — e todos os "chamados por encantador" derivados
> mudam junto. É exatamente a correção da §4 "Demanda por DU": **derive o DU da `dim_date`.**

| Indicador | BQ recalc. 28/08/26 | Registro abr/26 | Δ |
|---|---|---|---|
| Dias úteis (01–26/abr) | **16** | 18 | −2 (2 feriados) |
| HC Líquido | **61,63** | 54 | +7,6 |
| Total atendido (todos segmentos) | 15.995 | 16.057 | −62 |
| Chamados/enc Mês | 260 | 296 | −36 |
| Chamados/enc DU | 16,2 | 18 | −1,8 |
| Demanda Recebida Parceiro | *não recalculado* | 6.222 | — |
| Demanda Atendida Parceiro | *não recalculado* | 6.018 | — |
| CSAT Parceiro MTD | *não recalculado* | 92,65% | — |

> O `SUM(is_active_workday)` de abril dá o mesmo com e sem `CAST AS INT64` — a distorção do CAST
> (ver §4 HC Líquido) só aparece em meses onde o campo tem parte fracionária, como julho/26
> (39,56 correto vs 41,26 com CAST).

> ⚠️ Chamados/enc usa **total atendido de todos os segmentos** (PME + Parceiro = 16.057) como numerador — mesmo HC serve PME e Parceiros. O gráfico "[Parceiro]" só troca barras de demanda e CSAT; HC e produtividade são compartilhados.

---

### Performance dos Encantadores PME — abr.26 MTD (01–26/abr/2026, 18 DU)

| Indicador | BQ recalc. 28/08/26 | Registro abr/26 | Δ |
|---|---|---|---|
| Dias úteis (01–26/abr) | **16** | 18 | −2 (Sexta-feira Santa + Tiradentes) |
| HC Líquido | **61,63** | 54 | +7,6 |
| Chamados/enc Mês | 260 | 296 | −36 |
| Chamados/enc DU | 16,2 | 18 | −1,8 |
| Demanda Recebida CDP | *não recalculado* | 4.634 | — |
| Demanda Atendida CDP | *não recalculado* | 4.491 | — |
| CSAT CDP | *não recalculado* | 92,68% | — |
| Demanda Recebida CSP | *não recalculado* | 5.379 | — |
| Demanda Atendida CSP | *não recalculado* | 5.172 | — |
| CSAT CSP | *não recalculado* | 93,38% | — |

> HC e produtividade são **compartilhados** entre PME e Parceiros — a mesma equipe atende os dois.
> Os números acima são idênticos aos da seção de Parceiros por construção, não por coincidência.

> ⚠️ Discrepâncias de ~0,8pp em Bot_Fin/Fin AI total se devem a ~21 interações com `customer_type = NULL` que o dashboard provavelmente exclui. Para os demais bot_types a diferença é ≤0,14pp.

---

### Telefone — Indicadores Macro W16 e W17

Query: `channel = 'Telefone'` + `area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')`

| Indicador | W16 recalc. | W16 registro | W17 recalc. | W17 registro |
|---|---|---|---|---|
| Demanda total | 1.053 | 1.046 | 842 | 833 |
| Demanda PME | 859 | 753 | 691 | 624 |
| Demanda Parceiro | 194 | 205 | 151 | 143 |
| CSAT total | 99,40% | 99,44% | 99,49% | 99,50% |
| SLA TME total (≤3min) | 85,75% | 85,37% | 89,19% | 89,08% |
| TME total | 0:01:21 | 0:01:30 | 0:01:00 | 0:01:00 |
| TMA total | 0:11:56 | 0:13:16 | 0:11:31 | 0:12:05 |
| Abandono total | 4,75% | 4,49% | 5,11% | 4,92% |
| Demanda CDP / CSP | *não recalculado* | 242 / 511 | *não recalculado* | 185 / 439 |
| CSAT e SLA por segmento | *não recalculado* | — | *não recalculado* | — |

> O canal Telefone é o **mais estável** de todos: demanda ±1%, CSAT ±0,05pp, SLA ±0,4pp após
> quatro meses de reprocessamento. Note que o Telefone **não** é afetado pela anomalia de
> `channel = ''` (aquelas linhas têm canal vazio, não `Telefone`).

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

> ⏸️ **Números de abr/2026, não recalculados.** Os valores recalculados de CSAT Parceiros estão
> na §7 (W16 blended 90,83% · W17 blended 83,67%). A leitura executiva abaixo foi escrita com os
> números da época e é preservada como registro.

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

> ⏸️ **Leitura datada (abr/2026), não recalculada.** Esta seção registra a interpretação de
> negócio feita na época, com os números da época. Vários deles não reproduzem mais — o CSAT Cami
> PME da W16, por exemplo, era 75,7% e hoje devolve 83,9%. **Use como histórico de decisão, não
> como fonte de número.** Para valores atuais, rode as queries da §6.

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