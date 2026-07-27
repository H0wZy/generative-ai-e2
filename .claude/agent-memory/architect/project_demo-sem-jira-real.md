---
name: demo-sem-jira-real
description: Demo e vídeo do bootcamp rodam com FakeJiraClient — nenhum tenant Jira real deve ser configurado antes de gravar
metadata:
  type: project
---

Resolvido em 2026-07-27: a pergunta "qual tenant Jira aparece no vídeo" não é
decisão de negócio, é fato observável. `backend/.env` tem apenas
`DATABASE_URL`, `TEST_DATABASE_URL` e `POSTGRES_PASSWORD` — nenhuma credencial
Jira. `FakeJiraClient` ativa automaticamente quando faltam `JIRA_BASE_URL`,
`JIRA_EMAIL` e `JIRA_API_TOKEN`. A demo não faz chamada de rede e nenhum tenant
aparece na tela.

**Why:** o bootcamp proíbe dado da TCS ou de clientes dela no vídeo. Configurar
credencial real faria a URL do tenant vazar em log e em resposta de API — o
estado padrão já é o seguro, e mexer nele é que criaria o problema.

**How to apply:** se alguém propuser "ligar o Jira real para a demo ficar mais
convincente", diga não. Antes de qualquer gravação, confirme que `backend/.env`
segue sem as três variáveis Jira. O adaptador real (`JiraClient`, REST v3)
existe e está testado — a escolha é não usá-lo na gravação, não que falte.
Ver [[modelos-locais]].
