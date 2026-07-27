---
name: agent-teams-flag
description: Use when deciding whether to re-enable the experimental Agent Teams flag (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS) for this project — explains why it was turned off and the exact settings.json change needed to turn it back on.
---

# Flags experimentais (desligadas por padrão)

Agent Teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` em
`~/.claude/settings.json`) — bloco `env` removido inteiro do settings.json
global em 2026-07-18. Motivo real: travamentos do qa-dev, limitação
conhecida da [doc oficial](https://code.claude.com/docs/en/agent-teams#limitations)
("task status can lag" e "teammates stopping on errors" quando dispatch
de subagente vira teammate real). Custo de token maior também é fator,
mas travamento foi o motivo que forçou desligar.

Pra religar, adicionar de volta:

```json
"env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
```

Só religar quando escalar pros 7 agentes com necessidade real de
coordenação em paralelo — sabendo que qa-dev pode voltar a travar.
