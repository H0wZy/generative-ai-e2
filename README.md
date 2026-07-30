# GENERATIVE-AI-E2

Projeto do Bootcamp Gen AI E2 da TCS para demonstrar a aplicação de IA Generativa no ciclo completo de desenvolvimento.

## Objetivo

Automatizar a criação de issues no Jira a partir de tickets do Freshservice, com roteamento para a squad correta, rastreabilidade e operação segura. Em paralelo, o projeto inclui um laboratório RAG local, exposto por MCP, para consulta à documentação do repositório.

## Como rodar o backend

Nenhuma linha de código muda entre os dois caminhos abaixo — a diferença é apenas quem sobe o PostgreSQL.

### Pré-requisitos

- Python 3.11+
- PostgreSQL 16 (via Docker ou instalação local)
- `make` e `curl`

### Caminho 1: Com Docker (recomendado, padrão)

```bash
# Subir PostgreSQL container
make up

# Aplicar migrations
make migrate
make migrate-test

# Rodar testes
make test

# Iniciar API
make serve
```

### Caminho 2: PostgreSQL local (sem Docker)

Quando Docker não está disponível, use PostgreSQL nativo instalado na máquina:

1. **Ter PostgreSQL 16 rodando localmente.** Exemplo em systemd:
   ```bash
   sudo systemctl start postgresql
   ```
   (Ajuste para seu SO: `brew services start postgresql` em macOS, etc.)

2. **Inicializar role e databases:**
   ```bash
   make db-init-local
   ```
   (O target tenta `psql -U postgres` direto; se falhar por autenticação peer — comum em Fedora/RHEL/Debian — cai para `sudo -u postgres psql`.)

3. **Configurar environment:**
   ```bash
   cp backend/.env.example backend/.env
   # Ajustar DATABASE_URL/TEST_DATABASE_URL se a senha local for diferente
   ```

4. **Aplicar migrations:**
   ```bash
   make migrate
   make migrate-test
   ```

5. **Rodar testes e API:**
   ```bash
   make test
   make serve
   ```

### Operações adicionais (ambos os caminhos)

```bash
make ingest-demo      # POST da fixture sintética
make worker-once      # Processar um evento de saída
make poll-once        # Ler o Freshservice uma vez (usa dublê sem credencial)
make analytics-load   # Carregar os exports do Power BI de examples/
make rag-sync         # Indexar docs/ em rag/data/knowledge.db
make rag-eval         # Executar golden set do RAG
make clean            # Limpar cache Python
```

## Estado do Repositório

O repositório está na fase de arquitetura e documentação. A árvore abaixo descreve a organização **alvo**, e não afirma que todos os módulos já estão implementados.

## O ganho, em número

O problema que o projeto ataca é o tombamento manual do chamado para o card, e
a consequência medível dele é que o vínculo entre os dois sistemas só existe
como texto livre digitado no título do card:

| Base histórica (tombamento manual) | Número |
|---|---|
| Chamados exportados | 3.022 |
| Cards exportados | 428 |
| Cards com número de chamado extraível do título | 368 (86%) |
| Cards cujo número bate com um chamado real | 312 |
| **Cobertura de vínculo** | **72,9%** |
| Campo oficial "Tickets do Freshservice" preenchido | 1 card em 428 |

Contra a automação, onde o identificador do chamado vai num rótulo estruturado
da issue e não depende de ninguém digitá-lo: **cobertura 100% por construção**.

Os números acima foram medidos uma vez contra os arquivos reais exportados, não
estimados. A comparação viva (`/reports`, `GET /api/v1/analytics/*`) foi
removida na refatoração 003 — o dado vivo do CRUD de ticket (seção abaixo) a
substitui como prova de cobertura, demonstrável ao vivo em vez de em lote.

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

**CORS restrito a origens locais.** `cors_origins` (`backend/app/core/config.py`)
libera só `http://localhost:3000` e `http://localhost:3100` por padrão —
suficiente para `next dev` local, e consistente com "sem autenticação só é
aceitável localmente" acima. Hospedar exige apontar essa lista para o domínio
real do frontend, nunca abrir para `*`.

**Sem controle de acesso por titular.** Não existe conceito de dono ou de
tenant. O `workflow_execution_id` é UUID v4, o que torna enumeração inviável
por força bruta, mas isso é uma barreira de descoberta, não um controle de
autorização. Em cenário multi-cliente, isso vira IDOR real.

**`duplicates_avoided` não é mensurável.** A métrica é exposta como `null`. Um
ingest duplicado é detectado e rejeitado antes de qualquer persistência, então
não existe registro de quantas vezes isso ocorreu. Contabilizar exigiria coluna
ou tabela nova — mudança de schema fora do escopo deste incremento.

