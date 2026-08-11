---
kind: kb
id: suporte
domain: Atendimento / Suporte (Servir) — ContaAzul
schema_version: 2
bq_project: contaazul-ssbi
generated:
  by: kb-restructurer
  from: knowledge-bases/suporte/kb.md
  at: 2026-08-11
period_ref: "2026-04-06/2026-04-26"
sources:
  - id: dash-220
    resource: https://contaazul.cloud.looker.com/dashboards/220
    title: "[SUP_OFI] Gerencial 592 — explore fact_service_metrics"
  - id: dash-273
    resource: https://contaazul.cloud.looker.com/dashboards/273
    title: "[SUP_OFI] 275 Tickets Detail — explore dim_zendesk_tickets_detailed"
  - id: dash-210
    resource: https://contaazul.cloud.looker.com/dashboards/210
    title: "[SUP_OFI] Chatbots — explore dim_blip_messages"
---

# Camada semântica — Atendimento (Suporte / Servir)

Modelo Looker `serve_data_mart` (label "Servir"), dataset principal `contaazul-ssbi.gold_serve`.

## 1. Fontes

```yaml meta
kind: source
id: fact_service_metrics
table: contaazul-ssbi.gold_serve.fact_service_metrics
layer: gold
date_column: nk_event_date
date_type: DATE
partition: nk_event_date
cluster: [channel, area, nk_email]
looker_explore: fact_service_metrics
lineage: "silver_serve.agent_capacity (filtro team = 'Servir') → PDT pdt_agent_capacity_agg (inline no SQL Looker) → gold_serve.fact_service_metrics"
columns:
  - {name: nk_event_date, type: DATE, desc: Data do evento}
  - {name: channel, type: STRING, desc: Canal, values: [Chat, Email, Telefone, Web, Whatsapp]}
  - {name: area, type: STRING, desc: Área do encantador, values: [BK, DN, EC, "SAC - CA", "SAC - Pessoalize", "Ouvidoria - IP", RT, ENG, "N/I", SDM, TRAINING, BACKING_OPS, OUVIDORIA]}
  - {name: nk_email, type: STRING, desc: E-mail do encantador}
  - {name: squad, type: STRING, desc: Time por matriz de produto}
  - {name: customer_type, type: STRING, desc: Tipo de cliente, values: [PME, Parceiro, "Cliente do Parceiro", "Cliente sem Parceiro"]}
  - {name: has_premium_support, type: BOOLEAN, desc: Possui suporte premium}
  - {name: is_partner, type: BOOLEAN, desc: É parceiro}
  - {name: partner_level, type: STRING, desc: Nível de parceria}
  - {name: is_under_6m, type: BOOLEAN, desc: Menos de 6 meses de vida}
  - {name: count_of_demanded, type: INTEGER, desc: Chamados recebidos, unit: count}
  - {name: count_of_abandoned, type: INTEGER, desc: Chamados abandonados, unit: count}
  - {name: count_of_attended, type: INTEGER, desc: Chamados atendidos, unit: count}
  - {name: count_of_positive_ratings, type: INTEGER, desc: Avaliações positivas, unit: count}
  - {name: count_of_negative_ratings, type: INTEGER, desc: Avaliações negativas, unit: count}
  - {name: sum_of_ta, type: INTEGER, desc: Tempo total de atendimento, unit: seconds}
  - {name: sum_of_te, type: INTEGER, desc: Tempo total de espera, unit: seconds}
  - {name: sum_of_tpr, type: INTEGER, desc: Tempo total de primeira resposta, unit: seconds}
  - {name: count_of_tpr_ok, type: INTEGER, desc: Tickets com TPR dentro do SLA, unit: count}
  - {name: count_of_tpr_nok, type: INTEGER, desc: Tickets com TPR fora do SLA, unit: count}
pitfalls: [ouvidoria-ip-fora-do-filtro, area-rt-fora-do-atendimento, tma-tme-so-canais-online, demanda-recebida-diferente-de-atendida, web-tem-areas-extras, parceiros-exige-filtro-de-area, abandono-telefone-vem-de-customer-type-null]
provenance: [dash-220]
```

Fato de métricas diárias de atendimento humano (Zendesk). O valor `PME` consta na descrição de `customer_type`, mas o segmento PME nesta tabela é obtido por `customer_type != 'Parceiro'` (ver `segmento-pme-fsm`).

```yaml meta
kind: source
id: dim_chatbot
table: contaazul-ssbi.gold_serve.dim_chatbot
layer: gold
date_column: nk_date
date_type: DATE
partition: nk_date
cluster: [channel, team]
looker_explore: dim_blip_messages
lineage: "bronze_tool_blip / bronze_app_supercami → silver_serve.ingestion_blip_supercami_* + ingestion_takeblip_* → gold_serve.dim_chatbot"
columns:
  - {name: nk_date, type: DATE, desc: Data do registro}
  - {name: channel, type: STRING, desc: Canal, values: [Whatsapp, Chat]}
  - {name: team, type: STRING, desc: Produto, values: ["CA Mais", "CA Pro", "Conta PJ"]}
  - {name: bot_type, type: STRING, desc: Tipo de bot, values: [Gen2, "Gen3 CA Mais", "Gen3 CA Pro", Bot_Fin]}
  - {name: bot_departament, type: STRING, desc: Departamento do fluxo do bot, values: [Servir, Retenção], nullable: true}
  - {name: csat_type, type: STRING, desc: Tipo de linha de avaliação, values: ["N/I", csat_retidos, csat_transbordados]}
  - {name: is_gen3, type: BOOLEAN, desc: É fluxo Gen3}
  - {name: nk_company_id, type: INTEGER, desc: ID da empresa}
  - {name: customer_type, type: STRING, desc: Tipo de cliente, values: [PME, Parceiro, "Cliente do Parceiro", "Cliente sem Parceiro"], nullable: true}
  - {name: has_premium_support, type: BOOLEAN, desc: Possui suporte premium}
  - {name: is_partner, type: BOOLEAN, desc: É parceiro}
  - {name: thread_uid, type: STRING, desc: ID único da conversa}
  - {name: sum_of_interactions, type: INTEGER, desc: "Nº de interações (= 1 por linha)", unit: count}
  - {name: sum_of_transfers, type: INTEGER, desc: Transbordos para humano, unit: count}
  - {name: sum_of_final_bot, type: INTEGER, desc: "Conversas retidas (resolvidas pelo bot)", unit: count}
  - {name: sum_of_positive_ratings, type: INTEGER, desc: Avaliações positivas, unit: count}
  - {name: sum_of_negative_ratings, type: INTEGER, desc: Avaliações negativas, unit: count}
  - {name: sum_of_total_ratings, type: INTEGER, desc: "Total de avaliações (= positivas + negativas)", unit: count}
pitfalls: [bot-fin-nao-e-cami, csat-type-multiplica-linhas, demanda-cami-sem-filtro-csat-type, customer-type-null-em-dim-chatbot, sem-valor-literal-pme-em-dim-chatbot, denominador-csat-cami-total-ratings, bot-types-sem-avaliacoes-retornam-null, definicao-parceiro-em-dim-chatbot-ambigua, amostras-pequenas-por-bot-type]
provenance: [dash-210]
```

Interações diárias dos chatbots (Cami/SuperCami — Blip/Takeblip/Ultimate). Granularidade: 1 linha = 1 interação/sessão (`sum_of_interactions = 1` por linha); a mesma `thread_uid` pode gerar até 3 linhas por causa de `csat_type`. `bot_departament` NULL corresponde ao Bot_Fin sem departamento definido.

```yaml meta
kind: source
id: dim_zendesk_tickets_detailed
table: contaazul-ssbi.gold_serve.dim_zendesk_tickets_detailed
layer: gold
date_column: nk_date
date_type: DATETIME
partition: nk_date
cluster: [ticket_category, ticket_subcategory]
looker_explore: dim_zendesk_tickets_detailed
lineage: "bronze_tool_zendesk_events → silver_serve.ingestion_zendesk_tickets + _chats + _whatsapp + _web + _email → silver_serve.zendesk_tickets_detailed → gold_serve.dim_zendesk_tickets_detailed. Para Billing Dono de Negócio a fonte oficial do Looker é o explore churn_data_mart → cancellation_tickets (silver_retention)."
columns:
  - {name: id, desc: ID do ticket}
  - {name: nk_date, type: DATETIME, desc: "Data do ticket (partição mensal)"}
  - {name: nk_company_id, desc: ID da empresa}
  - {name: assignee_email, desc: E-mail do responsável}
  - {name: assignee_name, desc: Nome do responsável}
  - {name: assignee_area, desc: "Área do responsável (equivalente a area na fact_service_metrics)"}
  - {name: channel, desc: Canal do ticket}
  - {name: ticket_category, desc: Categoria do ticket}
  - {name: ticket_subcategory, desc: Subcategoria do ticket}
  - {name: ticket_level, desc: Nível do ticket}
  - {name: departament, desc: Departamento}
  - {name: attendance_type, desc: Tipo de atendimento}
  - {name: status, desc: Status do ticket}
  - {name: online_service_time, desc: Tempo de atendimento online, unit: seconds}
  - {name: online_waiting_time, desc: Tempo de espera online, unit: seconds}
  - {name: tags, desc: Tags do ticket}
  - {name: is_incomplete, desc: Ticket incompleto}
  - {name: is_charge, desc: Ticket de cobrança}
  - {name: customer_type, desc: Tipo de cliente}
  - {name: has_premium_support, desc: Possui suporte premium}
  - {name: is_partner, desc: É parceiro}
  - {name: is_service_metrics, desc: Marca os tickets que compõem as métricas de atendimento}
  - {name: current_rating, desc: "Avaliação do ticket; 'good' = positiva", values: [good]}
  - {name: source_solved_at, desc: "Data/hora de solução na origem; pode ser NULL", nullable: true}
  - {name: subclassification, desc: "Subclassificação do ticket; 'retido'/'retenção' marcam cliente mantido", values: [retido, retenção], nullable: true}
  - {name: servir_churn_type, desc: "Tipo de churn registrado pelo Servir; não-NULL indica negociação", nullable: true}
pitfalls: [source-solved-at-null-precisa-fallback, integracao-bancaria-divergencia-pendente, cancellation-tickets-pode-ter-defasagem]
provenance: [dash-273]
```

