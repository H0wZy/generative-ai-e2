# Contrato de UI — consolidação shadcn (round 006)

**Feature**: `specs/006-shadcn-ui-consolidation`
**Date**: 2026-08-01

Este projeto não expõe API pública nesta rodada. A superfície de contrato é a
**interface** — o que a pessoa vê e opera. O que segue é verificável por
inspeção da tela, medição no navegador e navegação por teclado.

---

## C1 — Contenção de rolagem

| # | Contrato | Verificação |
|---|---|---|
| C1.1 | A área rolável do documento é igual à área visível da janela em toda tela do shell | `document.documentElement.scrollHeight === document.documentElement.clientHeight` |
| C1.2 | Nenhum elemento destinado só a leitor de tela aumenta a área rolável do documento | inspecionar posicionados absolutos cujo bloco contentor seja o documento |
| C1.3 | Em tela de quadro, a rolagem vertical pertence à coluna; a horizontal, à faixa de colunas | rolar sobre uma coluna move só aquela coluna |
| C1.4 | Não existe terceira região rolável englobando as duas | contar regiões com `overflow` rolável na cadeia |
| C1.5 | Barra lateral, cabeçalho e abas permanecem visíveis em qualquer posição de rolagem | inspeção visual em janela baixa |
| C1.6 | Toda barra de rolagem tem a mesma aparência discreta | inspeção visual entre regiões |

**Estado de referência antes da correção** (para comprovar a diferença):
`scrollHeight = 1905`, `clientHeight = 853` em `/agile/kanban`.

---

## C2 — Revelação da resposta do assistente

| # | Contrato | Verificação |
|---|---|---|
| C2.1 | A resposta é revelada progressivamente, com sensação de digitação | observação |
| C2.2 | O conteúdo visível está formatado em sua apresentação final durante toda a revelação | não deve existir `###`, `**` ou `\|` literais em nenhum quadro |
| C2.3 | A altura do conteúdo é monotonicamente não decrescente | amostrar `scrollHeight` quadro a quadro; nenhuma queda |
| C2.4 | A posição de leitura nunca retrocede por iniciativa do sistema | amostrar `scrollTop`; nenhum retorno a 0 |
| C2.5 | Rolagem manual durante a revelação é respeitada | rolar para cima e confirmar que não é puxado de volta |
| C2.6 | Mensagem carregada do histórico aparece completa, sem animação | abrir conversa antiga |
| C2.7 | Com `prefers-reduced-motion: reduce`, a revelação é suprimida | ativar a preferência e reenviar |

**Estado de referência antes da correção**: `scrollTop` cai de `3460` para `0`
e `scrollHeight` de `4129` para `3821` no primeiro quadro da revelação.

---

## C3 — Uniformidade dos controles

| # | Contrato | Verificação |
|---|---|---|
| C3.1 | Campo de seleção abre lista no tema do produto, não no widget nativo do sistema | abrir cada select do produto |
| C3.2 | A lista de opções é navegável por teclado com a opção em foco visível | `Tab`, setas, `Enter`, `Esc` |
| C3.3 | Botões de mesma hierarquia têm altura, raio, tipografia e estados idênticos entre telas | comparação lado a lado |
| C3.4 | Todo controle interativo tem anel de foco visível | percorrer com `Tab` |
| C3.5 | A ordem de tabulação segue a ordem visual | percorrer com `Tab` |
| C3.6 | Estados repouso/hover/foco/pressionado/desabilitado existem e se distinguem | percorrer estados |
| C3.7 | Mover cartão entre colunas continua possível só com teclado | operar o seletor de coluna sem mouse |
| C3.8 | Nenhum utilitário de cor resolve para `transparent` sem intenção | medir os utilitários listados em `data-model.md` §1 |
| C3.9 | Paleta, espaçamento e densidade inalterados frente ao estado anterior | comparação visual antes/depois |
| C3.10 | Nenhuma dependência nova no `package.json` | `git diff` do manifesto |

---

## C4 — Entrada de novo chamado

| # | Contrato | Verificação |
|---|---|---|
| C4.1 | Apresentada como superfície de cartão, sem preenchimento sólido de alto contraste | inspeção visual |
| C4.2 | Continua sendo link real, com destino no atributo de navegação | inspecionar o elemento |
| C4.3 | Acionável por clique e por teclado, leva à criação de chamado | operar dos dois modos |
| C4.4 | Recebe foco visível e é anunciada como link | percorrer com `Tab` |
| C4.5 | Deixa de ser o elemento de maior contraste da tela | inspeção visual |

---

## C5 — Não regressão

| # | Contrato | Verificação |
|---|---|---|
| C5.1 | Verificação de tipos sem erro novo | `npx tsc --noEmit` |
| C5.2 | Linter sem erro novo (o apontamento pré-existente em `useActiveWorkspace` permanece conhecido e fora de escopo) | `npx eslint .` |
| C5.3 | Arrastar e soltar do quadro continua funcionando | mover cartão com o mouse |
| C5.4 | Tema do Assistente (`.v0-assistant`) inalterado | comparação visual da tela do Assistente |
| C5.5 | Contrastes de `Tag` e da rampa brass inalterados | medir os pares de cor |
