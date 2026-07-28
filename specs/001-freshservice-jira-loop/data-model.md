# Data Model — Fase 1

Duas populações no mesmo banco PostgreSQL, deliberadamente separadas:

- **Operacional** (schema `public`, já existe): chamados que passaram pelo
  fluxo de tombamento. É o "depois".
- **Histórica** (schema `analytics`, novo): o export do Power BI, espelho dos
  arquivos. É o "antes".

Só uma coisa atravessa as duas: a **origem do vínculo** chamado ↔ issue.

---

## Migration `002_link_origin`

Aditiva. Duas colunas, ambas com default, nenhuma reescrita de tabela.

### `tickets` — coluna nova

| Coluna | Tipo | Nulo | Default | Razão |
|---|---|---|---|---|
| `squad` | `varchar(40)` | sim | — | A squad vem preenchida do Freshservice (R-001). Guardar o valor de origem separa "o que a fonte disse" de "o que o roteamento decidiu" (`workflow_executions.squad_id`) |

### `jira_issue_links` — coluna nova

| Coluna | Tipo | Nulo | Default | Razão |
|---|---|---|---|---|
| `link_origin` | `varchar(20)` | não | `'deterministic'` | R-006. Todo vínculo criado pela automação é determinístico; o default cobre as linhas já existentes sem backfill |

Restrição: `link_origin IN ('deterministic', 'best_effort')` — `CHECK`, não
enum de banco, para não exigir migration em cada valor novo.

### `sync_state` — tabela nova (schema `public`)

| Coluna | Tipo | Razão |
|---|---|---|
| `source` | `text`, PK | `freshservice` |
| `last_sync_at` | `timestamptz` | Marca do poller (R-003). Consultada antes de cada chamada à API do Freshservice |

Pequena de propósito: é estado de integração, não dado de negócio. Fica no
schema operacional para que o tombamento não dependa da carga histórica.

### Não muda

`uq_ticket_event`, `outbox_events`, `routing_decisions`, `audit_logs`,
`external_references` e a unicidade `jira_issue_links.ticket_id` permanecem
como estão. A idempotência do fluxo não é tocada por esta feature.

---

## Migration `003_analytics_schema`

Cria o schema `analytics` e três tabelas espelho dos arquivos, na regra do
`data-receiver`: **cada arquivo tem sua tabela, coluna a coluna**, nome =
cabeçalho do Excel em snake_case sem acento. Célula vazia vira `NULL` — sem
placeholder fabricado.

### `analytics.chamados_abertos`

27 colunas do export de chamados em aberto, mais colunas de aplicação:

| Coluna de aplicação | Tipo | Razão |
|---|---|---|
| `synced_at` | `timestamptz` | Momento da carga. `timestamptz`, não `timestamp` — o `data-receiver` já pagou o preço do naive: a faixa "última atualização" exibia UTC com rótulo de hora local |
| `anonymized` | `boolean` | Marca que os campos de pessoa já passaram por R-005. `false` nunca deve existir em linha persistida; a coluna existe para tornar a violação detectável por consulta |

Chave: `source_id` (o `ID` do Excel, formato `LETRAS-NÚMEROS`), único.
Linha cujo `ID` não bate o formato é descartada na ingestão — é o rodapé de
filtros do export, que já produziu um chamado fantasma com data no ano 48113.

### `analytics.chamados_fechados`

28 colunas do export de fechados (tem `SLA` e `Tempo de Resolução`, que o de
abertos não tem), mais `synced_at` e `anonymized`. Mesma chave, mesma regra de
descarte.

Um chamado pode existir nas duas tabelas quando fecha entre uma exportação e
outra. Nas consultas que unem as duas, **fechados vencem**.

### `analytics.jira_cards`

15 colunas do CSV do Jira, mais:

| Coluna de aplicação | Tipo | Razão |
|---|---|---|
| `freshservice_ticket_id` | `varchar(20)`, nulo | Vínculo best-effort extraído do `Summary`. Sem FK física: o número pode apontar para um chamado fora da janela exportada |
| `synced_at` | `timestamptz` | Idem acima |
| `anonymized` | `boolean` | Idem acima |

Chave: `issue_key`, único.

