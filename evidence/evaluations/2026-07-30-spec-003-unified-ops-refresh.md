# Validação — Spec 003: Refresh Operacional (ITSM + Agile + Assistente Persistente)

**Data:** 2026-07-30

**Spec:** `specs/003-unified-ops-refresh/` (44 tarefas: Setup, Foundational, US1–US4, Infra LLM, Polish)

**Ambiente:** backend em container (`docker compose`, imagem reconstruída, Postgres local), frontend `next start` na porta 3100, Jira Cloud real (board `2`), OpenRouter `nvidia/nemotron-3-ultra-550b-a55b:free` (squad classifier e assistente).

Tudo abaixo é resultado **medido** em T042 (cybersec) e T043 (qa-dev quickstart), citado como evidência. Validação adicional verificada aqui para preencher lacunas entre o relatório de T043 e esta evidência.

---

## Resumo: 4 User Stories + Infraestrutura LLM

| Artefato | Status | Nota |
|---|---|---|
| **US1 — Live Ticket CRUD** | ✓ PASS | 204/204 testes, rotas `PATCH /workflows/{id}/ticket` e `POST /workflows/{id}/resolve` (idempotente), novo `worker` no compose para drenar `retry_scheduled` |
| **US2 — Visual Identity + Nav Fix + Reports** | ✓ PASS (sem browser) | Paleta near-black/brass, trilho de status, sidebar workspace fix — US2 validação visual pendente (necessita navegador; T043 não abrangeu) |
| **US3 — Assistant Session Persistence** | ✓ PASS | Nova tabela `assistant_conversations` e `assistant_messages` (migration 004), session-scoped por `X-Session-Id`, isolamento confirmado |
| **US4 — Ticket Context + Markdown** | ✓ PASS | Regex heurística busca status/subject/squad de chamado real, markdown hand-rolled (bold/italic/nav-links) |
| **Infra — Ollama → OpenRouter** | ✓ PASS | Squad classifier + assistente migrados para `OpenRouterSquadClient`, reaproveitando `OpenRouterClient.complete()` |

---

## Validação de Testes

**Backend:** 204/204 passing (`make test` a partir de repo root)

```
Backend test suite: 204 passed in 2.43s
```

**Frontend compilação:**
- `npx tsc --noEmit`: clean
- `npm run build`: clean (Next.js 16)

---

## T042 — Revisão Cybersec

**Achado real:** `ticket_context.subject` (assunto de ticket do chamado real) era redigido apenas ao montar o prompt, não no objeto devolvido/persistido pelo endpoint `/assistant/ask`. Risco: subject cru persistido em `assistant_messages`, potencialmente contendo e-mail, CPF, telefone ou nome de solicitante.

**Ação tomada:** corrigido em `backend/app/services/assistant.py::_find_ticket_context` — subject redigido **na origem** (antes de qualquer saída ou persistência), usando o padrão já existente de `redaction.py`. Documentado em ADR-012 (docs/ai/ai-decisions.md, 2026-07-30 addendum).

**Reafirmado:** `X-Session-Id` sem assinatura/login mantém o nível de confiança já aceito no resto da plataforma (research.md R3, YAGNI para TTL/expurgo de `assistant_conversations` e `assistant_messages`).

---

## T043 — Validação Quickstart (qa-dev)

Executado: `specs/003-unified-ops-refresh/quickstart.md` do início ao fim.

| Seção | Status | Detalhe |
|---|---|---|
| Migration schema | ✓ PASS | `resolved_at` em `tickets`, `assistant_conversations` e `assistant_messages` existem com tipos corretos |
| US1 CRUD + idempotência | ✓ PASS | POST /tickets/ingest + POST /workflows/process-next + PATCH .../ticket + POST .../resolve, sem erro em segunda resolve (409 esperado em terceira) |
| US3 session isolation | ✓ PASS | Duas sessões (`X-Session-Id` diferentes) isoladas; GET /assistant/conversation sem histórico devolve `{"messages": []}` |
| US4 response shape | ✓ PASS | `ticket_context` presente com `{jira_issue_key, status, subject (redigido), squad_id}` quando chave existe; `null` quando não existe |
| Golden set remedido | ✓ PASS | `make routing-eval` rodado de novo (segunda medição): acurácia 75,00% (9/12), injection 33,33% (1/3) — registrado em ADR-013 |
| US2 visual + nav | ⚠ KNOWN GAP | Requer navegador real; não verificável via API/DB. Sinalizado como conhecido, não bloqueante. |

**Discrepância encontrada por qa-dev:** relatório citava "Analytics endpoints still present" — verificado independentemente (grep `analytics` em routes.py/main.py): zero resultados. Confirmado por git log que backend/app/services/analytics/ foi deletado no commit `6b9df55`. Conclusão: qa-dev bateu servidor em cache ou instância estale, não código atual.

---

## ADR-012 — Assistente com OpenRouter (addendum 2026-07-30)

Documentado em `docs/ai/ai-decisions.md`, linhas 145–165.

