# Handoff — Automação Freshservice → Jira

## Objetivo

Transformar tickets do Freshservice em issues Jira no backlog da squad correta, com rastreabilidade, segurança e reprocessamento seguro.

## Arquitetura

```text
Freshservice ←(polling)← FastAPI → PostgreSQL → fila/worker → Jira REST API
```

FastAPI é dono do contrato, das regras de negócio, da classificação, da idempotência e do estado operacional. O worker faz o polling do Freshservice, executa as chamadas externas e os retries.

**Mudança em relação ao desenho original (ADR-007):** o fluxo era `Freshservice → webhook → n8n → FastAPI`. O tenant sandbox é um serviço em nuvem; para entregar um webhook, a API local precisaria estar publicamente acessível — túnel mais autenticação de boundary que o MVP não tem, e que invalidaria a aceitação de "sem autenticação porque é execução local" registrada no README. O polling mantém a superfície local e elimina o segredo de assinatura do webhook. n8n permanece fora de escopo.

**Freshservice é um mock, não o tenant real (ADR-011):** a conta não teve a API key liberada pelo admin do tenant do cliente, e replicar o tenant real é fora de escopo. `FreshserviceClient` fala o mesmo protocolo HTTP (`GET /api/v2/tickets`), só que contra um mock. Jira roda contra conta sandbox real.

## Responsabilidades

| Componente | Responsabilidade |
|---|---|
| Freshservice | Origem do evento e dados do ticket, incluindo o campo de squad |
| Poller | Ler tickets atualizados desde a marca de sincronização e chamar a ingestão |
| FastAPI | Validar schema, persistir estado, decidir roteamento e expor operação |
| Worker | Criar/localizar issue Jira, retry e atualização de estado |
| Jira | Backlog de destino (projeto único; a squad vai como rótulo da issue) |
| PostgreSQL | Fonte de verdade operacional, auditoria, vínculo e reprocessamento |

## Requisitos funcionais

1. Receber ticket e preservar identificador de origem.
2. Normalizar título, descrição, prioridade, categoria, solicitante e metadados autorizados de anexos.
3. Identificar squad e backlog por regras versionadas — a squad vem do próprio campo do chamado, validada contra o enum fechado das 8 squads genéricas do mock (ADR-011, substitui as 13 squads reais do ADR-006); casos sem squad conhecida seguem para revisão humana.
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

- Não há webhook a autenticar: a leitura é iniciada por nós, com chave de API em Basic Auth (ADR-007).
- Distinguir falha de credencial (`auth`), de conectividade (`connectivity`, inclui bloqueio de proxy corporativo) e de negócio (`business`) na causa registrada — um proxy respondendo 403 é indistinguível de chave rejeitada sem essa separação.
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
