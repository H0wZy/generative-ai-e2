# Phase 0 Research: Localização PT-BR completa do frontend

Nenhum `[NEEDS CLARIFICATION]` ficou aberto na spec (a validação de qualidade
passou na primeira iteração — ver `checklists/requirements.md`). As decisões
abaixo registram as escolhas técnicas feitas para não precisarem ser
redescobertas numa próxima rodada de i18n.

## D1 — Nenhuma biblioteca de internacionalização

**Decision**: manter texto em português direto nos componentes (string
literal ou constante local), sem `next-intl`, `react-i18next` ou similar.

**Rationale**: o produto tem um único idioma-alvo hoje (PT-BR); as poucas
strings em inglês eram resíduo de componentes portados de exemplos
shadcn/v0 (rodadas 006/007), não uma necessidade de multi-idioma. Introduzir
uma camada de i18n para um produto de um idioma só é infraestrutura que o
MVP não usa — viola o Principle V da constituição (Simples agora, escalável
pelas costuras).

**Alternatives considered**:
- `next-intl`: rejeitado — exigiria reestruturar rotas (`[locale]` segment
  no App Router), tocando toda a árvore de páginas para resolver 8 strings
  soltas.
- Arquivo único de dicionário (`strings.pt-BR.ts`) sem lib de i18n: rejeitado
  — indireção sem ganho enquanto só existe um idioma; comentário do próprio
  projeto author (specs anteriores) já usa texto direto em todos os outros
  ~200 pontos de UI já traduzidos.

## D2 — Método de auditoria: grep + revisão manual de falso positivo

**Decision**: varredura por `grep`/regex nos diretórios `frontend/src/app` e
`frontend/src/components`, filtrando identificadores técnicos (classes
Tailwind, `data-slot`, chaves de enum, nomes de import) antes de classificar
cada ocorrência como texto de UI ou não.

**Rationale**: não há ferramenta de lint para "string em inglês" configurada
no projeto (nem faria sentido — muita string técnica legítima é inglês:
`className`, `variant="outline"` etc.). Grep + revisão manual é o método já
usado no restante do projeto (a maior parte da UI já está em PT-BR sem
tooling dedicado) e é suficiente para o volume de ~200 arquivos do frontend.

**Alternatives considered**: um script de CI que reprova build ao achar
literal `/[A-Z][a-z]+/` em JSX — rejeitado, alta taxa de falso positivo
(nomes próprios, siglas, classes) tornaria o gate inútil sem curadoria
significativa; fora de escopo para uma correção pontual.

## D3 — Sigla "ITSM" e nomes de rota permanecem em inglês

**Decision**: "ITSM" não é traduzido (não existe tradução curta natural em
uso no domínio); URLs (`/itsm`, `/agile`, `/ai/chat`) não mudam.

**Rationale**: "ITSM" já é o nome próprio usado nos handoffs
(`docs/handoffs/freshservice-jira.md`) e no restante da documentação —
traduzir criaria inconsistência com material já publicado. Rotas são
identificador técnico, não texto lido pelo usuário como frase; renomeá-las
quebraria bookmark/link direto sem nenhum ganho de legibilidade percebido.

## D4 — Ícone de navegação passa a ser campo do item, não lookup por label

**Decision** (achado durante a implementação, não estava no spec original,
registrado aqui por afetar o mesmo arquivo `nav.ts`): `NavItem` ganhou o
campo `icon`, preenchido por item em `NAV`. O mapeamento antigo
`NAV_ICONS: Record<string, Icon>`, indexado pelo texto do `label`, foi
removido.

**Rationale**: indexar por `label` acoplava o texto exibido (que esta
própria feature estava mudando) à resolução do ícone — traduzir um label
sem atualizar a chave correspondente derrubava silenciosamente para o
ícone de fallback (`Home`), sem erro em tempo de build. Campo direto no
item elimina a classe inteira de bug (não há chave para desincronizar).

**Alternatives considered**: manter `NAV_ICONS` e só atualizar as chaves
junto com os labels (o que o spec original previa como FR-006) — funciona,
mas deixa a armadilha para a próxima tradução ou renomeação. Preferida a
correção estrutural por já estar tocando o arquivo e o custo adicional ser
mínimo (uma coluna a mais em cada entrada do array).

## D5 — Race condition em `board.tsx`: serialização via flag `moving`

**Decision** (achado de code review, fora do escopo original de i18n mas
corrigido na mesma sessão por estar em área correlata): uma flag booleana
`moving` no componente `Board` bloqueia início de nova transição (drag ou
select) enquanto uma já está em voo; UI desabilita drag e select durante
esse tempo.

**Rationale**: o bug real era um snapshot obsoleto — a primeira transição
capturava `columns` antes de começar, e se falhasse, revertia para esse
snapshot mesmo depois de uma segunda transição (em outro card) já ter
mudado o estado. Serializar é a correção mínima: qualquer solução de
"merge" de estados otimistas concorrentes seria desproporcional para uma
interação de drag-and-drop de um único usuário por sessão.

**Alternatives considered**: reconciliar por card em vez de por board
inteiro (permitir moves concorrentes de cards diferentes) — rejeitado por
complexidade; o ganho (permitir dois moves simultâneos) não compensa o
código extra para um board de uso single-player por tela.