Todos os tickets do Zendesk com detalhamento completo. Base da visão por categoria do Telefone e do Billing Dono de Negócio.

```yaml meta
kind: source
id: agent_capacity
table: contaazul-ssbi.silver_serve.agent_capacity
layer: silver
date_column: event_date
columns:
  - {name: event_date, desc: Data do registro de capacidade}
  - {name: team, desc: "Time; sempre filtrar 'Servir'", values: [Servir]}
  - {name: is_active_workday, desc: "Indica dia útil ativo do encantador (base do HC Líquido)"}
  - {name: capacity, desc: "Capacidade do encantador (base do FTE)"}
pitfalls: [hc-liquido-depende-de-qtd-du]
```

Capacidade dos encantadores. Alimenta o PDT `pdt_agent_capacity_agg` (inline no SQL do Looker) e a `fact_service_metrics`.

```yaml meta
kind: source
id: ingestion_zendesk_tickets
table: contaazul-ssbi.silver_serve.ingestion_zendesk_tickets
layer: silver
columns:
  - {name: id, desc: "ID do ticket Zendesk (join com dim_chatbot.thread_uid para Gen3/Ultimate)"}
  - {name: tags, desc: Tags do ticket — origem da categoria Cami}
  - {name: intercom_conversation_id, desc: "ID da conversa Intercom (join com dim_chatbot.thread_uid para Bot_Fin)", nullable: true}
pitfalls: [categoria-vendas-e-na-divergentes, tag-vendas-antiga-descontinuada, interacoes-sem-ticket-caem-em-na, ordem-dos-when-na-categorizacao-de-tags]
```

Fonte das tags que derivam a categoria temática das interações do Cami.

```yaml meta
kind: source
id: dim_date
table: contaazul-ssbi.gold_common.dim_date
layer: gold
```

Dimensão calendário — JOIN por `nk_date`.

```yaml meta
kind: source
id: dim_company
table: contaazul-ssbi.gold_common.dim_company
layer: gold
```

Dados das empresas clientes.

```yaml meta
kind: source
id: dim_accountancy
table: contaazul-ssbi.gold_common.dim_accountancy
layer: gold
```

Dados dos parceiros/contadores.

```yaml meta
kind: source
id: dim_active_companies_by_month
table: contaazul-ssbi.gold_common.dim_active_companies_by_month
layer: gold
date_column: nk_month
columns:
  - {name: nk_month, desc: "Mês de referência (JOIN por date_trunc(nk_event_date, month))"}
  - {name: total_active_companies, desc: Base ativa CAPRO no mês, unit: count}
```

Base ativa CAPRO por mês — denominador da Densidade de Demanda.

```yaml meta
kind: source
id: dim_chatbot_holidays
table: contaazul-ssbi.gold_serve.dim_chatbot_holidays
layer: gold
```

Feriados por canal, usados no filtro de dia útil do bot.

## 2. Políticas

```yaml meta
kind: policy
id: escopo-atendimento-areas
title: Escopo de áreas do Atendimento
severity: blocking
applies_to: [fact_service_metrics, dim_zendesk_tickets_detailed]
predicate:
  fact_service_metrics: "area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')"
  dim_zendesk_tickets_detailed: "assignee_area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')"
rationale: "Recorte padrão do Atendimento. Ouvidoria - IP e RT (Retenção) são fluxos distintos e ficam fora; no canal Web existem ainda BACKING_OPS, N/I, ENG, SDM, TRAINING e OUVIDORIA, todas fora do padrão."
if_omitted: "Para customer_type = 'Parceiro', linhas de RT, N/I e BACKING_OPS inflam sum_of_te e count_of_demanded — o TME sai 4–5x maior que o real."
```

A mesma regra usa `area` na fact e `assignee_area` na dim de tickets. A lista aparece no `kb.md` com e sem espaço depois da vírgula — é o mesmo predicado.

```yaml meta
kind: policy
id: escopo-atendimento-bot
title: Escopo do fluxo de suporte no chatbot
severity: blocking
applies_to: [dim_chatbot]
predicate:
  dim_chatbot: "bot_departament = 'Servir'"
rationale: "'Servir' é o fluxo de suporte principal; 'Retenção' é outro fluxo e NULL corresponde ao Bot_Fin sem departamento definido."
```

Presente em toda métrica de Cami. Não acrescentar filtro de `csat_type` nem de `bot_type` quando o objetivo é demanda total.

```yaml meta
kind: policy
id: escopo-canais-online
title: Canais com atendimento humano online (fila)
severity: blocking
applies_to: [fact_service_metrics]
predicate:
  fact_service_metrics: "channel IN ('Whatsapp','Telefone','Chat')"
rationale: "Só Whatsapp, Telefone e Chat têm tempo de atendimento e de espera; Email e Web não têm TA/TE."
if_omitted: "Email e Web entram no denominador sem TA/TE e distorcem TMA, TME e SLA TME."
```

Aplica-se a TMA, TME e SLA TME. O `kb.md` escreve a lista em duas ordens (`'Whatsapp','Telefone','Chat'` e `'Whatsapp','Chat','Telefone'`) — é o mesmo predicado.

```yaml meta
kind: policy
id: escopo-canais-humanos
title: Canais de atendimento humano
severity: advisory
applies_to: [fact_service_metrics]
predicate:
  fact_service_metrics: "channel IN ('Chat','Email','Telefone','Web','Whatsapp')"
rationale: "Conjunto completo dos canais humanos, usado na visão de Demanda Humana por Canal."
```

Enumeração explícita dos cinco canais; usada em conjunto com `escopo-atendimento-areas`.

```yaml meta
kind: policy
id: escopo-canal-telefone
title: Recorte do canal Telefone (voz)
severity: blocking
applies_to: [fact_service_metrics, dim_zendesk_tickets_detailed]
predicate:
  fact_service_metrics: "channel = 'Telefone'"
  dim_zendesk_tickets_detailed: "channel = 'Telefone'"
rationale: "Telefone é o componente de voz humana da Demanda Total e tem visões próprias (categorias de ticket, suporte premium)."
```

```yaml meta
kind: policy
id: escopo-csat-retidos
title: Linhas de avaliação de cliente retido pelo bot
severity: blocking
applies_to: [dim_chatbot]
predicate:
  dim_chatbot: "csat_type = 'csat_retidos'"
rationale: "O CSAT Cami usa apenas avaliações de clientes retidos pelo bot; 'N/I' é sessão sem avaliação e 'csat_transbordados' é avaliação de cliente transbordado para humano."
if_omitted: "Sem o recorte, linhas N/I e csat_transbordados entram no cálculo e o CSAT Cami fica errado."
```

```yaml meta
kind: policy
id: escopo-cami-sem-bot-fin
title: Cami sem Bot_Fin (Gen2 + Gen3)
severity: blocking
applies_to: [dim_chatbot]
predicate:
  dim_chatbot: "bot_type IN ('Gen2', 'Gen3 CA Pro', 'Gen3 CA Mais')"
rationale: "A visão por categoria considera só os bots Cami; Bot_Fin (Financeiro/FinAI) é produto diferente e é excluído."
```

Usada na Visão por Categoria Cami. Atenção: para **demanda** Cami o dashboard oficial inclui o Bot_Fin — nesse caso a política **não** se aplica (ver `bot-fin-nao-e-cami`).

```yaml meta
kind: policy
id: escopo-time-servir-capacity
title: Capacidade restrita ao time Servir
severity: blocking
applies_to: [agent_capacity]
predicate:
  agent_capacity: "team = 'Servir'"
rationale: "Só os encantadores do time Servir compõem HC Líquido e FTE do Atendimento; é o mesmo filtro do PDT pdt_agent_capacity_agg."
```

```yaml meta
kind: policy
id: segmento-pme-fsm
title: Segmento PME na fact_service_metrics
severity: blocking
applies_to: [fact_service_metrics]
predicate:
  fact_service_metrics: "customer_type != 'Parceiro'"
rationale: "Nesta tabela o padrão != 'Parceiro' é seguro (sem NULLs relevantes) e cobre Cliente do Parceiro + Cliente sem Parceiro."
```

```yaml meta
kind: policy
id: segmento-pme-chatbot
title: Segmento PME na dim_chatbot
severity: blocking
applies_to: [dim_chatbot]
predicate:
  dim_chatbot: "customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro')"
rationale: "Não existe valor literal 'PME' em dim_chatbot: PME = Cliente do Parceiro + Cliente sem Parceiro. O IN explícito evita incluir os NULLs existentes na tabela."
if_omitted: "Com != 'Parceiro' os NULLs de customer_type entram no PME e inflam o resultado (efeito observado sobretudo no Bot_Fin)."
```

