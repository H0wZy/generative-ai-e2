---
name: defeito-doc-sobre-codigo
description: Classe de defeito dominante neste projeto — afirmação sobre o sistema escrita em doc/evidência/release sem abrir o arquivo que a implementa
metadata:
  type: project
---

Toda revisão de artefato textual (evidência, ADR, README, notas de release,
canva, roteiro de vídeo) deve verificar cada afirmação factual contra o
arquivo que a implementa, antes de aprovar. Não aceite a afirmação porque
soa plausível.

**Why:** medido, não suposto. A Task 2.3 (evidência do Bloco 2) precisou de
4 rodadas de correção — e todos os defeitos das 4 rodadas foram desta
classe, zero foram defeitos de código. Depois disso, as notas da release
v0.1.0 trouxeram mais dois do mesmo tipo. Exemplos reais já capturados:
controle de segurança inventado que não existia em `backend/app/`;
`temperature=0` descrito como defesa contra injection (na verdade faz o
modelo obedecer à injeção de forma determinística); operadores de
comparação invertidos porque `distance` foi lido como `score`; idempotência
atribuída a `internal_correlation_id` quando é a constraint
`uq_ticket_event (source_system, source_ticket_id, event_type, event_id)`
mais os UNIQUE em `jira_issue_links`; mapa `CATEGORY_TO_SQUAD` citado
incompleto (esqueceram `integration` → `platform`).

**How to apply:** ao despachar qualquer agente que escreva sobre o sistema,
exija grep/Read do arquivo antes de escrever a frase, e cite arquivo:linha.
Ao revisar, faça o mesmo por conta própria — dois revisores independentes
(qa-dev e cybersec) já deixaram passar a inversão `score`/`distance` que só
apareceu na minha leitura. Pontos que erram com mais frequência: onde mora
a idempotência (banco, não app), semântica de `distance` (menor = mais
similar), o que a enum fechada do Pydantic realmente defende (saída
malformada, não saída válida-porém-manipulada), e qual fallback roda com
LLM desligado. Ver [[llm-desligado-injection]] e [[demo-sem-jira-real]].