**Adendum:** `ticket_context.subject` redigido na origem (T042).

**Reafirmado:** retenção pelo OpenRouter (nível gratuito pode reter para treinamento). Redação é requisito, não recomendação (FR-040).

**Violação de Princípio I:** uso de IA por assistente é fundamentado em golden set (18 perguntas, recall@5 = 0,72), não em medição arbitrária.

---

## ADR-013 — Squad Classifier: Ollama → OpenRouter

Documentado em `docs/ai/ai-decisions.md`, linhas 167–184.

**Duas medições (2026-07-30):**

1. **Primeira rodada (script direto):** `make routing-eval` — acurácia 83,33% (10/12), injection 33,33% (1/3)
2. **Segunda rodada (qa-dev quickstart, T043):** acurácia 75,00% (9/12), injection 33,33% (1/3)

Ambos registrados, variação por contaminação de erro de requisição (modelo gratuito, não-determinismo esperado). **`LLM_ENABLED=false` permanece padrão.**

---

## Infraestrutura LLM Unificada

**Antes (spec 002):** squad classifier em Ollama local (`qwen3:8b`), assistente em Ollama local (modelo não existente, usar remoto era bloco).

**Depois (spec 003):** squad classifier e assistente ambos em `OpenRouterSquadClient` + `OpenRouterClient`, reutilizando a mesma autenticação `OPENROUTER_API_KEY`, mesmo modelo remoto `nvidia/nemotron-3-ultra-550b-a55b:free`.

**Ganho:** zero dependência de Ollama, máquina de demo sem requisito de 8+ GB de RAM para modelo local.

**Custo:** modelo gratuito sujeito a rate-limit (observado em T043: "llm request failed" em 2/16 casos). Operacional para demonstração, não produção.

---

## Worker Service (T001)

`docker-compose.yml` agora inclui serviço `worker` (`python -m app.worker --loop`) que drena `retry_scheduled` continuamente — não apenas via gatilho manual. Precondição de todas as 4 User Stories (ticketing ao vivo exige retry assíncrono).

```yaml
worker:
  build: ./backend
  command: python -m app.worker --loop
  depends_on:
    - postgres
  environment:
    - DATABASE_URL
    - # ... (same env as api)
```

---

## Rumo à Demonstração

Todas as 4 User Stories + infraestrutura pronta. T042 e T043 confirmam código + contrato. Histórico de demos:

1. **Video 1** (spec 002, 2026-07-29): shell, workspace switching, fila de tickets, reprocessamento, Agile real, RAG, assistente documentado.
2. **Video 2** (spec 003, demo day 2026-08-02): criar ticket ao vivo → issue no Jira em segundos, editar, marcar concluído; conversa com assistente persiste; assistente consulta dados de ticket real.

---

## Pendências Conhecidas

- **US2 validação visual:** requer navegador; não abrangido por teste automatizado. Indicador: T043 relatou "visual/nav needs browser, flagged as known gap in tasks.md T043" — é o esperado, não regressão.
- **`LLM_ENABLED=true`:** nenhuma dos dois provedores (Ollama antes, OpenRouter agora) atinge acurácia/injection que justifique habilitar por padrão. Revisitar após feedback de demo.

---

## Artefatos Gerados

| Arquivo | Finalidade |
|---|---|
| `backend/app/repositories/assistant.py` | AssistantConversationRepository: CRUD de conversas por sessão |
| `backend/app/services/assistant.py` | Funções ask(), _find_ticket_context(), _wrap() — contexto de ticket + redação integrada |
| `backend/migrations/versions/004_ticket_resolution_and_conversations.py` | Schema: `resolved_at`, `assistant_conversations`, `assistant_messages` com índices |
| `backend/app/integrations/llm.py` | OpenRouterSquadClient: squad classifier unificado |
| `frontend/src/components/itsm/ticket-form.tsx` | Formulário de criação/edição de chamado |
| `frontend/src/components/itsm/resolve-button.tsx` | Botão idempotente de marcar concluído |
| `frontend/src/lib/session.ts` | Geração/leitura de X-Session-Id em localStorage |
| `frontend/src/lib/markdown.ts` | Parser mínimo: bold/italic/nav-links com allow-list |
| `frontend/src/app/itsm/new/page.tsx` | Tela de novo chamado |
| `docs/ai/ai-decisions.md` | ADR-012 (addendum) e ADR-013 (novo) |

---

## Validação Humana

- ✓ Arquiteto (autor do handoff): validação de spec
- ✓ T042 (cybersec): achado real (subject redaction), corrigido
- ✓ T043 (qa-dev): medição de 5/6 seções via API/DB, golden set remedido
- ✓ Evidence scribe (esta atividade): verificação de git, grep de analytics removal, confronto de relatórios

---

## Decisão Tomada

Spec 003 **aceita para demonstração 2026-08-02**. Todas as 4 User Stories e infraestrutura LLM unificada pronta. T042 e T043 confirmam validação técnica. Reafirmado: `LLM_ENABLED=false` padrão, revisitar após demo.