```yaml meta
kind: policy
id: segmento-parceiro
title: Segmento Parceiro
severity: blocking
applies_to: [fact_service_metrics, dim_chatbot]
predicate:
  fact_service_metrics: "customer_type = 'Parceiro'"
  dim_chatbot: "customer_type = 'Parceiro'"
rationale: "Parceiro é o canal de parceiros, distinto dos sub-segmentos de PME (Cliente do Parceiro / Cliente sem Parceiro)."
```

Para métricas de Parceiro na `fact_service_metrics` é **obrigatório** combinar com `escopo-atendimento-areas` (ver `parceiros-exige-filtro-de-area`). O `kb.md` registra também uma definição alternativa em `dim_chatbot` — ver `definicao-parceiro-em-dim-chatbot-ambigua`.

```yaml meta
kind: policy
id: escopo-service-metrics-tickets
title: Tickets que compõem métricas de atendimento
severity: blocking
applies_to: [dim_zendesk_tickets_detailed]
predicate:
  dim_zendesk_tickets_detailed: "is_service_metrics = TRUE"
rationale: "Restringe aos tickets contabilizados nas métricas de atendimento, replicando a visão por categoria do dashboard de Telefone."
```

```yaml meta
kind: policy
id: janela-solved-at-com-fallback-nk-date
title: Janela por data de solução com fallback para nk_date
severity: blocking
applies_to: [dim_zendesk_tickets_detailed]
predicate:
  dim_zendesk_tickets_detailed: "(source_solved_at BETWEEN '<inicio>' AND '<fim>' OR (source_solved_at IS NULL AND DATE(nk_date) BETWEEN '<inicio>' AND '<fim>'))"
rationale: "Tickets com source_solved_at NULL precisam usar nk_date como fallback para reproduzir o dashboard."
if_omitted: "Categorias como 'emissão de nfse' ficam 3 tickets abaixo do dashboard."
```

Regra de janela específica da visão por categoria do Telefone — não é a janela simples usada nas outras fontes.

```yaml meta
kind: policy
id: escopo-area-backing-ops
title: Área BACKING_OPS (Billing Dono de Negócio)
severity: blocking
applies_to: [dim_zendesk_tickets_detailed]
predicate:
  dim_zendesk_tickets_detailed: "assignee_area = 'BACKING_OPS'"
rationale: "Os atendimentos de Billing Dono de Negócio são tratados pela área BACKING_OPS."
```

```yaml meta
kind: policy
id: escopo-categoria-billing-dono-de-negocio
title: Categoria Billing Dono de Negócio
severity: blocking
applies_to: [dim_zendesk_tickets_detailed]
predicate:
  dim_zendesk_tickets_detailed: "LOWER(ticket_category) = 'billing dono de negócio'"
rationale: "Recorte da categoria de negociação/retenção de billing; comparação em LOWER por variação de caixa no campo."
```

## 3. Métricas

```yaml meta
kind: measure
id: demanda-humana-recebida
title: Demanda humana recebida
source: fact_service_metrics
unit: count
expr: "SUM(count_of_demanded)"
policies: [escopo-atendimento-areas]
direction: neutral
pitfalls: [demanda-recebida-diferente-de-atendida]
status: stable
provenance: [dash-220]
```

Demanda **recebida** = atendidos + abandonados. É a medida do dashboard "Demanda humana por canal".

```yaml meta
kind: measure
id: demanda-humana-atendida
title: Demanda humana atendida
source: fact_service_metrics
unit: count
expr: "SUM(count_of_attended)"
policies: [escopo-atendimento-areas]
direction: neutral
pitfalls: [demanda-recebida-diferente-de-atendida]
status: stable
provenance: [dash-220]
```

Só os chamados efetivamente atendidos (exclui abandonos). É o numerador de Chamados por Encantador.

```yaml meta
kind: measure
id: demanda-abandonada
title: Demanda abandonada
source: fact_service_metrics
unit: count
expr: "SUM(count_of_abandoned)"
policies: [escopo-atendimento-areas]
direction: lower_is_better
status: stable
provenance: [dash-220]
```

Diferença entre demanda recebida e atendida.

```yaml meta
kind: measure
id: taxa-abandono
title: "% Abandono"
source: fact_service_metrics
unit: ratio
expr: "SUM(count_of_abandoned) / NULLIF(SUM(count_of_demanded), 0)"
policies: [escopo-atendimento-areas]
direction: lower_is_better
pitfalls: [abandono-telefone-vem-de-customer-type-null]
status: stable
provenance: [dash-220]
```

Segmentar por `customer_type` para PME vs Parceiro.

```yaml meta
kind: measure
id: demanda-telefone
title: Demanda Telefone (voz)
source: fact_service_metrics
unit: count
expr: "SUM(count_of_demanded)"
policies: [escopo-canal-telefone, escopo-atendimento-areas]
direction: neutral
pitfalls: [ouvidoria-ip-fora-do-filtro]
status: stable
provenance: [dash-220]
```

Componente humano (voz) da Demanda Total.

```yaml meta
kind: measure
id: demanda-cami
title: Demanda Cami (autoatendimento)
source: dim_chatbot
unit: count
expr: "SUM(sum_of_interactions)"
policies: [escopo-atendimento-bot]
direction: neutral
pitfalls: [demanda-cami-sem-filtro-csat-type, bot-fin-nao-e-cami]
status: stable
provenance: [dash-210]
```

Total de interações do bot no fluxo Servir. **Não** filtrar `csat_type` nem `bot_type` — o dashboard oficial inclui o Bot_Fin.

```yaml meta
kind: measure
id: demanda-total
title: Demanda Total (Cami + Telefone)
unit: count
expr: "demanda_cami + demanda_telefone"
composed_of: [demanda-cami, demanda-telefone]
kind_of_measure: composite
direction: neutral
status: stable
provenance: [dash-210, dash-220]
```

Métrica principal do acompanhamento semanal: autoatendimento do bot + voz humana.

```yaml meta
kind: measure
id: demanda-por-du
title: Demanda por DU (média por dia útil)
unit: count
expr: "demanda_total / <qtd_du>"
composed_of: [demanda-total]
kind_of_measure: derived
direction: neutral
pitfalls: [demanda-por-du-nao-e-filtro-de-dia-util]
status: stable
```

Normaliza a demanda total pelo número de dias úteis do período, para comparação semana-a-semana justa. Semana padrão (seg–sex) = 5 DU.

```yaml meta
kind: measure
id: sessoes-unicas-cami
title: Sessões únicas do Cami
source: dim_chatbot
unit: count
expr: "SUM(sum_of_interactions)"
policies: [escopo-atendimento-bot]
extra_predicate: "csat_type = 'N/I'"
direction: neutral
pitfalls: [csat-type-multiplica-linhas]
status: stable
```

Para **contar sessões únicas** use apenas `csat_type='N/I'`, porque cada thread pode gerar até 3 linhas.

```yaml meta
kind: measure
id: transbordos-cami
title: Transbordos do Cami para humano
source: dim_chatbot
unit: count
expr: "SUM(sum_of_transfers)"
policies: [escopo-atendimento-bot]
direction: lower_is_better
status: stable
provenance: [dash-210]
```

```yaml meta
kind: measure
id: retencao-cami
title: Retenção Cami
source: dim_chatbot
unit: ratio
expr: "1 - SUM(sum_of_transfers) / NULLIF(SUM(sum_of_interactions), 0)"
policies: [escopo-atendimento-bot]
composed_of: [transbordos-cami, demanda-cami]
kind_of_measure: derived
direction: higher_is_better
pitfalls: [customer-type-null-em-dim-chatbot, sem-valor-literal-pme-em-dim-chatbot]
status: stable
provenance: [dash-210]
```

Percentual de interações que o bot resolveu sem transbordar para humano.

```yaml meta
kind: measure
id: csat-cami
title: CSAT Cami
source: dim_chatbot
unit: ratio
expr: "SUM(sum_of_positive_ratings) / NULLIF(SUM(sum_of_total_ratings), 0)"
policies: [escopo-atendimento-bot, escopo-csat-retidos]
direction: higher_is_better
pitfalls: [denominador-csat-cami-total-ratings, bot-types-sem-avaliacoes-retornam-null, customer-type-null-em-dim-chatbot]
status: stable
provenance: [dash-210]
```

Denominador é `sum_of_total_ratings` (= positivas + negativas), **não** `sum_of_interactions`. Nas queries de CSAT Blended a mesma razão aparece escrita como `pos / (pos + neg)` — equivalente.

```yaml meta
kind: measure
id: volume-avaliacoes-cami
title: Volume de avaliações do Cami
source: dim_chatbot
unit: count
expr: "SUM(sum_of_total_ratings)"
policies: [escopo-atendimento-bot, escopo-csat-retidos]
direction: neutral
pitfalls: [amostras-pequenas-por-bot-type]
status: stable
```

Base amostral do CSAT Cami — necessária para julgar se a variação de um `bot_type` é significativa.

```yaml meta
kind: measure
id: csat-humano
title: CSAT Humano
source: fact_service_metrics
unit: ratio
expr: "SUM(count_of_positive_ratings) / NULLIF(SUM(count_of_positive_ratings) + SUM(count_of_negative_ratings), 0)"
policies: [escopo-atendimento-areas]
direction: higher_is_better
status: stable
provenance: [dash-220]
```

Avaliações positivas sobre o total de avaliações do atendimento humano.

