"""
Avaliação do golden set: `python3 -m rag.golden.eval`.

Para cada pergunta em questions.jsonl, roda busca semântica (limit=5) e
verifica se o arquivo-fonte esperado aparece entre os resultados.
Imprime hit/miss por pergunta e recall@5 agregado.
"""

from __future__ import annotations

import json
from pathlib import Path

from rag.db import DEFAULT_DB_PATH, get_connection
from rag.search.query import search

QUESTIONS_PATH = Path(__file__).parent / "questions.jsonl"


def load_questions() -> list[dict]:
    with QUESTIONS_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    conn = get_connection(DEFAULT_DB_PATH)
    questions = load_questions()
    hits = 0

    for q in questions:
        results = search(conn, q["question"], limit=5)
        expected = q["expected_source"]
        hit = any(r.file_path.replace("\\", "/").endswith(expected) for r in results)
        hits += int(hit)
        status = "HIT " if hit else "MISS"
        top_files = [Path(r.file_path).as_posix().split("generative-ai-e2/")[-1] for r in results]
        print(f"[{status}] {q['question']}")
        print(f"       esperado={expected}  retornado={top_files}")

    total = len(questions)
    recall = hits / total if total else 0.0
    print(f"\nrecall@5 = {hits}/{total} = {recall:.2f}")
    conn.close()


if __name__ == "__main__":
    main()
