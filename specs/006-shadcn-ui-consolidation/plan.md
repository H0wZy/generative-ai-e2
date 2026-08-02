# Implementation Plan: Consolidação de UI em shadcn e correção de scroll/reveal

**Branch**: `006-shadcn-ui-consolidation` | **Date**: 2026-08-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-shadcn-ui-consolidation/spec.md`

## Summary

Três frentes, uma delas pré-requisito das outras.

A investigação (`research.md`) mostrou que os dois defeitos relatados têm causas
específicas e já reproduzidas — não são ajuste de estilo:

1. **Rolagem escapando no quadro**: 19 elementos `sr-only` são
   `position: absolute` sem nenhum ancestral posicionado. O bloco contentor
   deles é o documento, então escapam de todos os `overflow` da cadeia e esticam
   a área rolável para 1905px numa janela de 853px. Correção: remover o
   `sr-only` redundante (o `<select>` já tem `aria-label`) e tornar o contêiner
   de conteúdo do shell um bloco contentor.

2. **Salto na revelação da resposta**: `useTypewriter` começa em
   `displayedLength = 0`, então o primeiro quadro renderiza markdown vazio, o
   contêiner colapsa e o navegador *clampa* `scrollTop` para 0. Correção:
   reservar a altura final desde o primeiro quadro empilhando a cópia completa
   (invisível) e a revelada na mesma célula de grid, e remover o `scrollToEnd`
   introduzido na rodada anterior.

3. **Migração para shadcn**: bloqueada por uma descoberta que precisa vir antes
   de tudo — a camada de token shadcn está quebrada. O bloco `.dark` é CSS morto
   (o `<html>` nunca recebe a classe), então `bg-background` é branco puro e
   `border-border` é quase branco dentro de um app escuro; e entradas
   auto-referentes no `@theme inline` invalidam `bg-muted`, `bg-card` e
   `bg-accent`, que resolvem para transparente. É por isso que o "Novo chamado"
   é um retângulo branco. Sem reconciliar os tokens, todo componente migrado
   nasce branco ou invisível.

A migração em si não exige dependência nova: `@base-ui/react@1.6.0` já está
instalado e exporta `select`, `scroll-area`, `input`, `field`, `combobox`,
`tabs`, `separator`.

## Technical Context

**Language/Version**: TypeScript 5, React 19, Next.js (App Router)

**Primary Dependencies**: `@base-ui/react@1.6.0` (primitivas shadcn base-nova,
já instalado), `class-variance-authority`, `tailwind-merge`, `clsx`,
`lucide-react`, `react-markdown` + `remark-gfm`, `@shadcn/react` (só
`message-scroller`), Tailwind CSS v4 (`@theme inline`)

**Storage**: N/A — rodada exclusivamente de interface

**Testing**: `npx tsc --noEmit`, `npx eslint .`, e validação instrumentada no
navegador conforme `quickstart.md`. O projeto não tem suíte de teste de
frontend; a verificação é por medição no DOM, que é o que os critérios desta
spec exigem (altura rolável, monotonicidade de `scrollHeight`, valor computado
de token).

**Target Platform**: navegador desktop (Chromium/Firefox), tema escuro; layout
responsivo já estabelecido nas rodadas 004/005

**Project Type**: web — frontend Next.js dentro de `frontend/`

**Performance Goals**: revelação a 60fps sem refluxo; `scrollHeight`
monotonicamente não decrescente durante a animação

**Constraints**: nenhuma dependência nova (SC-008); identidade visual preservada
(FR-015/SC-007); tema do Assistente (`.v0-assistant`) intocado; arrastar e
soltar do quadro não pode regredir

**Scale/Scope**: ~7 telas, ~40 componentes em `frontend/src/components/`, 1
arquivo de token (`globals.css`, 464 linhas), 79 renomeações mecânicas de
utilitário

## Constitution Check

*GATE: avaliado antes da Phase 0 e reavaliado após a Phase 1.*

| Princípio | Aplicável? | Avaliação |
|---|---|---|
| **I — Determinismo primeiro, LLM como fallback** | não | Rodada de interface; nenhuma decisão de negócio, nenhum caminho de LLM tocado. |
| **II — Entrada externa é não confiável** | **sim** | A revelação passa a renderizar markdown do modelo durante toda a animação, não só ao final. Não amplia a superfície: `react-markdown` continua sem `rehype-raw` (HTML bruto nunca é processado) e `AssistantLink` continua validando link contra a allow-list de rotas internas. O texto revelado é o mesmo que já era renderizado — muda **quando**, não **o quê**. Conteúdo de ticket segue fora de log e evidência. ✅ |
| **III — Idempotência e rastreabilidade** | não | Nenhuma ingestão, persistência ou chamada externa. |
| **IV — Segredo nunca entra no repositório** | não | Nenhum segredo, variável de ambiente ou credencial tocada. |
| **V — Simples agora, escalável pelas costuras** | **sim** | Ver análise abaixo. ✅ |

### Detalhe do princípio V

- **"Nenhuma dependência nova onde o que já está instalado resolve"**: atendido —
  `@base-ui/react` já cobre todos os controles a migrar. SC-008 fecha isso.
- **"Código superado sai da navegação antes de sair do disco"**: a rodada
  *remove* código morto em vez de acumular — o bloco `.dark` (~32 linhas que
  nada aplica), as entradas auto-referentes do `@theme inline`, o `sr-only`
  redundante e o `scrollToEnd` da rodada anterior.
- **"Nenhuma abstração com uma única implementação"**: nenhum wrapper novo é
  introduzido; os componentes migrados são as primitivas da biblioteca, com o
  estilo do projeto.
- **"Mudanças pequenas, testáveis e reversíveis"**: a fase de token é a única
  com risco amplo, por isso é isolada, vem primeiro e tem verificação própria
  (V3 do `quickstart.md`) antes de qualquer migração de componente.
- **"Limitação conhecida é documentada como decisão"**: o teto da abordagem de
  revelação (renderizar o markdown duas vezes durante a animação; incompatível
  com streaming real futuro) está registrado em `research.md` §R2, não
  descoberto depois.

**Resultado do gate**: aprovado, sem violação. `Complexity Tracking` fica vazio.

### Reavaliação pós-Phase 1

Nenhum artefato da Phase 1 introduziu projeto novo, camada nova ou abstração
nova. `data-model.md` **reduz** vocabulário — de duas camadas de token
conflitantes para uma fonte de verdade com aliases derivados — em vez de
aumentar. Gate segue aprovado.

## Project Structure

### Documentation (this feature)

```text
specs/006-shadcn-ui-consolidation/
├── plan.md              # Este arquivo
├── spec.md              # O quê e por quê
├── research.md          # Phase 0 — causas-raiz medidas e decisões
├── data-model.md        # Phase 1 — vocabulário de tokens e inventário
├── quickstart.md        # Phase 1 — roteiro de validação
├── contracts/
│   └── ui-shadcn.md     # Phase 1 — contrato de interface verificável
├── checklists/
│   └── requirements.md  # Qualidade da spec (16/16)
└── tasks.md             # Phase 2 — criado por /speckit-tasks
```

### Source Code (repository root)

Apenas `frontend/` é tocado. Nada em `backend/`, `rag/` ou `docs/`.

```text
frontend/src/
├── app/
│   ├── globals.css                     # FASE 1 — reconciliação de tokens
│   ├── (shell)/
│   │   ├── page.tsx                    # painel — verificação visual
│   │   ├── itsm/page.tsx               # FASE 4 — "Novo chamado" vira cartão
│   │   └── agile/
│   │       ├── kanban/page.tsx         # verificação de contenção
│   │       └── scrum/page.tsx          # mesma verificação
│   └── assistant/page.tsx
├── components/
│   ├── ui/                             # FASE 4 — Card, Table, Skeleton,
│   │   │                               #   Tag→Badge, Select e Input novos
│   │   ├── button.tsx                  # já shadcn — revalidar após tokens
│   │   ├── context-menu.tsx            # já shadcn — revalidar
│   │   └── message-scroller.tsx        # já shadcn — revalidar
│   ├── agile/board.tsx                 # FASE 2 — remover sr-only; FASE 4 — Select
│   ├── itsm/ticket-filters.tsx         # FASE 4 — Select + Input
│   ├── itsm/ticket-form.tsx            # FASE 4 — Select + Input
│   ├── assistant/
│   │   ├── use-typewriter.ts           # FASE 3
│   │   ├── typewriter-message.tsx      # FASE 3 — reserva de altura
│   │   ├── conversation-view.tsx       # FASE 3 — remover scrollToEnd
│   │   └── chat-composer.tsx           # FASE 4 — Input/Button
│   └── shell/
│       ├── shell-chrome.tsx            # FASE 2 — bloco contentor no <main>
│       ├── app-sidebar.tsx             # FASE 4 — Button
│       └── topbar.tsx                  # FASE 4 — Button
└── lib/
```

**Structure Decision**: mantida a estrutura existente do `frontend/` — rodada de
consolidação, não de reorganização. Componentes de biblioteca ficam em
`components/ui/`, componentes de domínio nas pastas por área (`agile/`, `itsm/`,
`assistant/`, `shell/`), exatamente como hoje. Nenhum diretório novo.

## Fases de execução

A ordem é imposta por dependência real, não por preferência (`research.md` §R5).

### Fase 1 — Reconciliar a camada de tokens *(pré-requisito de tudo)*

Escopo: `globals.css` e os três componentes shadcn já versionados.

1. Levar os valores escuros para `:root` e **remover o bloco `.dark` morto**.
2. Remover as entradas auto-referentes do `@theme inline` que invalidam
   `bg-muted`, `bg-card` e `bg-accent`.
3. Apontar os nomes shadcn para a paleta do projeto conforme a tabela de
   `data-model.md` §2.1.
4. Renomear `text-muted` → `text-muted-foreground` (79 ocorrências, mecânico,
   **sem delta visual**: `oklch(0.708)` antes e depois), liberando `muted` para
   significar superfície como todo componente shadcn espera.
5. Ajustar o `@layer base` para não aplicar `border-border`/`bg-background`
   claros como padrão global.

**Porta de saída**: V3 do `quickstart.md` — nenhum utilitário transparente,
`background` escuro, brass 500/800 inalterados, `.dark` ausente, zero
`text-muted` remanescente.

**Risco**: única fase de alcance global. Por isso vem isolada e antes, com
comparação visual de todas as telas (SC-007) antes de seguir.

### Fase 2 — Contenção de rolagem

1. Remover o `<span className="sr-only">` de `board.tsx` (redundante com o
   `aria-label` do `<select>`).
2. Tornar o `<main>` do shell um bloco contentor, para que absolutos futuros
   não escapem para o documento.

**Porta de saída**: V1 — `scrollHeight - clientHeight === 0` no Kanban e no
Scrum, lista de absolutos escapando vazia, arrastar e soltar intacto.

### Fase 3 — Revelação sem solavanco

1. Reservar a altura final em `typewriter-message.tsx` (pilha em grid: cópia
   completa invisível + cópia revelada, mesma célula).
2. Remover o `scrollToEnd` de `conversation-view.tsx`.
3. Suprimir a revelação sob `prefers-reduced-motion`.

**Porta de saída**: V2 — `encolheu === false` e `voltouAoTopo === false` na
amostragem quadro a quadro; markdown formatado em todos os quadros.

### Fase 4 — Migração de componentes

Em fatias verificáveis, cada uma independentemente testável:

1. `ui/` primeiro: Card, Table, Skeleton, Tag→Badge, e os novos Select e Input.
2. Depois os consumidores, por área: `itsm/` (filtros, formulário) → `agile/`
   (seletor de coluna do cartão) → `assistant/` (composer) → `shell/`
   (sidebar, topbar).
3. Por último, "Novo chamado" vira cartão em `itsm/page.tsx`.

**Não migrar**: a rolagem das colunas do quadro permanece nativa — trocar por
rolagem gerida em script arrisca regredir o arrastar e soltar sem ganho visual,
já que a aparência da barra vem da regra global (`research.md` §R4).

**Porta de saída**: V4, V5 e V6.

## Complexity Tracking

Sem violação de constituição a justificar. Seção intencionalmente vazia.
