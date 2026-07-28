"""Classify an uploaded file by its column signature, never by its name.

The classification rule itself lives in ``excel_ingestion.classify_columns``,
shared with the directory loader. This module handles what is specific to
upload: reading bytes, the size ceiling, unreadable files, and the valid-row
count shown in the preview.
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd

from app.services.analytics.excel_ingestion import classify_columns, rows_for_kind

# The upload lives in memory (bytes plus DataFrame), so a huge file would take
# the process down. 20 MB is ample for the real exports (~100-500 KB).
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

# An xlsx is a zip. The byte ceiling above only bounds the *compressed* size,
# and openpyxl inflates the whole archive to build the DataFrame — so a small
# file with a high compression ratio still exhausts memory during the parse.
# This bounds what the parse is allowed to inflate to.
MAX_INFLATED_BYTES = 200 * 1024 * 1024


def _inflates_too_much(raw: bytes) -> bool:
    """True when the archive would expand past the inflated ceiling.

    A file that is not a zip at all is not a bomb — it fails later, at parse,
    and comes back as ``unreadable``.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            return sum(info.file_size for info in archive.infolist()) > MAX_INFLATED_BYTES
    except (zipfile.BadZipFile, OSError):
        return False


def _read_dataframe(filename: str, raw: bytes) -> pd.DataFrame:
    """Read an in-memory file with the same parameters the ingestion uses.

    Same parameters on purpose: it is what makes the previewed count match what
    the commit writes.
    """
    buffer = io.BytesIO(raw)
    if filename.lower().endswith(".csv"):
        return pd.read_csv(buffer, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    return pd.read_excel(buffer, engine="openpyxl")


def detect_file_type(filename: str, raw: bytes) -> dict:
    """Classify an uploaded file and count the rows a commit would persist.

    ``kind`` is one of ``fs_abertos``, ``fs_fechados``, ``jira_cards``,
    ``unknown`` (read fine, signature matched nothing), ``unreadable`` (did not
    open) or ``too_large``.

    The DataFrame comes back too, so the commit does not have to re-read it.
    """
    if len(raw) > MAX_UPLOAD_BYTES or _inflates_too_much(raw):
        return {"filename": filename, "kind": "too_large", "row_count": 0, "dataframe": None}

    try:
        df = _read_dataframe(filename, raw)
    except Exception:
        # The exception text can carry file content; the caller only needs the verdict.
        return {"filename": filename, "kind": "unreadable", "row_count": 0, "dataframe": None}

    kind = classify_columns(set(df.columns))
    row_count = len(rows_for_kind(kind, df)) if kind != "unknown" else 0

    return {"filename": filename, "kind": kind, "row_count": row_count, "dataframe": df}
