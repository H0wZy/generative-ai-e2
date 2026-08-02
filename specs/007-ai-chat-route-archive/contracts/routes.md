# Contrato — Endereços do frontend

**Feature**: `specs/007-ai-chat-route-archive`

Endereços do navegador. Nenhuma rota de servidor HTTP muda aqui (ver
`conversations-api.md` para o contrato de dados).

---

## Mapa

| Endereço | Significado | Renderiza |
|---|---|---|
| `/ai/chat` | conversa nova, ainda sem registro no servidor | tela do assistente sem conversa carregada |
| `/ai/chat/{id}` | conversa existente | tela do assistente com o histórico de `{id}` |
| `/ai/chat/arquivadas` — **não existe** | — | ver nota abaixo |
| `/ai/arquivadas` | lista de conversas arquivadas | destino próprio (A-004) |
| `/assistant` | **compatibilidade** | redirecionamento de servidor para `/ai/chat` |
| `/assistant?c={id}` | **compatibilidade** | redirecionamento de servidor para `/ai/chat/{id}` |

A lista de arquivadas fica **fora** de `/ai/chat/`, e não como segmento irmão
de `{id}`: qualquer palavra sob `/ai/chat/` disputaria espaço com identificador
de conversa, que é exatamente o que R1 evitou.

---

## `/ai/chat` — conversa nova

- Não faz requisição de histórico.
- Não cria conversa no servidor ao abrir (A-002).
- Ao enviar a primeira pergunta: a conversa é criada, e o endereço passa a
  `/ai/chat/{id}` via `history.replaceState` — **sem** navegação do roteador
  (R2), portanto sem remontar a árvore e sem abortar a resposta em voo
  (FR-006).
- A troca **substitui** a entrada de histórico: apertar voltar depois de enviar
  a primeira pergunta não deve voltar para "conversa nova em branco".

## `/ai/chat/{id}` — conversa existente

Entrada:

- `{id}`: identificador da conversa, formato UUID.

Estados possíveis da tela:

| Condição | Resultado |
|---|---|
| `{id}` não é UUID válido | estado "não encontrada" **sem** chegar a fazer requisição |
| requisição devolve `404` | estado "não encontrada" (FR-007) |
| requisição devolve `200` | histórico completo renderizado (FR-003) |

O estado "não encontrada" explica a ausência e oferece iniciar nova conversa.
Não distingue "não existe" de "é de outra sessão" — o servidor já não distingue
(R5), e distinguir vazaria existência (FR-014, SC-006).

Navegação entre conversas (clique na barra lateral) usa o roteador normalmente,
produzindo entrada de histórico e habilitando voltar/avançar (FR-002, FR-004).

## `/ai/arquivadas` — lista de arquivadas

- Lista conversas com estado `archived`.
- Lista vazia mostra mensagem de vazio, não espaço em branco (US2, cenário 7).
- Cada item leva a `/ai/chat/{id}` e oferece desarquivar e excluir.

## `/assistant` — compatibilidade

Página de **servidor** que lê a query e redireciona:

```
c presente e não vazio → /ai/chat/{c}
caso contrário         → /ai/chat
```

Redirecionamento de servidor, não de cliente: a rota antiga não fica no
histórico e a barra de endereço mostra só o formato novo (FR-017, SC-008).

A página antiga deixa de renderizar o assistente — vira apenas o
redirecionador. Os geradores internos de link
(`frontend/src/lib/nav.ts`, `frontend/src/components/shell/app-sidebar.tsx:116`)
passam a apontar direto para o formato novo; o redirecionamento existe para
links já em circulação.

---

## Proibições

- **Nenhuma** tela oferece copiar ou compartilhar endereço de conversa (FR-015,
  SC-007). O formato de endereço imita produtos onde o link é compartilhável;
  aqui a posse é por sessão de navegador. Não criar promessa falsa.
