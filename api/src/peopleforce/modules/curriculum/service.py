"""Loads the published learning path, validates it, and caches it.

Failure policy: a broken lesson never takes the path down (it becomes "not playable"); an unreachable
CMS serves the last good copy, and on a cold start falls back to the bundled seed content.
"""

import json
import time
from pathlib import Path
from typing import Any, Protocol

import structlog
from pydantic import ValidationError

from peopleforce.core.errors import AppError
from peopleforce.modules.curriculum.schemas import LearningPath, LessonContent

log = structlog.get_logger()

DEFAULT_DOMAIN = "software-development"
SEED_DIR = Path(__file__).resolve().parents[4] / "content"


class ContentSource(Protocol):
    name: str

    async def fetch_path(self, domain: str) -> dict[str, Any] | None:
        """Raw, unvalidated path document in the shape of `LearningPath`, or None if it does not exist."""
        ...


class LocalContentSource:
    """Seed content committed to the repo. Used in development and as the cold-start fallback."""

    name = "local"

    def __init__(self, directory: Path = SEED_DIR) -> None:
        self._directory = directory

    async def fetch_path(self, domain: str) -> dict[str, Any] | None:
        file = self._directory / f"{domain}.json"
        if not file.is_file():
            return None
        return json.loads(file.read_text(encoding="utf-8"))


def parse_path(raw: dict[str, Any]) -> LearningPath:
    """Validate a raw path. Lessons whose content is invalid or unsupported keep their map entry only."""
    raw = json.loads(json.dumps(raw))  # deep copy; we mutate below
    for chapter in raw.get("chapters") or []:
        for lesson in chapter.get("lessons") or []:
            content = lesson.get("content")
            if not content or not content.get("blocks"):
                lesson["content"] = None
                continue
            try:
                parsed = LessonContent.model_validate(content)
            except ValidationError as exc:
                lesson["content"] = None
                lesson["content_error"] = "; ".join(e["msg"] for e in exc.errors())[:500]
                log.warning("lesson_content_invalid", lesson_id=lesson.get("id"), errors=exc.errors())
                continue
            if parsed.unsupported_strategies:
                lesson["content"] = None
                lesson["content_error"] = f"unsupported completion: {parsed.unsupported_strategies}"
                log.warning("lesson_content_unsupported", lesson_id=lesson.get("id"))
    return LearningPath.model_validate(raw)


class CurriculumService:
    def __init__(self, source: ContentSource, fallback: ContentSource | None, ttl_seconds: int) -> None:
        self._source = source
        self._fallback = fallback
        self._ttl = ttl_seconds
        self._cache: dict[str, tuple[float, LearningPath]] = {}

    async def get_path(self, domain: str = DEFAULT_DOMAIN) -> LearningPath:
        cached = self._cache.get(domain)
        if cached and time.monotonic() - cached[0] < self._ttl:
            return cached[1]
        try:
            path = await self._load(self._source, domain)
        except Exception as exc:  # network error, bad JSON, schema violation at path level
            log.warning("content_source_failed", source=self._source.name, error=str(exc))
            if cached:
                # Keep serving the last good copy, and do not hammer a failing CMS on every request.
                self._cache[domain] = (time.monotonic(), cached[1])
                return cached[1]
            if not self._fallback:
                raise AppError("content_unavailable", "Lessons are temporarily unavailable.", 503) from exc
            try:
                path = await self._load(self._fallback, domain)
            except Exception as fallback_exc:
                raise AppError(
                    "content_unavailable", "Lessons are temporarily unavailable.", 503
                ) from fallback_exc
        self._cache[domain] = (time.monotonic(), path)
        return path

    async def get_path_by_id(self, path_id: str) -> LearningPath:
        # One path per domain in the MVP, so the default domain is the only candidate.
        path = await self.get_path(DEFAULT_DOMAIN)
        if path.id != path_id:
            log.warning("unknown_learning_path", path_id=path_id)
        return path

    def invalidate(self) -> None:
        self._cache.clear()

    @staticmethod
    async def _load(source: ContentSource, domain: str) -> LearningPath:
        raw = await source.fetch_path(domain)
        if raw is None:
            raise LookupError(f"no published learning path for domain {domain!r} in {source.name}")
        return parse_path(raw)
