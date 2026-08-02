# Phase 0 — Research: Upload de documento no chat com busca em árvore (TreeRAG)

**Feature**: `specs/013-upload-documento-treerag`
**Date**: 2026-08-02

Nenhum `NEEDS CLARIFICATION` restou no Technical Context do plano — as
decisões abaixo resolvem os pontos que exigiam escolha de abordagem antes do
desenho de dados/contratos.

---

## R1 — Onde armazenar o anexo e sua árvore

**Decision**: PostgreSQL operacional, em duas tabelas novas
(`assistant_attachments`, `assistant_attachment_nodes`) ligadas por
`conversation_id` com `ON DELETE CASCADE`. Embeddings guardados como `bytea`
(mesmo formato de `serialize_embedding` do RAG), comparados por cosine em
Python puro no momento da busca — sem índice vetorial dedicado.

**Rationale**: o ciclo de vida do anexo é o mesmo da conversa (FR-014 — some
quando a conversa é excluída), e `assistant_conversations` já vive no
Postgres operacional com cascade configurado (migration 006). Colocar o
anexo ali reaproveita esse mecanismo em vez de inventar um novo. O volume por
conversa é pequeno (um documento, algumas dezenas a poucas centenas de nós) —
a mesma ordem de grandeza do fallback Python puro que `rag/search/query.py`
já usa e testa quando `sqlite-vec` está indisponível. Não há motivo para
pagar o custo de uma extensão vetorial nova (`pgvector`) para esse volume.

**Alternatives considered**:
- Um arquivo `sqlite-vec` por conversa — rejeitado: cria arquivos soltos em
  disco sem dono claro no ciclo de vida da conversa, e duplica infraestrutura
  que o Postgres operacional já resolve via cascade.
- `pgvector` no Postgres operacional — rejeitado por ora: dependência nova
  não justificada pelo volume por conversa; reavaliar se o volume crescer
  além do que cosine em Python sustenta com folga de latência.
- Adicionar o anexo à base compartilhada `rag/data/knowledge.db` — rejeitado
  explicitamente pelo spec (FR-010): misturaria dado efêmero de uma pessoa
  usuária com a base de documentação interna revisada.

---

## R2 — Como montar a árvore (TreeRAG)

**Decision**: reaproveitar `chunk_markdown` (`rag/chunking/markdown.py`) para
gerar os chunks-folha de `.md`/`.txt` — texto puro é tratado como um
documento sem heading, produzindo um chunk raiz único quando não há
estrutura. A árvore é derivada agrupando os chunks-folha pelos prefixos do
`heading_path` que o chunker já calcula (ex.: `"Decisões > RAG > Modelo"`
vira três nós: `Decisões` → `RAG` → `Modelo`), com um nó raiz sintético
representando o documento inteiro. Nós de seção (não-folha) recebem embedding
da concatenação truncada do conteúdo dos filhos — sem sumarização via LLM.

**Rationale**: o `heading_path` já é uma árvore implícita — extrair a
hierarquia dele é reaproveitamento direto, não um chunker novo. Evitar
sumarização abstrativa por nível (a forma "completa" de RAPTOR/TreeRAG) corta
custo, latência e uma fonte extra de falha (chamada a LLM por nó) que o
escopo efêmero e a demonstração não justificam — a estrutura por heading já
preserva a relação lógica entre seções que a spec pede (FR-004).

**Alternatives considered**:
- Sumarização por LLM em cada nível (RAPTOR completo) — mais fiel ao nome
  "TreeRAG" em teoria, descartado pelo custo/latência/pontos de falha
  adicionais não justificados no MVP; heading_path hierárquico já entrega
  estrutura real de árvore, não chunking flat.
- Novo parser de estrutura de documento do zero — descartado: duplicaria
  `chunk_markdown`, que já resolve o mesmo problema para `.md`/`.txt`.

---

## R3 — Busca bidirecional (raiz→folha e folha→raiz)

**Decision**: duas passadas por pergunta. Passo 1 (raiz→folha): embedding da
pergunta comparado contra os nós de seção para restringir a subárvore
candidata. Passo 2 (folha→raiz): dentro só dessa subárvore, embedding
comparado contra os chunks-folha; a citação final inclui o caminho completo
folha→raiz (heading_path) e o trecho literal, com o mesmo limiar de
distância/ausência de evidência do RAG existente (retorna vazio, nunca
inventa).

**Rationale**: reaproveita `cosine_distance`/`encode_texts` de
`rag/embeddings/encoder.py` sem depender de índice vetorial. Restringir por
seção primeiro é o que torna a busca "em árvore" de fato (reduz ruído citado
no FR-005), em vez de uma busca flat sobre todos os chunks-folha do
documento inteiro.

**Alternatives considered**:
- Busca flat direta sobre todos os chunks-folha (ignorando a árvore) —
  rejeitada: não atende FR-005 (navegação hierárquica), viraria RAG comum
  já existente, sem diferencial de TreeRAG.

---

## R4 — Extração de PDF e OCR

**Decision**: tentar primeiro extrair texto embutido do PDF (biblioteca leve,
sem rede). Se não produzir conteúdo aproveitável (PDF escaneado), acionar
extração via modelo de OCR local servido por Ollama, atrás do mesmo padrão
de adapter (`Protocol` + cliente real + `Fake*` determinístico) já usado por
`OllamaClient` em `backend/app/integrations/llm.py`. Falha de extração marca
o anexo como `failed` com motivo, nunca segue como se o documento estivesse
disponível (FR-012).

**Rationale**: local por padrão é exigência da constituição (API paga de
OCR exigiria ADR); o padrão de adapter já validado no projeto (Protocol +
fake determinístico para teste sem rede) se aplica sem modificação
estrutural. Os modelos já avaliados no handoff do RAG
(`baidu/Unlimited-OCR`, `frob/unlimited-ocr:f16`) seguem convenção de tag
Ollama, então servem como candidato direto de configuração
(`settings.ocr_model`), sem pesquisa adicional de modelo.

**Alternatives considered**:
- Serviço de OCR isolado com fila/armazenamento de objetos — é o desenho que
  o handoff do RAG já previa para uma evolução *futura* e mais ampla (OCR
  para a base compartilhada). Desproporcional aqui: volume é um documento
  por conversa, efêmero, sem necessidade de fila.
- OCR via API paga — rejeitado sem ADR prévio, e sem necessidade
  demonstrada de qualidade que o modelo local não entregue.

---

## R5 — Upload concorrente com resposta em andamento

**Decision**: nenhum mecanismo novo de fila/lock. `/ask` hoje é síncrono
(request/response, sem streaming) — um upload em andamento e uma pergunta em
andamento na mesma conversa já são serializados pela própria natureza
bloqueante das duas rotas HTTP.

**Rationale**: introduzir lock explícito resolveria uma condição de corrida
que a arquitetura atual (sem streaming, sem worker assíncrono) não expõe na
prática — adicionar isso agora seria complexidade sem uso (constituição V).

**Alternatives considered**:
- Lock por `conversation_id` em memória ou no banco — descartado por ora:
  sem evidência de que a corrida ocorra dado o modelo request/response atual;
  revisitar se o assistente ganhar streaming.

---

## R6 — Substituição de anexo

**Decision**: `assistant_attachments.conversation_id` é `UNIQUE`. Um novo
upload apaga o anexo anterior (cascade remove os nós) antes de inserir o
novo — decisão já registrada em Assumptions do spec.

**Rationale**: mais simples e mais previsível para quem usa do que acumular
múltiplas fontes ativas sem indicação de qual está em uso (spec, Assumptions).
