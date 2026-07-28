"""Error categorization shared by the external adapters.

Three categories, because "HTTP 403" alone is ambiguous: a corporate proxy
returning 403 looks exactly like a rejected credential, and debugging the wrong
one costs hours (it already happened once with a blocked API host).

Never put the credential or the response body in the message — the category and
the status code are enough to act on.
"""
from __future__ import annotations

from typing import Literal

ErrorCategory = Literal["auth", "connectivity", "business"]

_AUTH_STATUS = {401, 403}
_CONNECTIVITY_STATUS = {408, 429, 500, 502, 503, 504}


def categorize_status(status_code: int) -> ErrorCategory:
    """Map an HTTP status to a category."""
    if status_code in _AUTH_STATUS:
        return "auth"
    if status_code in _CONNECTIVITY_STATUS:
        return "connectivity"
    return "business"


def categorize_exception(exc: Exception) -> ErrorCategory:
    """Map a transport-level exception to a category.

    Timeouts, refused connections and DNS failures are connectivity — never
    auth, even though a proxy can dress them up as a 403 (that case is caught
    by :func:`categorize_status`).
    """
    import httpx

    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
        return "connectivity"
    return "business"


def is_retryable(category: ErrorCategory) -> bool:
    """Only connectivity failures are worth retrying.

    An ``auth`` failure repeats identically until someone fixes the credential;
    retrying it just burns attempts and rate limit.
    """
    return category == "connectivity"


def format_error(category: ErrorCategory, detail: str) -> str:
    """Build the string that lands in ``last_error``.

    ``detail`` must already be safe to persist — a status code, a timeout
    label. Callers must not pass a response body or anything derived from a
    credential.
    """
    return f"{category}:{detail}"


def demo() -> None:
    """Self-check — the categorization is a branch, so it gets one."""
    import httpx

    assert categorize_status(401) == "auth"
    assert categorize_status(403) == "auth"
    assert categorize_status(429) == "connectivity"
    assert categorize_status(503) == "connectivity"
    assert categorize_status(400) == "business"
    assert categorize_status(422) == "business"

    assert categorize_exception(httpx.ConnectTimeout("x")) == "connectivity"
    assert categorize_exception(httpx.ConnectError("x")) == "connectivity"
    assert categorize_exception(ValueError("x")) == "business"

    assert is_retryable("connectivity") is True
    assert is_retryable("auth") is False
    assert is_retryable("business") is False

    assert format_error("auth", "HTTP 401") == "auth:HTTP 401"
    print("errors.demo OK")


if __name__ == "__main__":
    demo()
