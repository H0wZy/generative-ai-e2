# Phase 0 — Research: Rota por conversa e arquivamento

**Feature**: `specs/007-ai-chat-route-archive`
**Date**: 2026-08-01

Estado inspecionado no repositório, não presumido. Onde o pedido do usuário
conflitava com o código existente, o conflito está nomeado.

---

## R1 — Endereço da conversa ainda não persistida

### Problema

A conversa só vira registro no servidor na primeira pergunta (criação
preguiçosa, decisão deliberada da rodada anterior para não encher "Recentes" de
conversa vazia). Com endereço por identificador, existe uma janela em que a tela
está aberta e **não há identificador**. Precisa de endereço mesmo assim.

### Opções

| Opção | Forma | Problema |
|---|---|---|
| A | `/ai/chat/novo` (segmento literal) | Palavra reservada no mesmo espaço dos identificadores; obriga escolher idioma do segmento; exige excluir esse valor da validação de identificador |
| B | `/ai/chat` (sem segmento) | Nenhum — o vazio já significa "ainda não existe" |
| C | Criar a conversa no servidor ao abrir | Desfaz a criação preguiçosa; enche "Recentes" de conversa vazia |

### Decisão

**Opção B.** Duas rotas irmãs: `/ai/chat` é a conversa nova, `/ai/chat/{id}` é
uma conversa existente. Sem valor mágico convivendo com identificadores, sem
decidir idioma de segmento, e a validação do identificador não precisa abrir
exceção para nada.

Descarta C porque contraria escolha anterior consciente (spec 006) e produziria
lixo em "Recentes" a cada clique em "Nova conversa" sem envio.

---

## R2 — Trocar o endereço quando a conversa passa a existir

### Problema

FR-006: ao enviar a primeira pergunta em `/ai/chat`, o endereço deve passar a
`/ai/chat/{id}` **sem recarregar e sem interromper a resposta em andamento**. A
resposta é pedida logo depois da criação da conversa; qualquer coisa que
remonte a árvore aborta o `fetch` em voo ou descarta o estado local dos turnos.

### Opções

| Opção | Efeito |
|---|---|
| A | `router.push(...)` — navegação do App Router: re-renderiza o segmento, remonta o componente cliente, perde os turnos em memória e a requisição em voo |
| B | `router.replace(...)` — mesmo problema de A, só não empilha histórico |
| C | `window.history.replaceState` — troca a barra de endereço sem envolver o roteador; nada remonta |

### Decisão

**Opção C** para a troca no momento da criação. É o único caminho que satisfaz
"sem recarregar e sem interromper" literalmente.

Consequência aceita e registrada: o roteador do Next passa a ter uma URL que ele
não navegou. Isso é seguro aqui porque `/ai/chat` e `/ai/chat/{id}` renderizam o
**mesmo componente cliente**, com o identificador entrando por props; não há
árvore de servidor diferente para reconciliar. Se um dia as duas rotas passarem
a renderizar layouts distintos, esta escolha precisa ser revista — anotado como
teto conhecido.

Navegação normal entre conversas (clique na barra lateral) continua usando o
roteador, que é o que dá entrada de histórico e o botão voltar (FR-002, FR-004).

**ponytail**: `history.replaceState` em vez de sincronizar roteador é atalho
deliberado. Ceiling: se `/ai/chat` e `/ai/chat/{id}` divergirem em layout, trocar
por navegação de verdade com estado elevado para fora do segmento.

---

## R3 — Modelo do arquivamento

### Opções para representar

| Opção | Custo | Ganho |
|---|---|---|
| A | `is_archived BOOLEAN NOT NULL DEFAULT false` | Simples | Não registra quando |
| B | `archived_at TIMESTAMPTZ NULL` | Igual ao A | Registra quando; `NULL` = ativa |

### Decisão

**Opção B**, `archived_at TIMESTAMPTZ NULL`. Mesmo custo de migração e atende
FR-012 ("registrar o momento em que foi arquivada") sem coluna extra. Segue o
padrão temporal que o schema já usa (`created_at`, `updated_at`).

### Contrato do servidor

O `PATCH /conversations/{id}` já recebe campos opcionais (`title`,
`is_favorite`) e aplica só o que veio. Arquivar entra como terceiro campo
opcional no mesmo endpoint — não cria rota nova nem muda as existentes.

