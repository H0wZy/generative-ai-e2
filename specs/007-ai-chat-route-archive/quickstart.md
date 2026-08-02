# Phase 1 — Quickstart: verificação da rodada 007

**Feature**: `specs/007-ai-chat-route-archive`
**Date**: 2026-08-02

Cada bloco fecha um critério de sucesso da spec. Rodar na ordem: portas de
qualidade, servidor, depois navegador.

Pré-requisitos: stack de pé (`make up` ou equivalente do ambiente), migração
`008` aplicada, frontend em `http://localhost:3000`, backend em
`http://localhost:8000`.

---

## 0 — Portas de qualidade (SC-009)

```bash
# frontend
cd frontend && npx tsc --noEmit && npx eslint .

# backend
cd backend && pytest -q
```

Esperado: `tsc` sem saída; `eslint` sem erro **novo** (o
`react-hooks/set-state-in-effect` em `src/lib/nav.ts` é pré-existente da rodada
006); `pytest` verde, sem rede e sem credencial.

---

## 1 — Migração

```bash
cd backend && alembic upgrade head && alembic current
```

Esperado: cabeça em `008`.

```bash
psql "$DATABASE_URL" -c "\d assistant_conversations" | grep archived_at
```

Esperado: `archived_at | timestamp with time zone |` (nulável, sem default).

Reversão:

```bash
alembic downgrade 007 && alembic upgrade head
```

Esperado: ambos sem erro.

---

## 2 — Contrato de arquivamento (FR-008 … FR-013, SC-004, SC-005)

```bash
S=$(uuidgen)
API=http://localhost:8000/api/v1/assistant

# cria e favorita
C=$(curl -s -XPOST $API/conversations -H "X-Session-Id: $S" | jq -r .id)
curl -s -XPATCH $API/conversations/$C -H "X-Session-Id: $S" \
  -H 'content-type: application/json' -d '{"is_favorite":true}' >/dev/null

# arquiva
curl -s -XPATCH $API/conversations/$C -H "X-Session-Id: $S" \
  -H 'content-type: application/json' -d '{"is_archived":true}' | jq '{is_favorite,archived_at}'
```

Esperado: `is_favorite: true`, `archived_at` com carimbo (FR-011, FR-012).

```bash
curl -s "$API/conversations" -H "X-Session-Id: $S" | jq '.conversations|length'
curl -s "$API/conversations?state=archived" -H "X-Session-Id: $S" | jq '.conversations|length'
```

Esperado: `0` e `1` (FR-009, SC-004).

```bash
# idempotência do carimbo (data-model I-4)
A1=$(curl -s "$API/conversations?state=archived" -H "X-Session-Id: $S" | jq -r '.conversations[0].archived_at')
curl -s -XPATCH $API/conversations/$C -H "X-Session-Id: $S" \
  -H 'content-type: application/json' -d '{"is_archived":true}' >/dev/null
A2=$(curl -s "$API/conversations?state=archived" -H "X-Session-Id: $S" | jq -r '.conversations[0].archived_at')
[ "$A1" = "$A2" ] && echo "carimbo preservado" || echo "FALHA: re-carimbou"
```

```bash
# desarquiva → volta pra lista ativa, ainda favorita (SC-005)
curl -s -XPATCH $API/conversations/$C -H "X-Session-Id: $S" \
  -H 'content-type: application/json' -d '{"is_archived":false}' | jq '{is_favorite,archived_at}'
```

Esperado: `is_favorite: true`, `archived_at: null`.

---

## 3 — Isolamento por sessão (FR-014, SC-006)

```bash
S2=$(uuidgen)
curl -s -o /dev/null -w '%{http_code}\n' "$API/conversations/$C/messages" -H "X-Session-Id: $S2"
curl -s -o /dev/null -w '%{http_code}\n' -XPATCH "$API/conversations/$C" -H "X-Session-Id: $S2" \
  -H 'content-type: application/json' -d '{"is_archived":true}'
curl -s -o /dev/null -w '%{http_code}\n' "$API/conversations/$(uuidgen)/messages" -H "X-Session-Id: $S2"
```

Esperado: `404`, `404`, `404` — conversa de outra sessão indistinguível de
inexistente, e nenhum corpo com título ou mensagem.

---

## 4 — Endereço por conversa (SC-001, SC-002, SC-003)

No navegador, com pelo menos 3 conversas na sessão:

| Passo | Esperado |
|---|---|
| abrir 3 conversas em sequência pela barra lateral | endereço muda para `/ai/chat/{id}` distinto a cada uma (SC-001) |
| apertar voltar 3× | retorna à conversa imediatamente anterior nas 3 vezes, sem sair da tela do assistente (SC-002) |
| recarregar (F5) numa conversa | mesmo histórico completo reabre (SC-003) |
| copiar o endereço, abrir em aba nova da mesma sessão | mesma conversa abre (SC-001) |
| abrir `/ai/chat/nao-e-uuid` | tela "conversa não encontrada" com caminho para nova conversa; **nenhuma** requisição de mensagens na aba Network (FR-007) |
| abrir `/ai/chat/$(uuidgen)` | mesma tela de não encontrada |

### Troca de endereço na primeira pergunta (FR-006)

1. Abrir `/ai/chat`.
2. Enviar uma pergunta.
3. Enquanto a resposta ainda está chegando, observar a barra de endereço.

Esperado: endereço vira `/ai/chat/{id}` **durante** a espera; a resposta chega
normalmente; nenhum recarregamento; o indicador de carregamento não pisca nem
reinicia.

4. Apertar voltar.

Esperado: **não** volta para uma conversa nova em branco — a troca substituiu a
entrada, não empilhou.

### Console limpo

```js
// colar no console antes do passo 1
console.__errs = []; const _e = console.error;
console.error = (...a) => { console.__errs.push(a[0]); _e(...a); };
// depois de toda a navegação:
console.log(console.__errs.length);
```

Esperado: `0`.

---

## 5 — Compatibilidade dos endereços antigos (FR-016, FR-017, SC-008)

```bash
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' "http://localhost:3000/assistant"
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' "http://localhost:3000/assistant?c=$C"
```

Esperado: `307 .../ai/chat` e `307 .../ai/chat/$C`.

No navegador, abrir os dois endereços antigos: a barra de endereço termina no
formato novo, e o botão voltar **não** passa pela rota antiga (FR-017).

---

## 6 — Arquivamento na interface (US2)

| Passo | Esperado |
|---|---|
| arquivar uma conversa pelo menu de contexto | some de "Favoritos"/"Recentes" na hora; aviso de confirmação |
| abrir a lista de arquivadas | a conversa está lá |
| desarquivar | volta para a lista de origem — "Favoritos" se estava favoritada (SC-005) |
| arquivar a conversa que está aberta | a tela continua utilizável e informa que está arquivada |
| abrir `/ai/chat/{id}` de uma arquivada | abre normalmente, com aviso de arquivada (FR-010) |
| excluir uma arquivada | mesma janela de desfazer da rodada 006; desfazer devolve ao estado **arquivado** |
| esvaziar a lista de arquivadas | mensagem de lista vazia, não espaço em branco |

---

## 7 — Privacidade da interface (FR-015, SC-007)

```bash
cd frontend && grep -rniE "copiar link|compartilhar|share|clipboard" src/ | grep -v node_modules
```

Esperado: nenhuma ocorrência ligada a endereço de conversa. Nenhum menu de
conversa oferece copiar ou compartilhar endereço.
