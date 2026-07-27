---
name: feedback-agent-roster
description: Owner dá autonomia total para criar, reescrever e deletar subagents em .claude/agents/, inclusive o architect — mas exige leitura do repo real antes
metadata:
  type: feedback
---

O owner autoriza mexer no roster de `.claude/agents/` sem pedir confirmação:
reescrever, criar novo agente e **deletar** o que não serve — inclusive editar
o próprio `architect.md`.

**Why:** os agentes vieram por cópia do projeto Selzler Construtora (.NET, site
institucional) e descreviam uma stack que não existe aqui. Agente com stack
errada faz worker inventar comando (`dotnet test`) e alucinar estrutura.

**How to apply:** antes de tocar em qualquer agente, ler o repo real (pyproject,
Makefile, compose, árvore de arquivos) e as skills que existem em disco —
skill referenciada e inexistente (`definition-of-done-sync`, `plan`) é falha
silenciosa. Deletar é preferível a manter agente fora de contexto; git guarda.
Preferência confirmada: enxugar o roster, não acumular.
