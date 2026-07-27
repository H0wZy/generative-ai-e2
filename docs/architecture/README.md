# Arquitetura do Projeto

## Decisão de referência

O sistema possui dois bounded contexts independentes:

- **Automação operacional:** Freshservice → Jira, com PostgreSQL como fonte de verdade.
- **RAG local:** documentação do projeto indexada em SQLite + sqlite-vec e exposta por MCP.

PostgreSQL + pgvector não faz parte do MVP. Ele é uma alternativa futura caso o RAG precise ser hospedado, compartilhado ou executado em múltiplas instâncias.

## Arquitetura-alvo do MVP

```text
Freshservice → n8n → FastAPI (ingestão) → PostgreSQL
                                      │
                                      ▼
                              fila / worker assíncrono
                                      │
                                      ▼
                                Jira REST API

docs Markdown → sync → chunking → embeddings → SQLite + sqlite-vec → MCP
```

### Responsabilidades

| Componente | Responsabilidade | Não é responsável por |
|---|---|---|
| n8n | Receber/adaptar webhook e chamar a API de ingestão | Regras de roteamento, estado de negócio ou idempotência |
| FastAPI | Contratos, validação, regras, classificação, idempotência e APIs operacionais | Persistência de execuções do n8n |
| Worker | Executar efeitos externos, retries e atualização do estado | Expor API síncrona |
| PostgreSQL | Fonte de verdade operacional, auditoria e estado de processamento | Embeddings do RAG local |
| SQLite + sqlite-vec | Base RAG local e de usuário único | Dados operacionais ou uso multi-instância |
| MCP | Busca somente leitura, com proveniência | Acesso SQL arbitrário ou operações de escrita |

## Serviços e Cloud Run

- A API FastAPI e o worker devem ser serviços independentes, com contas de serviço e escalonamento próprios.
- PostgreSQL deve ser gerenciado e acessado com credenciais de menor privilégio.
- n8n requer persistência de execuções, credenciais e configuração; deve operar em runtime gerenciado/dedicado ou com sua infraestrutura de persistência explicitamente provisionada. Não deve ser considerado um container stateless comum.
- O RAG SQLite e Ollama permanecem locais no MVP. Cloud Run não é destino apropriado para uma base SQLite compartilhada ou para inferência pesada sem validação de limites de CPU, memória, disco e concorrência.
- OCR futuro deve ser serviço separado, acionado por fila, com timeout, armazenamento de objetos e limites de arquivo próprios.

## Organização-alvo

```text
backend/
  app/
    api/ domain/ services/ repositories/ integrations/ schemas/ core/
  tests/
  migrations/
rag/
  chunking/ embeddings/ sync/ search/ mcp/ data/
database/
  migrations/ seeds/
docs/
  architecture/ handoffs/ ai/
```

Esses diretórios são alvo de implementação; a estrutura atual deve ser sempre verificada antes de qualquer mudança.

## Observabilidade

Todo evento operacional deve ter `correlation_id`, `ticket_id`, `workflow_execution_id`, serviço, operação, status, duração e motivo de falha. Métricas mínimas: recebidos, concluídos, falhas, retries, itens em DLQ, duplicidades evitadas e latência ponta a ponta.

## Segurança

- Segredos no Secret Manager; nunca em arquivos versionados ou logs.
- Webhooks autenticados, com validação de assinatura/segredo, timestamp e proteção contra replay quando o provedor suportar.
- Contas de serviço e tokens externos com menor privilégio.
- Logs e evidências sanitizados; usar dados fictícios ou anonimizados.
- MCP com leitura restrita, allowlist de caminhos e limites de consulta.

## Roadmap

- **MVP:** ingestão de ticket sintético, regra determinística de squad, criação idempotente no Jira, auditoria e demo RAG Markdown local.
- **V1:** classificação assistida por LLM com JSON validado, fila/DLQ, dashboard de exceções e métricas.
- **V2:** OCR assíncrono, busca híbrida/reranking, RAG hospedado e controle de acesso por documento.
