from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Memory:
    id: str
    content: str
    tags: list[str]
    project: str | None
    source_agent: str | None
    importance: int
    created_at: str
    updated_at: str
    archived_at: str | None
    deleted_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "tags": self.tags,
            "project": self.project,
            "source_agent": self.source_agent,
            "importance": self.importance,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "archived_at": self.archived_at,
            "deleted_at": self.deleted_at,
        }
