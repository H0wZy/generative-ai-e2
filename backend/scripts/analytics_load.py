"""Load the Power BI exports from a directory into the analytics schema.

Usage: python -m scripts.analytics_load ../examples

Development entry point, equivalent to the two-step upload the dashboard uses.
Always merges, never replaces: running it twice updates and inserts nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.database import make_engine
from app.services.analytics.excel_ingestion import ingest_from_directory


def main(directory: str) -> None:
    path = Path(directory).expanduser().resolve()
    if not path.is_dir():
        raise SystemExit(f"not a directory: {path}")

    settings = get_settings()
    engine = make_engine(str(settings.database_url))
    summary = ingest_from_directory(engine, path)

    print(
        f"[analytics] chamados inserted={summary['chamados_inserted']} "
        f"updated={summary['chamados_updated']} | "
        f"cards inserted={summary['cards_inserted']} updated={summary['cards_updated']}"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m scripts.analytics_load <directory>")
    main(sys.argv[1])
