---
kind: kb
id: suporte
domain: Atendimento e Suporte ao Cliente (ContaAzul) — demanda, CSAT, retenção de chatbot, SLA, FCR e NPS
schema_version: 2
bq_project: contaazul-ssbi
generated:
  by: kb-restructurer
  from: knowledge-bases/suporte/kb.md
  at: 2026-08-28
period_ref: "2026-04-06/2026-04-26"
sources:
  - id: dash-220
    resource: https://contaazul.cloud.looker.com/dashboards/220
    title: "[SUP_OFI] Gerencial 592"
  - id: dash-273
    resource: https://contaazul.cloud.looker.com/dashboards/273
    title: "[SUP_OFI] 275 Tickets Detail"
  - id: dash-210
    resource: https://contaazul.cloud.looker.com/dashboards/210
    title: "[SUP_OFI] Chatbots"
---

# Camada semântica — Conhecimento Domínio Atendimento (ContaAzul)

Modelo Looker `serve_data_mart` (label "Servir"); dataset principal `contaazul-ssbi.gold_serve`.
Reexpressão estruturada do `kb.md` de 28/08/2026 — nenhum fato novo, nenhuma SQL alterada.

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
lineage: "bronze_tool_zendesk_events → silver_serve.ingestion_zendesk_* → silver_serve.zendesk_tickets_detailed; capacidade via silver_serve.agent_capacity (team = 'Servir') → PDT pdt_agent_capacity_agg (inline no SQL Looker) → gold_serve.fact_service_metrics"
columns:
  - {name: nk_event_date, type: DATE, desc: "Data do evento"}
  - {name: event_hour, type: INTEGER, desc: "Hora do evento"}
  - {name: channel, type: STRING, desc: "Canal do atendimento humano; inclui '' (string vazia)", values: ["Chat", "Email", "Telefone", "Web", "Whatsapp", ""]}
  - {name: area, type: STRING, desc: "Área do encantador", values: ["BK", "DN", "EC", "SAC - CA", "SAC - Pessoalize", "Ouvidoria - IP", "RT", "ENG", "N/I", "SDM", "TRAINING", "BACKING_OPS", "OUVIDORIA"]}
  - {name: nk_email, type: STRING, desc: "E-mail do encantador"}
  - {name: squad, type: STRING, desc: "Time por matriz de produto"}
  - {name: leader, type: STRING, desc: "Líder do encantador"}
  - {name: sub_leader, type: STRING, desc: "Sub-líder do encantador"}
  - {name: sac_theme, type: STRING, desc: "Tema que o cliente selecionou para falar com o SAC"}
  - {name: tool, type: STRING, desc: "Ferramenta de origem da demanda"}
  - {name: customer_type, type: STRING, desc: "Tipo de cliente; não existe valor literal 'PME'", values: ["Parceiro", "Cliente do Parceiro", "Cliente sem Parceiro", "N/I"], nullable: true}
  - {name: partner_profile, type: STRING, desc: "Perfil do parceiro contábil; NULL quando não é Parceiro", values: ["CONTADOR", "BPO", "MISTO"], nullable: true}
  - {name: has_premium_support, type: BOOLEAN, desc: "Possui suporte premium", nullable: true}
  - {name: is_partner, type: BOOLEAN, desc: "É parceiro"}
  - {name: partner_level, type: STRING, desc: "Nível de parceria"}
  - {name: is_under_6m, type: BOOLEAN, desc: "Menos de 6 meses de vida", nullable: true}
  - {name: count_of_demanded, type: INTEGER, desc: "Chamados recebidos (atendidos + abandonados)"}
  - {name: count_of_abandoned, type: INTEGER, desc: "Chamados abandonados"}
  - {name: count_of_attended, type: INTEGER, desc: "Chamados atendidos"}
  - {name: count_of_positive_ratings, type: INTEGER, desc: "Avaliações positivas"}
  - {name: count_of_negative_ratings, type: INTEGER, desc: "Avaliações negativas"}
  - {name: sum_of_ta, type: INTEGER, desc: "Tempo total de atendimento", unit: seconds}
  - {name: sum_of_te, type: INTEGER, desc: "Tempo total de espera", unit: seconds}
  - {name: sum_of_tpr, type: INTEGER, desc: "Tempo total de primeira resposta", unit: seconds}
  - {name: count_of_tpr_ok, type: INTEGER, desc: "Tickets com TPR dentro do SLA"}
  - {name: count_of_tpr_nok, type: INTEGER, desc: "Tickets com TPR fora do SLA"}
pitfalls: [ouvidoria-ip-e-rt-fora-do-filtro, tma-tme-so-em-canais-online, demanda-recebida-diferente-de-atendida, web-tem-areas-extras, parceiros-exige-filtro-de-area, channel-vazio-entra-no-abandono, diferente-de-parceiro-nao-e-pme, partner-profile-nao-particiona-base, sla-tme-usa-menor-ou-igual, tabelas-reprocessadas-retroativamente, anomalia-channel-vazio-abril-2026, abandono-telefone-vem-de-customer-type-nulo]
provenance: [dash-220]
```

Fato de métricas diárias de atendimento **humano** (Zendesk). Áreas presentes variam por canal:
Whatsapp/Chat têm BK, DN, EC, RT; Telefone tem DN, EC, SAC - CA, SAC - Pessoalize, Ouvidoria - IP;
Web tem muitas áreas extras; Email só BK e DN; e existe `channel = ''` dentro do filtro de área padrão.

```yaml meta
kind: source
id: dim_chatbot
table: contaazul-ssbi.gold_serve.dim_chatbot
layer: gold
grain: [thread_uid, csat_type]
date_column: nk_date
date_type: DATE
partition: nk_date
cluster: [channel, team]
looker_explore: dim_blip_messages
lineage: "bronze_tool_blip / bronze_app_supercami → silver_serve.ingestion_blip_supercami_* + ingestion_takeblip_* → gold_serve.dim_chatbot"
columns:
  - {name: nk_date, type: DATE, desc: "Data do registro"}
  - {name: event_hour, type: INTEGER, desc: "Hora do evento"}
  - {name: channel, type: STRING, desc: "Canal; grafia exata e case-sensitive — é 'Ios', não 'iOS'", values: ["Whatsapp", "Chat", "Ios", "Android"]}
  - {name: team, type: STRING, desc: "Produto", values: ["CA Mais", "CA Pro", "Conta PJ"]}
  - {name: subject, type: STRING, desc: "Assunto da interação"}
  - {name: subcategory, type: STRING, desc: "Subcategoria temática da interação — categorização nativa, mais de 25 valores"}
  - {name: bot_type, type: STRING, desc: "Tipo de bot", values: ["Gen2", "Gen3 CA Mais", "Gen3 CA Pro", "Bot_Fin"]}
  - {name: bot_departament, type: STRING, desc: "Departamento do fluxo; linhas NULL têm 0 interações", values: ["Servir", "Retenção"], nullable: true}
  - {name: csat_type, type: STRING, desc: "Tipo de avaliação da sessão", values: ["N/I", "csat_retidos", "csat_transbordados"]}
  - {name: csat_bot_comment, type: STRING, desc: "Comentário deixado na avaliação do bot"}
  - {name: open_offline, type: BOOLEAN, desc: "Conversa abriu ticket offline (só interações vindas do Intercom)"}
  - {name: is_gen3, type: BOOLEAN, desc: "É fluxo Gen3"}
  - {name: nk_company_id, type: INTEGER, desc: "ID da empresa (−1 se indisponível)"}
  - {name: nk_accountancy_id, type: INTEGER, desc: "ID do escritório contábil (−1 se indisponível) — parte da chave de contatos únicos"}
  - {name: customer_type, type: STRING, desc: "Tipo de cliente; não existe valor literal 'PME' e não há NULL (jun–jul/2026)", values: ["Parceiro", "Cliente do Parceiro", "Cliente sem Parceiro", "N/I"]}
  - {name: partner_profile, type: STRING, desc: "Perfil do parceiro contábil; NULL quando não é Parceiro (~68% das linhas)", values: ["CONTADOR", "BPO", "MISTO"], nullable: true}
  - {name: partner_level, type: STRING, desc: "Nível do parceiro no Programa de Parceria"}
  - {name: has_premium_support, type: BOOLEAN, desc: "Possui suporte premium"}
  - {name: is_partner, type: BOOLEAN, desc: "É parceiro"}
  - {name: is_under_6m, type: BOOLEAN, desc: "Cliente com menos de 6 meses de vida na abertura"}
  - {name: thread_uid, type: STRING, desc: "ID único da conversa"}
  - {name: sum_of_interactions, type: INTEGER, desc: "Nº de interações (= 1 por linha)"}
  - {name: sum_of_transfers, type: INTEGER, desc: "Transbordos para humano"}
  - {name: sum_of_final_bot, type: INTEGER, desc: "Campo morto — soma sempre 0"}
  - {name: sum_of_positive_ratings, type: INTEGER, desc: "Avaliações positivas"}
  - {name: sum_of_negative_ratings, type: INTEGER, desc: "Avaliações negativas"}
  - {name: sum_of_total_ratings, type: INTEGER, desc: "Total de avaliações (= positivas + negativas, verificado)"}
  - {name: sum_of_positive_ratings_gen3, type: INTEGER, desc: "Avaliações positivas geradas pela IA Gen3"}
  - {name: sum_of_negative_ratings_gen3, type: INTEGER, desc: "Avaliações negativas geradas pela IA Gen3"}
  - {name: sum_of_total_ratings_gen3, type: INTEGER, desc: "Total de avaliações Gen3"}
pitfalls: [bot-fin-nao-e-cami, csat-type-cria-multiplas-linhas, demanda-cami-inclui-todos-csat-type, sum-of-final-bot-sempre-zero, subcategory-e-mais-barata-que-tags, partner-profile-nao-particiona-base, contatos-unicos-usa-duas-colunas, diferente-de-parceiro-nao-e-pme, parceiro-em-dim-chatbot-com-not-in-inclui-ni, canal-ios-grafia-exata, bot-departament-null-nao-e-bot-fin, gen2-praticamente-extinto, sum-of-total-ratings-como-denominador, tabelas-reprocessadas-retroativamente, fin-ai-concentra-as-avaliacoes-cami, customer-type-null-em-dim-chatbot-abril-2026, volume-de-avaliacoes-cami-muda-com-reprocessamento]
provenance: [dash-210]
```

Interações diárias dos chatbots (Cami/SuperCami — Blip/Takeblip/Ultimate); 1 linha = 1 interação/sessão.
Em jul/2026 o departamento Servir tem 42.135 interações, 99% delas do `Bot_Fin` (41.772).

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
lineage: "bronze_tool_zendesk_events → silver_serve.ingestion_zendesk_tickets + _chats + _whatsapp + _web + _email → silver_serve.zendesk_tickets_detailed → gold_serve.dim_zendesk_tickets_detailed"
columns:
  - {name: id, desc: "ID do ticket"}
  - {name: nk_date, type: DATETIME, desc: "Data do ticket (partição mensal)"}
  - {name: nk_company_id, desc: "ID da empresa"}
  - {name: assignee_email, desc: "E-mail do responsável"}
  - {name: assignee_name, desc: "Nome do responsável"}
  - {name: assignee_area, desc: "Área do responsável — equivalente a 'area' da fact_service_metrics"}
  - {name: channel, desc: "Canal do ticket"}
  - {name: ticket_category, desc: "Categoria do ticket"}
  - {name: ticket_subcategory, desc: "Subcategoria do ticket"}
  - {name: ticket_level, desc: "Nível do ticket"}
  - {name: departament, desc: "Departamento"}
  - {name: attendance_type, desc: "Tipo de atendimento"}
  - {name: status, desc: "Status do ticket"}
  - {name: online_service_time, desc: "Tempo de atendimento online", unit: seconds}
  - {name: online_waiting_time, desc: "Tempo de espera online", unit: seconds}
  - {name: tags, desc: "Tags do ticket"}
  - {name: is_incomplete, desc: "Ticket incompleto"}
  - {name: is_charge, desc: "Ticket de cobrança"}
  - {name: customer_type, desc: "Tipo de cliente"}
  - {name: has_premium_support, desc: "Possui suporte premium"}
  - {name: is_partner, desc: "É parceiro"}
  - {name: is_service_metrics, desc: "Marca o ticket como parte das métricas de atendimento — filtro usado na visão por categoria"}
  - {name: source_solved_at, desc: "Data de solução na origem; NULL exige fallback para nk_date"}
  - {name: current_rating, desc: "Avaliação do ticket; 'good' conta como CSAT positivo"}
  - {name: subclassification, desc: "Subclassificação do atendimento; 'retido'/'retenção' marcam retenção em Billing DN"}
  - {name: servir_churn_type, desc: "Tipo de churn registrado pelo Servir; não-NULL indica negociação"}
pitfalls: [fallback-source-solved-at-em-tickets, integracao-bancaria-com-diff-pendente, billing-dn-fonte-oficial-pode-estar-defasada, parceiros-exige-filtro-de-area]
provenance: [dash-273]
```

Todos os tickets do Zendesk com detalhamento completo. Usada na visão por categoria do Telefone
e em Billing Dono de Negócio (com `assignee_area = 'BACKING_OPS'`).

```yaml meta
kind: source
id: dim_date
table: contaazul-ssbi.gold_common.dim_date
layer: gold
grain: [nk_date]
date_column: nk_date
date_type: DATE
columns:
  - {name: nk_date, type: DATE, desc: "Data"}
  - {name: national_work_day, desc: "Marca dia útil nacional (exclui fim de semana e feriado nacional) — base de dim_date.is_work_day e dim_date.total_work_days no Looker"}
  - {name: day_name, desc: "Nome do dia da semana em português", values: ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]}
pitfalls: [du-derive-da-dim-date, dim-chatbot-holidays-sem-linhas-de-2026]
```

Dimensão calendário — JOIN por `nk_date`. É a fonte correta de dias úteis (`national_work_day`),
definida em `repos/looker/0-Common/views/dim_date.view.lkml:195` e `:210`.

```yaml meta
kind: source
id: dim_chatbot_holidays
table: contaazul-ssbi.gold_serve.dim_chatbot_holidays
layer: gold
date_column: nk_date
columns:
  - {name: nk_date, desc: "Data do feriado naquele canal"}
  - {name: channel, desc: "Canal ao qual o feriado se aplica", values: ["Chat", "Web", "Whatsapp"]}
  - {name: is_holiday, desc: "Dimensão LookML cujo sql é '${TABLE}.nk_date is null' — 'Yes' significa NÃO é feriado"}
pitfalls: [dim-chatbot-holidays-sem-linhas-de-2026, is-holiday-label-invertido]
```

