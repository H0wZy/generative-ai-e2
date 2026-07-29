# syntax=docker/dockerfile:1
# Contexto de build é a raiz do repositório: o pacote é importado como `rag.*`.
FROM python:3.12-slim
WORKDIR /app

COPY rag/requirements.txt ./rag/requirements.txt

# torch CPU-only antes do resto: a wheel padrão do PyPI traz CUDA (~3.9 GB) e
# all-MiniLM-L6-v2 não precisa de GPU.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install --no-cache-dir -r rag/requirements.txt

COPY rag/ ./rag/

# Modelo baixado na build, não na primeira requisição.
ENV HF_HOME=/app/.cache/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

ENV RAG_DB_PATH=/app/rag/data/knowledge.db

EXPOSE 8100

CMD ["uvicorn", "rag.http.app:app", "--host", "0.0.0.0", "--port", "8100"]
