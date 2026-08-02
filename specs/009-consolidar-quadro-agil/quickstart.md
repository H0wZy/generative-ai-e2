# Quickstart: validar Quadro único e drag-and-drop

## Pré-requisitos

- Frontend rodando (`npm run dev` em `frontend/`) contra a API com um
  sprint ativo e board com issues em pelo menos 2 colunas.

## Passo 1 — Navegação consolidada

1. Abrir o workspace Ágil.
2. Confirmar: a navegação/abas mostram um único item "Quadro" (não
   "Quadro Scrum" e "Quadro Kanban" separados).
3. Acessar diretamente `/agile/scrum` e `/agile/kanban` (URLs antigas) —
   ambas devem redirecionar para `/agile/quadro` com o escopo
   correspondente.

## Passo 2 — Alternância de escopo sem reload de página inteira

1. Na tela "Quadro", alternar entre "sprint atual" e "board completo".
2. Confirmar que a URL reflete `?escopo=` e que a navegação não passa por
   uma tela de carregamento cheia (client-side).

## Passo 3 — Drag-and-drop isolado

1. Com pelo menos duas colunas com cards, iniciar o arrasto de um card
   (mouse down + mover).
2. **Esperado**: só o card arrastado acompanha o cursor; barra lateral,
   cabeçalho e outros cards permanecem parados.
3. Soltar sobre uma coluna válida — card se move, layout permanece
   estável.
4. Repetir soltando fora de qualquer coluna — card volta para a origem.
5. Repetir em viewport estreito (redimensionar janela para < 480px de
   largura, ou usar DevTools em modo responsivo) — mesmo resultado.

## Passo 4 — Indicador de destino

1. Iniciar arrasto e passar o cursor sobre uma coluna candidata.
2. **Esperado**: a coluna sob o cursor mostra indicador visual de "soltar
   aqui", distinto do aviso de limite de WIP estourado (testar também numa
   coluna com WIP estourado, se houver dado pra isso).

## Passo 5 — Caminho por teclado preservado

1. Usando apenas teclado, focar o seletor "Mover [card] para outra
   coluna" de um card e trocar a coluna.
2. **Esperado**: card se move exatamente como antes — nenhuma regressão.

## Passo 6 — Regressão de build

```sh
cd frontend && npm run lint && npm run build
```