**n8n e webhook fora de escopo, por decisão.** O adaptador de webhook foi
substituído por polling do Freshservice (ADR-007): o tenant sandbox é um
serviço em nuvem, e receber webhook exigiria expor esta API publicamente —
túnel mais autenticação de boundary que o MVP não tem, e que invalidaria
justamente a aceitação de "sem autenticação porque é execução local" descrita
acima. Consequência assumida: a latência ponta a ponta passa a depender do
intervalo de polling (30s por padrão).

**Freshservice roda contra um mock, não o tenant real (ADR-011).** A conta não
teve a API key liberada pelo admin do tenant do cliente, e replicar o tenant
real (org chart de 13 squads, volume de dados) é fora de escopo. O enum
fechado de squad passa a ser genérico — `SQUAD-01` a `SQUAD-08` — em vez do
nome real das squads do cliente; a base histórica do Power BI (US2/US3) não
muda. Jira roda contra conta sandbox real (credencial obtida e validada). Até
o Freshservice real existir, desenvolvimento e suíte de testes usam dublês
locais — `make test` roda verde sem credencial e sem rede.

**Pseudonimização não é anonimato forte.** A base histórica carregada do export
do Power BI tem os campos de pessoa substituídos por pseudônimo determinístico
antes de qualquer gravação (ADR-009). Quem tiver o arquivo original consegue
reverter por comparação, e campos de texto livre (`assunto`, `detalhes`,
`summary`) podem conter um nome digitado por humano. Adequado a uma base de
demonstração local; não a publicação.

**Classificação por LLM implementada, testada e desligada por padrão
(`LLM_ENABLED=false`).** O roteamento de squad é determinístico primeiro — a
squad vem preenchida do próprio chamado Freshservice (mock, ver acima) e é
validada contra o enum fechado das 8 squads genéricas (ADR-011); o LLM só é
consultado quando esse campo vem vazio ou com valor fora do enum. O provedor é
`nvidia/nemotron-3-ultra-550b-a55b:free` via OpenRouter — a refatoração 003
unificou todo uso de LLM no OpenRouter, removendo a dependência de Ollama
local (ADR-013); o classificador agora reaproveita o mesmo cliente HTTP do
assistente (`OpenRouterClient`, ADR-012), em namespace de configuração
próprio (`llm_*`, separado de `assistant_*`).

Golden set (`backend/tests/golden/routing_golden.jsonl`, 19 casos: 12 com squad
esperada, 4 de abstenção, 3 de prompt injection). **Os números abaixo foram
medidos em 2026-07-30 contra o provedor atual (ADR-013)** — os números do
Ollama (ADR-010/ADR-011) ficam como histórico de um provedor descontinuado e
não se aplicam mais:

| Métrica | Resultado |
|---|---|
| Acurácia | **83,33%** (10/12) |
| Abstenção | 37,50% (6/16) |
| Erros de requisição | 2 casos escoráveis (limite de taxa do tier gratuito) |
| **Sucesso de prompt injection** | **33,33% (1/3)** |

**A queda de acurácia frente ao Ollama (100% → 83,33%) é esperada, não uma
regressão a investigar** — são modelos diferentes, medidos honestamente cada
um contra o próprio provedor (Princípio I: golden set decide, não confirma).
Dois casos vieram com erro de requisição em vez de classificação, consistente
com limite de taxa do modelo gratuito — contados como abstenção/erro, não
como acerto nem como resistência real medida à injeção.

**A injeção continua sendo o que decide.** Um dos três vetores passou: pediu
uma squad específica dentro do texto do chamado, e o modelo devolveu essa
squad com confiança acima do limiar. Isso confirma o ADR-005 com o provedor
novo: enum fechado protege contra saída **malformada**, não contra saída
**válida-porém-manipulada**.

Assunto e descrição do ticket são entrada não confiável, escrita por quem
abre o chamado. Ativar o LLM hoje transferiria para essa pessoa a escolha da
squad de destino — e, desde ADR-008, também o rótulo gravado na issue do Jira.
Por isso a classificação por LLM permanece desligada — nem o provedor anterior
nem o atual atingiram um patamar que justifique `LLM_ENABLED=true` por padrão.
Ativar exigiria entrada confiável (ticket de origem autenticada e revisada) ou
uma defesa que não dependa do prompt; nenhuma das duas existe hoje.

As garantias determinísticas valem com o LLM ligado ou desligado: enum fechado
(hoje as 8 squads genéricas do ADR-011) mais `unknown`, limiar de confiança e
degradação para revisão humana em qualquer falha — provedor fora do ar, JSON
inválido, squad fora do enum ou confiança baixa nunca viram criação automática
de issue.

**Situação de SLA não existe na origem.** A fila de tickets tem coluna de SLA
porque o requisito pede, mas nenhum prazo chega do Freshservice — não há campo
de deadline no schema nem no payload. A coluna mostra `—` com o rótulo "sem
prazo conhecido na origem", e o indicador da Home é marcado como indisponível.
Derivar um prazo a partir de `next_attempt_at` seria inventar número que
ninguém consegue auditar numa apresentação.

