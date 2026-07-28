# Contrato Operacional — Freshservice → Jira

## Objetivo

Definir as responsabilidades e o comportamento confiável do fluxo antes da implementação. Os campos finais do webhook devem ser confirmados na documentação e no tenant configurado do Freshservice.

## Fluxo

```text
Freshservice ←(polling)← worker → POST /tickets/ingest → PostgreSQL → fila/worker → Jira
```

> **Atualizado (ADR-007):** o webhook via n8n foi substituído por polling. O tenant sandbox é nuvem e o webhook exigiria expor a API publicamente, o que o MVP não sustenta sem autenticação de boundary. A ingestão continua sendo o mesmo endpoint e a mesma chave de idempotência.

1. O poller lê os tickets atualizados desde a marca de sincronização (`sync_state`) e normaliza o payload. A marca só avança depois da página inteira persistida, usando o horário de início do poll.
2. FastAPI valida o schema e grava ticket, execução e chave de idempotência em uma transação.
3. A transação grava um evento de saída para processamento assíncrono e retorna aceite, sem esperar o Jira.
4. O worker calcula o roteamento, cria ou localiza a issue Jira e persiste o vínculo.
5. Falhas recuperáveis sofrem retry; falhas esgotadas seguem para DLQ e podem ser reprocessadas pelo dashboard.

## Contrato lógico de ingestão

Campos mínimos: `event_id`, `event_type`, `occurred_at`, `source_ticket_id`, `subject`, `description`, `priority`, `category`, `squad`, `requester`, `attachments` e `correlation_id`.

`squad` é o campo que dirige o roteamento determinístico (ADR-006). `event_id` carrega o `updated_at` do ticket, de modo que uma edição produz um evento novo e uma releitura sem alteração produz a mesma chave de idempotência.

O contrato deve ser versionado. Campos desconhecidos são preservados apenas quando necessários para auditoria e sempre sujeitos à classificação de dados e mascaramento.

## Idempotência e retry

- Chave de idempotência: combinação única de `source_system`, `source_ticket_id` e versão/tipo do evento.
- A criação Jira deve registrar `jira_issue_key` antes de marcar a execução como concluída.
- Retries usam backoff exponencial com jitter, limite de tentativas e classificação explícita de erro recuperável ou definitivo.
- Reprocessamento reutiliza a mesma chave de idempotência; nunca cria uma nova issue sem verificar o vínculo existente.

## Classificação de squad

A squad vem preenchida do chamado e é validada contra o enum fechado das 8 squads genéricas do mock de Freshservice (`SQUAD-01`..`SQUAD-08`, ADR-011) — determinístico, confiança `1.0`, sem chamada ao modelo. Campo vazio ou valor fora do enum pode usar LLM, com saída JSON validada, versão de prompt/modelo e score de confiança. Abaixo do limiar, o item segue para revisão humana, não para criação automática.

## Destino no Jira

Um projeto (`JIRA_PROJECT_KEY`); a squad vai como rótulo `squad-<id>` da issue (ADR-008). O rótulo `freshservice-<source_ticket_id>` é o vínculo estruturado: o número do chamado não depende de estar citado no título da issue. Squad sem destino configurado é falha explícita, nunca criação em projeto arbitrário.

## Anexos e dados

Anexos devem ter metadados, tamanho máximo, MIME allowlist, verificação de segurança e política de retenção definidos antes de serem transferidos. Logs, DLQ e evidências não podem conter conteúdo sensível desnecessário.
