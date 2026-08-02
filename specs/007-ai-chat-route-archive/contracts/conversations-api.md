# Contrato — `/api/v1/assistant/conversations`

**Feature**: `specs/007-ai-chat-route-archive`

Prefixo **não muda** (A-001). Nenhuma rota nova. Dois endpoints existentes
ganham campo opcional; os outros ficam byte a byte iguais.

Autenticação continua sendo o header `X-Session-Id` (UUID). Sem ele ou com
valor inválido: `400` nas rotas de recurso, lista vazia na listagem — regra
atual, preservada.

---

## `GET /conversations` — **estendido**

### Antes

```
GET /api/v1/assistant/conversations
X-Session-Id: <uuid>
→ 200 { "conversations": [ {id, title, updated_at, is_favorite}, ... ] }
```

### Depois

```
GET /api/v1/assistant/conversations?state=active|archived
```

| Parâmetro | Tipo | Default | Efeito |
|---|---|---|---|
| `state` | `"active" \| "archived"` | `"active"` | filtra por estado de arquivamento |

- `state=active` (e ausência do parâmetro): só `archived_at IS NULL`, ordenado
  por favorita e depois por atualização — **comportamento atual preservado**,
  agora sem as arquivadas (FR-009).
- `state=archived`: só `archived_at IS NOT NULL`, ordenado por `archived_at`
  decrescente.
- Valor fora do enum: `422` (validação do próprio FastAPI).

### Resposta — item

```json
{
  "id": "uuid",
  "title": "string",
  "updated_at": "iso-8601",
  "is_favorite": true,
  "archived_at": "iso-8601 | null"
}
```

`archived_at` é **campo novo** no resumo. Aditivo: consumidor que ignora campo
desconhecido não quebra.

---

## `PATCH /conversations/{id}` — **estendido**

### Antes

```json
{ "title": "string | null", "is_favorite": "bool | null" }
```

Campos opcionais, aplica só o que veio (PATCH parcial).

### Depois

```json
{ "title": "string | null", "is_favorite": "bool | null", "is_archived": "bool | null" }
```

| Valor | Efeito no servidor |
|---|---|
| `is_archived: true` | `archived_at := now()` — **só se ainda for `NULL`** (I-4: não re-carimba) |
| `is_archived: false` | `archived_at := NULL` |
| ausente / `null` | não toca `archived_at` |

O corpo é booleano, não data: a interface alterna um estado, e aceitar carimbo
do cliente seria confiar relógio de navegador (R3).

Arquivar **não** altera `is_favorite` (FR-011) e **não** toca `updated_at`
(data-model I-3).

Respostas:

| Situação | Código |
|---|---|
| conversa da sessão | `200` + resumo atualizado |
| conversa de outra sessão, ou inexistente | `404` — indistinguíveis |
| sem `X-Session-Id` válido | `400` |

---

## Inalterados

| Endpoint | Nota |
|---|---|
| `POST /conversations` | cria ativa (`archived_at` nasce `NULL`) |
| `DELETE /conversations/{id}` | funciona igual para arquivada (FR-013) |
| `POST /ask` | intocado |

### `GET /conversations/{id}/messages` — **campo aditivo**

Conversa arquivada continua abrindo normalmente (FR-010). A resposta ganha
`"conversation"` com o mesmo resumo de `GET /conversations`:

```json
{ "messages": [...], "conversation": { "id": "...", "archived_at": "... | null", ... } }
```

Motivo: a tela precisa avisar que a conversa aberta está arquivada (US2
cenários 4 e 5), e conversa arquivada **não aparece** em `GET /conversations`
por definição — sem isto a interface precisaria de uma segunda requisição só
para descobrir o estado do que já acabou de carregar.

---

## Testes de contrato

Em `backend/tests/test_assistant_conversation.py`, espelhando os padrões de
posse que o arquivo já usa:

1. arquivar tira de `state=active` e coloca em `state=archived`;
2. desarquivar devolve à lista ativa com `is_favorite` preservado;
3. arquivar conversa favoritada mantém `is_favorite: true`;
4. arquivar duas vezes preserva o `archived_at` do primeiro arquivamento (I-4);
5. arquivar/desarquivar não altera `updated_at` (I-3);
6. sessão B recebe `404` ao tentar arquivar conversa da sessão A;
7. `GET /conversations` sem `state` não devolve arquivadas (compatibilidade);
8. `DELETE` de conversa arquivada devolve o mesmo resultado de uma ativa;
9. `state` com valor inválido devolve `422`.

Todos de repositório e rota, sem rede e sem credencial — Constituição §IV
atendida sem esforço extra.