Feriados por canal, usada no join de dia útil da retenção Cami. Tem **32 linhas**, de 12/02/2024 a
20/11/2025, só nos canais Chat, Web e Whatsapp — nenhuma linha de 2026.

```yaml meta
kind: source
id: agent_capacity
table: contaazul-ssbi.silver_serve.agent_capacity
layer: silver
date_column: event_date
columns:
  - {name: event_date, desc: "Data"}
  - {name: team, desc: "Time do encantador; o escopo de Atendimento é 'Servir'"}
  - {name: is_active_workday, type: NUMERIC, desc: "Fração de dia útil ativo do encantador — decimal, NÃO booleano"}
  - {name: capacity, desc: "Capacidade do encantador (numerador do FTE)"}
pitfalls: [is-active-workday-e-numeric-nao-cast, du-derive-da-dim-date]
```

Capacidade dos encantadores. Alimenta o PDT `pdt_agent_capacity_agg` (inline no SQL do Looker)
e é a fonte de HC Líquido e FTE.

```yaml meta
kind: source
id: dim_active_companies_by_month
table: contaazul-ssbi.gold_common.dim_active_companies_by_month
layer: gold
columns:
  - {name: nk_month, desc: "Mês de referência — JOIN com date_trunc(nk_event_date, month)"}
  - {name: total_active_companies_by_day, desc: "Base ativa por dia — denominador correto da densidade de demanda"}
  - {name: total_active_companies, desc: "Base ativa do mês — NÃO é o denominador da densidade"}
pitfalls: [densidade-usa-total-active-companies-by-day]
```

Base ativa CAPRO por mês; usada apenas como denominador da densidade de demanda.

```yaml meta
kind: source
id: vw_rps_fcr_semanal
table: contaazul-ssbi.tmp_servir.vw_rps_fcr_semanal
grain: [semana_inicio, tipo, categoria]
date_column: semana_inicio
date_type: DATE
columns:
  - {name: semana_inicio, type: DATE, desc: "Primeiro dia da semana"}
  - {name: semana_fim, type: DATE, desc: "Último dia da semana"}
  - {name: semana_label, type: STRING, desc: "Rótulo da semana"}
  - {name: tipo, type: STRING, desc: "Origem do atendimento; o FCR de atendimento é o humano", values: ["humano", "bot"]}
  - {name: categoria, type: STRING, desc: "Categoria do atendimento — 28 valores no humano", nullable: true}
  - {name: numerador, type: INT, desc: "Atendimentos resolvidos no primeiro contato"}
  - {name: denominador, type: INT, desc: "Total de atendimentos"}
  - {name: fcr_pct, type: FLOAT, desc: "FCR já calculado por linha — não agregue com AVG"}
  - {name: nao_fcr_pct, type: FLOAT, desc: "Complemento do FCR por linha"}
pitfalls: [fcr-sem-tipo-humano, fcr-com-avg-fcr-pct, fcr-custa-2gb-por-execucao, fcr-do-bot-saltou-para-98, fcr-semanas-atravessam-o-mes]
```

**É uma view, não tabela** — escaneia 2,13 GB por execução, sem partição nem cluster.
Cobertura: 27/04/2025 a 16/08/2026.

```yaml meta
kind: source
id: fact_nps_survey
table: contaazul-ssbi.gold_nps.fact_nps_survey
layer: gold
grain: [sk_nps_survey]
date_column: nk_date
columns:
  - {name: nk_date, desc: "Data da resposta"}
  - {name: sk_nps_survey, desc: "Chave de unicidade da resposta — use esta, não nk_answer"}
  - {name: nk_answer, desc: "ID da resposta; só é único dentro de uma ferramenta"}
  - {name: nk_company, desc: "COALESCE de empresa e escritório contábil — depende do segment"}
  - {name: nps_classification, type: STRING, desc: "Classificação em português por faixa de nota", values: ["Promotor", "Neutro", "Detrator"]}
  - {name: nps_type, type: STRING, desc: "Tipo de pesquisa; 'Não identificado' cobre todo o histórico pré-2026", values: ["pNPS", "rNPS", "Não identificado"]}
  - {name: segment, type: STRING, desc: "CA Mais = parceiros contadores; CA Pro = donos de negócio (PME)", values: ["CA Mais", "CA Pro"]}
  - {name: survey_name_standard, desc: "Nome da campanha, ex.: '[Oficial_Pro] 2026 pNPS Ciclo 2'"}
  - {name: nps_tool, type: STRING, desc: "Ferramenta da pesquisa; só Survicate está viva", values: ["Survicate", "Tracksale", "IndeCX"]}
  - {name: nps_answer, desc: "Nota de 0 a 10"}
  - {name: nps_comment, desc: "Comentário livre"}
pitfalls: [pnps-ca-pro-agosto-2026-contaminado, nps-type-pnps-descarta-2025, unicidade-do-nps-e-sk-nps-survey, rnps-sem-base]
```

pNPS / rNPS — 1 linha = 1 resposta de pesquisa. Dataset é **`gold_nps`**, não `tmp`.
`NPS = (Promotores − Detratores) / total de respostas × 100`.

```yaml meta
kind: source
id: ingestion_zendesk_tickets
table: contaazul-ssbi.silver_serve.ingestion_zendesk_tickets
layer: silver
columns:
  - {name: id, desc: "ID do ticket — join com dim_chatbot.thread_uid (Gen3/Ultimate)"}
  - {name: tags, desc: "Tags do ticket; origem das categorias temáticas 'mt_*' e 'bot_ultimate_macro_tema_*'"}
  - {name: intercom_conversation_id, desc: "ID da conversa no Intercom — join com dim_chatbot.thread_uid (Bot_Fin)"}
pitfalls: [subcategory-e-mais-barata-que-tags, categoria-vendas-e-na-com-divergencia]
```

Fonte das tags do Zendesk usadas na visão por categoria da Cami. Interações sem ticket Zendesk
(retidas sem tag) caem em `NA`.

```yaml meta
kind: source
id: dim_company
table: contaazul-ssbi.gold_common.dim_company
layer: gold
```

Dados das empresas clientes. Listada como tabela de apoio; nenhuma query da KB a usa.

```yaml meta
kind: source
id: dim_accountancy
table: contaazul-ssbi.gold_common.dim_accountancy
layer: gold
```

Dados dos parceiros/contadores. Listada como tabela de apoio; nenhuma query da KB a usa.

---

## 2. Políticas

```yaml meta
kind: policy
id: escopo-servir
title: Escopo do chatbot — departamento Servir
severity: blocking
applies_to: [dim_chatbot]
predicate:
  dim_chatbot: "bot_departament = 'Servir'"
rationale: "Servir é o fluxo de suporte principal; 'Retenção' é o fluxo de retenção de clientes e não entra nas métricas de Atendimento."
if_omitted: "Entra o fluxo de Retenção (6.712 interações de Bot_Fin em jul/2026 contra 41.772 do Servir), inflando demanda, CSAT e retenção com um produto diferente."
```

Filtro presente em praticamente toda query de `dim_chatbot`. **Não** acompanhado de filtro de
`bot_type` nem de `csat_type` quando o objetivo é demanda total.

```yaml meta
kind: policy
id: escopo-area-atendimento
title: Escopo de área do Atendimento humano
severity: blocking
applies_to: [fact_service_metrics, dim_zendesk_tickets_detailed]
predicate:
  fact_service_metrics: "area IN ('BK', 'DN', 'EC', 'SAC - CA', 'SAC - Pessoalize')"
  dim_zendesk_tickets_detailed: "assignee_area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')"
rationale: "Delimita as áreas que compõem o Atendimento; Ouvidoria - IP e RT (Retenção) são operações separadas, e o canal Web carrega áreas de outras engenharias/ops."
if_omitted: "Entram RT, N/I, BACKING_OPS, ENG, SDM, TRAINING e OUVIDORIA. Em métricas de Parceiro isso infla sum_of_te e count_of_demanded e o TME sai 4–5x maior que o real."
```

A mesma regra usa `area` na `fact_service_metrics` e `assignee_area` na
`dim_zendesk_tickets_detailed` — por isso o predicado é indexado por fonte.

```yaml meta
kind: policy
id: escopo-csat-retidos
title: Avaliações do bot — apenas clientes retidos
severity: blocking
applies_to: [dim_chatbot]
predicate:
  dim_chatbot: "csat_type = 'csat_retidos'"
rationale: "O CSAT da Cami é medido sobre o cliente que o bot resolveu (retido); 'csat_transbordados' avalia quem foi para o humano e 'N/I' é sessão sem avaliação."
if_omitted: "Mistura avaliações de retidos e transbordados e multiplica linhas por thread (até 3), distorcendo a nota."
```

Aplica-se a CSAT Cami e ao volume de avaliações — não à demanda.

```yaml meta
kind: policy
id: escopo-sessoes-unicas
title: Contagem de sessões únicas do chatbot
severity: advisory
applies_to: [dim_chatbot]
predicate:
  dim_chatbot: "csat_type = 'N/I'"
rationale: "Cada thread pode gerar até 3 linhas (N/I + csat_retidos + csat_transbordados); a linha N/I é a que representa a sessão."
if_omitted: "Sessões com avaliação são contadas 2 ou 3 vezes."
```

Só para **contar sessões**. Para demanda (`SUM(sum_of_interactions)`) o correto é **não** filtrar
`csat_type`, porque a soma já é consistente entre as linhas.

```yaml meta
kind: policy
id: escopo-canais-online
title: Canais com atendimento humano online (fila)
severity: blocking
applies_to: [fact_service_metrics]
predicate:
  fact_service_metrics: "channel IN ('Whatsapp','Telefone','Chat')"
rationale: "Só esses canais têm tempo de atendimento e de espera; Email e Web não têm TA/TE."
if_omitted: "Email e Web entram com TA/TE vazio e derrubam artificialmente TMA, TME e SLA TME."
```

Usada em TMA, TME e SLA TME. Aparece na KB em duas ordens (`'Whatsapp','Telefone','Chat'` e
`'Whatsapp','Chat','Telefone'`) — é a mesma regra.

```yaml meta
kind: policy
id: escopo-canais-humanos
title: Canais da demanda humana
severity: blocking
applies_to: [fact_service_metrics]
predicate:
  fact_service_metrics: "channel IN ('Chat','Email','Telefone','Web','Whatsapp')"
rationale: "Conjunto dos cinco canais de atendimento humano usados no tile 'Demanda humana por canal'."
if_omitted: "Entram linhas com channel = '' (string vazia), que são 100% abandono e inflam a demanda humana."
```

Note a tensão deliberada com `channel-vazio-entra-no-abandono`: a demanda por canal filtra canal,
mas a measure oficial de **abandono** não.

```yaml meta
kind: policy
id: escopo-canal-telefone
title: Recorte do canal Telefone
severity: blocking
applies_to: [fact_service_metrics, dim_zendesk_tickets_detailed]
predicate:
  fact_service_metrics: "channel = 'Telefone'"
  dim_zendesk_tickets_detailed: "channel = 'Telefone'"
rationale: "O componente de voz da Demanda Total e todas as visões de Telefone (macro, categoria, suporte premium) usam este recorte."
```

Sempre combinado com `escopo-area-atendimento`.

```yaml meta
kind: policy
id: escopo-capacidade-servir
title: Capacidade — time Servir
severity: blocking
applies_to: [agent_capacity]
predicate:
  agent_capacity: "team = 'Servir'"
rationale: "O PDT de capacidade do Looker filtra team = 'Servir'; é o time de Atendimento."
```

Base de HC Líquido e FTE.

```yaml meta
kind: policy
id: escopo-dias-uteis-nacionais
title: Dias úteis vêm da dim_date
severity: blocking
applies_to: [dim_date]
predicate:
  dim_date: "national_work_day"
rationale: "É como o Looker conta (dim_date.total_work_days filtrado por dim_date.is_work_day, que é gold_common.dim_date.national_work_day); já exclui fim de semana e feriado nacional."
if_omitted: "Contar 'seg a sex' na mão superestima o período: 01–26/abr/2026 tem 16 DU e não 18, e o HC Líquido sai 54 em vez de 61,63."
```

Denominador de toda métrica "por DU" e do HC Líquido.

```yaml meta
kind: policy
id: escopo-dia-util-retencao
title: Dia útil por canal na retenção Cami (regra do tile KPI)
severity: blocking
applies_to: [dim_chatbot]
predicate:
  dim_chatbot: "((dd.day_name NOT IN ('Domingo','Sábado') OR dd.day_name IS NULL) AND h.nk_date IS NULL)"
rationale: "É o que o tile 'Retenção' (id 5691) do dashboard 210 faz: dim_date.day_name -Sábado,-Domingo + dim_chatbot_holidays.is_holiday: Yes. No fim de semana não há encantador para receber transbordo, então a retenção fica artificialmente em ~96% (vs ~57% em dia útil, mai–jul/26) e a métrica não significa nada ali."
if_omitted: "Vira a 'retenção observada' dos tiles de detalhe — 0,5 a 1,2pp mais alta ao mês. Numa janela segunda a sexta as duas regras dão o mesmo número."
```

Implementada por LEFT JOIN em `dim_date` (por data) e `dim_chatbot_holidays` (por canal **e** data).
O join de feriado está inerte em 2026 — ver `dim-chatbot-holidays-sem-linhas-de-2026`.

```yaml meta
kind: policy
id: segmento-pme
title: Segmento PME
severity: blocking
applies_to: [fact_service_metrics, dim_chatbot]
predicate:
  dim_chatbot: "customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro')"
  fact_service_metrics: "customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro')"
rationale: "PME = Cliente do Parceiro (CDP) + Cliente sem Parceiro (CSP). Não existe valor literal 'PME' em nenhuma das duas tabelas."
if_omitted: "Usar customer_type != 'Parceiro' infla o PME em ~11% no dim_chatbot (49.971 em vez de 44.876) e ~4% na fact_service_metrics, porque inclui o valor 'N/I'."
```

Definição correta e recomendada. As queries históricas da KB usam `!= 'Parceiro'` — ver
`segmento-pme-legado`.

```yaml meta
kind: policy
id: segmento-pme-legado
title: Segmento PME — definição legada por exclusão
severity: advisory
applies_to: [fact_service_metrics]
predicate:
  fact_service_metrics: "customer_type != 'Parceiro'"
rationale: "Várias queries validadas da KB usam esta forma e por isso reproduzem os números históricos dos dashboards."
if_omitted: "Trocar por segmento-pme muda o resultado: espere um número ~4% menor na fact_service_metrics, porque 'N/I' (1.702 chamados em jun–jul/2026) deixa de entrar."
```

