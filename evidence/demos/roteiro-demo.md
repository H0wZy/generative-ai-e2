# Roteiro de Demonstração — MVP Freshservice → Jira

**Data:** 2026-07-25
**Duração alvo:** 6 a 8 minutos
**Dados:** exclusivamente sintéticos

Este roteiro foi construído a partir de execução real. Todos os comandos e
saídas abaixo foram executados e verificados por query no PostgreSQL antes de
serem escritos aqui.

---

## Declaração de honestidade — dizer isto em voz alta na gravação

A demonstração roda com o **adaptador Jira falso** (`FakeJiraClient`), que é
ativado automaticamente quando `JIRA_BASE_URL`, `JIRA_EMAIL` e
`JIRA_API_TOKEN` não estão configurados. Nenhuma chamada de rede é feita.

O adaptador real (`JiraClient`, Jira REST API v3) existe, está implementado e
tem testes — incluindo retry em 5xx, falha terminal em 4xx e um teste que
garante que a mensagem de erro nunca vaza corpo de resposta, URL de tenant ou
credencial. Ele é ativado apenas configurando as três variáveis.

Narrar isso explicitamente. Um avaliador que descobre sozinho que a issue era
falsa lê como omissão; um avaliador que ouve a distinção lê como rigor.

---

## Pré-condições — conferir ANTES de apertar REC

### 1. Configuração assimétrica das chaves de projeto (crítico)

A cena de falha depende de uma chave de projeto ausente. A cena de sucesso
depende de outra presente. Em `backend/.env`:

```bash
JIRA_PROJECT_PLATFORM=PLAT      # DESCOMENTADA — cena de sucesso
# JIRA_PROJECT_FINANCE=FIN      # COMENTADA — cena de falha
# JIRA_PROJECT_IDENTITY=IDEN    # indiferente
```

Conferir sem revelar valores na tela:

```bash
grep -nE "^[[:space:]]*#?[[:space:]]*JIRA_PROJECT_" backend/.env
```

**Se `JIRA_PROJECT_PLATFORM` estiver comentada, o caminho feliz falha no
primeiro comando da demo.** É o erro mais provável desta gravação.

### 2. Stack no ar

```bash
make up && make migrate          # PostgreSQL + schema
make serve                       # API em :8000 (terminal próprio)
cd frontend && npm run dev       # dashboard em :3000 (terminal próprio)
```

Confirmar os dois:

```bash
curl -s localhost:8000/health    # {"status":"ok"}
curl -s -o /dev/null -w '%{http_code}\n' localhost:3000   # 200
```

### 3. Banco limpo

Um banco com workflows de testes anteriores polui os cards de métricas. Para
começar do zero:

```bash
docker compose exec postgres psql -U genai_e2 -d genai_e2 -c \
  "TRUNCATE audit_logs, outbox_events, routing_decisions, external_references,
   jira_issue_links, workflow_executions, tickets CASCADE;"
```

---

## Cena 1 — O problema (30s, sem comando)

Mostrar o dashboard vazio em `localhost:3000`.

**Narrar:** ticket chega no Freshservice, alguém lê, decide de qual squad é,
abre a issue no Jira à mão, copia e cola descrição. Repete dezenas de vezes por
dia. Erra a squad, duplica issue, perde rastro.

---

## Cena 2 — Ingestão (1 min)

```bash
make ingest-demo
```

Saída esperada:

```json
{
    "workflow_execution_id": "<uuid>",
    "internal_correlation_id": "<uuid>",
    "status": "accepted"
}
```

**Narrar:** a API aceitou e respondeu na hora, sem esperar o Jira. O ticket, a
execução e o evento de saída foram gravados numa transação só. O
`internal_correlation_id` é gerado aqui dentro — não é o id que veio de fora,
porque identificador de terceiro não serve como chave de rastreabilidade.

Mostrar o dashboard: uma linha, status `pending`, sem chave Jira.

---

## Cena 3 — Roteamento e criação (1 min)

```bash
make worker-once
```

Saída esperada:

```
[worker] workflow=<uuid> status=completed attempts=1 jira_key=PLAT-123
```

Atualizar o dashboard: linha verde, squad `platform`, confiança `1.0`, chave
`PLAT-123`.

**Narrar:** o worker aplicou a regra determinística — categoria `incident` vai
para a squad `platform` — e criou a issue. A chave só é gravada depois que o
vínculo persiste. Não existe "issue criada mas não registrada".

---

## Cena 4 — Idempotência (1min30, a cena mais importante)

### 4a. Reingestão do mesmo ticket

```bash
make ingest-demo
```

Saída esperada: `"status": "duplicate"`, com o **mesmo**
`workflow_execution_id` da cena 2.

Mostrar no dashboard que continua existindo **uma** linha.

### 4b. Reprocessar o que já foi concluído

No dashboard, o botão de reprocessar não aparece em linha concluída. Provar via
API:

```bash
curl -s -X POST localhost:8000/api/v1/workflows/<uuid>/reprocess -w '\nHTTP %{http_code}\n'
```

Saída esperada:

```json
{"workflow_execution_id":"<uuid>","status":"completed","jira_issue_key":"PLAT-123","reprocessed":false,"reason":"already_linked"}
HTTP 409
```

Provar no banco:

