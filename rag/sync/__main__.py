"""
CLI de sincronização incremental: `python3 -m rag.sync`.

Indexa docs/**/*.md (allowlist fixa) em rag/data/knowledge.db.
Idempotente: rodar de novo sem mudanças reindexa 0 arquivos.
"""

from __future__ import annotations

import logging
from pathlib import Path

from rag.db import DEFAULT_DB_PATH, initialize_db
from rag.sync.indexer import sync_directory

DOCS_ROOT = (Path(__file__).resolve().parent.parent.parent / "docs").resolve()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    conn = initialize_db(DEFAULT_DB_PATH)
    result = sync_directory(conn, root=str(DOCS_ROOT), allowed_prefixes=[str(DOCS_ROOT)])
    print(
        f"sync: adicionados={result.added} atualizados={result.updated} "
        f"sem_mudanca={result.unchanged} removidos={result.removed} "
        f"erros={len(result.errors)}"
    )
    conn.close()


if __name__ == "__main__":
    main()
