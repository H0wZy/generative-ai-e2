# Constituição — GENERATIVE-AI-E2

Projeto do Bootcamp Gen AI E2 (TCS). Automatiza o tombamento de tickets do
Freshservice para issues do Jira, com trilha RAG local exposta por MCP, e mede o
ganho operacional contra a linha de base manual.

## Core Principles

### I. Determinismo primeiro, LLM como fallback medido

Regra determinística é a primeira opção em qualquer decisão de negócio
(roteamento, vínculo, idempotência). O modelo generativo só entra onde o
determinístico devolve "não sei", e sempre com saída em enum fechado, score de
confiança, prompt/modelo versionados na `rule_version` gravada, e degradação
para revisão humana. Nenhum caminho de LLM pode transformar workflow em
`failed`: indisponibilidade do modelo degrada para o comportamento anterior.

Ativação de qualquer uso de LLM exige golden set executado, com número real
publicado. Golden set decide — não confirma o que já se queria ouvir.

### II. Entrada externa é não confiável

Assunto, descrição, anexo e conteúdo indexado vêm de fora e podem conter
instrução endereçada a um modelo. Texto de terceiro entra em bloco delimitado,
nunca como instrução; saída restrita a enum validado; conteúdo de ticket nunca
é concatenado em log, mensagem de erro, DLQ, screenshot ou evidência. O MCP
devolve trecho + proveniência e nunca executa o que está no trecho.

### III. Idempotência e rastreabilidade não são opcionais

Toda ingestão tem chave de idempotência (`source_system` + `source_ticket_id` +
versão/tipo do evento). O estado é persistido antes de qualquer chamada
externa. Reprocessamento reutiliza a mesma chave e nunca cria issue duplicada
sem antes verificar o vínculo existente. Toda execução registra
`correlation_id`, `workflow_execution_id`, status, tentativa, duração e causa de
falha.

### IV. Segredo nunca entra no repositório

Credencial de Jira, de Freshservice ou de qualquer API vive em variável de
ambiente ou Secret Manager, com `.env.example` contendo apenas placeholder
comentado. Menor privilégio nos tokens de integração. Nenhum token aparece em
log, teste, evidência ou saída de comando. Suíte de testes roda verde **sem**
credencial e **sem** rede — integração externa é exercitada por fake/respx.

### V. Simples agora, escalável pelas costuras

Não construir infraestrutura que o MVP não usa. Nenhuma abstração com uma única
implementação, nenhuma dependência nova onde o que já está instalado resolve.
Mudanças pequenas, testáveis e reversíveis. Código superado sai da navegação
antes de sair do disco. Limitação conhecida é documentada como decisão, não
descoberta tardia — a seção "o que ficou de fora" do README é obrigatória e
atualizada a cada bloco.

## Restrições Técnicas

- **Dado operacional**: PostgreSQL é a única fonte de verdade de ticket,
  roteamento, execução de workflow, auditoria e vínculo.
- **RAG**: SQLite + sqlite-vec, local, independente do banco operacional.
- **Modelos**: locais por padrão (Ollama + sentence-transformers). API paga
  exige ADR justificando custo e saída de dado da máquina.
- **Integração**: FastAPI é dono do contrato, das regras e da idempotência.
  n8n, quando existir, é adaptador de webhook — não dono de regra de negócio.
- **Backend**: Python/FastAPI. Reaproveitamento de código do projeto
  `data-receiver` é permitido e preferido; a trilha C# daquele projeto está
  fora de escopo.

## Fluxo de Trabalho

1. Ler `AGENTS.md`, `CLAUDE.md` e o handoff da trilha antes de qualquer código.
2. Inspecionar a estrutura real do repositório — não assumir caminho.
3. Spec (`/speckit-specify`) → plano (`/speckit-plan`) → tasks
   (`/speckit-tasks`) → implementação.
4. `qa-dev` valida critério de aceite com evidência de execução real, não
   revisão de código. `cybersec` revisa antes de fechar.
5. `evidence-scribe` registra prompt, decisão e saída sanitizada em `evidence/`
   e `docs/ai/`, e abre/atualiza o ADR numerado.

## Governance

Esta constituição prevalece sobre preferência pontual. Qualquer exceção precisa
de ADR registrado em `docs/ai/ai-decisions.md` explicando a complexidade
adicional e o que ela compra. Emenda exige atualização de versão abaixo e
justificativa no mesmo commit.

**Version**: 1.0.0 | **Ratified**: 2026-07-27 | **Last Amended**: 2026-07-27
