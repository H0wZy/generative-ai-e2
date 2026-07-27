# Handoff — Automação Freshservice → Jira

## Objetivo

Transformar tickets do Freshservice em issues Jira no backlog da squad correta, com rastreabilidade, segurança e reprocessamento seguro.

## Arquitetura

```text
Freshservice → webhook → n8n → FastAPI → PostgreSQL → fila/worker → Jira REST API
```

O n8n é adaptador e orquestrador de integração. FastAPI é dono do contrato, das regras de negócio, da classificação, da idempotência e do estado operacional. O worker executa chamadas externas e retries.

## Responsabilidades

| Componente | Responsabilidade |
|---|---|
| Freshservice | Origem do evento e dados do ticket |
| n8n | Receber/adaptar webhook e chamar a ingestão autenticada |
| FastAPI | Validar schema, persistir estado, decidir roteamento e expor operação |
| Worker | Criar/localizar issue Jira, retry e atualização de estado |
| Jira | Backlog de destino |
| PostgreSQL | Fonte de verdade operacional, auditoria, vínculo e reprocessamento |

## Requisitos funcionais

1. Receber ticket e preservar identificador de origem.
2. Normalizar título, descrição, prioridade, categoria, solicitante e metadados autorizados de anexos.
3. Identificar squad e backlog por regras versionadas; casos de baixa confiança seguem para revisão humana.
4. Criar ou localizar a issue correspondente no Jira.
5. Registrar decisão, tentativas, falhas e vínculo ticket ↔ Jira.

## Confiabilidade

- A chave de idempotência é única por sistema de origem, ticket e evento/versão.
- O processamento persiste ticket e evento antes de chamar Jira.
- Retry usa backoff exponencial com jitter e limite de tentativas.
- Falhas não recuperáveis ou tentativas esgotadas seguem para DLQ, com reprocessamento idempotente.
- A confirmação de sucesso só ocorre após persistir o vínculo Jira.

## Classificação de squad

Aplicar regras determinísticas primeiro. LLM é opcional e apenas para ambiguidade, com JSON validado, prompt/modelo versionados, score de confiança e fallback para revisão humana. Um golden set deve medir a qualidade antes de ativar automação.

## Segurança e dados

- Confirmar o mecanismo disponível de autenticação/assinatura do webhook no Freshservice antes de implementar.
- Autenticar chamadas n8n → FastAPI e validar payload versionado.
- Armazenar segredos em Secret Manager e aplicar menor privilégio em Jira/Freshservice.
- Definir MIME allowlist, tamanho, retenção e verificação de anexos antes de transferi-los.
- Não registrar credenciais ou PII desnecessária em logs, DLQ, screenshots ou evidências.

## Observabilidade

Cada execução deve registrar `correlation_id`, ticket de origem, `workflow_execution_id`, status, tentativa, serviço, duração e causa de falha. Métricas mínimas: recebidos, concluídos, falhas, retries, DLQ, duplicidades evitadas e latência ponta a ponta.

## Referências

- [Contrato operacional](../architecture/operational-contract.md)
- [Freshservice API](https://api.freshservice.com/v1/)
- [Jira REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/)
- [n8n Freshservice credentials](https://docs.n8n.io/integrations/builtin/credentials/freshservice/)
