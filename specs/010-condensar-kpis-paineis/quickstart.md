# Quickstart: validar densidade dos painéis

## Pré-requisitos

- Frontend rodando contra API com métricas e sprint disponíveis (para ver
  os cartões com dado real, não só estado indisponível).

## Passo 1 — Painel principal em desktop

1. Abrir `/` numa janela de 1280px de largura.
2. Comparar visualmente com o estado anterior (git stash / branch main) —
   confirmar que os 4 cartões de indicador e os 4 cartões de gráfico
   ocupam menos altura total.
3. Confirmar que todo texto (rótulo, valor, hint) continua legível.

## Passo 2 — Painel Ágil em desktop

1. Abrir `/agile` com sprint ativo.
2. Confirmar mesma densidade visual do painel principal — comparar altura
   de um `Stat` e do gráfico de barras de velocidade nas duas telas lado a
   lado.

## Passo 3 — Viewport estreito

1. Redimensionar a janela (ou DevTools responsivo) para ~380px de
   largura.
2. Confirmar: nenhum gráfico ultrapassa a borda do cartão, sem rolagem
   horizontal da página.

## Passo 4 — Estados vazio/indisponível

1. Com a API de agile fora do ar (ou sem sprint ativo), confirmar que a
   mensagem de estado vazio/indisponível continua totalmente legível
   dentro do cartão condensado.

## Passo 5 — Zoom de acessibilidade

1. Aumentar o zoom do navegador para 200%.
2. Confirmar que não há sobreposição de texto nos cartões condensados.

## Passo 6 — Regressão de build

```sh
cd frontend && npm run lint && npm run build
```
