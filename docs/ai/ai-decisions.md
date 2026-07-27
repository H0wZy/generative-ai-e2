# Decisões Assistidas por IA

As decisões abaixo foram revisadas por pessoas e são fonte de contexto, não substituto de validação técnica.

## ADR-001 — n8n como adaptador de integração

**Status:** aceito para MVP.

**Contexto:** é necessário receber eventos e reduzir código de adaptação entre Freshservice e FastAPI.

**Decisão:** usar n8n para webhook e orquestração leve; FastAPI mantém regras, idempotência e estado.

**Consequência:** n8n requer persistência e operação própria; não concentra regras de negócio.

**Auxílio de IA:** comparação de integração e responsabilidades, seguida de revisão humana.

## ADR-002 — FastAPI como núcleo da automação

**Status:** aceito para MVP.

**Contexto:** o fluxo precisa de contratos, validação, classificação, auditoria e integração externa testáveis.

**Decisão:** usar Python + FastAPI para API e domínio; efeitos externos são processados por worker.

**Consequência:** separar caminho de ingestão síncrona de processamento assíncrono.

**Auxílio de IA:** comparação de stacks e refinamento da separação de responsabilidades.

## ADR-003 — SQLite + sqlite-vec para RAG local

**Status:** aceito para MVP.

**Contexto:** o laboratório RAG deve demonstrar ingestão e busca local com baixo custo operacional.

**Decisão:** usar SQLite + sqlite-vec exclusivamente para RAG local. PostgreSQL permanece dedicado a dados operacionais.

**Consequência:** a base RAG não é distribuída nem adequada a múltiplas instâncias Cloud Run. Caso o RAG seja hospedado, reavaliar PostgreSQL + pgvector ou alternativa gerenciada.

**Auxílio de IA:** análise de trade-offs, seguida de consolidação documental e revisão humana.

## ADR-004 — Modelos locais em vez de API paga

**Status:** aceito para MVP.

**Contexto:** o bootcamp proíbe expor chave de API no código e o projeto proíbe commitar segredo. RAG requer embedding e classificação de squad requer LLM; ambos oferecem alternativas locais sem custo de API.

**Decisão:** usar `all-MiniLM-L6-v2` via sentence-transformers para embeddings (384 dimensões, 101 chunks indexados em SQLite) e `qwen3:8b` via Ollama para classificação de squad. Ambos em cache local, nenhuma rede externa para dados de ticket.

**Consequência:** elimina a classe inteira do problema de segredo (nenhuma chave de API exposta, nenhum token consumido de provedor); custo de API zero. Em troca, latência é determinada por hardware local (0,546s busca + embedding, 1,74s classificação em CPU i7-8550U); trocar de modelo exige criar novo golden set; escalabilidade em multi-instância requer repatriação do RAG para pgvector + PostgreSQL.

**Auxílio de IA:** comparação de opções (OpenAI text-embedding-3-small vs. all-MiniLM-L6-v2, Claude vs. qwen3:8b), análise de trade-offs custo-segurança, seguida de validação humana.

## ADR-005 — Classificação por LLM entregue desligada

**Status:** aceito para MVP.

**Contexto:** golden set de 18 casos sintéticos foi construído para decidir se habilitar LLM_ENABLED=true antes do lançamento. Testes de injection revelaram que 100% dos vetores com valor válido do enum passam pela defesa da enumeração fechada (Pydantic).

**Decisão:** entregar `LLM_ENABLED=false` por padrão em `backend/.env.example`. Quando LLM está desligado, `_augment_with_llm()` em `processing.py` retorna a decision original sem alteração; para categoria desconhecida, `route_ticket()` em `routing.py` devolve `squad_id=None, rule_version="routing-rules/v1:no-match", confidence=0.0, needs_human_review=True`. Habilitar LLM requer decisão estrutural explícita no deploy.

**Consequência:** registra-se que a defesa por enum fechado (`squad ∈ {identity, finance, platform, unknown}`) protege contra saída **MALFORMADA** (admin, xyz, 123), não contra saída **VÁLIDA-PORÉM-MANIPULADA** (platform com confidence 1.0, solicitado por injection g17/g18). Nenhum endurecimento de prompt resolve: cada nova redação do prompt que resiste às frases que nós mesmos escrevemos produz um novo prompt que é vulnerável a injeção criativa. Alternativas não implementadas, levantadas pelo cybersec: (a) LLM sugere candidato, humano confirma antes de criar issue Jira (orquestração manual); (b) restrição estrutural no Ollama mais segundo classificador independente verificando concordância (validação cruzada).

**Auxílio de IA:** análise de resultados do golden set, design de tabela de injection, decisão estrutural sobre habilitar LLM em produção com segunda camada de defesa.
