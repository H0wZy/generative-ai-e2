# Implementation Plan: Upload de documento no chat com busca em árvore (TreeRAG)

**Branch**: `013-upload-documento-treerag` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/013-upload-documento-treerag/spec.md`

## Summary

Habilitar o clipe hoje decorativo em `chat-composer.tsx` para upload de um
documento (`.md`/`.txt` em P1, `.pdf` em P3) por conversa do assistente. O
documento vira fonte efêmera, isolada por `conversation_id`, organizada numa
árvore hierárquica (raiz → seções → folhas) derivada do `heading_path` que o
chunker de Markdown já produz. A busca navega a árvore em duas passadas —
seções primeiro (raiz→folha), folhas depois dentro da subárvore encontrada
(folha→raiz) — para citar seção e trecho exatos e recusar resposta quando não
há evidência (P2), preservando as garantias já vigentes no RAG existente
(fonte verificável, conteúdo não confiável, sem invenção). PDF sem texto
embutido passa por extração via modelo de OCR local (Ollama), seguindo o
mesmo padrão de adapter do cliente LLM já usado no assistente.

## Technical Context

**Language/Version**: Python 3.11 (backend/rag), TypeScript 5 / Next.js (frontend) — mesma stack do restante do projeto.

**Primary Dependencies**:
- Reaproveitados sem mudança: FastAPI, SQLAlchemy + Alembic, httpx, `rag/chunking/markdown.py` (`chunk_markdown`), `rag/embeddings/encoder.py` (`encode_texts`, `serialize_embedding`, `cosine_distance`), o padrão `Protocol` + cliente real + `Fake*` determinístico já usado em `backend/app/integrations/llm.py` e `rag_search.py`.
- Novos, mínimos: biblioteca leve de extração de texto embutido de PDF (sem rede); cliente de OCR local via Ollama (`OcrClientProtocol` + `OllamaOcrClient` + `FakeOcrClient`, mesmo padrão de `OllamaClient`).

**Storage**: PostgreSQL operacional (já é a fonte de verdade de `assistant_conversations`/`assistant_messages`) — duas tabelas novas, `assistant_attachments` e `assistant_attachment_nodes`, com `ON DELETE CASCADE` a partir de `conversation_id`. **Não** usa `rag/data/knowledge.db` (base compartilhada do RAG de documentação interna permanece intocada — FR-010).

**Testing**: pytest (backend), mesmo padrão de fakes determinísticos (`FakeRagSearchClient`, `FakeLLMClient`) para o novo cliente de OCR e para o serviço de árvore; golden set próprio da feature para US2 (respostas sem evidência).

**Target Platform**: Linux server (stack Docker Compose já existente) + navegador (Next.js) — sem plataforma nova.

**Project Type**: Aplicação web (backend + frontend já existentes).

**Performance Goals**: primeira resposta citada em menos de 10s para `.md`/`.txt` (SC-001); extração de PDF via OCR não tem teto de tempo no MVP — se demorar, o estado do anexo permanece `processing` e a interface avisa, em vez de travar a conversa (ver research.md).

**Constraints**:
- Reaproveitar o mesmo modelo de embedding do RAG existente (`EMBEDDING_MODEL` em `rag/embeddings/encoder.py`) para manter dimensão/consistência sem introduzir um segundo modelo.
- OCR local por padrão (constituição — API paga de OCR exigiria ADR); nenhuma credencial nova.
- Conteúdo do documento anexado (e texto extraído de PDF) é não confiável: mesmo tratamento de `<untrusted_document>` já aplicado a `RetrievedSource.content` em `rag_search.py`.
- Nada do anexo entra em log, DLQ ou evidência (constituição IV).
- Sem fila/worker novo: upload processa de forma síncrona na mesma requisição, no mesmo estilo request/response de `/ask` hoje.

**Scale/Scope**: cenário de demonstração — um documento ativo por conversa, volume compatível com sessão de apresentação (não produção em escala). Tamanho máximo de upload e tempo de espera de UI são parâmetros de configuração (`Settings`), não hard-coded — valores default a registrar em `data-model.md`/`quickstart.md`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|---|---|
| I. Determinismo primeiro, LLM como fallback medido | N/A direto — esta feature não introduz decisão de roteamento de negócio; reaproveita o mesmo assistente LLM já existente e seu circuito de degradação (`AssistantStatus`). **PASS**. |
| II. Entrada externa é não confiável | Conteúdo do anexo (e texto extraído de PDF/OCR) segue o mesmo bloco `<untrusted_document>` já usado para `RetrievedSource.content`; FR-008 exige explicitamente que instrução embutida no documento não seja executada. **PASS**. |
| III. Idempotência e rastreabilidade | Upload não é um evento externo replayable (não precisa de chave `source_system`+`source_ticket_id`); mas cada anexo carrega `status` em enum fechado (`received/processing/ready/failed`) e fica associado a `conversation_id`, rastreável nos mesmos logs do assistente. **PASS** com nota — sem chave de idempotência clássica porque não se aplica ao caso de uso (upload manual, não reprocessamento de fila). |
| IV. Segredo nunca entra no repositório | Sem credencial nova — OCR local via Ollama (já é como o LLM de classificação de squad funciona hoje). **PASS**. |
| V. Simples agora, escalável pelas costuras | Duas adições novas de fato: leitura de PDF e cliente OCR. Justificadas em Complexity Tracking abaixo — são exigência direta do FR-011/FR-012 (US3), não escolha por conveniência. Tudo o resto (chunking, embeddings, padrão de adapter, tabela ligada por `conversation_id` com cascade) reaproveita o que já existe. **PASS com 2 itens registrados**. |

## Project Structure

### Documentation (this feature)

```text
specs/013-upload-documento-treerag/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── attachment-api.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── domain/
│   │   └── assistant.py          # + AttachmentStatus, AttachmentSummary, árvore em RetrievedSource-like shape
│   ├── integrations/
│   │   ├── pdf_extract.py        # NOVO — extração de texto embutido de PDF
│   │   └── ocr.py                # NOVO — OcrClientProtocol + OllamaOcrClient + FakeOcrClient (mesmo padrão de llm.py)
│   ├── services/
│   │   └── attachment_tree.py    # NOVO — monta árvore a partir de chunk_markdown, busca bidirecional
│   ├── repositories/
│   │   ├── schema.py             # + AssistantAttachmentRow, AssistantAttachmentNodeRow
│   │   └── attachment.py         # NOVO — repositório (create/get/replace/delete por conversation_id)
│   └── api/
│       └── routes_assistant.py   # + rotas de anexo (contracts/attachment-api.md)
└── migrations/versions/
    └── 010_assistant_attachments.py  # NOVO

