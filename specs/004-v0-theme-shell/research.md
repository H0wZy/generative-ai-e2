# Research: Unificação visual v0 — fundação de tokens + shell

## R1 — Como levar a paleta de `.v0-assistant` para `:root` sem duplicar arquitetura

**Decision**: Manter os *nomes* de token já existentes em `:root` (`--color-bg`, `--color-surface`, `--color-text`, `--color-muted`, `--color-primary`, `--color-elevated`, `--color-divider`, `--color-focus`, ...) e trocar apenas seus *valores* pelos mesmos números já usados em `.v0-assistant` (oklch). Os três tokens que não têm equivalente hoje (superfície tipo "card/popover" distinta de "elevated", "ring" de foco em contexto de menu/input, cor destrutiva) ganham token novo na mesma convenção.

**Rationale**: Todo componente em `frontend/src/components/ui/*` e `frontend/src/components/shell/*` já consome esses nomes via classe Tailwind gerada pelo `@theme inline` (`bg-surface`, `text-muted`, `border-divider`, etc). Trocar o valor por trás do nome é uma mudança de ~1 arquivo com zero diff nos consumidores — exatamente o que a spec pede (FR-004, "sem exigir alteração individual de cada tela").

**Alternatives considered**:
- *Referenciar `--v0-*` diretamente do `:root`* (`--color-bg: var(--v0-background)`), evitando duplicar o número. Rejeitado: `--v0-*` só existe dentro do seletor `.v0-assistant` (comentário explícito em `globals.css:159-165` — escopo é proposital, para não colidir nome-a-nome com o tema antigo). Uma variável CSS definida num seletor de classe não é visível fora dele; só duplicar o valor literal funciona sem reestruturar o bloco do Assistente.
- *Reestruturar `.v0-assistant` para herdar de `:root`* — trocaria a arquitetura já testada e em produção da tela do Assistente por causa de uma mudança que é sobre o *resto* do app. Maior risco, fora do pedido desta rodada.
- *Namespace novo (`--shell-*` ou similar) só para o shell* — rejeitado pelo Princípio V (nenhuma abstração nova onde o nome existente já resolve); criaria dois sistemas de token para o mesmo produto.

## R2 — Contraste real dos pares candidatos (medido, não estimado)

Conversão OKLCH → sRGB linear → luminância relativa → razão WCAG, calculada para cada par candidato (script Python, fórmula padrão WCAG 2.x):

| Par | Cores resultantes | Razão | Atende? |
|---|---|---|---|
| `foreground` / `bg` | `#fafafa` sobre `#0a0a0a` | 18.96:1 | AA corpo (≥4.5) ✅ |
| `muted-foreground` / `bg` | `#a1a1a1` sobre `#0a0a0a` | 7.63:1 | AA corpo ✅ |
| `foreground` / `card` | `#fafafa` sobre `#171717` | 17.16:1 | AA corpo ✅ |
| `foreground` / `popover` | `#fafafa` sobre `#0d0d0d` | 18.59:1 | AA corpo ✅ |
| `primary-foreground` / `primary` (botão) | `#171717` sobre `#e5e5e5` | 14.22:1 | AA corpo ✅ |
| `foreground` / `secondary` (elevated/hover) | `#fafafa` sobre `#262626` | 14.48:1 | AA corpo ✅ |
| `destructive` (texto) / `bg` | `#ff6467` sobre `#0a0a0a` | 6.84:1 | AA corpo ✅ |
| `foreground` / `destructive` sólido (texto branco em botão vermelho cheio) | `#fafafa` sobre `#ff6467` | 2.77:1 | ❌ reprova até o piso de 3:1 |

**Decision**: Adotar todos os pares acima como estão, **exceto** o último — texto claro sobre fundo destrutivo sólido não é um padrão a introduzir nesta rodada. O uso de "destructive" no produto (visto hoje em `ContextMenuItem variant="destructive"` do Assistente) já usa o padrão seguro: texto na cor destrutiva sobre fundo destrutivo **translúcido** (`bg-v0-destructive/15`), não sólido — par que passa longe do piso AA porque o fundo real é a mistura com a superfície escura por trás, não o vermelho puro. A regra para esta rodada e as seguintes: **nunca combinar texto claro sólido sobre fundo destrutivo 100% opaco**; usar sempre texto na cor destrutiva sobre fundo destrutivo tinturado (baixa opacidade) ou texto claro sobre um destrutivo escurecido — a decidir com medição real se/quando um botão destrutivo sólido for necessário (não é o caso desta rodada, que só cobre shell).

**Rationale**: Corresponde ao FR-005 (manter nível de contraste AA em toda combinação) e ao precedente do projeto (`specs/003-.../contracts/ui-nav.md`: "medido, não estimado").

## R3 — Nomes de token novos (cobrir "card", "popover", "ring", "input", "destructive")

**Decision**:
- Papel "elevated surface" (card/popover do v0) → reaproveitar `--color-elevated` já existente (hoje usado para hover de item/trilho/esqueleto) em vez de criar `--color-card` **e** `--color-popover` como tokens distintos. O v0 diferencia os dois (`card` = oklch 0.205, `popover` = oklch 0.16) por nuance de profundidade, mas o ink/brass já resolve isso com um único degrau de superfície elevada — introduzir dois tokens nesta rodada seria complexidade sem consumidor que precise da distinção (nenhum componente de `ui/*` hoje diferencia card de popover).
- Papel "ring" (contorno de foco de elemento interativo tipo menu/input) → reaproveitar `--color-focus` já existente (já usado em todo `focus-visible:outline-focus` do projeto) em vez de um token `--color-ring` novo — mesmo papel semântico, mesmo consumidor (indicador de foco de teclado).
- Papel "input border" → reaproveitar `--color-divider` já existente (já é o valor usado hoje para toda borda/traço do produto: `border-divider` em `sidebar.tsx`, `topbar.tsx`).
- Papel "destructive" → **token novo**, `--color-destructive`, porque não existe equivalente semântico hoje (`--color-status-critical` é documentado como uso exclusivo de trilho de status de 3px, nunca par texto/fundo — reaproveitá-lo para texto/botão destrutivo violaria essa regra já registrada no próprio arquivo).

**Alternatives considered**: Criar um token 1:1 para cada nome do v0 (`card`, `popover`, `ring`, `input` como quatro tokens novos). Rejeitado pelo Princípio V — nenhum consumidor real precisa da distinção fina agora; three-token reuse cobre o mesmo efeito visual com zero token extra.

## R4 — Remoção do dark/light toggle

**Decision**: Remover por completo `frontend/src/components/shell/theme-toggle.tsx`, sua importação/uso em `topbar.tsx`, o bloco `:root[data-theme="light"]` em `globals.css`, e o script anti-FOUC em `layout.tsx` (que só existe para aplicar o `data-theme` salvo antes da pintura).

**Rationale**: Spec (US2, FR-002/FR-003) exige dark-only sem controle de alternância. Manter o arquivo/código morto violaria o próprio Princípio V ("código superado sai da navegação antes de sair do disco" — aqui sai dos dois, já que não há mais nenhum outro consumidor do conceito de tema claro).

**Alternatives considered**: Manter o componente desabilitado/oculto "para o futuro". Rejeitado — YAGNI explícito na spec (Assumptions: "não há expectativa de reintroduzir tema claro").
