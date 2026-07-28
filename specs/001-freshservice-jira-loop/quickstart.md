# Quickstart — roteiro de validação

Como provar que cada fatia funciona. Cada bloco é executável e diz o que
esperar. Validação é execução real, não leitura de código — regra do
`qa-dev` no `AGENTS.md`.

## Pré-requisitos

```bash
# PostgreSQL 16 rodando (Docker ou local — ver README)
make up            # ou: make db-init-local
make migrate
make migrate-test
```

Sem credencial e sem rede, tudo abaixo funciona exceto os blocos marcados
**[sandbox]**.

---

## Baseline — o que já está verde hoje

Rode antes de escrever qualquer código. Se algo aqui falhar, o problema é
anterior a esta feature.

```bash
make test
```

Esperado: suíte verde, sem Ollama, sem credencial, sem rede.

---

## F1 — Taxonomia real de squad

```bash
make test
```

Esperado, além do baseline:

- Chamado com `squad: "SQUAD-04"` → `squad_id="SQUAD-04"`, `confidence=1.0`,
  `rule_version="routing-rules/v2"`, sem chamada ao LLM.
- Chamado com `squad` vazio e `LLM_ENABLED=false` → `needs_human_review=True`.
- Chamado com `squad: "SquadInexistente"` → fora do enum → revisão humana.
- Nenhum teste referencia `identity`, `finance` ou `platform`.

Fim a fim com dublê de Jira:

```bash
make ingest-demo     # fixture agora traz o campo squad
make worker-once
```

Esperado: `status=completed`, e a issue criada com os três rótulos —
`freshservice-<id>`, `trace-<uuid>`, `squad-<squad>`.

Golden set reescrito (exige Ollama, fora de `make test`):

```bash
make routing-eval
```

Esperado: imprime acurácia, taxa de abstenção e a lista de erros sobre o enum
de 8 squads genéricas. O número é o que decide ativar ou não o LLM — se ficar
abaixo de 80%, `LLM_ENABLED` continua `false` e isso é resultado, não
fracasso.

---

## F2 — Sandbox vivo **[sandbox, bloqueado]**

A API key do Freshservice nunca foi liberada pelo admin do tenant do cliente,
e replicar o tenant real é fora de escopo (ver D2 em `spec.md`). Este bloco
fica documentado para o dia em que o acesso existir; até lá, `FreshserviceClient`
pode ser exercitado contra um mock HTTP que fale o mesmo formato
(`GET /api/v2/tickets`), apontando `FRESHSERVICE_DOMAIN` para ele.

```bash
cp backend/.env.example backend/.env
# preencher FRESHSERVICE_DOMAIN, FRESHSERVICE_API_KEY (tenant real OU mock),
#           JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY
make poll-once
```

Esperado: os chamados atualizados desde a última marca entram como eventos,
`analytics.sync_state.last_sync_at` avança, nada duplica ao rodar de novo.

Ponta a ponta, cronometrado (SC-002): abrir um chamado no Freshservice sandbox
com o campo de squad preenchido; a issue correspondente deve aparecer no
projeto Jira em menos de 1 minuto, sem nenhuma ação manual.

Diagnóstico de falha (R-007) — provar as três categorias:

```bash
# chave errada de propósito
FRESHSERVICE_API_KEY=invalida make poll-once
```

Esperado: `last_error` com categoria `auth`, **sem** a chave no texto. Repetir
com domínio inalcançável e confirmar categoria `connectivity`. As duas
mensagens precisam ser distinguíveis a olho nu — é o ponto do requisito.

Sem credencial, a suíte continua verde:

```bash
make test
```

---

## F3 — Base histórica

Preview sem gravar:

```bash
curl -s -X POST http://localhost:8000/api/v1/analytics/upload/detect \
  -F "files=@'Data 20260602.xlsx'" \
  -F "files=@'Fechados 20260602.xlsx'" \
  -F "files=@jira.csv" | jq
```