```yaml meta
kind: measure
id: csat-blended
title: CSAT Blended
unit: ratio
expr: "(humano_pos + cami_pos) / NULLIF(humano_pos + humano_neg + cami_pos + cami_neg, 0)"
composed_of: [csat-humano, csat-cami]
kind_of_measure: composite
direction: higher_is_better
status: stable
provenance: [dash-210, dash-220]
```

"Blended" = avaliações do bot (Cami) + humano numa única nota: somam-se os numeradores e os denominadores das duas fontes, não se tira média das duas taxas.

```yaml meta
kind: measure
id: tma
title: TMA (Tempo Médio de Atendimento)
source: fact_service_metrics
unit: seconds
expr: "SUM(sum_of_ta) / NULLIF(SUM(count_of_attended), 0)"
policies: [escopo-canais-online, escopo-atendimento-areas]
direction: lower_is_better
pitfalls: [tma-tme-so-canais-online]
status: stable
provenance: [dash-220]
```

Resultado em segundos; dividir por 60 para minutos.

```yaml meta
kind: measure
id: tme
title: TME (Tempo Médio de Espera)
source: fact_service_metrics
unit: seconds
expr: "SUM(sum_of_te) / NULLIF(SUM(count_of_demanded), 0)"
policies: [escopo-canais-online, escopo-atendimento-areas]
direction: lower_is_better
pitfalls: [tma-tme-so-canais-online, parceiros-exige-filtro-de-area]
status: stable
provenance: [dash-220]
```

Denominador é a demanda **recebida** (também há espera em chamados abandonados).

```yaml meta
kind: measure
id: sla-tme-3min
title: SLA TME (<3 min)
source: fact_service_metrics
unit: ratio
expr: "SUM(CASE WHEN (sum_of_te / NULLIF(count_of_demanded,0)) < 180 THEN count_of_demanded END) / NULLIF(SUM(count_of_demanded), 0)"
policies: [escopo-canais-online, escopo-atendimento-areas]
direction: higher_is_better
pitfalls: [tma-tme-so-canais-online, parceiros-exige-filtro-de-area]
status: stable
provenance: [dash-220]
```

Percentual da demanda em linhas cujo TME médio ficou abaixo de 180 segundos — o teste é feito por linha, não sobre o TME agregado.

```yaml meta
kind: measure
id: hc-liquido
title: HC Líquido
source: agent_capacity
unit: count
expr: "ROUND(SUM(CAST(is_active_workday AS INT64)) / <qtd_du>, 0)"
policies: [escopo-time-servir-capacity]
direction: neutral
pitfalls: [hc-liquido-depende-de-qtd-du]
status: stable
provenance: [dash-220]
```

Média diária de encantadores ativos no período.

```yaml meta
kind: measure
id: chamados-por-encantador-mes
title: Chamados atendidos por encantador (mês)
unit: count
expr: "total_atendido / hc_liquido"
composed_of: [demanda-humana-atendida, hc-liquido]
kind_of_measure: composite
direction: higher_is_better
pitfalls: [chamados-por-encantador-usa-total-de-todos-os-segmentos]
status: stable
provenance: [dash-220]
```

Numerador é o total atendido de **todos** os segmentos (PME + Parceiro) — o mesmo HC atende os dois.

```yaml meta
kind: measure
id: chamados-por-encantador-du
title: Chamados atendidos por encantador (por DU)
unit: count
expr: "total_atendido / hc_liquido / <qtd_du>"
composed_of: [chamados-por-encantador-mes]
kind_of_measure: derived
direction: higher_is_better
pitfalls: [chamados-por-encantador-usa-total-de-todos-os-segmentos]
status: stable
provenance: [dash-220]
```

```yaml meta
kind: measure
id: densidade-demanda
title: Densidade de Demanda
unit: ratio
expr: "SUM(count_of_demanded) / MAX(dim_active_companies_by_month.total_active_companies)"
composed_of: [demanda-humana-recebida]
kind_of_measure: composite
direction: lower_is_better
status: stable
```

Demanda sobre base ativa. JOIN: `date_trunc(nk_event_date, month) = nk_month` de `dim_active_companies_by_month`.

```yaml meta
kind: measure
id: fte-capacidade
title: FTE (Capacidade)
unit: ratio
expr: "SUM(capacity) / SUM(count_of_demanded)"
composed_of: [demanda-humana-recebida]
kind_of_measure: composite
policies: [escopo-time-servir-capacity]
direction: neutral
status: draft
status_reason: "definida apenas por fórmula no kb.md (PDT inline de silver_serve.agent_capacity), sem query validada"
```

Capacidade sobre demanda, com a capacidade vinda do PDT inline de `silver_serve.agent_capacity`.

```yaml meta
kind: measure
id: atendimentos-mais-6m
title: Atendimentos de clientes com +6 meses de casa
source: fact_service_metrics
unit: count
expr: "SUM(CASE WHEN is_under_6m = FALSE OR is_under_6m IS NULL THEN count_of_attended END)"
policies: [escopo-canal-telefone, escopo-atendimento-areas]
direction: neutral
status: stable
```

NULL em `is_under_6m` conta como +6 meses de casa.

```yaml meta
kind: measure
id: atendimentos-menos-6m
title: Atendimentos de clientes com -6 meses de casa
source: fact_service_metrics
unit: count
expr: "SUM(CASE WHEN is_under_6m = TRUE THEN count_of_attended END)"
policies: [escopo-canal-telefone, escopo-atendimento-areas]
direction: neutral
status: stable
```

```yaml meta
kind: measure
id: interacoes-ticket
title: Interações (contagem de tickets)
source: dim_zendesk_tickets_detailed
unit: count
expr: "COUNT(*)"
policies: [escopo-canal-telefone, escopo-atendimento-areas, escopo-service-metrics-tickets, janela-solved-at-com-fallback-nk-date]
direction: neutral
status: stable
provenance: [dash-273]
```

Contagem de tickets na visão por categoria do Telefone.

```yaml meta
kind: measure
id: mix-categoria
title: Mix de demanda por categoria
source: dim_zendesk_tickets_detailed
unit: ratio
expr: "COUNT(*) / SUM(COUNT(*)) OVER ()"
composed_of: [interacoes-ticket]
kind_of_measure: derived
direction: neutral
status: stable
provenance: [dash-273]
```

Participação da categoria no total do recorte. A mesma forma (`interacoes / SUM(interacoes) OVER ()`) é usada no mix da Visão por Categoria Cami.

```yaml meta
kind: measure
id: csat-ticket-telefone
title: CSAT por ticket (Telefone)
source: dim_zendesk_tickets_detailed
unit: ratio
expr: "COUNTIF(current_rating = 'good') / NULLIF(COUNTIF(current_rating IS NOT NULL), 0)"
policies: [escopo-canal-telefone, escopo-atendimento-areas, escopo-service-metrics-tickets, janela-solved-at-com-fallback-nk-date]
direction: higher_is_better
status: stable
provenance: [dash-273]
```

`current_rating = 'good'` é a avaliação positiva; o denominador conta só tickets avaliados.

```yaml meta
kind: measure
id: tma-ticket-minutos
title: TMA por ticket (minutos)
source: dim_zendesk_tickets_detailed
unit: seconds
expr: "AVG(online_service_time) / 60"
policies: [escopo-canal-telefone, escopo-atendimento-areas, escopo-service-metrics-tickets, janela-solved-at-com-fallback-nk-date]
direction: lower_is_better
status: stable
provenance: [dash-273]
```

`online_service_time` está em segundos; a divisão por 60 entrega minutos.

```yaml meta
kind: measure
id: billing-dn-total-atendimentos
title: Billing DN — total de atendimentos
source: dim_zendesk_tickets_detailed
unit: count
expr: "COUNT(DISTINCT id)"
policies: [escopo-categoria-billing-dono-de-negocio, escopo-area-backing-ops]
direction: neutral
pitfalls: [cancellation-tickets-pode-ter-defasagem]
status: stable
```

Janela por `DATE(source_solved_at)`.

```yaml meta
kind: measure
id: billing-dn-negociacao
title: Billing DN — negociação
source: dim_zendesk_tickets_detailed
unit: count
expr: "COUNTIF(subclassification IN ('retido','retenção') OR servir_churn_type IS NOT NULL)"
policies: [escopo-categoria-billing-dono-de-negocio, escopo-area-backing-ops]
direction: neutral
status: stable
```

Atendimento classificado como negociação: subclassificação de retenção **ou** tipo de churn preenchido.

```yaml meta
kind: measure
id: billing-dn-retidos
title: Billing DN — retidos
source: dim_zendesk_tickets_detailed
unit: count
expr: "COUNTIF(subclassification IN ('retido','retenção'))"
policies: [escopo-categoria-billing-dono-de-negocio, escopo-area-backing-ops]
direction: higher_is_better
status: stable
```

```yaml meta
kind: measure
id: billing-dn-nao-retido
title: Billing DN — não retidos
source: dim_zendesk_tickets_detailed
unit: count
expr: "COUNTIF(servir_churn_type IS NOT NULL AND COALESCE(subclassification,'') NOT IN ('retido','retenção'))"
policies: [escopo-categoria-billing-dono-de-negocio, escopo-area-backing-ops]
direction: lower_is_better
status: stable
```

Negociação que **não** resultou em subclassificação retido/retenção.

