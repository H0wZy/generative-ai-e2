"""Standalone worker — claims and processes one or more outbox events.

Usage:
    python -m app.worker          # run continuously until queue is empty
    python -m app.worker --once   # process exactly one event
"""
from __future__ import annotations

import argparse
import sys

from app.core.config import get_settings
from app.core.database import make_session_factory
from app.integrations.jira import FakeJiraClient, JiraClient
from app.services.processing import ProcessingService


def main(once: bool = False) -> None:
    settings = get_settings()
    session_factory = make_session_factory(str(settings.database_url))
    jira_client = JiraClient(settings) if settings.jira_is_configured else FakeJiraClient()

    processed = 0
    while True:
        session = session_factory()
        try:
            result = ProcessingService(session, jira_client, settings).process_next()
        finally:
            session.close()

        if result is None:
            print(f"[worker] queue empty — processed {processed} event(s).")
            break

        processed += 1
        print(
            f"[worker] workflow={result.workflow_execution_id} "
            f"status={result.status} "
            f"attempts={result.attempt_count} "
            f"jira_key={result.jira_issue_key}"
        )

        if once:
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Outbox worker")
    parser.add_argument("--once", action="store_true", help="Process exactly one event then exit")
    args = parser.parse_args()
    main(once=args.once)