Mantida porque é o que está nas queries validadas — **não** é a definição correta de PME.
Se a pergunta for sobre PME de verdade, prefira `segmento-pme`.

```yaml meta
kind: policy
id: segmento-parceiro
title: Segmento Parceiro
severity: blocking
applies_to: [fact_service_metrics, dim_chatbot]
predicate:
  fact_service_metrics: "customer_type = 'Parceiro'"
  dim_chatbot: "customer_type = 'Parceiro'"
rationale: "Parceiro é o canal de parceiros contábeis, distinto dos sub-segmentos de PME."
```

Em métricas de tempo/SLA/abandono de Parceiro, combinar **obrigatoriamente** com
`escopo-area-atendimento` — ver `parceiros-exige-filtro-de-area`.

```yaml meta
kind: policy
id: segmento-cliente-do-parceiro
title: Sub-segmento PME — Cliente do Parceiro (CDP)
severity: blocking
applies_to: [fact_service_metrics, dim_chatbot]
predicate:
  fact_service_metrics: "customer_type = 'Cliente do Parceiro'"
  dim_chatbot: "customer_type = 'Cliente do Parceiro'"
rationale: "Sub-segmento de PME reportado separadamente na RPS (CSAT, SLA, TME, TMA e abandono)."
```

Cliente final que tem escritório contábil parceiro.

```yaml meta
kind: policy
id: segmento-cliente-sem-parceiro
title: Sub-segmento PME — Cliente sem Parceiro (CSP)
severity: blocking
applies_to: [fact_service_metrics, dim_chatbot]
predicate:
  fact_service_metrics: "customer_type = 'Cliente sem Parceiro'"
  dim_chatbot: "customer_type = 'Cliente sem Parceiro'"
rationale: "Sub-segmento de PME reportado separadamente na RPS (CSAT, SLA, TME, TMA e abandono)."
```

Cliente final sem escritório contábil parceiro.

```yaml meta
kind: policy
id: escopo-fcr-humano
title: FCR é o atendimento humano
severity: blocking
applies_to: [vw_rps_fcr_semanal]
predicate:
  vw_rps_fcr_semanal: "tipo = 'humano'"
rationale: "FCR de atendimento é o humano; o bot é outra métrica, de outra coisa."
if_omitted: "O agregado sobe para 76,7% (contra 67,8% humano no mesmo corte); o bot sozinho dá 81,2%."
```

Obrigatório em qualquer leitura de FCR de atendimento.

```yaml meta
kind: policy
id: escopo-pnps
title: Recorte de pesquisa pNPS
severity: advisory
applies_to: [fact_nps_survey]
predicate:
  fact_nps_survey: "nps_type = 'pNPS'"
rationale: "Separa o pNPS do rNPS e do histórico não identificado."
if_omitted: "Sem o filtro entram rNPS e 'Não identificado'."
```

⚠️ Usar esta policy **descarta silenciosamente todo o histórico de 2025** (16.011 respostas de
CA Pro + 2.293 de CA Mais). Para série longa, recorte por `segment` + `nk_date` e não filtre
`nps_type` — ver `nps-type-pnps-descarta-2025`.

```yaml meta
kind: policy
id: escopo-service-metrics
title: Tickets que compõem as métricas de atendimento
severity: blocking
applies_to: [dim_zendesk_tickets_detailed]
predicate:
  dim_zendesk_tickets_detailed: "is_service_metrics = TRUE"
rationale: "É o filtro que o dashboard usa na visão por categoria do Telefone."
```

Combinado com `escopo-canal-telefone` e `escopo-area-atendimento`.

```yaml meta
kind: policy
id: escopo-billing-dono-de-negocio
title: Escopo Billing Dono de Negócio
severity: blocking
applies_to: [dim_zendesk_tickets_detailed]
predicate:
  dim_zendesk_tickets_detailed: "LOWER(ticket_category) = 'billing dono de negócio' AND assignee_area = 'BACKING_OPS'"
rationale: "Replica no gold_serve o recorte do explore churn_data_mart → cancellation_tickets (silver_retention), que é a fonte oficial do Looker mas pode ter defasagem."
```

A data desta visão é `DATE(source_solved_at)`, não `nk_date`.

---

## 3. Métricas

```yaml meta
kind: measure
id: demanda-cami
title: Demanda Cami (autoatendimento)
source: dim_chatbot
unit: count
expr: SUM(sum_of_interactions)
policies: [escopo-servir]
direction: neutral
pitfalls: [demanda-cami-inclui-todos-csat-type, bot-fin-nao-e-cami, csat-type-cria-multiplas-linhas]
status: stable
provenance: [dash-210]
```

Interações de autoatendimento do bot. **Não** filtrar `csat_type` nem `bot_type` — o dashboard
oficial inclui o Bot_Fin, que hoje é 99% do volume.

```yaml meta
kind: measure
id: demanda-telefone
title: Demanda Telefone (voz)
source: fact_service_metrics
unit: count
expr: SUM(count_of_demanded)
policies: [escopo-canal-telefone, escopo-area-atendimento]
direction: neutral
pitfalls: [ouvidoria-ip-e-rt-fora-do-filtro, demanda-recebida-diferente-de-atendida]
status: stable
provenance: [dash-220]
```

Componente de voz humana da Demanda Total. Ouvidoria - IP e RT **não** entram.

```yaml meta
kind: measure
id: demanda-total
title: Demanda Total (Cami + Telefone)
unit: count
composed_of: [demanda-cami, demanda-telefone]
kind_of_measure: composite
direction: neutral
status: stable
provenance: [dash-220, dash-210]
```

Métrica principal do acompanhamento semanal: soma autoatendimento bot + voz humana.

```yaml meta
kind: measure
id: dias-uteis
title: Quantidade de dias úteis no período
source: dim_date
unit: count
expr: COUNT(DISTINCT nk_date)
policies: [escopo-dias-uteis-nacionais]
direction: neutral
pitfalls: [du-derive-da-dim-date]
status: stable
```

Julho/2026 tem 23 DU; uma semana padrão seg–sex sem feriado tem 5 DU; a W17 (20–26/abr/2026)
tem 4 DU porque 21/abr é Tiradentes.

```yaml meta
kind: measure
id: demanda-por-du
title: Demanda por DU (média por dia útil)
unit: ratio
composed_of: [demanda-total, dias-uteis]
kind_of_measure: derived
direction: neutral
pitfalls: [du-derive-da-dim-date]
status: stable
```

`Demanda por DU = Demanda Total / Qtd de Dias Úteis no Período`. Normaliza a demanda para
comparação WoW justa. **Não** é um filtro de dia útil — é divisão do total pelo nº de DU.

```yaml meta
kind: measure
id: demanda-humana-recebida
title: Demanda humana recebida por canal
source: fact_service_metrics
unit: count
expr: SUM(count_of_demanded)
policies: [escopo-canais-humanos, escopo-area-atendimento]
direction: neutral
pitfalls: [demanda-recebida-diferente-de-atendida, web-tem-areas-extras, channel-vazio-entra-no-abandono]
status: stable
provenance: [dash-220]
```

O tile "Demanda humana por canal" usa a demanda **recebida** (`count_of_demanded`),
não a atendida.

```yaml meta
kind: measure
id: demanda-humana-atendida
title: Demanda humana atendida
source: fact_service_metrics
unit: count
expr: SUM(count_of_attended)
policies: [escopo-area-atendimento]
direction: higher_is_better
pitfalls: [demanda-recebida-diferente-de-atendida, chamados-por-encantador-usa-total-de-todos-segmentos]
status: stable
```

Só os atendidos (exclui abandonos). É o numerador de "chamados por encantador", somando
**todos os segmentos**.

```yaml meta
kind: measure
id: demanda-abandonada
title: Demanda abandonada
source: fact_service_metrics
unit: count
expr: SUM(count_of_abandoned)
direction: lower_is_better
pitfalls: [channel-vazio-entra-no-abandono, anomalia-channel-vazio-abril-2026]
status: stable
```

`count_of_demanded − count_of_attended = count_of_abandoned`.

```yaml meta
kind: measure
id: csat-humano
title: CSAT Humano
source: fact_service_metrics
unit: ratio
expr: SUM(count_of_positive_ratings) / NULLIF(SUM(count_of_positive_ratings + count_of_negative_ratings), 0)
policies: [escopo-area-atendimento]
direction: higher_is_better
status: stable
provenance: [dash-220]
```

Positivas sobre o total avaliado (positivas + negativas). Segmentar com `segmento-pme`,
`segmento-parceiro` ou os sub-segmentos CDP/CSP.

```yaml meta
kind: measure
id: csat-cami
title: CSAT Cami
source: dim_chatbot
unit: ratio
expr: SUM(sum_of_positive_ratings) / NULLIF(SUM(sum_of_positive_ratings + sum_of_negative_ratings), 0)
policies: [escopo-servir, escopo-csat-retidos]
direction: higher_is_better
pitfalls: [csat-type-cria-multiplas-linhas, fin-ai-concentra-as-avaliacoes-cami, volume-de-avaliacoes-cami-muda-com-reprocessamento]
status: stable
provenance: [dash-210]
```

Nota do bot, medida só sobre clientes **retidos**.

```yaml meta
kind: measure
id: csat-cami-por-total-ratings
title: CSAT Cami com denominador sum_of_total_ratings
source: dim_chatbot
unit: ratio
expr: SUM(sum_of_positive_ratings) / NULLIF(SUM(sum_of_total_ratings), 0)
policies: [escopo-servir, escopo-csat-retidos]
direction: higher_is_better
pitfalls: [sum-of-total-ratings-como-denominador]
status: stable
```

Variante usada na quebra por `bot_type`. Equivale a `csat-cami` porque
`sum_of_total_ratings = positivas + negativas` (verificado) — o que **não** se pode usar como
denominador é `sum_of_interactions`.

```yaml meta
kind: measure
id: csat-blended
title: CSAT Blended (bot + humano)
unit: ratio
composed_of: [csat-humano, csat-cami]
kind_of_measure: composite
direction: higher_is_better
status: stable
provenance: [dash-220, dash-210]
```

"Blended" = avaliações do bot (Cami) + humano numa única nota:
`(humano_pos + cami_pos) / (humano_pos + humano_neg + cami_pos + cami_neg)`. Somam-se as
**contagens**, nunca as duas taxas.

```yaml meta
kind: measure
id: retencao-cami-kpi
title: Retenção Cami (Deflexão) — KPI oficial, dia útil
source: dim_chatbot
unit: ratio
expr: GREATEST(0, 1 - SAFE_DIVIDE(SUM(sum_of_transfers), SUM(sum_of_interactions)))
policies: [escopo-servir, escopo-dia-util-retencao]
direction: higher_is_better
pitfalls: [dashboard-duas-definicoes-retencao, dim-chatbot-holidays-sem-linhas-de-2026, sum-of-final-bot-sempre-zero, semanas-desta-kb-tem-7-dias, is-holiday-label-invertido]
status: stable
provenance: [dash-210]
```

% de interações que o bot resolveu sem transbordar. Definição autoritativa: measure
`dim_chatbot.pct_retention` (`repos/looker/1-SERVE/views/dim_chatbot.view.lkml:240`), como
consumida pelo tile "Retenção" (id 5691) do dashboard 210. **É a resposta padrão.**

```yaml meta
kind: measure
id: retencao-cami-observada
title: Retenção Cami observada (sem filtro de dia)
source: dim_chatbot
unit: ratio
expr: GREATEST(0, 1 - SAFE_DIVIDE(SUM(sum_of_transfers), SUM(sum_of_interactions)))
policies: [escopo-servir]
direction: higher_is_better
pitfalls: [dashboard-duas-definicoes-retencao, semanas-desta-kb-tem-7-dias]
status: stable
provenance: [dash-210]
```

Recorte dos tiles `Acumulado Mensal` (12073/12074/12086), `Detalhado *` e `Retenção por hora`.
Sempre **mais alta** que o KPI: 0,5 a 1,2pp ao mês. Numa janela seg–sex, idêntica ao KPI.

```yaml meta
kind: measure
id: contatos-unicos-chatbot
title: Contatos únicos do chatbot (clientes distintos)
source: dim_chatbot
unit: count
expr: COUNT(DISTINCT CONCAT(nk_company_id, nk_accountancy_id))
policies: [escopo-servir]
direction: neutral
pitfalls: [contatos-unicos-usa-duas-colunas, concat-sem-separador-tem-colisao]
status: stable
provenance: [dash-210]
```

Definição: measure `dim_chatbot.count_of_distinct_customers`
(`repos/looker/1-SERVE/views/dim_chatbot.view.lkml:274`). Medido em 08–12/jun/2026 (Servir,
canais Chat/Web/Whatsapp): **4.309** pela regra correta.

```yaml meta
kind: measure
id: tma
title: TMA — Tempo Médio de Atendimento
source: fact_service_metrics
unit: seconds
expr: SUM(sum_of_ta) / NULLIF(SUM(count_of_attended), 0)
policies: [escopo-canais-online]
direction: lower_is_better
pitfalls: [tma-tme-so-em-canais-online]
status: stable
provenance: [dash-220]
```

Denominador é o **atendido**. Resultado em segundos; dividir por 60 para minutos
(ex.: 2.706 seg = 45min 06seg). Fórmula verbatim do `kb.md`:

```sql
SUM(CASE WHEN channel IN ('Whatsapp','Telefone','Chat') THEN sum_of_ta END) /
NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Telefone','Chat') THEN count_of_attended END), 0)
-- resultado em segundos; dividir por 60 para minutos
-- Ex: 2.706 seg = 45min 06seg
```

```yaml meta
kind: measure
id: tme
title: TME — Tempo Médio de Espera
source: fact_service_metrics
unit: seconds
expr: SUM(sum_of_te) / NULLIF(SUM(count_of_demanded), 0)
policies: [escopo-canais-online]
direction: lower_is_better
pitfalls: [tma-tme-so-em-canais-online, parceiros-exige-filtro-de-area]
status: stable
provenance: [dash-220]
```

Denominador é o **demandado** (a espera existe para quem chegou, não só para quem foi atendido).
Fórmula verbatim do `kb.md`:

```sql
SUM(CASE WHEN channel IN ('Whatsapp','Telefone','Chat') THEN sum_of_te END) /
NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Telefone','Chat') THEN count_of_demanded END), 0)
-- resultado em segundos
```

```yaml meta
kind: measure
id: sla-tme-3min
title: SLA TME (≤ 3 min)
source: fact_service_metrics
unit: pct
expr: SUM(CASE WHEN (sum_of_te / NULLIF(count_of_demanded,0)) <= 180 THEN count_of_demanded END) / NULLIF(SUM(count_of_demanded), 0)
policies: [escopo-canais-online]
direction: higher_is_better
pitfalls: [sla-tme-usa-menor-ou-igual, lookml-nomes-mentem]
status: stable
provenance: [dash-220]
```