O corpo continua booleano (`is_archived`) em vez de expor a data: a interface
alterna um estado, e deixar o cliente escolher o carimbo de tempo seria confiar
relógio de navegador. O servidor grava `now()` ao arquivar e `NULL` ao
desarquivar.

Listagem: `GET /conversations` ganha filtro por estado em vez de endpoint novo —
menos superfície. Por padrão devolve **apenas ativas**, preservando o
comportamento atual de quem já consome (FR-009).

### Interação com favorita

`archived_at` e `is_favorite` são ortogonais (A-003). As listas ativas filtram
`archived_at IS NULL` e continuam ordenando por favorita e depois por
atualização; a lista de arquivadas ignora a marcação. Desarquivar não precisa
restaurar nada: a conversa reaparece sozinha na lista certa porque
`is_favorite` nunca foi tocado (FR-011).

---

## R4 — Compatibilidade dos endereços antigos

### Situação

Os endereços em circulação são `/assistant` e `/assistant?c=<id>`. A barra
lateral também gera `/assistant?c=<id>` hoje (`app-sidebar.tsx`), e o
`ai-assistant.tsx` lê `searchParams.get("c")`.

### Opções

| Opção | Limite |
|---|---|
| A | Redirecionar por configuração de build | Casar query string em regra estática é possível mas verboso, e o destino muda de caminho conforme o valor da query |
| B | Manter a rota antiga como página de servidor que lê a query e redireciona | Direto, testável, e o redirecionamento some da barra de endereço (FR-017) |

### Decisão

**Opção B.** A página antiga vira um redirecionador de servidor: com `c`, manda
para `/ai/chat/{c}`; sem `c`, para `/ai/chat`. Redirecionamento de servidor não
deixa a rota antiga no histórico, o que satisfaz FR-017.

Os geradores internos de link (`app-sidebar.tsx`) passam a apontar direto para o
formato novo — o redirecionamento existe para links já circulando, não para uso
corrente.

---

## R5 — Conversa inexistente

### Situação

Hoje `loadConversation()` faz `if (!result.ok) return;` — falha silenciosa. Com
endereço direto, um identificador inválido, de outra sessão ou já excluído passa
a ser caminho de entrada normal, não caso raro.

O servidor já trata os três casos de forma indistinguível: `get_owned()` devolve
`404` tanto para inexistente quanto para "existe mas é de outra sessão". Isso já
atende FR-014 e SC-006 — nenhuma informação vaza sobre existência. Nada a mudar
no servidor.

### Decisão

O cliente passa a distinguir três estados: carregando, carregada, não
encontrada. O terceiro rende a tela de ausência com caminho para nova conversa
(FR-007). Identificador malformado não chega a virar requisição — a validação de
formato acontece antes e cai no mesmo estado.

---

## R6 — Cobertura de teste no servidor

`backend/tests/test_assistant_conversation.py` tem 14 testes e já cobre posse
por sessão, renomear, favoritar, excluir e 404. O arquivamento entra no mesmo
arquivo, seguindo o padrão existente:

- arquivar tira das ativas e coloca nas arquivadas;
- desarquivar devolve à lista correta, com a marcação de favorita preservada;
- sessão B não arquiva conversa da sessão A (espelha o teste de posse já
  existente para renomear/favoritar/excluir);
- excluir conversa arquivada continua funcionando.

Constituição exige suíte verde **sem rede e sem credencial** — estes testes são
de repositório e rota, sem chamada externa, então seguem a regra sem esforço
extra.

---

## R7 — Ordem de execução

1. **Servidor** (coluna, migração, contrato, testes) — é a base; sem
   `archived_at` a interface não tem o que exibir.
2. **Rota** (`/ai/chat` e `/ai/chat/{id}`, redirecionamento) — independente do
   item 1, mas é o P1 da spec.
3. **Interface de arquivamento** — depende de 1 e 2.

1 e 2 não se bloqueiam: podem sair em qualquer ordem ou em paralelo. A spec
prioriza a rota (US1 = P1), então ela vai primeiro na entrega, mesmo o servidor
sendo pré-requisito do arquivamento.
