# Phase 1 — Data Model: Upload de documento no chat com busca em árvore (TreeRAG)

**Feature**: `specs/013-upload-documento-treerag`
**Date**: 2026-08-02

Duas tabelas novas no Postgres operacional, ambas atadas ao ciclo de vida de
`assistant_conversations` (migration 006) via `ON DELETE CASCADE`. Nenhuma
tabela do RAG compartilhado (`rag/data/knowledge.db`: `source_files`,
`document_chunks`, `embeddings`) é tocada — reaproveitadas só como bibliotecas
(chunker, encoder), não como armazenamento.

---

## 1. Anexo (`assistant_attachments`)

Um anexo por conversa (substitui o anterior em novo upload — research.md R6).

| Campo | Tipo | Regra |
|---|---|---|
| `id` | `UUID` | chave primária, gerada no servidor |
| `conversation_id` | `UUID` | `UNIQUE`, `FK → assistant_conversations.id ON DELETE CASCADE` |
| `file_name` | `String(255)` | nome original do arquivo, exibido na UI (FR-013) — tratado como não confiável para renderização (mesma regra de `RetrievedSource.content`) |
| `mime_type` | `String(100)` | detectado por assinatura de conteúdo, não só extensão (edge case de tipo não suportado) |
| `size_bytes` | `Integer` | validado contra limite de configuração antes de processar (FR-003) |
| `status` | `String(20)` enum fechado: `received`, `processing`, `ready`, `failed` | mesmo padrão de enum fechado de `AssistantStatus` — nunca string de erro livre |
| `error_reason` | `String(200)` nullable | preenchido só quando `status = failed`; mensagem estática, nunca conteúdo do arquivo (constituição IV) |
| `created_at` | `TIMESTAMPTZ NOT NULL` | `now()` |

**Transições de `status`**: `received` → `processing` → (`ready` | `failed`).
Não há transição de volta — um novo upload substitui a linha inteira
(delete + insert), nunca reprocessa a mesma linha.

---

## 2. Nó da árvore (`assistant_attachment_nodes`)

| Campo | Tipo | Regra |
|---|---|---|
| `id` | `UUID` | chave primária |
| `attachment_id` | `UUID` | `FK → assistant_attachments.id ON DELETE CASCADE` |
| `parent_id` | `UUID` nullable | `FK → assistant_attachment_nodes.id ON DELETE CASCADE`; `NULL` só na raiz |
| `node_type` | `String(10)` enum fechado: `root`, `section`, `leaf` | raiz sintética única; folhas vêm de `chunk_markdown`; seções vêm do agrupamento por `heading_path` (research.md R2) |
| `level` | `Integer` | `0` na raiz, cresce por nível de heading |
| `heading_path` | `Text` | caminho completo até este nó (ex.: `"Decisões > RAG > Modelo"`), mesmo formato de `document_chunks.heading_path` |
| `content` | `Text` | folha: trecho literal do documento (não confiável). Seção/raiz: concatenação truncada do conteúdo dos filhos, usada só para embedding — nunca citada diretamente como trecho de origem |
| `embedding` | `bytea` nullable | serializado com `serialize_embedding` (mesmo formato do RAG); `NULL` seria só um estado transitório durante processamento, nunca em `status = ready` |
| `start_line` | `Integer` nullable | só em folhas — `NULL` em `root`/`section` |
| `end_line` | `Integer` nullable | só em folhas — `NULL` em `root`/`section` |

**Índice**: `(attachment_id, node_type)` para acelerar o passo 1 da busca
(restringir a seções antes de descer às folhas).

---

## 3. Fonte Recuperada (em memória — não é tabela)

Reaproveita a forma de `RetrievedSource` já existente em
`backend/app/domain/assistant.py`, com `file_path` preenchido pelo
`file_name` do anexo em vez de um caminho de `docs/`:

```python
class AttachmentRetrievedSource(RetrievedSource):
    """Mesma forma de RetrievedSource — file_path = nome do arquivo anexado,
    heading_path = caminho completo folha→raiz encontrado na árvore."""
```

Não precisa de campo novo: `file_path`, `heading_path`, `start_line`,
`end_line`, `distance`, `content` já cobrem o que a citação exige (FR-006).

---

## Configuração nova (`Settings`)

| Campo | Default proposto | Uso |
|---|---|---|
| `attachment_max_bytes_text` | `5_000_000` (5 MB) | teto de upload para `.md`/`.txt` |
| `attachment_max_bytes_pdf` | `20_000_000` (20 MB) | teto de upload para `.pdf` |
| `ocr_base_url` / `ocr_model` | mesma convenção de `llm_base_url`/`llm_model` | endpoint e tag do modelo de OCR local (Ollama) |

Valores default documentados aqui para review — não são decisão de escopo do
spec (Assumptions já registra isso), mas precisam existir em algum lugar
antes da implementação.
