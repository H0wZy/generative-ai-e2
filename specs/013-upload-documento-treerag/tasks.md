---

description: "Task list for Upload de documento no chat com busca em árvore (TreeRAG)"
---

# Tasks: Upload de documento no chat com busca em árvore (TreeRAG)

**Input**: Design documents from `specs/013-upload-documento-treerag/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/attachment-api.md, quickstart.md

**Tests**: backend tem suíte pytest com padrão de fakes determinísticos
(`FakeRagSearchClient`, `FakeLLMClient`) — todo componente novo com lógica
não trivial (árvore, busca bidirecional, extração de PDF, OCR) ganha teste
seguindo esse mesmo padrão. Frontend não tem suíte automatizada no projeto;
validação via `quickstart.md` (roteiros manuais) e `npm run lint`.

**Organization**: tarefas agrupadas por user story (spec.md) para permitir
entrega e teste independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: US1 (P1 — texto/Markdown citado), US2 (P2 — resposta honesta sem evidência), US3 (P3 — PDF + OCR)

---

## Phase 1: Setup

**Purpose**: infraestrutura compartilhada antes de qualquer user story

- [X] T001 Adicionar `attachment_max_bytes_text`, `attachment_max_bytes_pdf`, `ocr_base_url`, `ocr_model` em `backend/app/core/config.py` (`Settings`), com defaults de `data-model.md` §Configuração nova
- [X] T002 [P] Adicionar dependência de leitura de PDF (texto embutido) em `backend/pyproject.toml` / `backend/requirements.txt`
- [X] T003 [P] Registrar `ocr_base_url`/`ocr_model` no `.env.example` do backend, só com placeholder comentado (constituição IV)

**Checkpoint**: dependências e configuração disponíveis para as fases seguintes.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: schema de dados e domínio compartilhados por todas as user stories — nenhuma story começa antes disso.

**⚠️ CRITICAL**: bloqueia todas as user stories abaixo.

- [X] T004 Criar migration `backend/migrations/versions/010_assistant_attachments.py` com `assistant_attachments` e `assistant_attachment_nodes` (`data-model.md` §1–2), ambas com `ON DELETE CASCADE` a partir de `assistant_conversations.id` / `assistant_attachments.id`, `UNIQUE(conversation_id)` em `assistant_attachments`, índice `(attachment_id, node_type)` em `assistant_attachment_nodes`
- [X] T005 [P] Adicionar `AssistantAttachmentRow` e `AssistantAttachmentNodeRow` em `backend/app/repositories/schema.py`, espelhando a migration
- [X] T006 [P] Adicionar `AttachmentStatus` (enum fechado `received|processing|ready|failed`), `AttachmentSummary` e `AttachmentRetrievedSource` (subclasse de `RetrievedSource`) em `backend/app/domain/assistant.py` (`data-model.md` §3)
- [X] T007 Criar `backend/app/repositories/attachment.py` com `AssistantAttachmentRepository`: `create_or_replace(conversation_id, ...)` (apaga anexo anterior antes de inserir — research.md R6), `get_by_conversation(conversation_id)`, `delete_by_conversation(conversation_id)`, `bulk_insert_nodes(...)`
- [X] T008 [P] Criar `backend/app/services/attachment_tree.py` com a função de montagem da árvore a partir de `chunk_markdown` (`rag/chunking/markdown.py`): agrupar chunks-folha por prefixo de `heading_path`, gerar nó raiz sintético e nós de seção, embedar seções/raiz via concatenação truncada do conteúdo dos filhos (research.md R2) usando `encode_texts`/`serialize_embedding` de `rag/embeddings/encoder.py`
- [X] T009 [US1][US2][US3] Teste unitário de `attachment_tree.py` em `backend/tests/test_attachment_tree.py`: documento com 3 níveis de heading produz árvore com raiz única, seções corretas e folhas idênticas às de `chunk_markdown`; `.txt` sem heading produz só raiz + 1 folha

**Checkpoint**: schema, domínio e montagem de árvore prontos — user stories podem começar.

---

## Phase 3: User Story 1 - Anexar texto/Markdown e obter resposta citada (Priority: P1) 🎯 MVP

**Goal**: clipe funcional para `.md`/`.txt`, árvore montada, busca bidirecional citando seção/trecho exatos.

**Independent Test**: anexar `.md`/`.txt` com seções distintas, perguntar sobre uma seção específica, confirmar citação da seção e trecho corretos (quickstart.md Roteiro 1).

### Implementation for User Story 1

- [X] T010 [US1] Implementar busca bidirecional (raiz→folha, depois folha→raiz dentro da subárvore) em `backend/app/services/attachment_tree.py` (research.md R3), reaproveitando `cosine_distance`; retorna lista de `AttachmentRetrievedSource` ou vazio (nunca inventa)
- [X] T011 [P] [US1] Teste de `attachment_tree.py::search` em `backend/tests/test_attachment_tree.py`: pergunta sobre seção B não retorna trecho da seção A; pergunta sem cobertura no documento retorna lista vazia
- [X] T012 [US1] Implementar `POST /conversations/{conversation_id}/attachment` em `backend/app/api/routes_assistant.py`: valida MIME/extensão (`.md`/`.txt` nesta rodada — `.pdf` chega em US3) e `size_bytes` contra `attachment_max_bytes_text` (FR-002/FR-003), chama `create_or_replace` + `attachment_tree`, retorna `AttachmentSummary` (`contracts/attachment-api.md`)
- [X] T013 [P] [US1] Implementar `GET /conversations/{conversation_id}/attachment` em `backend/app/api/routes_assistant.py`
- [X] T014 [P] [US1] Implementar `DELETE /conversations/{conversation_id}/attachment` em `backend/app/api/routes_assistant.py` (idempotente — `204` mesmo sem anexo, mesmo padrão de `set_favorite`)
- [X] T015 [US1] Estender `backend/app/services/assistant.py::ask` para consultar a árvore do anexo (`status == ready`) além da busca RAG existente, mesclando `AttachmentRetrievedSource` em `sources` sem mudar o formato de `AssistantAnswer` (contracts/attachment-api.md §`/ask`)
- [X] T016 [P] [US1] Teste de contrato das 3 rotas novas em `backend/tests/test_routes_assistant_attachment.py`: upload válido → `201 ready`; MIME não suportado → `422`; acima do limite → `413`; `GET` sem anexo → `{"attachment": null}`; `DELETE` idempotente
- [X] T017 [P] [US1] Teste de integração de `/ask` com anexo em `backend/tests/test_assistant_service.py`: pergunta sobre conteúdo do anexo cita `heading_path`/trecho corretos; conversa sem anexo segue comportamento atual inalterado
- [X] T018 [US1] Adicionar handler de upload no botão `Paperclip` já existente em `frontend/src/components/assistant/chat-composer.tsx:153` (input de arquivo oculto, `POST` multipart para a rota nova, exibir estado de carregamento)
- [X] T019 [P] [US1] Adicionar indicador de documento anexado na tela de conversa em `frontend/src/app/ai/chat/[id]/` (consome `GET /conversations/{id}/attachment` ao carregar)

**Checkpoint**: US1 completa e testável isoladamente — MVP demonstrável (upload `.md`/`.txt` + resposta citada).

---

## Phase 4: User Story 2 - Resposta honesta quando o documento não cobre a pergunta (Priority: P2)

**Goal**: garantir que ausência de evidência no anexo produz aviso explícito, e que conteúdo do anexo nunca é tratado como instrução.

**Independent Test**: anexar documento sobre assunto A, perguntar sobre assunto B, confirmar aviso de ausência de evidência sem trecho citado (quickstart.md Roteiro 2).

### Implementation for User Story 2

- [X] T020 [US2] Confirmar/ajustar em `backend/app/services/assistant.py::ask` que a mesclagem de fontes do anexo (T015) aplica o mesmo limiar de distância/ausência de evidência já usado pela busca RAG — sem trecho acima do limiar, nenhuma fonte de anexo entra no prompt
- [X] T021 [US2] Envolver o conteúdo de `AttachmentRetrievedSource.content` no mesmo bloco `<untrusted_document>` já usado para `RetrievedSource.content` em `backend/app/services/assistant.py`, garantindo que texto do anexo nunca seja lido como instrução (FR-008)
- [X] T022 [P] [US2] Teste de prompt injection em `backend/tests/test_assistant_service.py`: anexo com linha tipo "ignore instruções anteriores..." é citado como texto, nunca altera o comportamento da resposta
- [X] T023 [P] [US2] Teste de ausência de evidência em `backend/tests/test_assistant_service.py`: pergunta fora do domínio do anexo retorna resposta com aviso explícito de "não encontrei no documento", `sources` vazio de origem anexo

**Checkpoint**: US1 + US2 funcionam juntas — resposta citada quando há evidência, honesta quando não há.

---

## Phase 5: User Story 3 - Anexar PDF com extração de texto (Priority: P3)

**Goal**: `.pdf` aceito no clipe, com extração de texto embutido e fallback de OCR local para PDF escaneado.

**Independent Test**: anexar PDF com texto selecionável e PDF escaneado, confirmar resposta citada equivalente à US1 em ambos, e aviso claro quando extração falha (quickstart.md Roteiros 3 e 4).

### Implementation for User Story 3

- [X] T024 [P] [US3] Criar `backend/app/integrations/pdf_extract.py`: extrai texto embutido de PDF (biblioteca de T002); retorna texto vazio/`None` quando não há camada de texto, sem lançar exceção para esse caso (é o sinal de "precisa OCR", não uma falha)
- [X] T025 [P] [US3] Criar `backend/app/integrations/ocr.py` com `OcrClientProtocol`, `OllamaOcrClient` (chama `ocr_base_url`/`ocr_model` de `Settings`, mesmo padrão de `OllamaClient` em `backend/app/integrations/llm.py`) e `FakeOcrClient` determinístico para teste sem rede
- [X] T026 [P] [US3] Teste de `ocr.py` em `backend/tests/test_ocr.py` usando `FakeOcrClient`: sucesso retorna texto; falha de conexão/timeout retorna erro tipado (mesmo padrão de `LLMClientError`), nunca propaga conteúdo do arquivo no erro
- [X] T027 [US3] Estender `POST /conversations/{conversation_id}/attachment` (T012) para aceitar `.pdf`: valida contra `attachment_max_bytes_pdf`; tenta `pdf_extract` primeiro; se vazio, aciona `OcrClientProtocol`; falha de qualquer extração marca `status="failed"` com `error_reason` estático (FR-012), nunca segue como se o texto estivesse disponível
- [X] T028 [P] [US3] Teste de contrato do upload de PDF em `backend/tests/test_routes_assistant_attachment.py`: PDF com texto embutido → `ready` via `pdf_extract`; PDF escaneado (fake sem texto embutido) → `ready` via `FakeOcrClient`; PDF corrompido/ilegível → `failed` com `error_reason`
- [X] T029 [US3] Atualizar mensagem de formato aceito no handler do frontend (T018) em `frontend/src/components/assistant/chat-composer.tsx` para incluir `.pdf` no `accept` do input de arquivo

**Checkpoint**: todas as user stories funcionam de forma independente — US1 (texto/md), US2 (honestidade), US3 (PDF/OCR).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: cobrir edge cases e limpeza cruzando as três stories.

- [X] T030 [P] Cobrir edge case de substituição de anexo (novo upload apaga o anterior) em `backend/tests/test_routes_assistant_attachment.py` (research.md R6)
- [X] T031 [P] Cobrir edge case de exclusão de conversa removendo anexo/nós via cascade em `backend/tests/test_repositories_attachment.py` (quickstart.md Roteiro 6)
- [X] T032 [P] Cobrir edge case de isolamento entre conversas (documento de A nunca aparece em B) em `backend/tests/test_assistant_service.py` (quickstart.md Roteiro 5, SC-004)
- [X] T033 Rodar `pytest backend/tests/ -k attachment` e a suíte completa do backend, confirmando 0 regressão
- [X] T034 Rodar `npm run lint` no frontend e todos os 6 roteiros de `quickstart.md` manualmente contra o stack local

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — começa imediatamente
- **Foundational (Phase 2)**: depende do Setup — bloqueia todas as user stories
- **US1 (Phase 3)**: depende só do Foundational
- **US2 (Phase 4)**: depende do Foundational; integra com o `ask` estendido em T015 (US1), mas é testável de forma isolada assim que T015/T020/T021 existirem
- **US3 (Phase 5)**: depende do Foundational e reaproveita a rota de upload de US1 (T012), estendendo-a em T027 — não bloqueia nem é bloqueada pela conclusão de US2
- **Polish (Phase 6)**: depende de todas as stories desejadas estarem completas

### Parallel Opportunities

- T002/T003 (Setup) em paralelo
- T005/T006/T008 (Foundational) em paralelo — arquivos diferentes
- Dentro de US1: T011/T013/T014/T016/T017/T019 em paralelo entre si onde marcado `[P]`
- US2 e US3 podem ser trabalhadas em paralelo por pessoas diferentes depois que T015 (US1) existir, já que T020/T021 (US2) e T024-T026 (US3) tocam arquivos distintos

---

## Parallel Example: User Story 1

```bash
Task: "T011 [P] [US1] Teste de attachment_tree.py::search em backend/tests/test_attachment_tree.py"
Task: "T013 [P] [US1] Implementar GET /conversations/{conversation_id}/attachment"
Task: "T014 [P] [US1] Implementar DELETE /conversations/{conversation_id}/attachment"
Task: "T016 [P] [US1] Teste de contrato das 3 rotas novas"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1 (Setup) e Phase 2 (Foundational)
2. Completar Phase 3 (US1)
3. **PARAR e VALIDAR**: rodar Roteiro 1 de `quickstart.md` isoladamente
4. Demonstrável como MVP: clipe funcional, upload `.md`/`.txt`, resposta citada

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 → validar isoladamente → demo (clipe + texto/md citado)
3. US2 → validar isoladamente → demo (honestidade sem evidência, resistência a prompt injection)
4. US3 → validar isoladamente → demo (PDF + OCR)
5. Polish → regressão completa + roteiros manuais de `quickstart.md`
