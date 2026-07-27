# Uso de IA Generativa

Esta área documenta como IA foi usada e validada durante o projeto. Ela complementa, mas não substitui, os artefatos técnicos e as evidências sanitizadas em [`evidence/`](../../evidence/README.md).

## Índice

- [Decisões assistidas por IA](./ai-decisions.md)
- [Prompt engineering](./prompt-engineering.md)
- [Uso dos modelos](./llm-usage.md)

## Evidência mínima por atividade

Cada evidência deve conter: objetivo, data, modelo/ferramenta, prompt ou entrada sanitizada, saída/artefato, validação humana, decisão tomada e referência ao arquivo resultante. Nunca incluir dados reais de clientes, tokens ou conteúdo restrito.

## Avaliação de qualidade

Antes de automatizar classificação ou resposta RAG, manter um golden set versionado com entradas sintéticas, resultado esperado e critério de aprovação. Registrar taxa de acerto, falhas conhecidas, latência e custo quando aplicável.
