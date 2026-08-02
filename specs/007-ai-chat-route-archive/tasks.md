---

description: "Task list — Rodada 007: rota por conversa e arquivamento"
---

# Tasks: Rota por conversa e arquivamento de conversas

**Input**: Design documents from `/specs/007-ai-chat-route-archive/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: incluídos **só no backend**. `contracts/conversations-api.md` lista 9
testes de contrato e SC-009 exige a suíte verde. O frontend não tem suíte
automatizada — a verificação dele é por `quickstart.md`, que é o que os
critérios desta spec (histórico do navegador, troca de endereço sem recarregar)
pedem.

**Organization**: por user story, na ordem de prioridade da spec.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizável (arquivo diferente, sem dependência pendente)
- **[Story]**: US1, US2, US3 — mapeia para as user stories da spec

## Path Conventions

Web app: `backend/` (FastAPI) e `frontend/` (Next.js App Router). Caminhos
abaixo são relativos à raiz do repositório.

---

## Phase 1: Setup

**Purpose**: fixar a linha de base antes de qualquer mudança, para que qualquer
regressão depois seja atribuível.

- [X] T001 Registrar linha de base do backend: `cd backend && alembic current && pytest -q` — confirmar cabeça em `007` e suíte verde antes de tocar em nada
- [X] T002 [P] Registrar linha de base do frontend: `cd frontend && npx tsc --noEmit && npx eslint .` — o erro `react-hooks/set-state-in-effect` em `frontend/src/lib/nav.ts` é pré-existente da rodada 006 e é o único aceitável

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: o segmento de rota novo e a mudança de assinatura da tela do
assistente. US1 e US3 dependem das duas; US2 depende do segmento.

**⚠️ CRITICAL**: nenhuma user story começa antes desta fase fechar.

- [X] T003 Criar `frontend/src/app/ai/chat/loading.tsx` e `frontend/src/app/ai/chat/error.tsx` copiando o conteúdo de `frontend/src/app/assistant/loading.tsx` e `frontend/src/app/assistant/error.tsx` (o esqueleto sem timeout da rodada 006 é reaproveitado como está)
- [X] T004 Em `frontend/src/components/assistant/ai-assistant.tsx`, trocar a leitura de `useSearchParams()` por uma prop `conversationId?: string | null`: remover os dois `useEffect` de mount que leem `searchParams.get("c")` e passar a carregar a conversa a partir da prop. Manter `contextTokenRef` e a regra de resposta em voo intactos
- [X] T005 Em `frontend/src/components/assistant/ai-assistant.tsx`, **remover** o auto-carregamento da conversa mais recente (`autoLoadedFirstRef` + o `useEffect` sobre `conversations`). Com endereço por conversa, `/ai/chat` significa conversa nova — abrir a mais recente ali contradiz FR-005

**Checkpoint**: a tela do assistente é dirigida por prop, não por query string. US1, US2 e US3 podem começar.

---

## Phase 3: User Story 1 — Cada conversa tem endereço próprio (Priority: P1) 🎯 MVP

**Goal**: `/ai/chat/{id}` identifica a conversa; `/ai/chat` é a conversa nova; voltar/avançar e recarregar funcionam.

**Independent Test**: abrir duas conversas em sequência, conferir que o endereço muda a cada uma, apertar voltar e confirmar que retorna à anterior (não à tela inicial), recarregar e confirmar que a conversa continua aberta.

### Implementation for User Story 1

- [X] T006 [P] [US1] Criar `frontend/src/app/ai/chat/page.tsx`: renderiza `<AiAssistant conversationId={null} />` dentro do `<Suspense>` que a página antiga já usa
- [X] T007 [P] [US1] Criar `frontend/src/app/ai/chat/[id]/page.tsx`: lê `params.id` e renderiza `<AiAssistant conversationId={id} />`
- [X] T008 [P] [US1] Criar o estado visual de conversa ausente em `frontend/src/components/assistant/not-found-state.tsx`: explica a ausência e oferece iniciar nova conversa (FR-007), reaproveitando `frontend/src/components/ui/empty-state.tsx`
- [X] T009 [US1] Em `frontend/src/components/assistant/ai-assistant.tsx`, validar `conversationId` como UUID **antes** de qualquer requisição e distinguir três estados de carga (carregando / carregada / não encontrada); `404` do servidor cai no mesmo estado que identificador malformado — nunca distinguir os dois (FR-014, SC-006). Substitui o `if (!result.ok) return;` silencioso de `loadConversation` (depende de T004, T008)
- [X] T010 [US1] Em `frontend/src/components/assistant/ai-assistant.tsx`, trocar o endereço para `/ai/chat/{id}` com `window.history.replaceState` logo depois de `ensureConversationId()` resolver na primeira pergunta — **não** usar `router.push`/`router.replace`, que remontariam a árvore e abortariam o `fetch` em voo (research R2, FR-006). Deixar comentário `ponytail:` nomeando o teto: válido enquanto `/ai/chat` e `/ai/chat/{id}` renderizarem o mesmo componente
- [X] T011 [US1] Em `frontend/src/components/shell/app-sidebar.tsx:116,122`, trocar `router.push('/assistant?c=' + id)` por `router.push('/ai/chat/' + id)` e `router.push('/assistant')` por `router.push('/ai/chat')`; atualizar o comentário do topo do arquivo que ainda descreve o formato `?c=<id>`
- [X] T012 [P] [US1] Em `frontend/src/lib/nav.ts:49,60`, trocar `href: "/assistant"` por `"/ai/chat"` nas duas entradas "Assistente de IA", e atualizar os comentários das linhas 80 e 100 que citam `/assistant` como rota compartilhada
- [X] T013 [US1] Validar US1 rodando a seção 4 de [quickstart.md](./quickstart.md): endereço distinto por conversa, voltar 3× , recarregar, aba nova, `/ai/chat/nao-e-uuid` sem requisição, troca de endereço durante a resposta em voo, console sem erro

**Checkpoint**: US1 entregável sozinha. Endereços antigos ainda funcionam pela página `/assistant` original, que só é substituída na US3.

---

## Phase 4: User Story 2 — Arquivar conversa (Priority: P2)

**Goal**: conversa arquivada some das listas ativas, continua acessível por lista própria e por endereço direto, e volta ao lugar certo ao desarquivar.

**Independent Test**: arquivar uma conversa, confirmar que sai das listas ativas, encontrá-la na lista de arquivadas, desarquivar e confirmar que volta ao lugar de origem.

### Tests for User Story 2 ⚠️

> Escrever primeiro, confirmar que falham antes de implementar.

- [X] T014 [P] [US2] Em `backend/tests/test_assistant_conversation.py`, adicionar os testes 1–3 de `contracts/conversations-api.md`: arquivar tira de `state=active` e coloca em `state=archived`; desarquivar devolve à lista ativa com `is_favorite` preservado; arquivar conversa favoritada mantém `is_favorite: true`
- [X] T015 [P] [US2] Em `backend/tests/test_assistant_conversation.py`, adicionar os testes 4–5: arquivar duas vezes preserva o `archived_at` do primeiro arquivamento (data-model I-4); arquivar e desarquivar não alteram `updated_at` (I-3)
- [X] T016 [P] [US2] Em `backend/tests/test_assistant_conversation.py`, adicionar os testes 6–9: sessão B recebe `404` ao arquivar conversa da sessão A (espelhar o teste de posse já existente para renomear); `GET /conversations` sem `state` não devolve arquivadas; `DELETE` de conversa arquivada devolve o mesmo resultado de uma ativa; `state` fora do enum devolve `422`

### Implementation for User Story 2 — servidor

- [X] T017 [US2] Em `backend/app/repositories/schema.py`, adicionar `archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)` a `AssistantConversationRow`, com comentário explicando `NULL` = ativa
- [X] T018 [US2] Criar `backend/migrations/versions/008_conversation_archived.py` com `revision = "008"`, `down_revision = "007"`: `upgrade` faz `ADD COLUMN archived_at TIMESTAMPTZ NULL`, `downgrade` faz `DROP COLUMN`. Sem backfill, sem `NOT NULL`, sem default (data-model §4)
- [X] T019 [US2] Em `backend/app/repositories/assistant.py`, dar a `list_conversations` um parâmetro `state: Literal["active","archived"] = "active"`: `active` filtra `archived_at IS NULL` mantendo a ordenação atual; `archived` filtra `archived_at IS NOT NULL` ordenando por `archived_at` decrescente. Default preserva o comportamento de quem já consome (depende de T017)
- [X] T020 [US2] Em `backend/app/repositories/assistant.py`, adicionar `set_archived(conversation_id, session_id, is_archived) -> bool` no padrão de `set_favorite`: usa `get_owned`, grava `datetime.now(timezone.utc)` **só se `archived_at` ainda for `None`** (não re-carimba — I-4), grava `None` ao desarquivar, e **não** toca `updated_at` nem `is_favorite` (I-2, I-3)
- [X] T021 [US2] Em `backend/app/api/routes_assistant.py`, adicionar `is_archived: bool | None = None` a `ConversationUpdateRequest`, chamar `set_archived` quando presente, e incluir `"archived_at"` (ISO-8601 ou `null`) em `_conversation_summary` (depende de T020)
- [X] T022 [US2] Em `backend/app/api/routes_assistant.py`, dar a `GET /conversations` o parâmetro de query `state: Literal["active","archived"] = "active"` e repassar a `list_conversations` (depende de T019)
- [X] T023 [US2] Rodar `cd backend && alembic upgrade head && pytest -q` — testes T014–T016 passam, os 14 existentes continuam verdes; conferir reversão com `alembic downgrade 007 && alembic upgrade head` (quickstart §1)

### Implementation for User Story 2 — interface

- [X] T024 [P] [US2] Em `frontend/src/lib/types.ts`, adicionar `archived_at: string | null` a `ConversationSummary`
- [X] T025 [US2] Em `frontend/src/lib/use-conversations.ts`, adicionar `archive(id, next: boolean)` no padrão de `toggleFavorite` (PATCH `{ is_archived: next }` seguido de `refresh()`), e permitir que `refresh` busque por estado — a lista de arquivadas usa o mesmo hook, sem duplicar chamada (depende de T024)
- [X] T026 [P] [US2] Criar `frontend/src/app/ai/arquivadas/page.tsx`: lista as conversas de `state=archived`, cada item linkando para `/ai/chat/{id}`, com ações de desarquivar e excluir. Lista vazia mostra `frontend/src/components/ui/empty-state.tsx`, nunca espaço em branco (US2 cenário 7)
- [X] T027 [US2] Em `frontend/src/components/shell/app-sidebar.tsx`, adicionar "Arquivar" ao menu de contexto da conversa e um caminho de navegação para `/ai/arquivadas`. **Não** adicionar seção de arquivadas sempre visível na barra lateral — o objetivo do arquivamento é tirar essas conversas do caminho (A-004)
- [X] T028 [US2] Em `frontend/src/components/assistant/ai-assistant.tsx`, exibir aviso de "conversa arquivada" quando a conversa aberta tiver `archived_at`, mantendo a tela utilizável (US2 cenários 4 e 5)
- [X] T029 [US2] Em `frontend/src/components/shell/app-sidebar.tsx`, garantir que a exclusão de conversa arquivada use a mesma janela de desfazer da rodada 006 (`frontend/src/lib/undoable.ts` + `removeLocally`/`restoreLocally`) e que desfazer devolva a conversa ao estado **arquivado**, não ao ativo (FR-013)
- [X] T030 [US2] Validar US2 rodando as seções 2, 3 e 6 de [quickstart.md](./quickstart.md): contrato de arquivamento, idempotência do carimbo, isolamento por sessão, e a passagem de interface completa

**Checkpoint**: US1 e US2 funcionam independentes.

---

## Phase 5: User Story 3 — Endereços antigos continuam funcionando (Priority: P3)

**Goal**: `/assistant` e `/assistant?c=<id>` chegam ao destino equivalente no formato novo, e a barra de endereço termina no formato novo.

**Independent Test**: acessar o endereço antigo, com e sem identificador de conversa, e confirmar que chega ao destino equivalente no formato novo.

### Implementation for User Story 3

- [X] T031 [US3] Reescrever `frontend/src/app/assistant/page.tsx` como página de **servidor** que lê `searchParams.c` e chama `redirect()`: com `c` não vazio vai para `/ai/chat/{c}`, sem `c` vai para `/ai/chat`. Redirecionamento de servidor, não de cliente — a rota antiga não fica no histórico (FR-017). Remove o `"use client"` e o `<Suspense>`, que existiam só por causa de `useSearchParams`
- [X] T032 [P] [US3] Excluir `frontend/src/app/assistant/loading.tsx` e `frontend/src/app/assistant/error.tsx` — o redirecionador não renderiza nada; os equivalentes vivem em `frontend/src/app/ai/chat/` desde T003 (depende de T031)
- [X] T033 [US3] Validar US3 rodando a seção 5 de [quickstart.md](./quickstart.md): `307` para os dois formatos, barra de endereço no formato novo, e voltar não passando pela rota antiga

**Checkpoint**: as três user stories funcionam.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T034 [P] Varrer `frontend/src/` atrás de "copiar link"/"compartilhar"/"share"/"clipboard" ligado a endereço de conversa e confirmar zero ocorrência (FR-015, SC-007, quickstart §7)
- [X] T035 [P] Atualizar a seção "o que ficou de fora" do `README.md` cobrindo as rodadas **006 e 007** — ficou devendo desde a 006 (`T054`) e a Constituição §V a exige a cada bloco. Registrar como decisões conscientes: `history.replaceState` em vez de sincronizar roteador (teto: layouts divergentes), ausência de índice em `archived_at`, e os itens de "Out of Scope" da spec (rename da API, compartilhamento, envio de arquivo)
- [X] T036 Portas de qualidade finais (SC-009): `cd backend && pytest -q` e `cd frontend && npx tsc --noEmit && npx eslint .` — comparar com a linha de base de T001/T002, nenhum erro novo
- [X] T037 Passagem completa de [quickstart.md](./quickstart.md) do começo ao fim, numa sessão limpa de navegador

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependência
- **Foundational (Phase 2)**: depende do Setup — **bloqueia todas as user stories**
- **US1 (Phase 3)**: depende da Phase 2
- **US2 (Phase 4)**: depende da Phase 2; **não** depende da US1
- **US3 (Phase 5)**: depende da **US1** — o redirecionador precisa de um destino existente
- **Polish (Phase 6)**: depende das stories entregues

### User Story Dependencies

- **US1 (P1)**: independente
- **US2 (P2)**: independente da US1. A spec diz que depende dela "apenas por conveniência" (o alvo fica explícito); tecnicamente o servidor e a lista de arquivadas não precisam do endereço novo
- **US3 (P3)**: **depende da US1**. Única dependência real entre stories nesta rodada

### Within Each User Story

- Testes de backend (T014–T016) antes da implementação de servidor (T017–T022)
- Schema antes de migração antes de repositório antes de rota
- Servidor antes da interface, dentro da US2
- Validação por quickstart fecha cada story

### Parallel Opportunities

- T001/T002 em paralelo
- T006, T007, T008, T012 em paralelo (arquivos distintos)
- T014, T015, T016 em paralelo (blocos independentes do mesmo arquivo de teste — se escritos pela mesma pessoa, sequencial)
- **US1 e US2 em paralelo**: US1 é só frontend, US2 começa por backend. Duas pessoas não colidem em arquivo até T028
- T024 e T026 em paralelo com o bloco de servidor da US2
- T034 e T035 em paralelo

---

## Parallel Example: User Story 1

```bash
# Rotas e estado visual, arquivos distintos:
Task: "Criar frontend/src/app/ai/chat/page.tsx"
Task: "Criar frontend/src/app/ai/chat/[id]/page.tsx"
Task: "Criar frontend/src/components/assistant/not-found-state.tsx"
Task: "Atualizar hrefs em frontend/src/lib/nav.ts"
```

## Parallel Example: User Story 2

```bash
# Servidor e interface arrancam juntos:
Task: "Testes de contrato de arquivamento em backend/tests/test_assistant_conversation.py"
Task: "archived_at em frontend/src/lib/types.ts"
Task: "Página de arquivadas em frontend/src/app/ai/arquivadas/page.tsx"
```

---

## Implementation Strategy

### MVP (US1)

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1)
2. **PARAR e VALIDAR**: quickstart §4
3. Entregável: endereço por conversa, com os endereços antigos ainda servidos pela página original

### Entrega incremental

1. Setup + Foundational → base pronta
2. US1 → validar → **MVP**
3. US2 → validar (backend primeiro, interface depois)
4. US3 → validar — fecha a compatibilidade e aposenta `/assistant`
5. Polish

### Ordem sugerida para uma pessoa só

Phase 1 → Phase 2 → US1 → US3 (barato, fecha a regressão de endereço que a US1 abre) → US2 → Polish.

Trocar US2 e US3 de ordem em relação à prioridade da spec é deliberado: a US1 sozinha deixa `/assistant` renderizando uma segunda cópia da tela, e a US3 são 2 tasks que fecham isso.

---

## Desvios do plano (registrados na execução, 2026-08-02)

Quatro coisas saíram diferente do planejado. Todas medidas, nenhuma silenciosa.

1. **`loading.tsx` do segmento `/ai/chat` foi criado (T003) e depois
   removido.** Com ele no lugar, `/ai/chat` e `/ai/chat/[id]` **param de
   hidratar**: nenhum efeito roda, nenhuma requisição sai, a tela congela no
   HTML do servidor (`TypeError: Cannot read properties of null (reading
   'parentNode')` no injetor de stream do React). Reproduzido nos dois
   sentidos — com o arquivo quebra, sem ele funciona. `error.tsx` ficou.

2. **A lista de arquivadas saiu do grupo `(shell)` (T026).** Ela nasceu em
   `frontend/src/app/(shell)/ai/arquivadas/page.tsx` para herdar topbar e
   barra lateral de graça. Declarar o segmento `ai` dentro **e** fora de um
   grupo de rota fez o Next aplicar o layout do `(shell)` a `/ai/chat/[id]` e
   quebrar a hidratação da tela do Assistente. Movida para
   `frontend/src/app/ai/arquivadas/page.tsx`, chamando `ShellChrome`
   diretamente — o que o grupo fazia, em uma linha.

3. **`GET /conversations/{id}/messages` ganhou o campo `conversation`**, que o
   contrato marcava como inalterado. Conversa arquivada, por definição, não
   aparece em `GET /conversations` — sem esse campo a tela precisaria de uma
   segunda requisição só para descobrir o estado do que acabou de carregar.
   Campo aditivo; `contracts/conversations-api.md` foi atualizado junto.

4. **`sectionLabel` ganhou uma linha para `/ai/arquivadas`.** A rota não é item
   de NAV (A-004), então o cabeçalho do shell mostrava "Home" nela.

## Notes

- `[P]` = arquivos diferentes, sem dependência pendente
- Migração `008` tem `down_revision = "007"` — conferir a cabeça antes (T001), não presumir
- Nenhuma dependência nova (Constituição §V). Nada de rota nova no servidor: campo opcional no `PATCH` existente
- Testes de backend rodam **sem rede e sem credencial** (Constituição §IV)
- Commitar por task ou grupo lógico; parar em qualquer checkpoint para validar