% de tickets com TME médio **menor ou igual a** 180 segundos. Definição: dimensão
`fact_service_metrics.sla_tme_3min` (`repos/looker/1-SERVE/views/fact_service_metrics.view.lkml:276`).
Fórmula verbatim do `kb.md`:

```sql
SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone')
         AND (sum_of_te / NULLIF(count_of_demanded,0)) <= 180
    THEN count_of_demanded END) /
NULLIF(SUM(CASE WHEN channel IN ('Whatsapp','Chat','Telefone') THEN count_of_demanded END), 0)
```

```yaml meta
kind: measure
id: sla-tme-5min
title: SLA TME (≤ 5 min)
source: fact_service_metrics
unit: pct
policies: [escopo-canais-online]
direction: higher_is_better
pitfalls: [sla-tme-usa-menor-ou-igual]
status: draft
status_reason: "sem query validada na KB; só é declarada a existência da dimensão sla_tme_5min com limiar <= 300"
```

Mesma construção do `sla-tme-3min`, trocando 180 por **300** segundos.

```yaml meta
kind: measure
id: percentual-abandono
title: % Abandono
source: fact_service_metrics
unit: pct
expr: SUM(count_of_abandoned) / NULLIF(SUM(count_of_demanded), 0)
direction: lower_is_better
pitfalls: [channel-vazio-entra-no-abandono, anomalia-channel-vazio-abril-2026, abandono-telefone-vem-de-customer-type-nulo]
status: stable
provenance: [dash-220]
```

Segmentar por `customer_type` para PME vs Parceiro. A measure oficial
`percent_of_abandoned` (`fact_service_metrics.view.lkml:401`) **não filtra canal** — por isso esta
measure também não tem policy de canal. Fórmula verbatim do `kb.md`:

```sql
SUM(count_of_abandoned) / NULLIF(SUM(count_of_demanded), 0)
-- Segmentar por customer_type para PME vs Parceiro
```

```yaml meta
kind: measure
id: hc-liquido
title: HC Líquido (média diária de encantadores ativos)
source: agent_capacity
unit: count
expr: ROUND(SUM(is_active_workday) / <qtd_du>, 2)
policies: [escopo-capacidade-servir]
composed_of: [dias-uteis]
kind_of_measure: derived
direction: neutral
pitfalls: [is-active-workday-e-numeric-nao-cast, du-derive-da-dim-date]
status: stable
```

`is_active_workday` é **NUMERIC (decimal)**, nunca `CAST(... AS INT64)`. O `<qtd_du>` vem da
`dim_date`. Recalculado em 28/08/2026 para 01–26/abr/2026 (16 DU): **61,63**.

```yaml meta
kind: measure
id: chamados-por-encantador-mes
title: Chamados atendidos por encantador (mês)
unit: ratio
composed_of: [demanda-humana-atendida, hc-liquido]
kind_of_measure: derived
direction: neutral
pitfalls: [chamados-por-encantador-usa-total-de-todos-segmentos, du-derive-da-dim-date]
status: stable
```

`total atendido / HC Líquido`. Numerador = `SUM(count_of_attended)` de **todos os segmentos**
(PME + Parceiro), porque o mesmo HC atende os dois.

```yaml meta
kind: measure
id: chamados-por-encantador-du
title: Chamados atendidos por encantador (por DU)
unit: ratio
composed_of: [demanda-humana-atendida, hc-liquido, dias-uteis]
kind_of_measure: derived
direction: neutral
pitfalls: [chamados-por-encantador-usa-total-de-todos-segmentos, du-derive-da-dim-date]
status: stable
```

`total atendido / HC Líquido / DU`.

```yaml meta
kind: measure
id: densidade-demanda
title: Densidade de Demanda
source: fact_service_metrics
unit: ratio
expr: SAFE_DIVIDE(SUM(count_of_demanded), MAX(dim_active_companies_by_month.total_active_companies_by_day))
direction: neutral
pitfalls: [densidade-usa-total-active-companies-by-day]
status: stable
```

Definição: measure `fact_service_metrics.density_tickets`
(`repos/looker/1-SERVE/views/fact_service_metrics.view.lkml:133`). JOIN:
`date_trunc(nk_event_date, month) = nk_month` de `dim_active_companies_by_month`.
Fórmula verbatim do `kb.md`:

```sql
SAFE_DIVIDE(SUM(count_of_demanded), MAX(dim_active_companies_by_month.total_active_companies_by_day))
-- JOIN: date_trunc(nk_event_date, month) = nk_month de dim_active_companies_by_month
```

```yaml meta
kind: measure
id: fte
title: FTE (Capacidade)
source: agent_capacity
unit: ratio
expr: SUM(capacity) / SUM(count_of_demanded)
policies: [escopo-capacidade-servir]
direction: neutral
status: stable
```

Capacidade sobre demanda; o numerador vem do PDT inline
(`silver_serve.agent_capacity WHERE team = 'Servir'`). Fórmula verbatim do `kb.md`:

```sql
-- PDT inline: silver_serve.agent_capacity WHERE team = 'Servir'
SUM(capacity) / SUM(count_of_demanded)
```

```yaml meta
kind: measure
id: fcr
title: FCR — Resolução no Primeiro Contato
source: vw_rps_fcr_semanal
unit: pct
expr: ROUND(100 * SAFE_DIVIDE(SUM(numerador), SUM(denominador)), 2)
policies: [escopo-fcr-humano]
direction: higher_is_better
pitfalls: [fcr-com-avg-fcr-pct, fcr-sem-tipo-humano, fcr-custa-2gb-por-execucao, fcr-semanas-atravessam-o-mes, fcr-do-bot-saltou-para-98]
status: stable
```

% dos atendimentos resolvidos sem o cliente precisar voltar. Sempre
`SUM(numerador)/SUM(denominador)`, **nunca** `AVG(fcr_pct)`.

```yaml meta
kind: measure
id: volume-avaliacoes-cami
title: Volume de avaliações da Cami
source: dim_chatbot
unit: count
expr: SUM(sum_of_total_ratings)
policies: [escopo-servir, escopo-csat-retidos]
direction: neutral
pitfalls: [fin-ai-concentra-as-avaliacoes-cami, volume-de-avaliacoes-cami-muda-com-reprocessamento]
status: stable
```

Denominador do CSAT Cami e base para julgar se uma quebra por `bot_type` tem amostra suficiente.

```yaml meta
kind: measure
id: nps
title: NPS (pNPS / rNPS)
source: fact_nps_survey
unit: pct
expr: ROUND(100 * SAFE_DIVIDE(COUNTIF(nps_classification = 'Promotor') - COUNTIF(nps_classification = 'Detrator'), COUNT(*)), 1)
policies: [escopo-pnps]
direction: higher_is_better
pitfalls: [pnps-ca-pro-agosto-2026-contaminado, nps-type-pnps-descarta-2025, unicidade-do-nps-e-sk-nps-survey, rnps-sem-base]
status: stable
```

`NPS = (Promotores − Detratores) / total de respostas × 100`. Quebrar por `segment`
(CA Pro = PME, CA Mais = parceiros contadores).

```yaml meta
kind: measure
id: respostas-por-empresa-nps
title: Respostas de NPS por empresa
source: fact_nps_survey
unit: ratio
expr: COUNT(*) / NULLIF(COUNT(DISTINCT nk_company), 0)
kind_of_measure: derived
direction: neutral
pitfalls: [pnps-ca-pro-agosto-2026-contaminado]
status: stable
```

Termômetro de contaminação da campanha: o normal é ~1,05 resposta por empresa; em ago/2026 o
CA Pro chegou a **2,98** (15.742 respostas de 5.290 empresas).

```yaml meta
kind: measure
id: telefone-categoria-interacoes
title: Interações por categoria de Telefone
source: dim_zendesk_tickets_detailed
unit: count
expr: COUNT(*)
policies: [escopo-canal-telefone, escopo-area-atendimento, escopo-service-metrics]
direction: neutral
pitfalls: [fallback-source-solved-at-em-tickets, integracao-bancaria-com-diff-pendente]
status: stable
provenance: [dash-273]
```

Contagem de tickets por `ticket_category`.

```yaml meta
kind: measure
id: telefone-categoria-mix
title: Mix de demanda por categoria de Telefone
source: dim_zendesk_tickets_detailed
unit: ratio
expr: COUNT(*) / SUM(COUNT(*)) OVER ()
policies: [escopo-canal-telefone, escopo-area-atendimento, escopo-service-metrics]
composed_of: [telefone-categoria-interacoes]
kind_of_measure: derived
direction: neutral
status: stable
```

Participação da categoria no total do período.

```yaml meta
kind: measure
id: telefone-categoria-csat
title: CSAT por categoria de Telefone
source: dim_zendesk_tickets_detailed
unit: ratio
expr: COUNTIF(current_rating = 'good') / NULLIF(COUNTIF(current_rating IS NOT NULL), 0)
policies: [escopo-canal-telefone, escopo-area-atendimento, escopo-service-metrics]
direction: higher_is_better
status: stable
provenance: [dash-273]
```

Aqui o CSAT vem de `current_rating = 'good'`, não de contadores de avaliação.

```yaml meta
kind: measure
id: telefone-categoria-tma
title: TMA por categoria de Telefone
source: dim_zendesk_tickets_detailed
unit: seconds
expr: AVG(online_service_time)
policies: [escopo-canal-telefone, escopo-area-atendimento, escopo-service-metrics]
direction: lower_is_better
status: stable
provenance: [dash-273]
```

Média simples de `online_service_time` (a query divide por 60 para exibir em minutos).

```yaml meta
kind: measure
id: interacao-total-telefone
title: Interação total atendida no Telefone
source: fact_service_metrics
unit: count
expr: SUM(count_of_attended)
policies: [escopo-canal-telefone, escopo-area-atendimento]
direction: neutral
status: stable
```

Base da segmentação de Suporte Premium (`has_premium_support`: TRUE / FALSE / NULL =
Não Identificado) e de tempo de casa.

```yaml meta
kind: measure
id: atendidos-mais-6m
title: Atendidos com +6 meses de casa
source: fact_service_metrics
unit: count
expr: SUM(CASE WHEN is_under_6m = FALSE OR is_under_6m IS NULL THEN count_of_attended END)
policies: [escopo-canal-telefone, escopo-area-atendimento]
direction: neutral
status: stable
```

O `IS NULL` conta como +6 meses — é assim que a segmentação da KB define.

```yaml meta
kind: measure
id: atendidos-menos-6m
title: Atendidos com -6 meses de casa
source: fact_service_metrics
unit: count
expr: SUM(CASE WHEN is_under_6m = TRUE THEN count_of_attended END)
policies: [escopo-canal-telefone, escopo-area-atendimento]
direction: neutral
status: stable
```

Complemento de `atendidos-mais-6m`.

```yaml meta
kind: measure
id: billing-dn-total
title: Billing DN — total de atendimentos
source: dim_zendesk_tickets_detailed
unit: count
expr: COUNT(DISTINCT id)
policies: [escopo-billing-dono-de-negocio]
direction: neutral
pitfalls: [billing-dn-fonte-oficial-pode-estar-defasada]
status: stable
```

Tickets distintos de Billing Dono de Negócio, por `DATE(source_solved_at)`.

```yaml meta
kind: measure
id: billing-dn-negociacao
title: Billing DN — negociações
source: dim_zendesk_tickets_detailed
unit: count
expr: COUNTIF(subclassification IN ('retido','retenção') OR servir_churn_type IS NOT NULL)
policies: [escopo-billing-dono-de-negocio]
direction: neutral
status: stable
```

Atendimento que virou negociação de retenção.

```yaml meta
kind: measure
id: billing-dn-retidos
title: Billing DN — retidos
source: dim_zendesk_tickets_detailed
unit: count
expr: COUNTIF(subclassification IN ('retido','retenção'))
policies: [escopo-billing-dono-de-negocio]
direction: higher_is_better
status: stable
```

Negociações que terminaram com o cliente mantido na base.

```yaml meta
kind: measure
id: billing-dn-nao-retido
title: Billing DN — não retidos
source: dim_zendesk_tickets_detailed
unit: count
expr: COUNTIF(servir_churn_type IS NOT NULL AND COALESCE(subclassification,'') NOT IN ('retido','retenção'))
policies: [escopo-billing-dono-de-negocio]
direction: lower_is_better
status: stable
```

Negociação que **não** resultou em `subclassification` retido/retenção.

```yaml meta
kind: measure
id: billing-dn-taxa-retencao
title: Billing DN — taxa de retenção
source: dim_zendesk_tickets_detailed
unit: ratio
expr: COUNTIF(subclassification IN ('retido','retenção')) / NULLIF(COUNTIF(subclassification IN ('retido','retenção') OR servir_churn_type IS NOT NULL), 0)
policies: [escopo-billing-dono-de-negocio]
composed_of: [billing-dn-retidos, billing-dn-negociacao]
kind_of_measure: derived
direction: higher_is_better
status: stable
```

Retidos sobre negociações.

```yaml meta
kind: measure
id: billing-dn-mix-demanda
title: Billing DN — mix de demanda
source: dim_zendesk_tickets_detailed
unit: ratio
direction: neutral
status: draft
status_reason: "sem query validada; a KB define a fórmula só em prosa"
```

`COUNT(DISTINCT id billing) / COUNT(DISTINCT id BACKING_OPS total)` — participação do Billing DN
no total da área BACKING_OPS.

---

## 4. Relatórios

```yaml meta
kind: report
id: rel-demanda-total-definicao
title: Demanda Total (Cami + Telefone) — bloco de definição
sources: [dim_chatbot, fact_service_metrics]
measures: [demanda-cami, demanda-telefone, demanda-total]
policies: [escopo-servir, escopo-canal-telefone, escopo-area-atendimento]
status: stable
```

Bloco de definição da §4: dois `SELECT` independentes, **sem janela de data**. A versão
parametrizada e validada é `rel-demanda-total-semanal`.

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

