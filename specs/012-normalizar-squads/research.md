# Research: Normalização de squads exibidas

## Decisão 1 — Onde corrigir o dado legado

**Decision**: Backfill via migration Alembic (`UPDATE workflow_executions
SET squad_id = <canônico> WHERE squad_id IN (<legados>)`), não uma tradução
só na camada de exibição.

**Rationale**: a constituição do projeto declara PostgreSQL como única
fonte de verdade operacional. Um mapeamento só no frontend ou só na
serialização deixaria o dado incorreto no banco, e qualquer outro consumidor
futuro (relatório, filtro direto em SQL, export) voltaria a ver o valor
legado. Corrigir na fonte resolve para todos os consumidores de uma vez.

**Alternatives considered**:
- Tradução só na exibição (frontend ou serializer, sem tocar o banco):
  mais rápido, mas deixa o dado errado persistente — rejeitado por
  divergir de "PostgreSQL é a única fonte de verdade".
- Reseed completo do banco de demo: mais disruptivo, apaga histórico de
  execuções que pode ser útil para debug/demonstração; desnecessário
  quando um UPDATE cirúrgico resolve.

## Decisão 2 — Formato de exibição ("SquadN" vs "SQUAD-0N")

**Decision**: manter `SQUAD-01`..`SQUAD-08` como valor canônico interno e
de contrato de API (usado em `domain/squads.py`, roteamento, filtro por
querystring `?squad=SQUAD-04`) e formatar para `SquadN` (sem zero à
esquerda, sem hífen) só no frontend, no momento de exibir — nunca no valor
que volta pro backend num filtro.

**Rationale**: o pedido do usuário foi explícito ("Squad1-Squad8"), mas é
um pedido de rótulo visível, não de identificador. Trocar o valor
canônico exigiria migrar roteamento e integrações externas (rótulo no
Jira) por ganho cosmético — desnecessário. Formatar no backend (response
da API) quebraria o filtro: a tela hoje monta as opções do filtro a partir
do próprio `squad_id` devolvido na listagem e reenvia esse valor como
querystring para o backend comparar contra a coluna no banco; se a API
devolvesse já formatado (`Squad4`), o filtro enviaria `Squad4` e o
`WHERE squad_id = 'Squad4'` não bateria com `SQUAD-04` no banco. Formatar
só no frontend, mantendo `value` canônico e `label` formatado (mesmo
padrão de `PRIORITY_OPTIONS`), evita esse descasamento.

**Alternatives considered**:
- Renomear o enum canônico inteiro para `Squad1`..`Squad8`: mais invasivo,
  toca roteamento, labels no Jira e todo teste que hoje assume
  `SQUAD-0N` — rejeitado por violar Princípio V (simplicidade,
  mudança mínima reversível).
- Formatar no backend, na serialização da API: mais próximo de "uma fonte
  de verdade" à primeira vista, mas quebra o round-trip do filtro de
  squad (explicado acima) a menos que o backend também aceitasse o
  formato `SquadN` como entrada de filtro e traduzisse de volta — mais
  código para o mesmo resultado. Rejeitado.

## Decisão 3 — Squad legada sem correspondência

**Decision**: qualquer valor de squad fora do conjunto canônico e fora da
tabela de legado conhecida (`platform`, `identity`, `finance`, `Squad4`)
é tratado como "sem squad" (mesmo estado neutro "—" já usado para
`squad_id IS NULL`), nunca exibido cru.

**Rationale**: evita reintroduzir o mesmo problema para uma squad legada
não mapeada ainda não vista — a spec explicitamente proíbe (FR-005)
mostrar valor legado cru.

**Alternatives considered**: exibir o valor cru como fallback — rejeitado,
é exatamente o comportamento que está sendo corrigido.

## Decisão 4 — Escopo de teste de frontend

**Decision**: sem suíte automatizada de frontend no projeto hoje
(`frontend/package.json` só tem `lint`/`build`); validação desta feature no
frontend é lint + build + verificação manual dos cenários da spec, igual ao
padrão já usado nas specs 005-008.

**Rationale**: manter consistência com o resto do projeto — não introduzir
um framework de teste novo (Vitest/Playwright) só para esta mudança, que é
puramente de leitura de um campo já formatado pela API.

**Alternatives considered**: adicionar teste de componente para
`ticket-table.tsx` — fora de escopo, nenhuma outra spec do frontend fez
isso até aqui.