Esperado: três arquivos classificados como `fs_abertos`, `fs_fechados` e
`jira_cards`, com `row_count` **393**, **2629** e **428**. Banco intocado —
conferir que `analytics.chamados_abertos` continua vazia.

Gravar:

```bash
curl -s -X POST http://localhost:8000/api/v1/analytics/upload/commit \
  -F "files=@'Data 20260602.xlsx'" \
  -F "files=@'Fechados 20260602.xlsx'" \
  -F "files=@jira.csv" | jq
```

Esperado: 3.022 chamados (não 3.024 — as duas linhas de rodapé do export são
descartadas) e 428 cards. Rodar o **mesmo comando de novo**: `inserted: 0`,
todo o resto `updated`, total de registros inalterado.

Anonimização (FR-016) — a checagem que não pode ser pulada:

```sql
SELECT solicitante, agente_tecnico FROM analytics.chamados_abertos LIMIT 20;
SELECT count(*) FROM analytics.chamados_abertos WHERE anonymized = false;
```

Esperado: nenhum nome real de pessoa, e a segunda consulta devolve `0`.

Vínculo best-effort:

```sql
SELECT count(*) FROM analytics.jira_cards WHERE freshservice_ticket_id IS NOT NULL;
```

Esperado: **368** de 428. Confirmar que `PAV (277795/357558)` — dois números
soltos, sem prefixo — ficou `NULL`.

Arquivo ruim não derruba os bons: repetir o `detect` com um `.pdf` junto.
Esperado: `kind: "unknown"` para ele, os outros três classificados normalmente.

---

## F4 — Comparação

```bash
curl -s http://localhost:8000/api/v1/analytics/link-coverage | jq
```

Esperado: `best_effort.cobertura` ≈ **0.729** (312 de 428) e
`deterministic.cobertura` = **1.0**. Essa é a frase da apresentação, com
número.

Indicadores:

```bash
curl -s 'http://localhost:8000/api/v1/analytics/throughput?periodicidade=mes' | jq
curl -s 'http://localhost:8000/api/v1/analytics/lead-time' | jq
```

Esperado: throughput conta `Resolution = "Done"` — **291** cards na base de
exemplo, não 241 (`Status = Done`) nem 290 (a soma antiga). Lead time devolve
média **e** mediana, com `amostras` sobre o dataset filtrado inteiro.

Cascata de filtro:

```bash
curl -s 'http://localhost:8000/api/v1/analytics/filter-options?sistema=<um valor>' | jq '.tecnologia | length'
```

Esperado: as opções de `tecnologia` estreitam; as opções de `squad` **não**
estreitam por causa de um filtro do Jira. As duas bases não se afetam — decisão
deliberada, porque ~73% dos chamados não têm card e sumiriam do dropdown.

---

## F5 — Frontend

Banco vazio → tela de carga aparece no lugar do painel, não erro nem painel
zerado. Subir os três arquivos pela interface, confirmar o preview, ver os
painéis. Recarregar a página não faz a tela de carga voltar. Derrubar o backend
e recarregar mostra erro de conexão com botão de nova tentativa — não
"Carregando..." eterno.

Aplicar um filtro real e conferir que os indicadores da tela mudam juntos.
Trocar um filtro que invalida outro: o inválido é limpo sozinho, sem `<select>`
exibindo valor inexistente.

---

## Fechamento (antes de considerar pronto)

```bash
make test          # verde, sem rede, sem credencial
```

Checagem manual obrigatória (SC-007), com o dashboard e a fila de exceções
abertos e um dump de log em mãos: nenhuma credencial, nenhum nome de pessoa,
nenhuma descrição bruta de chamado e nenhuma saída bruta do modelo em log,
resposta de API, fila de exceções, evidência ou captura de tela.

Atualizar a seção "o que ficou de fora" do `README.md` com o que esta feature
mudou e com a limitação de R-005 (pseudônimo não é anonimato forte).