```yaml meta
kind: report
id: rel-dias-uteis-do-periodo
title: Quantidade de dias úteis no período
sources: [dim_date]
measures: [dias-uteis]
policies: [escopo-dias-uteis-nacionais]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Denominador de toda métrica "por DU" e do HC Líquido. É assim que o Looker conta.

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

```yaml meta
kind: report
id: rel-demanda-humana-por-canal-definicao
title: Demanda Humana por Canal — bloco de definição
sources: [fact_service_metrics]
measures: [demanda-humana-recebida]
policies: [escopo-canais-humanos, escopo-area-atendimento]
status: stable
```

Versão sem janela de data; a validada com período e com atendida/abandonada é
`rel-demanda-humana-por-canal`.

```sql
SELECT channel, SUM(count_of_demanded) AS demanda_recebida
FROM `contaazul-ssbi.gold_serve.fact_service_metrics`
WHERE channel IN ('Chat', 'Email', 'Telefone', 'Web', 'Whatsapp')
  AND area IN ('BK', 'DN', 'EC', 'SAC - CA', 'SAC - Pessoalize')
GROUP BY channel
```

```yaml meta
kind: report
id: rel-csat-blended-pme-definicao
title: CSAT Blended PME / Parceiro — bloco de definição
sources: [fact_service_metrics, dim_chatbot]
measures: [csat-blended, csat-humano, csat-cami]
policies: [escopo-area-atendimento, escopo-servir, escopo-csat-retidos, segmento-pme-legado]
status: stable
```

Traz a fórmula do blended e os dois agregados componentes, sem janela de data. A versão executável
é `rel-csat-blended-pme-e-parceiro`.

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

```yaml meta
kind: report
id: rel-retencao-cami-kpi-definicao
title: Retenção Cami (Deflexão) — bloco de definição do KPI
sources: [dim_chatbot, dim_date, dim_chatbot_holidays]
measures: [retencao-cami-kpi]
policies: [escopo-servir, escopo-dia-util-retencao, segmento-pme, segmento-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Regra do tile "Retenção" (5691) do dashboard 210. Idêntica em conteúdo a
`rel-retencao-cami-kpi-por-segmento` (Q4).

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

```yaml meta
kind: report
id: rel-contatos-unicos-do-chatbot
title: Contatos únicos do chatbot (clientes distintos)
sources: [dim_chatbot]
measures: [contatos-unicos-chatbot]
policies: [escopo-servir]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

A chave é o `CONCAT` de `nk_company_id` com `nk_accountancy_id` — reproduza sem separador.

```sql
SELECT COUNT(DISTINCT CONCAT(nk_company_id, nk_accountancy_id)) AS contatos_unicos
FROM `contaazul-ssbi.gold_serve.dim_chatbot`
WHERE nk_date BETWEEN '<inicio>' AND '<fim>'
  AND bot_departament = 'Servir'
```

```yaml meta
kind: report
id: rel-hc-liquido
title: HC Líquido e chamados por encantador
sources: [agent_capacity, fact_service_metrics]
measures: [hc-liquido, chamados-por-encantador-mes, chamados-por-encantador-du, demanda-humana-atendida]
policies: [escopo-capacidade-servir]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
  - {name: qtd_du, type: integer}
status: stable
```

O `<qtd_du>` deve vir de `rel-dias-uteis-do-periodo`, nunca de contagem manual de dias de semana.

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

```yaml meta
kind: report
id: rel-fcr-mensal-humano
title: FCR mensal do atendimento humano
sources: [vw_rps_fcr_semanal]
measures: [fcr]
policies: [escopo-fcr-humano]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Custa 2,13 GB por execução — rode uma vez e reaproveite. `DATE_TRUNC(semana_inicio, MONTH)`
atribui a semana inteira ao mês em que ela começou.

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

```yaml meta
kind: report
id: rel-nps-mensal-por-segmento
title: pNPS mensal por segmento
sources: [fact_nps_survey]
measures: [nps, respostas-por-empresa-nps]
policies: [escopo-pnps]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Traz respostas e empresas na mesma linha, o que permite detectar contaminação de campanha
(respostas/empresa muito acima de ~1,05).

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

```yaml meta
kind: report
id: rel-demanda-total-semanal
title: Q1 — Demanda Total Semanal (Cami + Telefone)
sources: [dim_chatbot, fact_service_metrics]
measures: [demanda-cami, demanda-telefone, demanda-total]
policies: [escopo-servir, escopo-canal-telefone, escopo-area-atendimento]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Query validada da §6: `UNION ALL` entre o autoatendimento e a voz.

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

```yaml meta
kind: report
id: rel-demanda-humana-por-canal
title: Q2 — Demanda Humana por Canal
sources: [fact_service_metrics]
measures: [demanda-humana-recebida, demanda-humana-atendida, demanda-abandonada]
policies: [escopo-canais-humanos, escopo-area-atendimento]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Recebida, atendida e abandonada por canal, na mesma linha.

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
id: rel-csat-blended-pme-e-parceiro
title: Q3 — CSAT Blended PME e Parceiro
sources: [fact_service_metrics, dim_chatbot]
measures: [csat-blended, csat-humano, csat-cami]
policies: [escopo-area-atendimento, escopo-servir, escopo-csat-retidos, segmento-pme-legado, segmento-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Usa `customer_type != 'Parceiro'` como PME (definição legada) — reproduz os números históricos.

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
id: rel-retencao-cami-kpi-por-segmento
title: Q4 — Retenção Cami / Deflexão (total, PME e Parceiro)
sources: [dim_chatbot, dim_date, dim_chatbot_holidays]
measures: [retencao-cami-kpi]
policies: [escopo-servir, escopo-dia-util-retencao, segmento-pme, segmento-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Para a **retenção observada**, troque `IF(is_business_day, x, 0)` por `x` em todos os termos.

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

```yaml meta
kind: report
id: rel-csat-blended-pme-por-sub-segmento
title: Q6 — CSAT Blended PME por sub-segmento (CDP / CSP)
sources: [fact_service_metrics, dim_chatbot]
measures: [csat-blended, csat-humano, csat-cami]
policies: [escopo-area-atendimento, escopo-servir, escopo-csat-retidos, segmento-pme, segmento-pme-legado, segmento-cliente-do-parceiro, segmento-cliente-sem-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Atenção à assimetria interna: o lado humano usa `!= 'Parceiro'` para PME e o lado Cami usa o
`IN (...)` explícito.

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

```yaml meta
kind: report
id: rel-csat-cami-pme-por-bot-type
title: Q7 — CSAT Cami PME por bot_type e sub-segmento
sources: [dim_chatbot]
measures: [csat-cami-por-total-ratings, volume-avaliacoes-cami]
policies: [escopo-servir, escopo-csat-retidos, segmento-pme, segmento-cliente-do-parceiro, segmento-cliente-sem-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Gen 2 e Gen 3 CA Mais podem não ter avaliações `csat_retidos` em PME — retornam NULL.

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

```yaml meta
kind: report
id: rel-retencao-cami-por-bot-type
title: Q8 — Retenção Cami por bot_type e sub-segmento
sources: [dim_chatbot, dim_date, dim_chatbot_holidays]
measures: [retencao-cami-kpi]
policies: [escopo-servir, escopo-dia-util-retencao, segmento-pme, segmento-parceiro, segmento-cliente-do-parceiro, segmento-cliente-sem-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Breakdown completo: total + PME (CDP/CSP) + Parceiro, por `bot_type`.

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

```yaml meta
kind: report
id: rel-visao-por-categoria-cami
title: Q9 — Visão por Categoria Cami (Gen2 + Gen3 CA Pro + Gen3 CA Mais)
sources: [dim_chatbot, ingestion_zendesk_tickets]
measures: [demanda-cami, retencao-cami-observada]
policies: [escopo-servir]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

`extra_predicate` exclusivo deste relatório: `c.bot_type IN ('Gen2', 'Gen3 CA Pro', 'Gen3 CA Mais')`
(exclui Bot_Fin). Prefira `dim_chatbot.subcategory` a este join quando a pergunta for por tema.

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

```yaml meta
kind: report
id: rel-performance-dos-encantadores-pme
title: Q10 — Performance dos Encantadores PME (HC, chamados/enc, CSAT por sub-segmento)
sources: [agent_capacity, fact_service_metrics]
measures: [hc-liquido, chamados-por-encantador-mes, chamados-por-encantador-du, demanda-humana-recebida, demanda-humana-atendida, csat-humano]
policies: [escopo-capacidade-servir, escopo-area-atendimento, segmento-cliente-do-parceiro, segmento-cliente-sem-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
  - {name: qtd_du, type: integer}
status: stable
```

HC e produtividade são **compartilhados** entre PME e Parceiros — a mesma equipe atende os dois.

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

```yaml meta
kind: report
id: rel-sla-tme-tma-abandono-por-segmento
title: Q5 — SLA TME, TMA e Abandono (PME total + CDP + CSP + Parceiro)
sources: [fact_service_metrics]
measures: [sla-tme-3min, tme, tma, percentual-abandono]
policies: [escopo-area-atendimento, escopo-canais-online, segmento-pme-legado, segmento-parceiro, segmento-cliente-do-parceiro, segmento-cliente-sem-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Note que SLA/TME/TMA aplicam o filtro de canais online, mas o **abandono não** — é fiel à measure
oficial.

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

```yaml meta
kind: report
id: rel-telefone-por-categoria
title: Telefone — visão por categoria (ticket_category)
sources: [dim_zendesk_tickets_detailed]
measures: [telefone-categoria-interacoes, telefone-categoria-mix, telefone-categoria-csat, telefone-categoria-tma]
policies: [escopo-canal-telefone, escopo-area-atendimento, escopo-service-metrics]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

A janela usa `source_solved_at` com fallback para `nk_date` quando ele é NULL.

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

```yaml meta
kind: report
id: rel-telefone-suporte-premium
title: Telefone — segmentação por Suporte Premium e tempo de casa
sources: [fact_service_metrics]
measures: [interacao-total-telefone, atendidos-mais-6m, atendidos-menos-6m]
policies: [escopo-canal-telefone, escopo-area-atendimento]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

`has_premium_support` NULL vira "Não Identificado" e `customer_type` NULL vira
"Sem Tipo de Cliente".

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

```yaml meta
kind: report
id: rel-billing-dono-de-negocio
title: Billing Dono de Negócio — negociação e retenção
sources: [dim_zendesk_tickets_detailed]
measures: [billing-dn-total, billing-dn-negociacao, billing-dn-retidos, billing-dn-nao-retido]
policies: [escopo-billing-dono-de-negocio]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Data por `DATE(source_solved_at)`.

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

```yaml meta
kind: report
id: rel-csat-parceiros-blended-humano-cami
title: CSAT Blended + Humano + Cami — Parceiros
sources: [fact_service_metrics, dim_chatbot]
measures: [csat-blended, csat-humano, csat-cami]
policies: [escopo-area-atendimento, escopo-servir, escopo-csat-retidos, segmento-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Query da §10, validada na W16 com diff máximo de 0,02pp. É o recorte só-Parceiro de
`rel-csat-blended-pme-e-parceiro`.

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

```yaml meta
kind: report
id: rel-retencao-e-avaliacoes-por-bot-type
title: Retenção observada e concentração de avaliações por bot_type
sources: [dim_chatbot]
measures: [retencao-cami-observada, volume-avaliacoes-cami]
policies: [escopo-servir, escopo-csat-retidos, segmento-pme, segmento-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Usa a retenção **sem** filtro de dia útil (`1 - transbordos/interações`) e mede na mesma passada
o volume de avaliações por bot — é como se detecta a concentração no Fin AI.

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

```yaml meta
kind: report
id: rel-abandono-cdp-vs-csp
title: Abandono — Cliente do Parceiro vs Cliente sem Parceiro
sources: [fact_service_metrics]
measures: [percentual-abandono]
policies: [escopo-area-atendimento, segmento-cliente-do-parceiro, segmento-cliente-sem-parceiro]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Sem filtro de canal, fiel à measure oficial — e por isso sujeito ao artefato de `channel = ''`.

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

```yaml meta
kind: report
id: rel-billing-dn-taxa-de-retencao
title: Billing DN — taxa de retenção
sources: [dim_zendesk_tickets_detailed]
measures: [billing-dn-total, billing-dn-negociacao, billing-dn-retidos, billing-dn-taxa-retencao]
policies: [escopo-billing-dono-de-negocio]
params:
  - {name: inicio, type: date}
  - {name: fim, type: date}
status: stable
```

Mesmo recorte de `rel-billing-dono-de-negocio`, já devolvendo a taxa. No `kb.md` este é o último
bloco do arquivo e a cerca ```` ``` ```` de fechamento está ausente (arquivo termina no `AND` final).

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

---

## 5. Armadilhas

```yaml meta
kind: pitfall
id: lookml-nomes-mentem
severity: high
applies_to: [fact_service_metrics, dim_chatbot, dim_chatbot_holidays]
```

**Regra geral: os nomes do LookML mentem — confie no `sql:`.** Três casos confirmados em
`repos/looker/`, todos capazes de inverter uma query: (1) `dim_chatbot_holidays.is_holiday` tem
label "Desconsiderar Feriados?" e parece marcar feriados, mas o `sql:` é `${TABLE}.nk_date is null`;
(2) `fact_service_metrics.sla_tme_3min` diz "menor do que 180 segundos" e usa `<= 180`;
(3) `dim_chatbot.rated_demands` fala em "clientes que chegaram no chatbot Final" e divide por
`count_of_interactions`, não por `count_of_final_bot`. Ao traduzir um tile do Looker para SQL,
**abra o `.lkml` e leia o `sql:`**.

```yaml meta
kind: pitfall
id: is-holiday-label-invertido
severity: high
applies_to: [dim_chatbot_holidays, retencao-cami-kpi]
enforced_by: escopo-dia-util-retencao
```

`dim_chatbot_holidays.is_holiday` (`dim_chatbot_holidays.view.lkml:21`) tem `sql:`
`${TABLE}.nk_date is null` — ou seja, `Yes` significa **NÃO é feriado**, e o filtro
`is_holiday: "Yes"` **exclui** feriados. O label "Desconsiderar Feriados?" sugere o contrário.
Em SQL isso corresponde ao `h.nk_date IS NULL` do join da retenção.

```yaml meta
kind: pitfall
id: sla-tme-usa-menor-ou-igual
severity: medium
applies_to: [sla-tme-3min, sla-tme-5min]
```

É `<= 180`, **não** `< 180`. O label e a description do LookML dizem "menor do que 180 segundos",
mas o SQL da dimensão `fact_service_metrics.sla_tme_3min`
(`fact_service_metrics.view.lkml:276`) usa `<=`. Vale a regra geral: confiar no SQL, não no nome.
Existe também `sla_tme_5min`, com `<= 300`.

```yaml meta
kind: pitfall
id: rated-demands-divide-por-interacoes
severity: medium
applies_to: [dim_chatbot]
```

A measure `dim_chatbot.rated_demands` (`dim_chatbot.view.lkml:266`) tem description falando "em
relação aos clientes que chegaram no **chatbot Final**", mas o `sql:` divide por
`count_of_interactions`, não por `count_of_final_bot` — o que aliás salva a measure, porque
`count_of_final_bot` é sempre 0.

```yaml meta
kind: pitfall
id: dashboard-duas-definicoes-retencao
severity: high
applies_to: [retencao-cami-kpi, retencao-cami-observada, dim_chatbot]
enforced_by: escopo-dia-util-retencao
```

**Existem DUAS retenções oficiais no dashboard 210** — não é bug, são recortes diferentes.
Os tiles `Retenção` (5691) e `Retenção Diária` (5688) filtram dia útil e excluem feriado: é o
**KPI**, a resposta padrão. Os tiles `Acumulado Mensal` (12073/12074/12086), `Detalhado *` e
`Retenção por hora` não filtram dia: é a retenção **observada** no período. Diferença medida de
**0,5 a 1,2pp** ao mês, a versão sem filtro sempre mais alta. Motivo: no fim de semana não há
encantador para receber transbordo, então a retenção fica artificialmente em ~96% (vs ~57% em dia
útil, mai–jul/26). Antes de responder, identifique **qual tile** a pergunta quer.

```yaml meta
kind: pitfall
id: semanas-desta-kb-tem-7-dias
severity: medium
applies_to: [retencao-cami-kpi, retencao-cami-observada]
```

Numa janela **segunda a sexta** as duas regras de retenção dão exatamente o mesmo número (o filtro
não remove nada). A diferença só aparece em janela que inclui fim de semana — e as "semanas" desta
KB (W15/W16/W17) são de **7 dias, segunda a domingo**. Na W17 a diferença KPI vs observada é 0,8pp,
maior que na W16 (0,3pp), por causa do mix de volume do sábado/domingo — não por causa do feriado.

```yaml meta
kind: pitfall
id: bot-fin-nao-e-cami
severity: high
applies_to: [dim_chatbot, demanda-cami]
```

**Bot_Fin não é o Cami.** `bot_type = 'Bot_Fin'` é o bot Financeiro/FinAI — está incluído em
`bot_departament = 'Servir'` mas representa produto diferente. Para demanda Cami, use
`bot_departament = 'Servir'` **sem** filtrar `bot_type`, porque o dashboard oficial inclui o
Bot_Fin. Hoje ele é **99% do volume** (jul/26: 41.772 de 42.135 interações do Servir).

```yaml meta
kind: pitfall
id: csat-type-cria-multiplas-linhas
severity: high
applies_to: [dim_chatbot, csat-cami]
enforced_by: escopo-csat-retidos
```

`csat_type` cria múltiplas linhas: cada thread pode ter até 3 (`N/I` + `csat_retidos` +
`csat_transbordados`). Para contar **sessões únicas** use apenas `csat_type = 'N/I'`; para
**CSAT** use `csat_type = 'csat_retidos'`.

```yaml meta
kind: pitfall
id: demanda-cami-inclui-todos-csat-type
severity: high
applies_to: [demanda-cami, dim_chatbot]
```

**Demanda Cami = todos os `csat_type`.** `SUM(sum_of_interactions)` com
`bot_departament = 'Servir'` e **sem** filtro de `csat_type` é o total correto de interações.
Filtrar `csat_type` aqui subconta a demanda.

```yaml meta
kind: pitfall
id: area-rt-fora-do-atendimento
severity: high
applies_to: [fact_service_metrics]
enforced_by: escopo-area-atendimento
```

**RT (Retenção) é área separada.** A área `RT` na `fact_service_metrics` representa atendimentos do
fluxo de Retenção — **não** entra no filtro padrão de Atendimento.

```yaml meta
kind: pitfall
id: sum-of-final-bot-sempre-zero
severity: high
applies_to: [dim_chatbot, retencao-cami-kpi]
```

**`sum_of_final_bot` é sempre 0.** Campo morto: soma **0** nos 12 meses (ago/25–jul/26), tanto em
`Servir` como em `Retenção`. A descrição "conversas retidas" engana — **retenção NÃO se calcula com
ele**, e sim `1 − transbordos/interações`. A measure `count_of_final_bot` do LookML herda o
problema.

```yaml meta
kind: pitfall
id: subcategory-e-mais-barata-que-tags
severity: medium
applies_to: [dim_chatbot, ingestion_zendesk_tickets, rel-visao-por-categoria-cami]
```

**`subcategory` é a categorização nativa** e traz o tema já classificado (`Emissão de Nota Fiscal`,
`Lançamentos Financeiros`, `Conciliação bancária`, `Transferência sem Contexto`, `Desistente`,
`Abandono Chatbot`, `N/I`, …). É muito mais barata que o join com as tags do Zendesk de
`rel-visao-por-categoria-cami`, não tem custo de join e não carrega a divergência pendente de
Vendas/NA — **prefira `subcategory`** quando a pergunta for por tema.

```yaml meta
kind: pitfall
id: partner-profile-nao-particiona-base
severity: medium
applies_to: [dim_chatbot, fact_service_metrics]
```

**`partner_profile` não particiona a base.** Só existe para Parceiro (`CONTADOR`, `BPO`, `MISTO`) e
é **NULL em ~68% das linhas** (todo cliente que não é parceiro). É subconjunto de
`customer_type = 'Parceiro'`, não uma segmentação alternativa da base inteira. Distribuição jul/26
em `dim_chatbot`: NULL 33.105 · CONTADOR 7.535 · MISTO 4.276 · BPO 3.967.

```yaml meta
kind: pitfall
id: contatos-unicos-usa-duas-colunas
severity: high
applies_to: [contatos-unicos-chatbot, dim_chatbot]
```

**Contatos únicos usa duas colunas**: `COUNT(DISTINCT CONCAT(nk_company_id, nk_accountancy_id))` —
não `nk_company_id` sozinho (diferença de ~40%) e não contagem de `thread_uid`. Um mesmo
`nk_company_id` atendido por escritórios contábeis diferentes conta como contatos distintos.
Medido em 08–12/jun/2026 (Servir, canais Chat/Web/Whatsapp): **4.309** pela regra correta, contra
3.077 usando só `nk_company_id` e 8.242 contando `thread_uid` (= nº de interações).

```yaml meta
kind: pitfall
id: concat-sem-separador-tem-colisao
severity: low
applies_to: [contatos-unicos-chatbot]
```

O `CONCAT` sem separador tem colisão teórica (empresa `1` + contabilidade `23` gera a mesma string
que empresa `12` + contabilidade `3`). **Reproduza assim mesmo** — é exatamente o que a measure do
Looker faz, e o objetivo é bater com o dashboard. Não "conserte" com separador: o número deixaria
de casar.

```yaml meta
kind: pitfall
id: ouvidoria-ip-e-rt-fora-do-filtro
severity: high
applies_to: [fact_service_metrics, demanda-telefone]
enforced_by: escopo-area-atendimento
```

**Ouvidoria - IP fica fora do filtro.** O escopo é
`area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')` — Ouvidoria e RT ficam de fora da Demanda
Total, mesmo o Telefone tendo `Ouvidoria - IP` entre suas áreas presentes.

```yaml meta
kind: pitfall
id: tma-tme-so-em-canais-online
severity: high
applies_to: [tma, tme, sla-tme-3min]
enforced_by: escopo-canais-online
```

**TMA/TME só em canais online.** Calcule apenas para
`channel IN ('Whatsapp','Telefone','Chat')` — Email e Web não têm TA/TE.

```yaml meta
kind: pitfall
id: demanda-recebida-diferente-de-atendida
severity: high
applies_to: [demanda-humana-recebida, demanda-humana-atendida, demanda-abandonada]
```

**Demanda recebida ≠ atendida.** O tile "Demanda humana por canal" usa `count_of_demanded`
(recebida = atendidos + abandonados). `count_of_attended` é menor porque exclui abandonos, e a
diferença é exatamente o abandono (W16 registro: 5.220 − 5.014 = 206 abandonos).

```yaml meta
kind: pitfall
id: web-tem-areas-extras
severity: medium
applies_to: [fact_service_metrics]
enforced_by: escopo-area-atendimento
```

**Web tem muitas áreas extras**: BACKING_OPS, N/I, RT, ENG, SDM, TRAINING, OUVIDORIA — todas fora
do filtro padrão de Atendimento.

```yaml meta
kind: pitfall
id: parceiros-exige-filtro-de-area
severity: high
applies_to: [fact_service_metrics, tme, tma, sla-tme-3min, percentual-abandono]
enforced_by: escopo-area-atendimento
```

**Parceiros exige filtro de área.** Para SLA/TME/TMA/Abandono de `customer_type = 'Parceiro'` é
**obrigatório** `area IN ('BK','DN','EC','SAC - CA','SAC - Pessoalize')`. Sem isso, linhas de RT,
N/I e BACKING_OPS inflam `sum_of_te` e `count_of_demanded`, e o TME sai **4–5x maior** que o real.

```yaml meta
kind: pitfall
id: channel-vazio-entra-no-abandono
severity: high
applies_to: [percentual-abandono, fact_service_metrics]
```

**`channel = ''` entra no abandono — e isso está certo.** Existem linhas com canal vazio **dentro**
do filtro de área padrão, e elas são **100% abandono** (jul/26: 61 demandados, 61 abandonados). A
measure oficial `percent_of_abandoned` (`fact_service_metrics.view.lkml:401`) **não filtra canal**,
logo o abandono oficial **inclui** essas linhas. Não adicione filtro de canal ao abandono "para
limpar": você se afasta do Looker. Efeito: ~0,23pp a mais na taxa. (O Book Pré-RMR filtra canal e
por isso reporta abandono menor.)

```yaml meta
kind: pitfall
id: anomalia-channel-vazio-abril-2026
severity: high
applies_to: [percentual-abandono, demanda-humana-recebida, fact_service_metrics]
```

**Abril/2026 tem uma anomalia de dados em `channel = ''`.** Naquele mês há **3.966 chamados com
canal vazio, 100% abandonados** — contra 1 a 336 em qualquer outro mês do ano (na W16 são 934
chamados; na W17, 1.077). Isso sozinho leva o abandono de abril de 4,84% para 19,81%, e o abandono
PME da W16 de 4,85% para 20,03%. Como a measure oficial não filtra canal, esses são os valores
**fiéis à definição** — mas não são leitura operacional. Para leitura operacional de abril,
reporte também a versão sem o artefato. O canal Telefone **não** é afetado (aquelas linhas têm
canal vazio, não `Telefone`).

```yaml meta
kind: pitfall
id: diferente-de-parceiro-nao-e-pme
severity: high
applies_to: [fact_service_metrics, dim_chatbot, segmento-pme-legado]
enforced_by: segmento-pme
```

**`!= 'Parceiro'` NÃO é PME — nas duas tabelas.** Existe um quarto valor literal, **`'N/I'`**, e ele
é volumoso. Medido em jun–jul/2026: em `dim_chatbot` (Servir) há Parceiro 25.337 · Cliente do
Parceiro 22.274 · Cliente sem Parceiro 22.602 · **N/I 5.095** · NULL 0; na `fact_service_metrics`,
16.074 · 12.978 · 14.528 · **1.702** · NULL 6. Usar `customer_type != 'Parceiro'` como PME **infla o
PME em ~11% no `dim_chatbot`** (49.971 em vez de 44.876) e ~4% na `fact_service_metrics`. Para PME
use sempre `customer_type IN ('Cliente do Parceiro','Cliente sem Parceiro')`. Isso corrige duas
afirmações antigas: (a) o problema **não** é `NULL` — o `dim_chatbot` não tem nenhum `NULL` em
`customer_type`; (b) `!= 'Parceiro'` **não** é seguro na `fact_service_metrics`. Várias queries da
§6 ainda usam `!= 'Parceiro'` e por isso reproduzem os números históricos.

```yaml meta
kind: pitfall
id: parceiro-em-dim-chatbot-com-not-in-inclui-ni
severity: high
applies_to: [dim_chatbot, segmento-parceiro]
enforced_by: segmento-parceiro
```

A §10 do `kb.md` define Parceiro em `dim_chatbot` como
`customer_type NOT IN ('Cliente do Parceiro','Cliente sem Parceiro')` (i.e., "exclui PME"). Como
existe o valor `'N/I'` (5.095 interações em jun–jul/2026), essa forma **inclui N/I no Parceiro** e
não equivale a `customer_type = 'Parceiro'`. Para o segmento Parceiro, prefira a igualdade
explícita.

```yaml meta
kind: pitfall
id: partner-profile-grafia-diferente-na-tabela-mensal
severity: medium
applies_to: [dim_chatbot, fact_service_metrics]
```

**Não confundir `partner_profile` com a tabela de perfil mensal.** Em
`tmp_data_analytics.fact_customer_partner_profile_nova_regra` o mesmo conceito aparece em
**minúsculas e com nomes diferentes**: `contador`, `bpo`, `contador_bpo`, `sem_uso` (contra
`CONTADOR`, `BPO`, `MISTO`, NULL nas tabelas transacionais). Um `JOIN`/`IN` entre as duas grafias
devolve vazio silenciosamente.

```yaml meta
kind: pitfall
id: canal-ios-grafia-exata
severity: medium
applies_to: [dim_chatbot]
```

A grafia dos canais de `dim_chatbot` é **case-sensitive** em SQL: é **`Ios`**, com I maiúsculo e
"os" minúsculo — escrever `'iOS'` não casa com nada e descarta o canal silenciosamente. O filtro
oficial do canal está no tile 20110 do dashboard 220: `Android, Chat, Ios, Whatsapp`. O volume de
app é pequeno mas não-nulo (jul/26: 430 `Ios` + 240 `Android` de 42.135 interações do Servir).

```yaml meta
kind: pitfall
id: bot-departament-null-nao-e-bot-fin
severity: medium
applies_to: [dim_chatbot]
enforced_by: escopo-servir
```

**`bot_departament` NULL não é "Bot_Fin sem departamento"** — as linhas com
`bot_departament IS NULL` têm **0 interações**. O Bot_Fin está distribuído entre `Servir` (41.772)
e `Retenção` (6.712) em jul/26. A description do schema menciona um valor `Ouvidoria`, que não
aparece nos dados dos últimos 12 meses.

```yaml meta
kind: pitfall
id: gen2-praticamente-extinto
severity: medium
applies_to: [dim_chatbot]
```

**Gen2 está praticamente extinto**: 4 interações em jul/26 no Servir. A descrição histórica ("bot
principal de Whatsapp") vale para o período W16/abr-2026, **não** para hoje. Volumes de jul/26 por
bot: Bot_Fin 41.772 · Gen3 CA Pro 299 · Gen3 CA Mais 60 · Gen2 4.

```yaml meta
kind: pitfall
id: sum-of-total-ratings-como-denominador
severity: medium
applies_to: [csat-cami-por-total-ratings, rel-csat-cami-pme-por-bot-type]
```

Usar `sum_of_total_ratings` como denominador do CSAT Cami (= positivas + negativas), **não**
`sum_of_interactions`. Gen 2 e Gen 3 CA Mais podem não ter avaliações `csat_retidos` em PME —
nesses casos o resultado é NULL, e NULL não é zero.

```yaml meta
kind: pitfall
id: du-derive-da-dim-date
severity: high
applies_to: [dias-uteis, demanda-por-du, hc-liquido, chamados-por-encantador-mes, chamados-por-encantador-du]
enforced_by: escopo-dias-uteis-nacionais
```

**Derive o DU da `dim_date`, não conte "seg a sex" na mão**: o `national_work_day` já exclui feriado
nacional. Numa janela mensal a diferença é real. Foi exatamente esse o erro do cálculo original da
KB: 01–26/abr/2026 tem 18 dias de semana mas **16 dias úteis** (03/abr Sexta-feira Santa e 21/abr
Tiradentes), e o HC Líquido registrado (54) veio de dividir por 18 — o correto é **61,63**, com
todos os "chamados por encantador" derivados mudando junto. A W17 (20–26/abr) tem **4 DU, não 5**,
então toda métrica "por DU" da W17 no registro original está subestimada em ~20%.

```yaml meta
kind: pitfall
id: dim-chatbot-holidays-sem-linhas-de-2026
severity: high
applies_to: [dim_chatbot_holidays, retencao-cami-kpi, escopo-dia-util-retencao]
```

**`dim_chatbot_holidays` está desatualizada — o join de feriado é INERTE em 2026.** A tabela tem
**32 linhas**, de 12/02/2024 a **20/11/2025**, só nos canais `Chat`, `Web` e `Whatsapp`; não há
nenhuma linha de 2026. Consequências: o `h.nk_date IS NULL` é sempre verdadeiro para datas de 2026,
então **na prática só o filtro de fim de semana está atuando**; a diferença de 0,5–1,2pp entre KPI e
retenção observada vem **inteiramente do fim de semana**, não de feriado; e feriados nacionais de
2026 (Tiradentes 21/04, Sexta-feira Santa 03/04) **contam como dia útil** na retenção, tanto na sua
query quanto no tile do Looker. Mantenha o join mesmo assim: é o que o tile faz e volta a ter efeito
se a tabela for repovoada. Mas **não confunda com o `national_work_day` da `dim_date`**, que cobre
2026 normalmente e é quem deve contar dias úteis.

```yaml meta
kind: pitfall
id: is-active-workday-e-numeric-nao-cast
severity: high
applies_to: [agent_capacity, hc-liquido]
```

`is_active_workday` é **NUMERIC (decimal), NÃO booleano** — nunca use `CAST(... AS INT64)`. Some
direto. Em abril/2026 o `SUM` dá o mesmo com e sem CAST, porque o campo não tem parte fracionária
naquele mês; a distorção aparece em meses como julho/26 (**39,56 correto vs 41,26 com CAST**).

```yaml meta
kind: pitfall
id: densidade-usa-total-active-companies-by-day
severity: medium
applies_to: [densidade-demanda, dim_active_companies_by_month]
```

O denominador da densidade é `total_active_companies_by_day`, **não**
`total_active_companies`.

```yaml meta
kind: pitfall
id: fcr-sem-tipo-humano
severity: high
applies_to: [fcr, vw_rps_fcr_semanal]
enforced_by: escopo-fcr-humano
```

**`tipo = 'humano'` é obrigatório.** Sem o filtro, o agregado sobe de 67,8% para **76,7%**; o bot
sozinho dá **81,2%**. São métricas de coisas diferentes — o FCR de atendimento é o humano.

```yaml meta
kind: pitfall
id: fcr-com-avg-fcr-pct
severity: high
applies_to: [fcr, vw_rps_fcr_semanal]
```

**Use `SUM(numerador)/SUM(denominador)`, nunca `AVG(fcr_pct)`** — média de proporção pesa semanas
pequenas igual a semanas grandes.

```yaml meta
kind: pitfall
id: fcr-custa-2gb-por-execucao
severity: medium
applies_to: [vw_rps_fcr_semanal, rel-fcr-mensal-humano]
```

**Custo: 2,13 GB por execução.** A view não é particionada nem clusterizada, e o `WHERE` em
`semana_inicio` **não** reduz o scan. Rode uma vez e reaproveite; nunca em loop.

```yaml meta
kind: pitfall
id: fcr-semanas-atravessam-o-mes
severity: medium
applies_to: [fcr, rel-fcr-mensal-humano]
```

**Semanas atravessam o mês.** `DATE_TRUNC(semana_inicio, MONTH)` atribui a semana inteira ao mês em
que ela começou — é aproximação, não recorte exato de mês.

```yaml meta
kind: pitfall
id: fcr-do-bot-saltou-para-98
severity: high
applies_to: [fcr, vw_rps_fcr_semanal]
```

**O FCR do bot mudou de patamar**: ~87% até abril, **98,2% em junho e 98,96% em julho**. Salto
grande demais para ser real. Investigue antes de reportar qualquer FCR de bot.

```yaml meta
kind: pitfall
id: pnps-ca-pro-agosto-2026-contaminado
severity: high
applies_to: [nps, fact_nps_survey, respostas-por-empresa-nps]
```

**NÃO reporte o pNPS de CA Pro de agosto/2026 sem tratar.** A campanha
`[Oficial_Pro] 2026 pNPS Ciclo 2` reenviou para quem já havia respondido: **15.742 respostas de
5.290 empresas = 2,98 por empresa**, contra ~1,05 em maio/junho/julho. A nota cai de 55,1 para
**22,5** sem que nada tenha piorado. Não é duplicação de linha — `sk_nps_survey` e `nk_answer` são
únicos; a pesquisa foi mesmo respondida várias vezes. **CA Mais não foi afetado.** Mitigação:
deduplique por empresa (ex.: última resposta por `nk_company` no período) ou filtre a campanha.

```yaml meta
kind: pitfall
id: nps-type-pnps-descarta-2025
severity: high
applies_to: [nps, fact_nps_survey, escopo-pnps]
```

**Troca de ferramenta em 31/12/2025 — IndeCX → Survicate.** Todo dado anterior a 2026 tem
`nps_type = 'Não identificado'` (a IndeCX não marcava o ciclo no nome da campanha). **Filtrar
`nps_type = 'pNPS'` descarta silenciosamente todo o histórico de 2025** (16.011 respostas de CA Pro
+ 2.293 de CA Mais). Para série longa, use `segment` + `nk_date` e **não** filtre `nps_type`.

```yaml meta
kind: pitfall
id: unicidade-do-nps-e-sk-nps-survey
severity: medium
applies_to: [fact_nps_survey]
```

A chave de unicidade do NPS é **`sk_nps_survey`**. O `nk_answer` só é único dentro de uma
ferramenta — pode colidir entre IndeCX e Survicate.

```yaml meta
kind: pitfall
id: rnps-sem-base
severity: medium
applies_to: [nps, fact_nps_survey]
```

**rNPS é praticamente inexistente**: 20 respostas no total (CA Mais, mar–abr/2026). Se a pergunta
for sobre rNPS, responda que não há base suficiente.

```yaml meta
kind: pitfall
id: categoria-vendas-e-na-com-divergencia
severity: high
applies_to: [rel-visao-por-categoria-cami, ingestion_zendesk_tickets]
```

Na visão por categoria da Cami, **Vendas e NA ainda têm divergência a investigar — não use para
esses dois até resolução**. Na validação da W17, 9 de 11 categorias fecharam com o dashboard, mas
Vendas veio 132 no BQ contra 88 no dashboard (+44) e NA 113 contra 139 (−26), com retenção de NA
73,5% contra 43,4%. A tag atual de Vendas é `mt_vendas_estoque_e_api` (a antiga
`mt_vendas_compras_estoque_e_api` não existe mais em 2026); a ordem das cláusulas `WHEN` importa
(temáticas antes das comportamentais) e interações sem ticket Zendesk caem em `NA`.

```yaml meta
kind: pitfall
id: tabelas-reprocessadas-retroativamente
severity: high
applies_to: [fact_service_metrics, dim_chatbot]
```

**As tabelas são reprocessadas retroativamente.** `gold_serve.fact_service_metrics` e
`gold_serve.dim_chatbot` mudam para períodos passados: a retenção Cami da W16, registrada como 55,6%
em abril, hoje devolve 57,08% com a mesma query; o CSAT Cami PME moveu 8pp (75,7% → 83,9%). Não é
erro de cálculo, é o dado que mudou embaixo. **Não persiga décimos contra alvo móvel** e não trate
valor histórico de dashboard como gabarito de hoje.

```yaml meta
kind: pitfall
id: volume-de-avaliacoes-cami-muda-com-reprocessamento
severity: medium
applies_to: [csat-cami, volume-avaliacoes-cami, dim_chatbot]
```

O **volume** de avaliações muda muito com o reprocessamento, mais até que a nota: as avaliações PME
do Bot_Fin na W17 caíram de 788 para 251; as de Parceiros na W17 caíram de 386 para 148 (Bot_Fin era
377, hoje 139). Com amostras desse tamanho, **não leia `bot_type` como tendência** — Gen 3 CA Pro
tem 2 avaliações na W17.

```yaml meta
kind: pitfall
id: fin-ai-concentra-as-avaliacoes-cami
severity: medium
applies_to: [csat-cami, volume-avaliacoes-cami, dim_chatbot]
```

O Fin AI (Bot_Fin) concentra **95%+ das avaliações da Cami** (788 de 830 em PME e 377 de 386 em
Parceiros na W17). Qualquer oscilação dele move o consolidado — risco estrutural ao ler CSAT Cami
como métrica agregada.

```yaml meta
kind: pitfall
id: chamados-por-encantador-usa-total-de-todos-segmentos
severity: medium
applies_to: [chamados-por-encantador-mes, chamados-por-encantador-du, hc-liquido]
```

"Chamados por encantador" usa o **total atendido de todos os segmentos** (PME + Parceiro) como
numerador, porque o mesmo HC serve os dois. O gráfico "[Parceiro]" só troca as barras de demanda e
CSAT; HC e produtividade são compartilhados, e por isso os números de HC das seções PME e Parceiros
são idênticos **por construção**, não por coincidência.

```yaml meta
kind: pitfall
id: abandono-telefone-vem-de-customer-type-nulo
severity: medium
applies_to: [percentual-abandono, fact_service_metrics]
```

O abandono total do canal Telefone (~4,5–5%) vem de `customer_type IS NULL` ou de segmentos fora de
PME/Parceiro — **PME e Parceiro têm 0% de abandono no canal Telefone**. Segmentar o abandono de
Telefone sem entender isso faz o número "desaparecer".

```yaml meta
kind: pitfall
id: customer-type-null-em-dim-chatbot-abril-2026
severity: low
applies_to: [dim_chatbot, retencao-cami-kpi]
```

Discrepâncias de ~0,8pp em Bot_Fin/Fin AI total (abril/2026) se devem a ~21 interações com
`customer_type = NULL` que o dashboard provavelmente exclui; para os demais `bot_type` a diferença é
≤0,14pp. Note a tensão com a medição de jun–jul/2026, que não encontrou nenhum `NULL` em
`customer_type` no `dim_chatbot` — o comportamento pode ter mudado com o reprocessamento.

```yaml meta
kind: pitfall
id: fallback-source-solved-at-em-tickets
severity: high
applies_to: [dim_zendesk_tickets_detailed, rel-telefone-por-categoria, telefone-categoria-interacoes]
```

Tickets com `source_solved_at IS NULL` precisam usar `nk_date` como **fallback** na janela de data.
Sem isso, categorias como "emissão de nfse" ficam 3 tickets abaixo do dashboard. A lógica validada
na W17, verbatim do `kb.md`:

```sql
WHERE (source_solved_at BETWEEN '2026-04-20' AND '2026-04-26')
   OR (source_solved_at IS NULL AND DATE(nk_date) BETWEEN '2026-04-20' AND '2026-04-26')
```

```yaml meta
kind: pitfall
id: integracao-bancaria-com-diff-pendente
severity: low
applies_to: [rel-telefone-por-categoria, dim_zendesk_tickets_detailed]
```

Na validação W17 da visão por categoria do Telefone, "integração bancária" ficou com diff de −5
(53 no dashboard, 48 no BQ) — investigação pendente, possivelmente um join adicional no Looker
capturando tickets atendidos com solve fora da janela. As demais categorias fecharam em 0 a −3.

```yaml meta
kind: pitfall
id: billing-dn-fonte-oficial-pode-estar-defasada
severity: medium
applies_to: [dim_zendesk_tickets_detailed, rel-billing-dono-de-negocio]
enforced_by: escopo-billing-dono-de-negocio
```

A fonte oficial do Looker para Billing Dono de Negócio é
`silver_retention.cancellation_tickets` (explore `churn_data_mart` → `cancellation_tickets`), **mas
ela pode ter defasagem**. Usar `gold_serve.dim_zendesk_tickets_detailed` com os filtros de
categoria + `assignee_area = 'BACKING_OPS'` + `DATE(source_solved_at)` replica os números
corretamente. Há um resíduo conhecido de tracking (Fortknox): o dashboard mostrava 1 não retido no
MTD de abril contra ~0 no BQ.

---

## 6. Glossário

```yaml meta
kind: term
id: pme
aliases: [PME, Dono de Negócio, DN]
scoped_by: segmento-pme
```

Clientes que não são parceiros contábeis: **Cliente do Parceiro (CDP) + Cliente sem Parceiro (CSP)**.
Não existe valor literal `PME` em nenhuma tabela — é sempre a soma dos dois sub-segmentos.

```yaml meta
kind: term
id: parceiro
aliases: [Parceiros, Contador parceiro]
scoped_by: segmento-parceiro
```

Escritório contábil parceiro da ContaAzul; é o canal de parceiros, distinto dos sub-segmentos de
PME. Corresponde ao valor `customer_type = 'Parceiro'`.

```yaml meta
kind: term
id: cliente-do-parceiro
aliases: [CDP]
scoped_by: segmento-cliente-do-parceiro
```

Sub-segmento de PME: cliente final que tem um escritório contábil parceiro cuidando dele.

```yaml meta
kind: term
id: cliente-sem-parceiro
aliases: [CSP]
scoped_by: segmento-cliente-sem-parceiro
```

Sub-segmento de PME: cliente final sem escritório contábil parceiro. Historicamente tem abandono
~1pp acima do CDP.

```yaml meta
kind: term
id: cami
aliases: [SuperCami, chatbot, Cami]
quantified_by: demanda-cami
```

O conjunto de chatbots de autoatendimento (Blip/Takeblip/Ultimate) registrado em `dim_chatbot`.
No uso corrente da KB, "Cami" = tudo que está em `bot_departament = 'Servir'`, o que **inclui** o
Bot_Fin.

```yaml meta
kind: term
id: bot-fin
aliases: [Bot_Fin, Fin AI, FinAI, bot Financeiro]
```

Bot Financeiro/FinAI. **Não é o Cami** em sentido estrito (é produto diferente), mas está dentro do
departamento Servir e hoje responde por 99% do volume e 95%+ das avaliações.

```yaml meta
kind: term
id: gen2
aliases: [Gen 2]
```

Geração antiga do chatbot. Foi descrita como "bot principal de Whatsapp" no período W16/abr-2026;
hoje está praticamente extinta (4 interações em jul/26 no Servir).

```yaml meta
kind: term
id: gen3
aliases: [Gen 3, Gen3 CA Pro, Gen3 CA Mais, is_gen3]
```

Geração atual do fluxo de chatbot, com IA. Aparece em dois `bot_type` (`Gen3 CA Pro` no Chat e
Whatsapp, `Gen3 CA Mais` no Chat) e tem contadores próprios de avaliação
(`sum_of_*_ratings_gen3`).

```yaml meta
kind: term
id: retencao-cami
aliases: [Deflexão Cami, Deflexão, Retenção, pct_retention]
quantified_by: retencao-cami-kpi
scoped_by: escopo-dia-util-retencao
```

% de interações que o bot resolveu sem precisar transbordar para humano. O Book Pré-RMR chama esta
métrica de **Deflexão Cami** — é a mesma coisa. Calcula-se como
`1 − transbordos/interações` (com `GREATEST(...,0)`), **nunca** com `sum_of_final_bot`.

```yaml meta
kind: term
id: transbordo
aliases: [transferência para humano, sum_of_transfers, transbordados]
```

Passagem da conversa do bot para um encantador humano. É o numerador da não-retenção e a origem do
`csat_transbordados`.

```yaml meta
kind: term
id: blended
aliases: [CSAT Blended]
quantified_by: csat-blended
```

Visão que junta avaliações do bot (Cami) e do humano numa única nota, somando as **contagens** de
positivas e negativas dos dois lados — não a média das duas taxas.

```yaml meta
kind: term
id: csat
aliases: [Customer Satisfaction, satisfação]
quantified_by: csat-humano
```

Proporção de avaliações positivas sobre o total avaliado (positivas + negativas). No Zendesk
detalhado o equivalente é `current_rating = 'good'` sobre os avaliados.

```yaml meta
kind: term
id: csat-retidos
aliases: [csat_retidos]
scoped_by: escopo-csat-retidos
```

Avaliação deixada por cliente que o bot **reteve** (resolveu sem transbordar). É a base do CSAT
Cami.

```yaml meta
kind: term
id: csat-transbordados
aliases: [csat_transbordados]
```

Avaliação deixada por cliente que foi **transbordado** para humano. Não entra no CSAT Cami.

```yaml meta
kind: term
id: dia-util
aliases: [DU, dias úteis, national_work_day, total_work_days]
quantified_by: dias-uteis
scoped_by: escopo-dias-uteis-nacionais
```

Dia útil nacional conforme `gold_common.dim_date.national_work_day` — exclui fim de semana **e**
feriado nacional. É o denominador de tudo que é "por DU" e do HC Líquido. Não confundir com o
filtro de dia útil da retenção, que usa `day_name` + `dim_chatbot_holidays`.

```yaml meta
kind: term
id: semana-de-referencia
aliases: [W15, W16, W17, semana, WoW]
```

Convenção de semana desta KB: bloco de **7 dias, de segunda a domingo**. W15 = 06–12/abr/2026,
W16 = 13–19/abr/2026, W17 = 20–26/abr/2026. Por incluírem fim de semana, distinguem a retenção KPI
da observada. "WoW" = week over week, a comparação com a semana anterior.

```yaml meta
kind: term
id: perfil-de-parceiro
aliases: [partner_profile, CONTADOR, BPO, MISTO]
```

Segunda dimensão de segmento, **dentro** do universo Parceiro: `CONTADOR` (empresa contábil /
contador), `BPO` (financial BPO), `MISTO` (consultoria ou empresa contábil com BPO — o Book chama
de "Contador BPO & Consultor") e `NULL` (cliente não é Parceiro, ou não houve match com uma
accountancy).

```yaml meta
kind: term
id: areas-de-atendimento
aliases: [area, assignee_area, BK, DN, EC, SAC - CA, SAC - Pessoalize, Ouvidoria - IP, RT, BACKING_OPS]
scoped_by: escopo-area-atendimento
```

Área do encantador. O Atendimento é `BK`, `DN`, `EC`, `SAC - CA` e `SAC - Pessoalize`. Fora do
escopo: `Ouvidoria - IP`, `RT` (fluxo de Retenção), `BACKING_OPS` (onde vive o Billing DN), além de
`ENG`, `SDM`, `TRAINING`, `OUVIDORIA` e `N/I` que aparecem no canal Web.

```yaml meta
kind: term
id: suporte-premium
aliases: [has_premium_support, SP]
```

Flag de contrato de suporte premium. Na segmentação do Telefone: TRUE = "Possui Suporte Premium",
FALSE = "Não Possui", NULL = "Não Identificado" (categoria numerosa).

```yaml meta
kind: term
id: encantador
aliases: [agente, atendente, HC, headcount]
quantified_by: hc-liquido
```

Atendente humano do time Servir. O "HC Líquido" é a média diária de encantadores ativos no período,
derivada de `is_active_workday`.

```yaml meta
kind: term
id: resolucao-no-primeiro-contato
aliases: [FCR, First Contact Resolution]
quantified_by: fcr
scoped_by: escopo-fcr-humano
```

% dos atendimentos resolvidos sem o cliente precisar voltar. Medido semanalmente na view
`vw_rps_fcr_semanal`, com `tipo` separando humano de bot.

```yaml meta
kind: term
id: pnps
aliases: [pNPS, NPS de produto]
quantified_by: nps
scoped_by: escopo-pnps
```

Pesquisa de NPS de produto, aplicada em ciclos por campanha. É o tipo de NPS com base relevante
nesta KB.

```yaml meta
kind: term
id: rnps
aliases: [rNPS, NPS relacional]
```

NPS relacional. **Praticamente inexistente**: 20 respostas no total (CA Mais, mar–abr/2026) — sem
base para análise.

```yaml meta
kind: term
id: promotor-neutro-detrator
aliases: [nps_classification, Promotor, Neutro, Detrator]
```

Classificação da nota de NPS, gravada **em português**: `Promotor` (nota 9–10), `Neutro` (7–8),
`Detrator` (0–6).

```yaml meta
kind: term
id: ferramenta-de-nps
aliases: [nps_tool, Survicate, IndeCX, Tracksale]
```

Plataforma que coletou a resposta. `Survicate` é a viva; `Tracksale` e `IndeCX` estão
descontinuadas. A virada IndeCX → Survicate foi em **31/12/2025** e é a razão de todo o histórico
anterior ter `nps_type = 'Não identificado'`.

```yaml meta
kind: term
id: ca-pro
aliases: [CA Pro, Conta Azul Pro]
```

Produto/segmento dos **donos de negócio (PME)**. Aparece como `segment` no NPS e como `team` no
`dim_chatbot`, e dá nome ao `bot_type` `Gen3 CA Pro`.

```yaml meta
kind: term
id: ca-mais
aliases: [CA Mais, Conta Azul Mais]
```

Produto/segmento dos **parceiros contadores**. Aparece como `segment` no NPS e como `team` no
`dim_chatbot`, e dá nome ao `bot_type` `Gen3 CA Mais`.

```yaml meta
kind: term
id: conta-pj
aliases: [Conta PJ]
```

Terceiro valor de `team` em `dim_chatbot`, ao lado de CA Mais e CA Pro.

```yaml meta
kind: term
id: rps
aliases: [RPS, Reunião de Performance Semanal, acompanhamento semanal]
```

O relatório semanal de acompanhamento do Atendimento, organizado por segmento (Blended, PME,
Parceiros, Telefone, Billing DN). É o consumidor final da maioria das métricas desta KB.

```yaml meta
kind: term
id: mtd
aliases: [MTD, Month to Date, acumulado do mês]
```

Acumulado do mês até a data. Ex.: "MTD abril" = 01–26/abr/2026 na validação desta KB — período que
tem **16 dias úteis**, não 18.

```yaml meta
kind: term
id: kr
aliases: [KR, Key Result, meta]
```

Meta de resultado usada como referência de leitura executiva (ex.: KR de CSAT Blended Parceiros de
79,1% para abril e 90% como meta final de dezembro). Não é um valor calculado a partir das tabelas.

```yaml meta
kind: term
id: book-pre-rmr
aliases: [Book Pré-RMR, Book]
```

Documento de referência de negócio auditado junto com o LookML. Usa vocabulário próprio em dois
pontos: chama a retenção de **Deflexão** e o perfil `MISTO` de "Contador BPO & Consultor". Filtra
canal no abandono e por isso reporta abandono menor que a measure oficial.

---

## 7. Notas

```yaml meta
kind: note
id: placeholders-de-periodo
```

As queries do `kb.md` **não** usam `@inicio`/`@fim`: usam os literais `'<inicio>'` e `'<fim>'`
(e `<qtd_du>` nos relatórios de HC), que devem ser substituídos antes de executar. A SQL foi
copiada verbatim, então os placeholders estão preservados como estão na fonte. Note também que a
coluna de data muda por fonte: `nk_event_date` na `fact_service_metrics`, `nk_date` no
`dim_chatbot`/`dim_date`, `event_date` no `agent_capacity`, `semana_inicio` no FCR e
`DATE(source_solved_at)` no Billing DN.

```yaml meta
kind: note
id: duplicidade-definicao-versus-query-validada
```

Cinco KPIs aparecem duas vezes no `kb.md`: uma vez como bloco de **definição** na §4 (sem janela de
data) e outra como **query validada** na §6/§10. Os pares são
`rel-demanda-total-definicao`/`rel-demanda-total-semanal`,
`rel-demanda-humana-por-canal-definicao`/`rel-demanda-humana-por-canal`,
`rel-csat-blended-pme-definicao`/`rel-csat-blended-pme-e-parceiro`,
`rel-retencao-cami-kpi-definicao`/`rel-retencao-cami-kpi-por-segmento` e o recorte de Parceiros
`rel-csat-parceiros-blended-humano-cami`. As duas versões foram preservadas verbatim; para executar,
prefira as validadas (parametrizadas). Os blocos de definição da §4 juntam mais de um `SELECT` na
mesma cerca e por isso **não são executáveis como estão**.

```yaml meta
kind: note
id: fragmentos-de-formula-preservados
```

Sete blocos ```` ```sql ```` do `kb.md` não são queries: são fragmentos de fórmula (TMA, TME,
SLA TME, % Abandono, Densidade, FTE) e um fragmento de lógica de data. Eles **não** viraram
`report` — o endereço deles é a `measure` correspondente (ou, no caso da data, o pitfall
`fallback-source-solved-at-em-tickets`), mas o texto foi preservado verbatim logo abaixo do bloco
`meta` a que pertence, para não perder a forma original.

```yaml meta
kind: note
id: serie-fcr-humano-2026
```

Série de FCR humano de 2026 registrada no `kb.md` (medida em 28/08/2026), preservada como
referência em prosa — **não** como gabarito: jan 65,31% · fev 69,19% · mar 70,25% · abr 72,13% ·
mai 69,03% · jun 70,45% · jul 68,22% · ago 71,04%. A cobertura da view vai de 27/04/2025 a
16/08/2026.

```yaml meta
kind: note
id: serie-pnps-2026
```

Série de pNPS de 2026 registrada no `kb.md` (medida em 28/08/2026), preservada como referência em
prosa — **não** como gabarito. CA Pro: mai 54,5 · jun 54,5 · jul 55,1 · ago 22,5 (contaminado, ver
`pnps-ca-pro-agosto-2026-contaminado`). CA Mais: mai 66,3 · jun 64,2 · jul 59,8 · ago 65,4.

```yaml meta
kind: note
id: valores-de-subcategory
```

Exemplo do que `dim_chatbot.subcategory` devolve em jul/26 no departamento Servir:
`Transferência sem Contexto` 5.730 · `Desistente` 5.456 · `Emissão de Nota Fiscal` 3.777 ·
`Falha na Emissão de Nota Fiscal` 2.438 · `Lançamentos Financeiros` 2.263 · `Conciliação bancária`
2.054 — mais de 25 categorias no total.

```yaml meta
kind: note
id: quebras-nao-recalculadas-na-fonte
```

O `kb.md` declara explicitamente que algumas quebras **não foram recalculadas** no ciclo de
28/08/2026 e seguem com números de abr/2026: a quebra de CSAT Cami PME por sub-segmento × bot_type,
a visão por categoria da Cami, a demanda/CSAT de Parceiros e PME no MTD de abril, e as quebras por
segmento do Telefone. Some isso a `tabelas-reprocessadas-retroativamente` antes de comparar
qualquer número antigo com uma execução de hoje.

```yaml meta
kind: note
id: valores-de-referencia-datados-descartados
```

As tabelas de validação W16/W17 da §7, a leitura executiva de Parceiros da §10 e os 7 insights
datados da §11 do `kb.md` **não** foram transportados para esta camada: são valores conferidos
contra dashboard num recorte específico de abril/2026, que o próprio `kb.md` marca como alvo móvel.
O que neles era regra atemporal virou pitfall — `anomalia-channel-vazio-abril-2026`,
`du-derive-da-dim-date`, `tabelas-reprocessadas-retroativamente`,
`volume-de-avaliacoes-cami-muda-com-reprocessamento`, `fin-ai-concentra-as-avaliacoes-cami`,
`abandono-telefone-vem-de-customer-type-nulo`, `integracao-bancaria-com-diff-pendente` e
`categoria-vendas-e-na-com-divergencia`. Para valores atuais, execute os relatórios da §4.

```yaml meta
kind: note
id: tabelas-de-apoio-sem-uso-documentado
```

`gold_common.dim_company` e `gold_common.dim_accountancy` estão listadas como tabelas de apoio no
`kb.md`, mas nenhuma query da KB as usa e não há dicionário de colunas para elas. Foram mantidas
como `source` só para preservar a listagem — trate qualquer uso como não documentado.
