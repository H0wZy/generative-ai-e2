# Phase 1 — Data Model: Rota por conversa e arquivamento

**Feature**: `specs/007-ai-chat-route-archive`
**Date**: 2026-08-02

Uma entidade muda. Nada novo é criado.

---

## 1. Conversa (`assistant_conversations`)

### Estado atual (inspecionado, `backend/app/repositories/schema.py:192`)

| Campo | Tipo | Regra |
|---|---|---|
| `id` | `UUID` | chave primária, gerada no servidor (`uuid4`) |
| `session_id` | `UUID` | dono; gerado no navegador, sem login |
| `title` | `String(200)` | vazio até a primeira pergunta |
| `is_favorite` | `Boolean NOT NULL` | default `false` |
| `created_at` | `TIMESTAMPTZ NOT NULL` | `now()` |
| `updated_at` | `TIMESTAMPTZ NOT NULL` | `now()`, tocado a cada mensagem |

### Adição desta rodada

| Campo | Tipo | Regra |
|---|---|---|
| `archived_at` | `TIMESTAMPTZ NULL` | `NULL` = ativa; carimbo = arquivada |

Nulável e sem default: linhas existentes viram ativas automaticamente na
migração, sem `UPDATE` de backfill.

Decisão de forma em `research.md` §R3 — coluna temporal em vez de booleana,
mesmo custo e já atende FR-012.

### Índice

Nenhum. A tabela é por sessão de navegador, dezenas de linhas por sessão, e a
consulta já filtra por `session_id` — acrescentar `archived_at` ao predicado não
muda o plano de execução em escala nenhuma que este projeto tenha.

> **ponytail**: sem índice em `archived_at`. Teto: se a listagem por sessão
> passar de milhares de linhas, índice composto `(session_id, archived_at)`.

---

## 2. Estados e transições

```
        arquivar (PATCH is_archived=true)
ATIVA ──────────────────────────────────────► ARQUIVADA
  ▲            archived_at := now()               │
  │                                               │
  └───────────────────────────────────────────────┘
        desarquivar (PATCH is_archived=false)
                 archived_at := NULL

ATIVA ──── excluir ────► (linha some, CASCATA nas mensagens)
ARQUIVADA ─ excluir ───► (idem — FR-013)
```

Invariantes:

- **I-1**: `archived_at` é escrito **só pelo servidor**. O corpo do `PATCH` é
  booleano; relógio de navegador nunca vira carimbo persistido.
- **I-2**: `archived_at` e `is_favorite` são ortogonais (A-003). Arquivar não
  toca `is_favorite`; desarquivar não restaura nada porque nada foi perdido
  (FR-011).
- **I-3**: arquivar e desarquivar **não** tocam `updated_at`. `updated_at`
  significa "última atividade da conversa" e ordena "Recentes"; arquivar não é
  atividade. Desarquivar devolve a conversa à posição que ela tinha.
- **I-4**: transição para o mesmo estado é idempotente e **não** re-carimba
  `archived_at` (arquivar uma conversa já arquivada preserva o carimbo
  original — senão FR-012 registraria o último clique, não o arquivamento).

---

## 3. Consultas afetadas

`AssistantConversationRepository.list_conversations` (`backend/app/repositories/assistant.py:33`)
ganha um parâmetro de estado:

| Estado | Predicado | Ordenação |
|---|---|---|
| `active` (default) | `archived_at IS NULL` | `is_favorite DESC, updated_at DESC` |
| `archived` | `archived_at IS NOT NULL` | `archived_at DESC` |

O default preserva o comportamento de quem já consome (FR-009): nenhum chamador
existente precisa mudar para deixar de ver arquivadas.

A lista de arquivadas ordena por momento de arquivamento — a ordem que a pessoa
espera ao procurar "o que eu acabei de tirar da frente" — e ignora
`is_favorite`, conforme A-003.

`get_owned` **não muda**: acesso direto a conversa arquivada continua
funcionando (FR-010), e conversa de outra sessão continua indistinguível de
inexistente (FR-014, SC-006).

---

## 4. Migração `008`

- **revision**: `008`, **down_revision**: `007` (cabeça atual conferida em
  `backend/migrations/versions/`).
- **upgrade**: `ADD COLUMN archived_at TIMESTAMPTZ NULL`.
- **downgrade**: `DROP COLUMN archived_at`.

Sem backfill, sem `NOT NULL`, sem default — a migração não bloqueia tabela nem
perde dado ao ser revertida (só o registro de quem estava arquivada, que é
inerente a remover a coluna).

---

## 5. O que **não** muda

- `assistant_messages`: intacta. Arquivar não toca mensagem.
- Prefixo das rotas (`/api/v1/assistant`): intacto por decisão do usuário
  (A-001, Out of Scope).
- Geração de `id` e posse por sessão: reaproveitadas como estão (D-001). Esta
  rodada **usa** a identidade existente para virar endereço; não cria
  identidade nova.
