---
name: modelos-locais
description: Bloco 2 usa modelos locais (Ollama qwen3:8b + all-MiniLM-L6-v2) em vez de API paga — máquina do dono já tem ambos
metadata:
  type: project
---

Decisão de 2026-07-26: a camada GenAI do produto roda em modelos locais.
Embeddings = `all-MiniLM-L6-v2` (sentence-transformers, já no cache HuggingFace
do usuário). Classificação de squad = `qwen3:8b` via Ollama em
`http://localhost:11434` (Ollama instalado na máquina, também tem
`gemma4:latest`).

**Why:** o bootcamp proíbe expor chave de API no código e o projeto proíbe
commitar segredo. Modelo local elimina a classe inteira do problema — não há
chave para vazar, custo de API é zero, e nenhum dado de ticket sai da máquina.
Também destravou o Bloco 2 sem precisar de decisão do dono sobre provedor.

**How to apply:** ao planejar qualquer feature GenAI deste projeto, assuma
inferência local por padrão e trate API paga como exceção que precisa de
justificativa. O custo relevante para o canva do bootcamp é latência de
inferência local, não dólar por token. Antes de recomendar, confirme que os
modelos ainda estão presentes (`ollama list`, cache HF) — é estado de máquina,
não do repositório, e pode sumir.