```yaml meta
kind: measure
id: billing-dn-taxa-retencao
title: Billing DN — taxa de retenção
source: dim_zendesk_tickets_detailed
unit: ratio
expr: "COUNTIF(subclassification IN ('retido','retenção')) / NULLIF(COUNTIF(subclassification IN ('retido','retenção') OR servir_churn_type IS NOT NULL), 0)"
composed_of: [billing-dn-retidos, billing-dn-negociacao]
kind_of_measure: derived
policies: [escopo-categoria-billing-dono-de-negocio, escopo-area-backing-ops]
direction: higher_is_better
status: stable
```

Retidos sobre negociações.

```yaml meta
kind: measure
id: billing-dn-mix-demanda
title: Billing DN — mix de demanda
unit: ratio
expr: "COUNT(DISTINCT id) da categoria billing dono de negócio / COUNT(DISTINCT id) total de BACKING_OPS"
composed_of: [billing-dn-total-atendimentos]
kind_of_measure: derived
policies: [escopo-area-backing-ops]
direction: neutral
status: draft
status_reason: "definida em prosa no kb.md (tabela de definições de campos), sem query validada isolada"
```

Peso da categoria Billing Dono de Negócio dentro do total atendido pela BACKING_OPS.

## 4. Relatórios

```yaml meta
kind: report
id: rel-demanda-cami-e-telefone-sem-janela
title: Demanda Total (Cami + Telefone) — expressões por fonte, sem janela de data
sources: [dim_chatbot, fact_service_metrics]
measures: [demanda-cami, demanda-telefone]
policies: [escopo-atendimento-bot, escopo-canal-telefone, escopo-atendimento-areas]
status: stable
```

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

Bloco de definição do KPI: duas consultas separadas, sem filtro de período. A versão executável com janela é `rel-demanda-total-semanal-cami-telefone`.

```yaml meta
kind: report
id: rel-demanda-total-semanal-cami-telefone
title: Demanda Total Semanal (Cami + Telefone)
sources: [dim_chatbot, fact_service_metrics]
measures: [demanda-cami, demanda-telefone, demanda-total]
policies: [escopo-atendimento-bot, escopo-canal-telefone, escopo-atendimento-areas]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

A Demanda Total é a soma das duas linhas do resultado.

```yaml meta
kind: report
id: rel-demanda-humana-recebida-por-canal-sem-janela
title: Demanda Humana por Canal (recebida) — sem janela de data
sources: [fact_service_metrics]
measures: [demanda-humana-recebida]
policies: [escopo-canais-humanos, escopo-atendimento-areas]
status: stable
```

```sql
SELECT channel, SUM(count_of_demanded) AS demanda_recebida
FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
WHERE channel IN ('Chat', 'Email', 'Telefone', 'Web', 'Whatsapp')
  AND area IN ('BK', 'DN', 'EC', 'SAC - CA', 'SAC - Pessoalize')
GROUP BY channel
```

Bloco de definição do KPI; usa `count_of_demanded` (recebida), não `count_of_attended`.

```yaml meta
kind: report
id: rel-demanda-humana-por-canal
title: Demanda Humana por Canal (recebida, atendida e abandonada)
sources: [fact_service_metrics]
measures: [demanda-humana-recebida, demanda-humana-atendida, demanda-abandonada]
policies: [escopo-canais-humanos, escopo-atendimento-areas]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

```yaml meta
kind: report
id: rel-csat-blended-pme-componentes-sem-janela
title: CSAT Blended PME — componentes humano e Cami, sem janela de data
sources: [fact_service_metrics, dim_chatbot]
measures: [csat-humano, csat-cami, csat-blended]
policies: [escopo-atendimento-areas, segmento-pme-fsm, escopo-atendimento-bot, escopo-csat-retidos]
status: stable
```

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

Bloco de definição do KPI (fórmula + duas consultas de componente, sem janela). Atenção: o recorte PME do lado Cami usa `!= 'Parceiro'`, contrariando `segmento-pme-chatbot` — ver `customer-type-null-em-dim-chatbot`.

```yaml meta
kind: report
id: rel-csat-blended-pme-e-parceiro
title: CSAT Blended PME e Parceiro (humano, Cami e blended)
sources: [fact_service_metrics, dim_chatbot]
measures: [csat-humano, csat-cami, csat-blended]
policies: [escopo-atendimento-areas, segmento-pme-fsm, segmento-parceiro, escopo-atendimento-bot, escopo-csat-retidos]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

```yaml meta
kind: report
id: rel-csat-blended-pme-por-sub-segmento
title: CSAT Blended PME por sub-segmento (Cliente do Parceiro / Cliente sem Parceiro)
sources: [fact_service_metrics, dim_chatbot]
measures: [csat-humano, csat-cami, csat-blended]
policies: [escopo-atendimento-areas, segmento-pme-fsm, segmento-pme-chatbot, escopo-atendimento-bot, escopo-csat-retidos]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

No lado Cami o PME usa `IN ('Cliente do Parceiro','Cliente sem Parceiro')`; no lado humano, `!= 'Parceiro'`.

```yaml meta
kind: report
id: rel-csat-parceiros-blended-humano-cami
title: CSAT Parceiros — Blended, Humano e Cami
sources: [fact_service_metrics, dim_chatbot]
measures: [csat-humano, csat-cami, csat-blended]
policies: [escopo-atendimento-areas, segmento-parceiro, escopo-atendimento-bot, escopo-csat-retidos]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

Recorte só do segmento Parceiro. Aqui a janela da fact usa `nk_event_date` direto, sem `DATE()`.

```yaml meta
kind: report
id: rel-csat-cami-pme-por-bot-type-e-sub-segmento
title: CSAT Cami PME por bot_type e sub-segmento
sources: [dim_chatbot]
measures: [csat-cami, volume-avaliacoes-cami]
policies: [escopo-atendimento-bot, escopo-csat-retidos, segmento-pme-chatbot]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

Devolve também o volume de avaliações de cada recorte — necessário para julgar significância.

```yaml meta
kind: report
id: rel-retencao-cami-segmentos-sem-janela
title: Retenção Cami (total, PME, Parceiro) — sem janela de data
sources: [dim_chatbot]
measures: [retencao-cami]
policies: [escopo-atendimento-bot, segmento-parceiro]
status: stable
```

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

Bloco de definição do KPI, sem filtro de período. O PME aqui usa `!= 'Parceiro'` em `dim_chatbot` — ver `customer-type-null-em-dim-chatbot`.

