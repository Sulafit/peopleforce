"""Server-side product analytics. Never the source of truth, and never given private content."""

from typing import Any, Protocol

import structlog

log = structlog.get_logger()


class Analytics(Protocol):
    def capture(self, distinct_id: str, event: str, properties: dict[str, Any] | None = None) -> None: ...

    def shutdown(self) -> None: ...


class NoopAnalytics:
    def capture(self, distinct_id: str, event: str, properties: dict[str, Any] | None = None) -> None:
        log.debug("analytics_event", distinct_id=distinct_id, analytics_event=event, properties=properties)

    def shutdown(self) -> None:
        return None


class PostHogAnalytics:
    def __init__(self, api_key: str, host: str) -> None:
        from posthog import Posthog

        self._client = Posthog(api_key, host=host)

    def capture(self, distinct_id: str, event: str, properties: dict[str, Any] | None = None) -> None:
        try:
            self._client.capture(
                event, distinct_id=distinct_id, properties={"source": "server", **(properties or {})}
            )
        except Exception as exc:  # analytics must never break a request
            log.warning("analytics_capture_failed", analytics_event=event, error=str(exc))

    def shutdown(self) -> None:
        try:
            self._client.shutdown()
        except Exception:
            pass
