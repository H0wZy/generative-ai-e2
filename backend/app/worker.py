"""Standalone worker — polls Freshservice and drains the outbox.

Usage:
    python -m app.worker              # drain the outbox until empty
    python -m app.worker --once       # process exactly one outbox event
    python -m app.worker --poll-once  # poll Freshservice once, then exit
    python -m app.worker --loop       # poll + drain forever, on the configured interval
"""
from __future__ import annotations

import argparse
import time

from app.core.config import get_settings
from app.core.database import make_session_factory
from app.integrations.freshservice import FakeFreshserviceClient, FreshserviceClient
from app.integrations.jira import FakeJiraClient, JiraClient
from app.services.polling import PollingService
from app.services.processing import ProcessingService


def poll_once(settings=None, session_factory=None) -> dict:
    settings = settings or get_settings()
    session_factory = session_factory or make_session_factory(str(settings.database_url))
    client = (
        FreshserviceClient(settings)
        if settings.freshservice_is_configured
        else FakeFreshserviceClient()
    )

    session = session_factory()
    try:
        summary = PollingService(session, client).poll_once()
    finally:
        session.close()

    if summary["error"]:
        # The category ('auth' / 'connectivity' / 'business') is the actionable
        # part. A bad key and a blocked proxy must not read the same.
        print(f"[poll] failed: {summary['error']}")
    else:
        print(
            f"[poll] fetched={summary['fetched']} "
            f"accepted={summary['accepted']} duplicates={summary['duplicates']}"
        )
    return summary


def drain_outbox(once: bool = False, settings=None, session_factory=None) -> int:
    settings = settings or get_settings()
    session_factory = session_factory or make_session_factory(str(settings.database_url))
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
    return processed


def main(once: bool = False, poll_only: bool = False, loop: bool = False) -> None:
    settings = get_settings()
    session_factory = make_session_factory(str(settings.database_url))

    if poll_only:
        poll_once(settings, session_factory)
        return

    if loop:
        interval = settings.freshservice_poll_interval_seconds
        while True:
            poll_once(settings, session_factory)
            drain_outbox(once=False, settings=settings, session_factory=session_factory)
            time.sleep(interval)
        return

    drain_outbox(once=once, settings=settings, session_factory=session_factory)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Freshservice poller + outbox worker")
    parser.add_argument("--once", action="store_true", help="Process exactly one outbox event then exit")
    parser.add_argument("--poll-once", action="store_true", help="Poll Freshservice once then exit")
    parser.add_argument("--loop", action="store_true", help="Poll and drain forever on the configured interval")
    args = parser.parse_args()
    main(once=args.once, poll_only=args.poll_once, loop=args.loop)