```yaml meta
kind: report
id: rel-retencao-cami-pme-e-parceiro
title: Retenção Cami (total, PME e Parceiro)
sources: [dim_chatbot]
measures: [retencao-cami]
policies: [escopo-atendimento-bot, segmento-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

```yaml meta
kind: report
id: rel-retencao-cami-por-bot-type-e-sub-segmento
title: Retenção Cami por bot_type e sub-segmento
sources: [dim_chatbot]
measures: [retencao-cami]
policies: [escopo-atendimento-bot, segmento-pme-chatbot, segmento-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

Breakdown completo: total + PME (CDP/CSP) + Parceiro, por bot_type.

```yaml meta
kind: report
id: rel-retencao-e-volume-avaliacoes-por-bot-type
title: Retenção por bot_type + volume de avaliações (concentração)
sources: [dim_chatbot]
measures: [retencao-cami, volume-avaliacoes-cami]
policies: [escopo-atendimento-bot, segmento-pme-chatbot, segmento-parceiro, escopo-csat-retidos]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

Junta retenção por segmento e volume de avaliações no mesmo recorte — usado para medir concentração de avaliações num único bot.

```yaml meta
kind: report
id: rel-visao-por-categoria-cami
title: Visão por Categoria Cami (Gen2 + Gen3 CA Pro + Gen3 CA Mais)
sources: [dim_chatbot, ingestion_zendesk_tickets]
measures: [demanda-cami, transbordos-cami, retencao-cami, mix-categoria]
policies: [escopo-atendimento-bot, escopo-cami-sem-bot-fin]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

Categoria derivada das tags do Zendesk via join `dim_chatbot` ↔ `silver_serve.ingestion_zendesk_tickets`: por `thread_uid` (Gen3/Ultimate) ou por `intercom_conversation_id` (Bot_Fin).

```yaml meta
kind: report
id: rel-sla-tme-tma-abandono-por-segmento
title: SLA TME, TME, TMA e Abandono (PME total, CDP, CSP e Parceiro)
sources: [fact_service_metrics]
measures: [sla-tme-3min, tme, tma, taxa-abandono]
policies: [escopo-atendimento-areas, escopo-canais-online, segmento-pme-fsm, segmento-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

O abandono é calculado **sem** o recorte de canais online; SLA TME, TME e TMA usam os três canais com fila.

```yaml meta
kind: report
id: rel-abandono-cdp-vs-csp
title: Abandono — Cliente do Parceiro vs Cliente sem Parceiro
sources: [fact_service_metrics]
measures: [taxa-abandono]
policies: [escopo-atendimento-areas]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

Comparação direta dos dois sub-segmentos de PME. Sobrepõe-se a `rel-sla-tme-tma-abandono-por-segmento`, que já devolve `abandono_cdp`/`abandono_csp`.

```yaml meta
kind: report
id: rel-hc-liquido
title: HC Líquido e Chamados por Encantador
sources: [agent_capacity, fact_service_metrics]
measures: [hc-liquido, chamados-por-encantador-mes, chamados-por-encantador-du, demanda-humana-atendida]
policies: [escopo-time-servir-capacity]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
  - {name: qtd_du, type: integer}
status: stable
```

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

Só o HC é query; as duas derivações de chamados por encantador ficam documentadas em comentário.

```yaml meta
kind: report
id: rel-performance-encantadores-pme
title: Performance dos Encantadores PME (HC, Chamados/enc, demanda e CSAT por sub-segmento)
sources: [agent_capacity, fact_service_metrics]
measures: [hc-liquido, chamados-por-encantador-mes, chamados-por-encantador-du, demanda-humana-recebida, demanda-humana-atendida, csat-humano]
policies: [escopo-time-servir-capacity, escopo-atendimento-areas]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
  - {name: qtd_du, type: integer}
status: stable
```

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

O CTE `total` não segmenta `customer_type` — o numerador de chamados/encantador é o total atendido de todos os segmentos.

```yaml meta
kind: report
id: rel-telefone-por-categoria-de-ticket
title: Telefone — Visão por Categoria de Ticket
sources: [dim_zendesk_tickets_detailed]
measures: [interacoes-ticket, mix-categoria, csat-ticket-telefone, tma-ticket-minutos]
policies: [escopo-canal-telefone, escopo-atendimento-areas, escopo-service-metrics-tickets, janela-solved-at-com-fallback-nk-date]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

Nesta fonte o campo de área é `assignee_area` (não `area`), e a janela usa fallback de data.

```yaml meta
kind: report
id: rel-telefone-suporte-premium
title: Telefone — Segmentação por Suporte Premium e tempo de casa
sources: [fact_service_metrics]
measures: [demanda-humana-atendida, atendimentos-mais-6m, atendimentos-menos-6m]
policies: [escopo-canal-telefone, escopo-atendimento-areas]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

`has_premium_support` NULL vira "Não Identificado" e `customer_type` NULL vira "Sem Tipo de Cliente". A base é `count_of_attended` (interação total).

```yaml meta
kind: report
id: rel-billing-dono-de-negocio-negociacao
title: Billing Dono de Negócio — total, negociação, retidos e não retidos
sources: [dim_zendesk_tickets_detailed]
measures: [billing-dn-total-atendimentos, billing-dn-negociacao, billing-dn-retidos, billing-dn-nao-retido]
policies: [escopo-categoria-billing-dono-de-negocio, escopo-area-backing-ops]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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

Aqui a janela usa `DATE(source_solved_at)` **sem** o fallback para `nk_date`.

```yaml meta
kind: report
id: rel-billing-dono-de-negocio-taxa-retencao
title: Billing Dono de Negócio — taxa de retenção
sources: [dim_zendesk_tickets_detailed]
measures: [billing-dn-total-atendimentos, billing-dn-negociacao, billing-dn-retidos, billing-dn-taxa-retencao]
policies: [escopo-categoria-billing-dono-de-negocio, escopo-area-backing-ops]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

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
```

Mesma base do relatório anterior, acrescentando a razão retidos/negociação.

## 5. Armadilhas

```yaml meta
kind: pitfall
id: bot-fin-nao-e-cami
severity: high
applies_to: [dim_chatbot, demanda-cami]
enforced_by: escopo-cami-sem-bot-fin
```

`bot_type = 'Bot_Fin'` é o bot Financeiro/FinAI — está incluído em `bot_departament = 'Servir'` mas representa produto diferente do Cami. Para **demanda Cami** use `bot_departament='Servir'` **sem** filtrar `bot_type`, porque o dashboard oficial inclui o Bot_Fin. Já na visão por categoria o Bot_Fin é excluído explicitamente.

```yaml meta
kind: pitfall
id: csat-type-multiplica-linhas
severity: high
applies_to: [dim_chatbot, sessoes-unicas-cami, csat-cami]
```

`csat_type` cria múltiplas linhas: cada thread pode ter até 3 linhas (`N/I` + `csat_retidos` + `csat_transbordados`). Para contar sessões únicas use apenas `csat_type='N/I'`; para CSAT use `csat_type='csat_retidos'`.

```yaml meta
kind: pitfall
id: demanda-cami-sem-filtro-csat-type
severity: high
applies_to: [demanda-cami]
enforced_by: escopo-atendimento-bot
```

Demanda Cami = **todos** os `csat_type`. `SUM(sum_of_interactions)` com `bot_departament='Servir'` e sem filtro de `csat_type` é o total correto de interações; filtrar `csat_type` aqui subestima a demanda.

```yaml meta
kind: pitfall
id: area-rt-fora-do-atendimento
severity: high
applies_to: [fact_service_metrics]
enforced_by: escopo-atendimento-areas
```

A área `RT` na `fact_service_metrics` representa atendimentos do fluxo de **Retenção** — não entra no filtro padrão de Atendimento.

```yaml meta
kind: pitfall
id: ouvidoria-ip-fora-do-filtro
severity: high
applies_to: [fact_service_metrics, demanda-telefone]
enforced_by: escopo-atendimento-areas
```

`area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')` é o filtro padrão: `Ouvidoria - IP` e `RT` ficam **fora** da Demanda Total — inclusive no canal Telefone, onde `Ouvidoria - IP` existe.

```yaml meta
kind: pitfall
id: tma-tme-so-canais-online
severity: high
applies_to: [tma, tme, sla-tme-3min]
enforced_by: escopo-canais-online
```

Calcular TMA/TME/SLA apenas para `channel IN ('Whatsapp','Telefone','Chat')` — Email e Web não têm TA/TE e contaminam o denominador.

```yaml meta
kind: pitfall
id: demanda-recebida-diferente-de-atendida
severity: medium
applies_to: [demanda-humana-recebida, demanda-humana-atendida]
```

O dashboard "Demanda humana por canal" usa `count_of_demanded` (**recebida** = atendidos + abandonados). `count_of_attended` é menor porque exclui os abandonos; a diferença entre as duas é exatamente `count_of_abandoned`.

```yaml meta
kind: pitfall
id: web-tem-areas-extras
severity: medium
applies_to: [fact_service_metrics]
enforced_by: escopo-atendimento-areas
```

O canal Web carrega muitas áreas extras — `BACKING_OPS`, `N/I`, `RT`, `ENG`, `SDM`, `TRAINING`, `OUVIDORIA` — todas fora do filtro padrão de Atendimento.

```yaml meta
kind: pitfall
id: parceiros-exige-filtro-de-area
severity: high
applies_to: [tme, tma, sla-tme-3min, taxa-abandono]
enforced_by: escopo-atendimento-areas
```

Para SLA/TME/TMA/Abandono de `customer_type='Parceiro'` é **obrigatório** incluir `area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')`. Sem esse filtro, linhas de `RT`, `N/I` e `BACKING_OPS` inflam `sum_of_te` e `count_of_demanded`, e o TME sai 4–5x maior que o real.

```yaml meta
kind: pitfall
id: customer-type-null-em-dim-chatbot
severity: high
applies_to: [dim_chatbot, retencao-cami, csat-cami]
enforced_by: segmento-pme-chatbot
```

Em `dim_chatbot` existe `customer_type = NULL` (na ordem de ~21 linhas por `bot_type` numa semana). Não usar `!= 'Parceiro'` para PME nessa tabela — usar `IN ('Cliente do Parceiro','Cliente sem Parceiro')` explícito para não incluir os NULLs. Em `fact_service_metrics` o padrão `!= 'Parceiro'` é seguro (sem NULLs relevantes). Esses NULLs explicam divergências de até ~0,8pp nos indicadores totais de Bot_Fin/Fin AI, que o dashboard provavelmente exclui; nos outros bot_types a diferença fica ≤0,14pp.

```yaml meta
kind: pitfall
id: sem-valor-literal-pme-em-dim-chatbot
severity: high
applies_to: [dim_chatbot]
enforced_by: segmento-pme-chatbot
```

Em `dim_chatbot` **não existe** valor literal `PME`: além de `Parceiro`, o PME se divide em `Cliente do Parceiro` (CDP) e `Cliente sem Parceiro` (CSP). Logo PME = `customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro')`.

```yaml meta
kind: pitfall
id: definicao-parceiro-em-dim-chatbot-ambigua
severity: medium
applies_to: [dim_chatbot, segmento-parceiro]
```

O `kb.md` traz duas definições para Parceiro em `dim_chatbot`: `customer_type = 'Parceiro'` (usada em todas as queries validadas) e `customer_type NOT IN ('Cliente do Parceiro','Cliente sem Parceiro')` ("exclui PME", na seção do segmento Parceiros). As duas divergem exatamente nas linhas com `customer_type` NULL — a segunda as inclui no Parceiro. Prefira a forma usada nas queries validadas.

```yaml meta
kind: pitfall
id: denominador-csat-cami-total-ratings
severity: high
applies_to: [csat-cami]
```

Usar `sum_of_total_ratings` como denominador do CSAT Cami (= positivas + negativas), **nunca** `sum_of_interactions` — a maioria das interações não tem avaliação.

```yaml meta
kind: pitfall
id: bot-types-sem-avaliacoes-retornam-null
severity: low
applies_to: [csat-cami]
```

Alguns `bot_type` (por exemplo Gen 2 e Gen 3 CA Mais no recorte PME) podem não ter avaliações `csat_retidos` no período e retornam **NULL** — NULL aqui significa "sem avaliação", não zero.

```yaml meta
kind: pitfall
id: amostras-pequenas-por-bot-type
severity: medium
applies_to: [csat-cami, volume-avaliacoes-cami]
```

As avaliações do Cami se concentram fortemente num único `bot_type` (o Fin AI costuma responder por 95%+ do volume), e os demais podem ficar com amostras irrisórias (poucas unidades de avaliação). Sempre reportar o volume junto do percentual e não ler variação de amostra pequena como tendência.

```yaml meta
kind: pitfall
id: categoria-vendas-e-na-divergentes
severity: high
applies_to: [ingestion_zendesk_tickets, rel-visao-por-categoria-cami]
```

Na Visão por Categoria Cami, as categorias **Vendas** e **NA** têm divergência conhecida contra o dashboard e ainda não foram reconciliadas — não usar esses dois valores até resolução. As demais categorias reproduzem o dashboard.

```yaml meta
kind: pitfall
id: tag-vendas-antiga-descontinuada
severity: medium
applies_to: [ingestion_zendesk_tickets]
```

A tag atual de Vendas é `mt_vendas_estoque_e_api`; a tag antiga `mt_vendas_compras_estoque_e_api` não existe mais em 2026. Consultas herdadas que ainda usam a tag antiga retornam zero.

```yaml meta
kind: pitfall
id: interacoes-sem-ticket-caem-em-na
severity: medium
applies_to: [rel-visao-por-categoria-cami]
```

Interações sem ticket Zendesk correspondente (retidas sem tag) caem na categoria `NA` — o `NA` não é erro de dado, é o resíduo esperado do join por `thread_uid`/`intercom_conversation_id`.

```yaml meta
kind: pitfall
id: ordem-dos-when-na-categorizacao-de-tags
severity: high
applies_to: [rel-visao-por-categoria-cami]
```

A ordem dos `WHEN` na categorização por tags é a ordem exata da query oficial: primeiro as categorias temáticas (`mt_*` específicas), só depois as comportamentais (`mt_desistente`, `mt_falar_com_atendente`). Reordenar os `WHEN` muda a classificação de interações que carregam mais de uma tag.

```yaml meta
kind: pitfall
id: hc-liquido-depende-de-qtd-du
severity: high
applies_to: [agent_capacity, hc-liquido]
enforced_by: escopo-time-servir-capacity
```

O HC Líquido é `SUM(CAST(is_active_workday AS INT64))` dividido pelo **número de dias úteis do período** (`<qtd_du>`), com `team = 'Servir'`. O divisor não sai da query: precisa ser informado corretamente, ou o HC — e tudo que dele deriva — fica proporcionalmente errado.

```yaml meta
kind: pitfall
id: chamados-por-encantador-usa-total-de-todos-os-segmentos
severity: high
applies_to: [chamados-por-encantador-mes, chamados-por-encantador-du]
```

Chamados por encantador usa o **total atendido de todos os segmentos** (PME + Parceiro) como numerador — o mesmo HC atende PME e Parceiros. A visão "[Parceiro]" do dashboard só troca as barras de demanda e CSAT; HC e produtividade são compartilhados. Segmentar o numerador por `customer_type` produz número errado.

```yaml meta
kind: pitfall
id: demanda-por-du-nao-e-filtro-de-dia-util
severity: medium
applies_to: [demanda-por-du]
```

Demanda por DU **não** é um filtro de dia útil na query — é a divisão do total do período pelo número de dias úteis (semana padrão seg–sex = 5 DU). Filtrar dias úteis na base daria outro número.

```yaml meta
kind: pitfall
id: source-solved-at-null-precisa-fallback
severity: high
applies_to: [dim_zendesk_tickets_detailed, interacoes-ticket]
enforced_by: janela-solved-at-com-fallback-nk-date
```

Tickets com `source_solved_at IS NULL` precisam usar `nk_date` como fallback na janela de data. Sem isso, categorias como "emissão de nfse" ficam alguns tickets abaixo do dashboard.

```yaml meta
kind: pitfall
id: integracao-bancaria-divergencia-pendente
severity: low
applies_to: [rel-telefone-por-categoria-de-ticket]
```

A categoria "integração bancária" apresenta diferença residual contra o dashboard, com investigação pendente — hipótese registrada: join adicional no Looker capturando tickets atendidos cujo solve caiu fora da janela.

```yaml meta
kind: pitfall
id: cancellation-tickets-pode-ter-defasagem
severity: medium
applies_to: [dim_zendesk_tickets_detailed, billing-dn-total-atendimentos]
```

A tabela `silver_retention.cancellation_tickets` (explore `churn_data_mart` → `cancellation_tickets`) é a fonte oficial do Looker para Billing Dono de Negócio, mas pode ter defasagem. Usar `gold_serve.dim_zendesk_tickets_detailed` com os filtros de categoria + `BACKING_OPS` + `DATE(source_solved_at)` replica os números corretamente. Diferenças de 1 unidade em "não retidos" podem vir de tracking no Fortknox.

```yaml meta
kind: pitfall
id: abandono-telefone-vem-de-customer-type-null
severity: medium
applies_to: [taxa-abandono]
```

No canal Telefone, PME e Parceiro têm ~0% de abandono; o abandono total do canal (na casa de 4–5%) vem de linhas com `customer_type IS NULL` ou de segmentos fora de PME/Parceiro. Somar os segmentos não reproduz o total do canal.

## 6. Glossário

```yaml meta
kind: term
id: cami
aliases: [SuperCami, "Cami/SuperCami", chatbot]
scoped_by: escopo-atendimento-bot
quantified_by: demanda-cami
```

Chatbot de autoatendimento da ContaAzul (plataformas Blip/Takeblip/Ultimate), registrado em `gold_serve.dim_chatbot`. No fluxo de suporte corresponde a `bot_departament = 'Servir'`.

```yaml meta
kind: term
id: bot-fin
aliases: [Bot_Fin, "Fin AI", FinAI, "bot Financeiro"]
```

Bot Financeiro/FinAI. Aparece como `bot_type = 'Bot_Fin'` dentro de `bot_departament = 'Servir'`, mas **não é o Cami** — é produto diferente, e é o bot cujos registros aparecem com `bot_departament` NULL.

```yaml meta
kind: term
id: bot-type
aliases: [Gen2, "Gen 2", "Gen3 CA Mais", "Gen 3 CA Mais", "Gen3 CA Pro", "Gen 3 CA Pro"]
```

Tipo de bot: `Gen2` (bot principal de Whatsapp), `Gen3 CA Mais` (Gen3 para CA Mais, no Chat), `Gen3 CA Pro` (Gen3 para CA Pro, no Chat e no Whatsapp) e `Bot_Fin`.

```yaml meta
kind: term
id: bot-departament
aliases: [bot_departament, "departamento do bot"]
scoped_by: escopo-atendimento-bot
```

Fluxo ao qual a interação do bot pertence: `Servir` (suporte principal, base das métricas de Atendimento), `Retenção` (retenção de clientes) e NULL (Bot_Fin sem departamento definido).

```yaml meta
kind: term
id: csat-type
aliases: [csat_type, "N/I", csat_retidos, csat_transbordados]
scoped_by: escopo-csat-retidos
```

Classificação da linha de avaliação em `dim_chatbot`: `N/I` = sessão sem avaliação (topo de funil, maioria das interações); `csat_retidos` = avaliação de cliente retido pelo bot; `csat_transbordados` = avaliação de cliente transbordado para humano.

```yaml meta
kind: term
id: pme
aliases: [PME]
scoped_by: segmento-pme-fsm
```

Segmento de pequenas e médias empresas. PME = Cliente do Parceiro (CDP) + Cliente sem Parceiro (CSP). Em `fact_service_metrics` obtém-se com `customer_type != 'Parceiro'`; em `dim_chatbot`, com `IN ('Cliente do Parceiro','Cliente sem Parceiro')`.

```yaml meta
kind: term
id: parceiro
aliases: [Parceiros, "canal de parceiros", contador]
scoped_by: segmento-parceiro
```

Canal de parceiros (contadores) — distinto dos sub-segmentos de PME. `customer_type = 'Parceiro'`.

```yaml meta
kind: term
id: cliente-do-parceiro
aliases: [CDP, "Cliente do Parceiro"]
```

Sub-segmento de PME: cliente que tem um parceiro/contador associado.

```yaml meta
kind: term
id: cliente-sem-parceiro
aliases: [CSP, "Cliente sem Parceiro"]
```

Sub-segmento de PME: cliente sem parceiro/contador associado.

```yaml meta
kind: term
id: sem-tipo-de-cliente
aliases: ["Sem Tipo de Cliente", "customer_type NULL"]
```

Rótulo dado a `customer_type IS NULL` (via `COALESCE`). Não é segmento de negócio — é ausência de classificação, e é fonte recorrente de divergência com o dashboard.

```yaml meta
kind: term
id: blended
aliases: ["CSAT Blended", blended]
quantified_by: csat-blended
```

Visão que junta bot (Cami) e humano numa única nota: somam-se os numeradores e os denominadores das duas fontes, em vez de tirar média das duas taxas.

```yaml meta
kind: term
id: transbordo
aliases: [transbordos, transbordado, transfer, sum_of_transfers]
```

Passagem de uma conversa do bot para atendimento humano. É o complemento da retenção do bot.

```yaml meta
kind: term
id: retencao-do-bot
aliases: ["Retenção Cami", "retenção do bot", "retido pelo bot", sum_of_final_bot]
quantified_by: retencao-cami
```

Interação que o bot resolveu sem transbordar para humano. Não confundir com a área/fluxo `RT` (Retenção de clientes) nem com "retido" do Billing DN.

```yaml meta
kind: term
id: area-de-atendimento
aliases: [area, assignee_area, "área do encantador"]
scoped_by: escopo-atendimento-areas
```

Área do encantador que atendeu. Escopo padrão do Atendimento: `BK`, `DN`, `EC`, `SAC - CA`, `SAC - Pessoalize`. Fora do escopo: `Ouvidoria - IP`/`OUVIDORIA`, `RT`, `ENG`, `N/I`, `SDM`, `TRAINING`, `BACKING_OPS`. Na `dim_zendesk_tickets_detailed` o campo equivalente é `assignee_area`.

```yaml meta
kind: term
id: encantador
aliases: [encantadores, atendente, agente]
quantified_by: hc-liquido
```

Atendente humano do time Servir. Sua capacidade e seus dias ativos vivem em `silver_serve.agent_capacity` (`team = 'Servir'`); na `fact_service_metrics` é identificado por `nk_email`.

```yaml meta
kind: term
id: dia-util
aliases: [DU, "dias úteis", qtd_du]
```

Dia da semana excluindo sábado e domingo. Semana padrão (seg–sex) = 5 DU. Feriados por canal do bot ficam em `gold_serve.dim_chatbot_holidays`. O número de DU do período é parâmetro de entrada (`<qtd_du>`) de HC Líquido, Demanda por DU e Chamados/enc DU.

```yaml meta
kind: term
id: semana-de-referencia
aliases: [W15, W16, W17, "W<NN>", semana]
```

Convenção de nomeação das semanas de acompanhamento: `W<NN>` identifica uma semana corrida. As semanas citadas na base: W15 = 06–12/abr/2026, W16 = 13–19/abr/2026, W17 = 20–26/abr/2026.

```yaml meta
kind: term
id: mtd
aliases: [MTD, month-to-date, "MTD abril"]
```

Acumulado do mês até a data de corte (por exemplo 01–26/abr/2026, com 18 DU). Usado nas visões de produtividade dos encantadores.

```yaml meta
kind: term
id: ta-tempo-de-atendimento
aliases: [TA, sum_of_ta, "tempo de atendimento"]
quantified_by: tma
```

Tempo de atendimento acumulado, em segundos. A média é o TMA, calculado apenas nos canais online.

```yaml meta
kind: term
id: te-tempo-de-espera
aliases: [TE, sum_of_te, "tempo de espera"]
quantified_by: tme
```

Tempo de espera em fila acumulado, em segundos. A média é o TME, calculado apenas nos canais com fila.

```yaml meta
kind: term
id: tpr-tempo-de-primeira-resposta
aliases: [TPR, sum_of_tpr, count_of_tpr_ok, count_of_tpr_nok]
```

Tempo de primeira resposta. A `fact_service_metrics` traz o acumulado (`sum_of_tpr`) e a contagem de tickets dentro (`count_of_tpr_ok`) e fora (`count_of_tpr_nok`) do SLA. Não há KPI de TPR definido nesta base.

```yaml meta
kind: term
id: sla-tme
aliases: ["SLA TME", "SLA TME (<3 min)"]
quantified_by: sla-tme-3min
```

Percentual da demanda com tempo médio de espera abaixo de 180 segundos (3 minutos).

```yaml meta
kind: term
id: suporte-premium
aliases: ["Suporte Premium", SP, has_premium_support]
```

Flag de contrato de suporte premium. Na segmentação: `TRUE` = "Possui Suporte Premium", `FALSE` = "Não Possui Suporte Premium", NULL = "Não Identificado".

```yaml meta
kind: term
id: categoria-cami
aliases: ["macro tema", "mt_*", "categoria do bot"]
```

Categoria temática de uma interação do Cami, derivada por `LIKE` das tags do Zendesk (`silver_serve.ingestion_zendesk_tickets.tags`). Categorias: Configuração e Emissão de Notas Fiscais, Não Identificado, Retenção, Vendas, Fiscal, Financeiro, Serviços Financeiros, Contabilidade, Cross, Cobrança de chamado, Desistente, Falar com atendente e `NA` (resíduo).

```yaml meta
kind: term
id: categoria-telefone
aliases: [ticket_category, "Categorias Telefone"]
```

Categoria do ticket na `dim_zendesk_tickets_detailed`, usada na visão por categoria do canal Telefone (ex.: "billing dono de negócio", "conciliação", "emissão de nfse", "integração bancária", "emissão de nfe", "financeiro", "sac_0800", "plataforma").

```yaml meta
kind: term
id: negociacao-billing-dn
aliases: [negociação, "Billing Dono de Negócio", "Billing DN"]
scoped_by: escopo-categoria-billing-dono-de-negocio
quantified_by: billing-dn-negociacao
```

Atendimento de billing do dono do negócio, tratado pela BACKING_OPS, que envolveu tentativa de retenção: `subclassification IN ('retido','retenção')` **ou** `servir_churn_type IS NOT NULL`.

```yaml meta
kind: term
id: retido-billing-dn
aliases: [retido, retenção, "não retido"]
quantified_by: billing-dn-retidos
```

No contexto de Billing DN, **retido** é o atendimento com `subclassification IN ('retido','retenção')` (cliente mantido na base); **não retido** é a negociação que não terminou nessa subclassificação. Não confundir com retenção do bot.

```yaml meta
kind: term
id: rps
aliases: [RPS, "acompanhamento semanal"]
```

Relatório periódico semanal de acompanhamento do Atendimento, organizado em Blended / PME / Parceiros / Telefone / Billing DN. A estrutura de apresentação do relatório está fora do escopo desta camada.

## 7. Notas

```yaml meta
kind: note
id: arquitetura-camadas-data-lake
```

Linhagem das fontes (bronze → silver → gold), conforme declarado na base:

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

Projeto BigQuery: `contaazul-ssbi`. Modelo Looker: `serve_data_mart` (label "Servir"). Dataset principal: `contaazul-ssbi.gold_serve`.

```yaml meta
kind: note
id: placeholders-de-periodo-nas-queries
```

Todas as queries usam placeholders textuais `'<inicio>'`, `'<fim>'` e `<qtd_du>` — **não** parâmetros nomeados do BigQuery (`@inicio`/`@fim`). As SQLs foram copiadas verbatim, então esses placeholders precisam ser substituídos antes da execução. Note também que a janela da `fact_service_metrics` aparece nas duas formas — `DATE(nk_event_date) BETWEEN ...` e `nk_event_date BETWEEN ...` — conforme a query original de cada relatório.

```yaml meta
kind: note
id: areas-presentes-por-canal
```

Áreas efetivamente observadas em cada canal da `fact_service_metrics` (descobertas em validação): Whatsapp = BK, DN, EC, RT; Chat = BK, DN, EC, RT; Telefone = DN, EC, SAC - CA, SAC - Pessoalize, Ouvidoria - IP; Web = BK, DN, EC, ENG, N/I, RT, SDM, TRAINING, BACKING_OPS, OUVIDORIA; Email = BK, DN. Consequência prática: o filtro padrão de áreas remove conteúdo sobretudo em Web e Telefone.

```yaml meta
kind: note
id: redundancia-definicao-vs-queries-validadas
```

A base documenta vários KPIs duas vezes: na seção de definições (expressão ou consulta **sem** filtro de período) e na seção de queries validadas (**com** janela de data). Pares redundantes preservados aqui: `rel-demanda-cami-e-telefone-sem-janela` ↔ `rel-demanda-total-semanal-cami-telefone`; `rel-demanda-humana-recebida-por-canal-sem-janela` ↔ `rel-demanda-humana-por-canal`; `rel-csat-blended-pme-componentes-sem-janela` ↔ `rel-csat-blended-pme-e-parceiro`; `rel-retencao-cami-segmentos-sem-janela` ↔ `rel-retencao-cami-pme-e-parceiro`. Há ainda sobreposição entre `rel-abandono-cdp-vs-csp` e `rel-sla-tme-tma-abandono-por-segmento` (que já devolve `abandono_cdp`/`abandono_csp`) e entre `rel-billing-dono-de-negocio-negociacao` e `rel-billing-dono-de-negocio-taxa-retencao`. Em caso de dúvida, prefira a versão com janela de data.

```yaml meta
kind: note
id: metas-e-krs
```

Metas e KRs citados como referência do acompanhamento: Retenção Cami — meta 57% (o segmento Parceiros nunca a atingiu nas semanas registradas); CSAT Blended PME — meta 81,3%; SLA TME — meta 70%; CSAT Blended Parceiros — KR de abril 79,1% e KR de dezembro (meta final) 90%. São alvos de negócio, não valores calculados.

```yaml meta
kind: note
id: conteudo-descartado-na-conversao
```

Deliberadamente fora desta camada, por serem procedimento de apresentação, análise datada ou artefato de saída: a seção de geração de gráficos QuickChart.io (paleta de cores, configurações Chart.js, função Python `chart_url`, estrutura de bar chart, cores semáforo); a estrutura de seções da RPS e a lista de gráficos embutidos; as páginas Notion geradas (títulos, IDs e URLs); os insights datados W15/W16/W17 e as leituras executivas WoW/MoM; e todas as tabelas de validação por período (W16, W17, MTD abril) com valores calculados vs. dashboard, diffs e contagens de "N/N indicadores validados", incluindo os volumes por semana da tabela de Semanas de Referência. As **regras atemporais** que apareciam nesses trechos foram extraídas para armadilhas (NULLs de `customer_type` inflando Bot_Fin, divergência de Vendas/NA, "integração bancária" pendente, amostras pequenas por bot_type, abandono de Telefone vindo de NULL, obrigatoriedade do filtro de área para Parceiros, numerador compartilhado de chamados/encantador) e para termos (convenção `W<NN>`, períodos das semanas, MTD).
