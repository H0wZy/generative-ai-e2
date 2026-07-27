# Contrato Operacional — Freshservice → Jira

## Objetivo

Definir as responsabilidades e o comportamento confiável do fluxo antes da implementação. Os campos finais do webhook devem ser confirmados na documentação e no tenant configurado do Freshservice.

## Fluxo

```text
Freshservice → n8n → POST /tickets/ingest → PostgreSQL → fila/worker → Jira
```

1. n8n valida o webhook conforme a capacidade documentada do Freshservice e repassa um payload normalizado ao FastAPI.
2. FastAPI autentica n8n, valida o schema e grava ticket, execução e chave de idempotência em uma transação.
3. A transação grava um evento de saída para processamento assíncrono e retorna aceite, sem esperar o Jira.
4. O worker calcula o roteamento, cria ou localiza a issue Jira e persiste o vínculo.
5. Falhas recuperáveis sofrem retry; falhas esgotadas seguem para DLQ e podem ser reprocessadas pelo dashboard.

## Contrato lógico de ingestão

Campos mínimos: `event_id`, `event_type`, `occurred_at`, `source_ticket_id`, `subject`, `description`, `priority`, `category`, `requester`, `attachments` e `correlation_id`.

O contrato deve ser versionado. Campos desconhecidos são preservados apenas quando necessários para auditoria e sempre sujeitos à classificação de dados e mascaramento.

## Idempotência e retry

- Chave de idempotência: combinação única de `source_system`, `source_ticket_id` e versão/tipo do evento.
- A criação Jira deve registrar `jira_issue_key` antes de marcar a execução como concluída.
- Retries usam backoff exponencial com jitter, limite de tentativas e classificação explícita de erro recuperável ou definitivo.
- Reprocessamento reutiliza a mesma chave de idempotência; nunca cria uma nova issue sem verificar o vínculo existente.

## Classificação de squad

Regras determinísticas são a primeira opção. Casos ambíguos podem usar LLM com saída JSON validada, versão de prompt/modelo e score de confiança. Abaixo do limiar definido, o item segue para revisão humana, não para criação automática.

## Anexos e dados

Anexos devem ter metadados, tamanho máximo, MIME allowlist, verificação de segurança e política de retenção definidos antes de serem transferidos. Logs, DLQ e evidências não podem conter conteúdo sensível desnecessário.