frontend/
└── src/
    ├── components/assistant/
    │   └── chat-composer.tsx     # handler no botão Paperclip já existente (linha 153)
    └── app/ai/chat/[id]/         # indicador de documento anexado na tela de conversa
```

**Structure Decision**: aplicação web já existente (backend FastAPI +
frontend Next.js). Nenhum projeto/serviço novo — a feature vive inteira
dentro de `backend/app` (novos módulos em `integrations/`, `services/`,
`repositories/`) e do componente de chat já existente no `frontend/`. Sem
diretório `rag/` tocado (a base compartilhada de documentação interna não
muda) além de reaproveitar `rag/chunking/markdown.py` e
`rag/embeddings/encoder.py` como bibliotecas importadas pelo backend.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Nova dependência de leitura de PDF + novo cliente de OCR local | Exigência direta de FR-011/FR-012 e da User Story 3 (aceite exige PDF escaneado sem texto selecionável funcionando) | Sem eles, upload de PDF fica limitado a texto já embutido, e PDF escaneado (o caso mais comum de documento real) falharia sempre — não atende ao critério de aceite já acordado com o usuário |
| Tabela de nós em árvore (`assistant_attachment_nodes`, parent/child) em vez de reaproveitar `document_chunks` flat do RAG existente | TreeRAG exige navegação hierárquica bidirecional real (FR-004/FR-005); `document_chunks` é flat por design (uma linha por chunk, sem `parent_id`) | Reaproveitar a tabela flat existente resolveria só uma busca por similaridade simples — não modela seção↔documento nem permite a segunda passada (raiz→folha) que o spec pede |
