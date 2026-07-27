# GENERATIVE-AI-E2

Projeto do Bootcamp Gen AI E2 da TCS para demonstrar a aplicação de IA Generativa no ciclo completo de desenvolvimento.

## Objetivo

Automatizar a criação de issues no Jira a partir de tickets do Freshservice, com roteamento para a squad correta, rastreabilidade e operação segura. Em paralelo, o projeto inclui um laboratório RAG local, exposto por MCP, para consulta à documentação do repositório.

## Estado do Repositório

O repositório está na fase de arquitetura e documentação. A árvore abaixo descreve a organização **alvo**, e não afirma que todos os módulos já estão implementados.

## Decisões Arquiteturais

- **Dados operacionais:** PostgreSQL, usado exclusivamente para tickets, roteamento, execução de workflows, auditoria e configuração.
- **RAG do MVP:** SQLite + sqlite-vec, local e independente do banco operacional. Não é um banco compartilhado entre instâncias Cloud Run.
- **Integração:** n8n é adaptador de webhook e orquestração; FastAPI é o dono das regras de negócio, idempotência e integração com Jira.
- **OCR:** evolução pós-MVP, isolada e assíncrona.

## Iniciativas

1. [Freshservice → Jira](./docs/handoffs/freshservice-jira.md)
2. [RAG Local + MCP](./docs/handoffs/rag-mcp.md)

## Documentação

- [Arquitetura](./docs/architecture/README.md)
- [Contrato operacional Freshservice → Jira](./docs/architecture/operational-contract.md)
- [Banco de dados](./database/README.md)
- [Uso e evidências de IA](./docs/ai/README.md)
- [Índice de handoffs](./docs/handoffs/README.md)

## Escopo do MVP — o que ficou de fora

Estas são limitações conhecidas e deliberadas, não descobertas tardias. Foram
revisadas em 2026-07-25 por validação funcional e por revisão de segurança
defensiva.

**Superfície sem autenticação.** A API de ingestão, o endpoint de
reprocessamento (`POST /api/v1/workflows/{id}/reprocess`) e o dashboard não
possuem autenticação. O reprocessamento dispara efeito externo — agenda a
criação de uma issue Jira. Isso é aceito no escopo atual: execução local,
usuário único, dados sintéticos. **Não é aceitável em ambiente hospedado.**
Antes de qualquer exposição pública é necessário exigir credencial no
boundary (API key validada contra variável de ambiente, ou invoker IAM
restrito no Cloud Run) e autenticar o dashboard.

**Sem controle de acesso por titular.** Não existe conceito de dono ou de
tenant. O `workflow_execution_id` é UUID v4, o que torna enumeração inviável
por força bruta, mas isso é uma barreira de descoberta, não um controle de
autorização. Em cenário multi-cliente, isso vira IDOR real.

**`duplicates_avoided` não é mensurável.** A métrica é exposta como `null`. Um
ingest duplicado é detectado e rejeitado antes de qualquer persistência, então
não existe registro de quantas vezes isso ocorreu. Contabilizar exigiria coluna
ou tabela nova — mudança de schema fora do escopo deste incremento.

**n8n não implementado.** O adaptador de webhook está desenhado no contrato
operacional, mas não construído. O Freshservice permanece sintético e nenhuma
credencial real é usada.

**Classificação por LLM implementada, testada e desligada por padrão
(`LLM_ENABLED=false`).** O roteamento de squad é determinístico primeiro; o
LLM (`qwen3:8b` via Ollama local) só é consultado quando a categoria não bate
com nenhuma regra. Golden set (`backend/tests/golden/routing_golden.jsonl`,
18 casos, 13 escoráveis para acurácia; casos de injection reportados à parte)
mediu acurácia de 100% (13/13) numa execução e 84,62% em outra —
avaliação de LLM não é determinística, os dois números são reais, sem ajuste
de prompt entre eles. O mesmo golden set mediu taxa de sucesso de prompt
injection de **2/2 (100%)** com `qwen3:8b`, em casos que pedem um valor válido
do enum (`platform`) com confiança alta — o modelo obedeceu a instrução
embutida no texto do ticket em vez de ignorá-la.

Assunto e descrição do ticket são entrada não confiável, escrita por quem
abre o chamado. Ativar o LLM hoje transferiria para essa pessoa a escolha da
squad de destino. Por isso a classificação por LLM permanece desligada — o
golden set decidiu não ativar, e essa é a função de um golden set: decidir,
não confirmar o que já se queria ouvir. Ativar exigiria entrada confiável
(ticket de origem autenticada e revisada) ou uma defesa que não dependa do
prompt; nenhuma das duas existe hoje.

As garantias determinísticas valem com o LLM ligado ou desligado: enum
fechado (`identity`, `finance`, `platform`, `unknown`), limiar de confiança e
degradação para revisão humana em qualquer falha — Ollama fora do ar, JSON
inválido, squad fora do enum ou confiança baixa nunca viram criação automática
de issue.

**Sem paginação por cursor.** A listagem aplica apenas `LIMIT`, com teto de 200.
Adequado ao volume sintético da demonstração.

**OCR, RAG hospedado, busca híbrida e reranking** permanecem pós-MVP.

**Sem limite de tamanho na resposta do Ollama.** O adaptador LLM não trunca
nem rejeita uma resposta anômalamente grande antes de fazer parse. Aceitável
local e single-user; hospedado, precisa de teto de tamanho antes do `json.loads`.

**Sem limite de fila nem circuit breaker no worker.** Uma rajada de tickets com
categoria inválida serializa o processamento em ~20s por ticket (timeout do
LLM). Hoje é DoS acidental; com webhook externo em produção viraria DoS
barato — mitigação futura é rate limit no boundary de ingestão mais teto na
fila.

## Uso de IA Generativa

As evidências rastreáveis do uso de IA — prompts, decisões, saídas sanitizadas, validações e material de demonstração — devem ser mantidas em [`evidence/`](./evidence/README.md) e indexadas em [`docs/ai/`](./docs/ai/README.md). Dados reais de clientes, credenciais e conteúdo sensível não devem ser incluídos.
