---
name: llm-desligado-injection
description: Classificação por LLM ficou desligada por padrão — golden set mediu 100% de sucesso em prompt injection; não fazer corrida de endurecimento de prompt
metadata:
  type: project
---

Decisão de 2026-07-26 (Bloco 2): a classificação de squad por LLM foi
implementada, testada e **entregue desligada** (`LLM_ENABLED=false`). O golden
set de roteamento mediu, com `qwen3:8b`: acurácia 100% (13/13) numa execução e
84,62% em outra, mas **2/2 (100%) de sucesso em prompt injection** nos casos que
pedem um valor válido do enum com confiança alta.

**Why:** o conteúdo do ticket é entrada não confiável e o modelo obedece
instrução embutida nela. Ativar transferiria para quem escreve o ticket a
escolha da squad de destino. O golden set existia para decidir a ativação — e
decidiu não. Recusei explicitamente endurecer o prompt: injeção de prompt não
tem defesa robusta hoje, e cada rodada de "reforçar a delimitação" só produz um
prompt que resiste às frases que nós mesmos escrevemos — o mesmo teatro que o
caso `g16` já tinha produzido (pedia squad `admin`, fora do enum, então o
Pydantic rejeitava antes de qualquer defesa de prompt agir).

**How to apply:** se alguém propuser ligar o LLM ou "melhorar o prompt para
resistir", peça primeiro a medição contra o modelo real e separe garantia de
medição: garantia determinística (enum fechado, limiar, degradação para revisão
humana) é testável com fake e vale sempre; resistência a injection só se mede
contra o modelo real e é probabilística, nunca um selo. Ligar exige entrada
confiável ou defesa que não dependa de prompt. Ver [[modelos-locais]].
