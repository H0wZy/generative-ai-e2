# Contrato — `/api/v1/assistant/conversations/{conversation_id}/attachment`

**Feature**: `specs/013-upload-documento-treerag`

Três rotas novas. Nenhuma rota existente muda de forma — `/ask` ganha
comportamento adicional (busca também na árvore do anexo quando existir),
sem mudar seu formato de entrada/saída.

Autenticação: mesmo header `X-Session-Id` (UUID) já usado pelas rotas de
conversa. Sem ele, ou conversa que não pertence à sessão: `404` (mesma regra
de `get_conversation_messages`).

---

## `POST /conversations/{conversation_id}/attachment` — **novo**

Upload multipart/form-data, um único campo `file`.

```
POST /api/v1/assistant/conversations/{conversation_id}/attachment
X-Session-Id: <uuid>
Content-Type: multipart/form-data; file=<binário>
```

Processamento é síncrono — a resposta só volta quando `status` chega a
`ready` ou `failed` (sem polling nesta rodada; ver quickstart.md para o
comportamento esperado em PDF grande via OCR).

### Resposta — `201`

```json
{
  "id": "uuid",
  "file_name": "manual.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 182004,
  "status": "ready",
  "error_reason": null
}
```

### Erros

| Situação | Status | Corpo |
|---|---|---|
| Conversa não encontrada / não pertence à sessão | `404` | `{"detail": "Conversa não encontrada."}` |
| Extensão/MIME fora de `.md`, `.txt`, `.pdf` | `422` | `{"detail": "Formato não suportado. Envie .md, .txt ou .pdf."}` |
| Acima do tamanho máximo (FR-003) | `413` | `{"detail": "Arquivo acima do limite permitido (<N> MB)."}` |
| Extração/OCR falhou (FR-012) | `201` com `status: "failed"` | corpo acima, `error_reason` preenchido — **não** é erro HTTP: o upload em si teve sucesso, o processamento que falhou, e a pessoa precisa ver isso na conversa, não só num toast |

Upload bem-sucedido substitui qualquer anexo anterior da mesma conversa
(research.md R6) — a linha antiga (e seus nós) é removida antes da nova ser
criada.

---

## `GET /conversations/{conversation_id}/attachment` — **novo**

```
GET /api/v1/assistant/conversations/{conversation_id}/attachment
X-Session-Id: <uuid>
```

### Resposta — `200`

Mesmo formato do `POST`, ou `{"attachment": null}` quando a conversa não tem
anexo ativo. Usado pela tela ao carregar uma conversa existente, para mostrar
o indicador de documento anexado (FR-013) sem depender de estado só em
memória do navegador.

---

## `DELETE /conversations/{conversation_id}/attachment` — **novo**

```
DELETE /api/v1/assistant/conversations/{conversation_id}/attachment
X-Session-Id: <uuid>
→ 204
```

Remove o anexo ativo (e seus nós, via cascade) sem exigir upload de
substituição. `404` se a conversa não existe/não pertence à sessão; `204`
mesmo se não havia anexo (idempotente, mesmo espírito de `set_favorite`).

---

## `POST /ask` — **estendido, sem mudança de forma**

Quando a conversa referenciada por `conversation_id` tem anexo com
`status = ready`, o serviço (`services/assistant.py::ask`) passa a consultar
também a árvore do anexo (research.md R3), além da busca RAG já existente.
Fontes de ambas origens compartilham a mesma forma `RetrievedSource` — o
consumidor (frontend) não precisa distinguir de onde veio uma citação, só
exibir `file_path`/`heading_path`/trecho, como já faz hoje.

Se o anexo existe mas está `processing` ou `failed`, o comportamento é o
mesmo de "sem anexo": a pergunta segue só com a busca RAG existente (nunca
bloqueia `/ask` esperando o processamento terminar).
