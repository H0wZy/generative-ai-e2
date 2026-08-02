# Quickstart: validar a localização PT-BR do frontend

## Pré-requisitos

- Node.js instalado (versão compatível com Next.js 16 — ver `frontend/package.json`).
- Dependências instaladas: `cd frontend && npm install` (se ainda não instalado).
- Backend não precisa estar no ar para os passos estáticos (build/lint); para
  checar as telas com dado real, siga o `README.md` da raiz do repositório
  para subir o stack via `docker-compose`.

## 1. Validação estática (obrigatória, cobre SC-002 e SC-004)

```bash
cd frontend
npx tsc --noEmit      # esperado: "TypeScript: No errors found"
npx eslint src         # esperado: sem saída (sem findings)
npm run build           # esperado: "✓ Compiled successfully" + todas as rotas listadas
```

## 2. Varredura de texto residual em inglês (cobre SC-002 / FR-005)

```bash
cd frontend/src
grep -rn '"Home"\|"Dashboard"\|"Assets"\|"Agile"\|Scroll to' . \
  --include="*.tsx" --include="*.ts" | grep -v node_modules
```

**Esperado**: nenhuma ocorrência. Se aparecer algo, é uma regressão ou uma
string nova introduzida em inglês fora do escopo desta feature — investigar
antes de considerar a auditoria completa.

## 3. Checagem visual (cobre SC-001, SC-003, SC-005)

Com o stack no ar (`docker-compose up` conforme README da raiz) e o
frontend em `npm run dev`:

1. Abrir `/` — sidebar mostra "Início", "Painel", "Ativos" (ITSM) e o logo
   do shell mostra "ITSM+Ágil".
2. Abrir `/itsm` e `/agile` — seletor de workspace mostra "ITSM" / "Ágil";
   topbar mostra o mesmo rótulo depois do "·".
3. Confirmar que o item de menu ativo continua com o ícone correto ao lado
   (não o ícone de fallback `Home`) em cada rota — valida a correção do
   acoplamento label→ícone (research.md D4).
4. Abrir `/ai/chat/[id]` com uma conversa longa o bastante para os botões
   de rolagem aparecerem; inspecionar via DevTools (Elements → Accessibility)
   ou leitor de tela que o nome acessível é "Ir para o fim da conversa" /
   "Ir para o início da conversa".
5. Na home (`/`), card "Volume por status" — legenda do donut mostra
   "Retry agendado", não "Retry".
6. `/em-construcao/assets` — título do card é "Ativos".
7. Acessar uma rota inexistente — página 404 mostra "Voltar para o início".

## 4. Validação da correção de concorrência no board (cobre research.md D5)

Em `/agile/kanban`, com throttling de rede ligado no DevTools (Slow 3G):

1. Iniciar o drag de um card ou trocar o `Select` de coluna dele.
2. Enquanto a requisição está em voo, tentar arrastar/trocar outro card.

**Esperado**: os demais cards ficam com `draggable=false` e o `Select`
desabilitado até a primeira transição resolver (sucesso ou erro) — não é
possível iniciar uma segunda transição simultânea. Depois que a primeira
resolve, os controles voltam a responder normalmente.

## Critério de pronto

Todos os passos acima passam sem intervenção manual em código — este
quickstart não tem passo de "corrigir X e repetir"; qualquer falha aqui é
regressão a ser investigada, não parte esperada do fluxo.