**Responsável sem imagem.** O avatar do Jira exige requisição autenticada, o
que obrigaria um proxy no backend só para servir imagem. As iniciais resolvem a
identificação; `avatar_url` é sempre `null` por decisão, não por falta.

**O workspace Agile depende de credencial viva.** Sprint, backlog e quadros são
projeção do Jira em tempo de requisição — não há cópia no Postgres. Sem
`JIRA_BOARD_ID` ou com token recusado, as telas renderizam estado nomeado
(`not_configured`, `unauthorized`, `forbidden`, `unavailable`, `rate_limited`)
em vez de erro; nada de Agile funciona offline, e isso é deliberado: cache de
sprint mentiria numa demonstração ao vivo.

**O board de demonstração foi povoado em 2026-07-29** contra o board `FRESH`
real, via script contra a API do Jira (não código do produto — ver
`evidence/evaluations/2026-07-29-plataforma-unificada-itsm-agile.md`): issues
estimadas em `customfield_10016`, dois épicos (`FRESH-1`, `FRESH-13`) com
issues vinculadas, `goal` gravado no sprint ativo, e dois sprints históricos
fechados dando série real de velocidade (11 e 18 pontos). **Uma peça continua
manual**: `constraintType: "none"` — a REST API pública do Jira não expõe
escrita para `columnConfig` (limite de WIP por coluna só se define pela UI,
em Board Settings → Columns). Recomendado: 1 no `max` da coluna "Fazendo",
que hoje já tem exatamente 1 card, para exercitar o indicador de limite
atingido (FR-028) sem precisar mover mais nada.

**Assistente desligado por padrão (`ASSISTANT_ENABLED=false`).** Roda em modelo
remoto no OpenRouter porque a máquina local não comporta modelo de geração
grande (ADR-012). Generativo com guardrail de escopo, não travado à
recuperação (FR-038/038a, 2026-07-30): a busca no RAG nunca bloqueia a
resposta — sem trecho relevante o modelo responde com conhecimento geral
dentro do escopo do projeto (ITSM/Freshservice, Agile/Jira, RAG, a
arquitetura deste sistema), avisando que a resposta não vem da documentação
indexada; pergunta sem relação nenhuma com esse escopo é recusada. O
guardrail é instrução de prompt, não corte de código. `recall@5 = 0,72`
medido em 2026-07-29 sobre 18 perguntas — cerca de uma em cada quatro não
recupera trecho, e agora essas seguem para resposta geral em vez de ficarem
sem resposta. O nível gratuito do provedor pode reter prompt para treino;
por isso a redação de PII acontece antes de o texto sair do processo, e
nenhum dado de produção deve entrar numa pergunta.

**`process-next` reivindica o evento mais antigo da fila, não um alvo
específico (research.md R1).** A tela de criação de chamado (US1) chama
`POST /tickets/ingest` seguido de `POST /workflows/process-next` para dar
feedback instantâneo no demo, sem esperar o intervalo de poll. Sob uso de um
avaliador por vez a fila está vazia antes da criação, então o evento
processado é sempre o recém-criado; sob dois chamados quase simultâneos, a
*resposta HTTP* de uma tela poderia, em teoria, descrever o resultado do
chamado da outra (a ordem de processamento em si continua FIFO correta).
Aceito como limitação conhecida de execução local/demo, não hospedada — um
serviço `worker` (`python -m app.worker --loop`) roda continuamente no
Docker Compose para que nada fique preso em `retry_scheduled` fora do
gatilho síncrono da tela.

**Sem paginação por cursor.** A listagem aplica apenas `LIMIT`, com teto de 200.
Adequado ao volume sintético da demonstração.

**OCR, RAG hospedado, busca híbrida e reranking** permanecem pós-MVP.

**Sem limite de tamanho na resposta do provedor LLM.** O adaptador do
classificador não trunca nem rejeita uma resposta anomalamente grande antes de
fazer parse. Aceitável local e single-user; hospedado, precisa de teto de
tamanho antes do `json.loads`.

**Sem limite de fila nem circuit breaker no worker.** Uma rajada de tickets com
categoria inválida serializa o processamento em ~20s por ticket (timeout do
LLM). Hoje é DoS acidental; com webhook externo em produção viraria DoS
barato — mitigação futura é rate limit no boundary de ingestão mais teto na
fila.

## Uso de IA Generativa

As evidências rastreáveis do uso de IA — prompts, decisões, saídas sanitizadas, validações e material de demonstração — devem ser mantidas em [`evidence/`](./evidence/README.md) e indexadas em [`docs/ai/`](./docs/ai/README.md). Dados reais de clientes, credenciais e conteúdo sensível não devem ser incluídos.