```bash
docker compose exec postgres psql -U genai_e2 -d genai_e2 -c \
  "SELECT COUNT(*) FROM jira_issue_links;"
```

**Narrar:** o webhook repetiu, alguém clicou duas vezes, o n8n reenviou — não
importa. Uma issue. O `reason` diz por quê: `already_linked`. Esta é a
propriedade que separa automação confiável de automação que polui o backlog.

---

## Cena 5 — A exceção e a recuperação (2 min)

### 5a. Provocar a falha

```bash
curl -s -X POST localhost:8000/api/v1/tickets/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "evt-billing-001",
    "event_type": "ticket.created",
    "occurred_at": "2026-07-25T14:00:00Z",
    "source_ticket_id": "FS-200",
    "subject": "Cobranca duplicada em fatura",
    "description": "Fatura sintetica para demonstracao.",
    "priority": "high",
    "category": "billing",
    "requester": "billing@example.test",
    "attachments": [],
    "external_correlation_id": "demo-billing-001"
  }' | python3 -m json.tool

make worker-once
```

Saída esperada:

```
[worker] workflow=<uuid-2> status=failed attempts=1 jira_key=None
```

Dashboard: linha destacada como falha, com `no_project_key_for_squad:finance`.

**Narrar:** categoria `billing` roteia para a squad `finance`, que não tem
projeto Jira configurado. Falha terminal, registrada, visível. O erro é curto e
descritivo de propósito — mensagem de erro que ecoa corpo de resposta é como
credencial vaza para tela e para log.

### 5b. Corrigir e recuperar

Reprocessar primeiro, ainda quebrado, para mostrar que reprocessar não é mágica:

```bash
curl -s -X POST localhost:8000/api/v1/workflows/<uuid-2>/reprocess -w '\nHTTP %{http_code}\n'
```

Saída: `HTTP 200`, `"reprocessed":true`, `"reason":null` — volta para `pending`.

Corrigir a configuração:

```bash
# descomentar JIRA_PROJECT_FINANCE=FIN em backend/.env
```

**Reiniciar a API** (a configuração é lida na inicialização) e rodar o worker:

```bash
make worker-once
```

Saída esperada:

```
[worker] workflow=<uuid-2> status=completed attempts=2 jira_key=FIN-123
```

Dashboard: linha verde, chave `FIN-123`, **sem mensagem de erro** — o campo de
erro é limpo no sucesso, o histórico fica na auditoria.

**Narrar:** a chave é `FIN-123`, não `PLAT-123`. Squad diferente, backlog
diferente. É isso que o roteamento faz.

> **Ponto de risco ao vivo:** este é o único passo que exige editar arquivo e
> reiniciar processo durante a gravação. Ter o backup pronto.

---

## Cena 6 — Rastreabilidade (1 min, fecho)

```bash
docker compose exec postgres psql -U genai_e2 -d genai_e2 -c \
  "SELECT event_type, created_at FROM audit_logs
   WHERE workflow_execution_id = '<uuid-2>' ORDER BY created_at;"
```

Saída esperada:

```
 ticket.ingested
 jira.failed
 workflow.reprocess_requested
 jira.issue_linked
```

**Narrar:** quatro linhas contam a história inteira do ticket — chegou, falhou,
foi reprocessado por decisão humana, virou issue. Auditoria não é log: é estado
consultável.

---

## Plano de backup

Gravar ANTES, em arquivo separado, e ter aberto numa aba durante a demo:

1. Vídeo curto do ciclo completo das cenas 2 a 5, já executado com sucesso
2. Captura do dashboard com as três situações simultâneas: concluído, falha e
   pendente
3. Captura da saída do `psql` da cena 6

Se qualquer serviço não subir na hora, narrar a captura sem tentar depurar ao
vivo. Depuração em gravação queima o tempo e a atenção do avaliador.

---

## Checklist de sanitização — conferir antes de gravar e depois de gravar

**No terminal:**

- [ ] `backend/.env` NUNCA aberto na tela. Para conferir chave, usar o `grep`
      que mostra só o nome da variável
- [ ] Histórico do shell limpo de comandos com token (`history -c` se necessário)
- [ ] Prompt do shell não expõe caminho com nome de cliente ou de projeto interno
- [ ] Nenhum `docker compose config` ou `env` na tela (imprimem segredo)

**Na tela do navegador:**

- [ ] Nenhuma aba com sistema corporativo (Freshservice real, Jira corporativo,
      e-mail, chat interno)
- [ ] Notificações do sistema operacional silenciadas
- [ ] Gerenciador de senhas fechado

**Nos dados:**

- [ ] Apenas `FS-100` e `FS-200` sintéticos, `@example.test`
- [ ] Nenhum ticket, nome, e-mail ou anexo real da TCS ou de cliente
- [ ] Se o Jira real for usado em vez do fake: tenant pessoal, projeto criado
      para a demo, nunca tenant corporativo

**Depois de gravar, antes de enviar:**

- [ ] Assistir o vídeo inteiro procurando token, URL de tenant e e-mail
- [ ] Conferir que nenhum quadro mostra `.env` aberto

---

## Restauração do ambiente após a gravação

```bash
# recomentar JIRA_PROJECT_FINANCE em backend/.env
make down
```