> `sync_state` **não** fica aqui — ver migration `002`. É estado do fluxo
> operacional (polling), não da base histórica; deixá-la no schema `analytics`
> faria o tombamento depender da carga do export.

---

## Entidades e relações

```text
                        ┌──────────────────────────┐
   OPERACIONAL          │ tickets                  │
   (public)             │  source_ticket_id (uq)   │
                        │  squad          ← novo   │
                        └────────────┬─────────────┘
                                     │ 1:N
                        ┌────────────▼─────────────┐
                        │ workflow_executions      │
                        │  squad_id (decidido)     │
                        │  status, attempt_count   │
                        └────────────┬─────────────┘
                          1:N │      │ 1:1 (via ticket)
              ┌───────────────▼──┐ ┌─▼────────────────────────┐
              │ routing_decisions│ │ jira_issue_links         │
              │  rule_version    │ │  jira_issue_key (uq)     │
              │  confidence      │ │  link_origin ← novo      │
              └──────────────────┘ └──────────────────────────┘

                        ┌──────────────────────────┐
   HISTÓRICA            │ chamados_abertos         │
   (analytics)          │ chamados_fechados        │
                        │  source_id (uq)          │
                        └────────────▲─────────────┘
                                     │ N:1, best-effort, sem FK
                        ┌────────────┴─────────────┐
                        │ jira_cards               │
                        │  freshservice_ticket_id  │
                        └──────────────────────────┘
```

### Regra de extração do vínculo histórico (FR-015)

Ordem de prioridade, portada sem alteração:

1. Prefixo explícito `SR-` ou `INC-` seguido de 6 dígitos, em qualquer ponto do
   `Summary` — aceita hífen normal e as variantes invisíveis (non-breaking,
   travessão) que aparecem em texto copiado de outra ferramenta.
2. Se não achar: número solto de 6 dígitos, **e apenas quando houver exatamente
   um distinto**. `PAV (277795/357558)` não vincula.
3. Nada encontrado ou ambíguo: `NULL`. Não é erro.

O número é guardado **sem prefixo** (`143695`, não `SR-143695`), e o lado do
Freshservice remove o prefixo do `source_id` antes de comparar.

Cardinalidade: **N:1** — vários cards para um chamado; um card nunca aponta
para mais de um. Na base de exemplo, um chamado é citado por 29 cards.

### Regra de cobertura (o número da feature)

```text
cobertura_best_effort  = cards com freshservice_ticket_id que casa com um
                         chamado existente  ÷  total de cards
cobertura_deterministica = links com link_origin='deterministic'
                         ÷  chamados tombados pela automação
```

Linha de base medida na base de exemplo: 368/428 cards têm número extraível
(86%), 312 casam com chamado real. Alvo do "depois": 100% (SC-001).

---

## Validações

| Regra | Onde vale | Falha resulta em |
|---|---|---|
| `squad` do chamado dentro do enum fechado de 13 valores | Roteamento (F1) | Fallback: LLM se habilitado, senão revisão humana |
| `link_origin ∈ {deterministic, best_effort}` | Banco (`CHECK`) | Erro de escrita — bug, não caso de negócio |
| `source_id` no formato `LETRAS-NÚMEROS` | Ingestão histórica | Linha descartada, silenciosamente contabilizada |
| Arquivo acima de 20 MB | Pré-visualização de upload | `too_large` no preview, ignorado no commit, demais arquivos seguem |
| Assinatura de coluna não reconhecida | Pré-visualização de upload | `unknown`, mesmo tratamento acima |
| Campos de pessoa pseudonimizados | Antes de qualquer `INSERT` | Bloqueio da carga — nunca gravar identificável |
| Lote de upsert ≤ 1.000 linhas | Ingestão histórica | Acima disso, o limite de 65.535 parâmetros bind do Postgres derruba o `INSERT` inteiro |

---

## Transições de estado (inalteradas)

`workflow_executions.status` continua com a máquina atual:

```text
pending → processing → completed
                    ├→ retry_scheduled → (volta a processing, até 5 tentativas)
                    ├→ failed
                    └→ needs_human_review
```

`failed` e `needs_human_review` são reprocessáveis; o reprocessamento reutiliza
a chave de idempotência e, se já houver `jira_issue_links` para o ticket,
responde `already_linked` sem tocar no Jira.
