from __future__ import annotations

import json
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from memory_forge.models import Memory, utc_now

DEFAULT_LIMIT = 10
MAX_LIMIT = 50


class MemoryStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def remember(
        self,
        content: str,
        tags: list[str] | None = None,
        project: str | None = None,
        source_agent: str | None = None,
        importance: int = 3,
    ) -> Memory:
        content = _clean_content(content)
        clean_tags = _clean_tags(tags)
        clean_importance = _clean_importance(importance)
        now = utc_now()
        memory_id = str(uuid.uuid4())

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (
                    id, content, tags, project, source_agent, importance,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    content,
                    json.dumps(clean_tags),
                    _clean_optional(project),
                    _clean_optional(source_agent),
                    clean_importance,
                    now,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()

        return _memory_from_row(row)

    def search(
        self,
        query: str | None = None,
        project: str | None = None,
        tags: list[str] | None = None,
        source_agent: str | None = None,
        include_archived: bool = False,
        limit: int = DEFAULT_LIMIT,
    ) -> list[Memory]:
        clean_limit = _clean_limit(limit)
        clauses = ["m.deleted_at IS NULL"]
        params: list[Any] = []

        if not include_archived:
            clauses.append("m.archived_at IS NULL")
        if project:
            clauses.append("m.project = ?")
            params.append(project.strip())
        if source_agent:
            clauses.append("m.source_agent = ?")
            params.append(source_agent.strip())

        clean_tags = _clean_tags(tags)
        for tag in clean_tags:
            clauses.append(
                "EXISTS (SELECT 1 FROM json_each(m.tags) WHERE json_each.value = ?)"
            )
            params.append(tag)

        fts_query = _to_fts_query(query)
        if fts_query:
            sql = f"""
                SELECT m.*
                FROM memories_fts f
                JOIN memories m ON m.rowid = f.rowid
                WHERE memories_fts MATCH ?
                  AND {' AND '.join(clauses)}
                ORDER BY bm25(memories_fts), m.importance DESC, m.updated_at DESC
                LIMIT ?
            """
            params = [fts_query, *params, clean_limit]
        else:
            sql = f"""
                SELECT m.*
                FROM memories m
                WHERE {' AND '.join(clauses)}
                ORDER BY m.importance DESC, m.updated_at DESC
                LIMIT ?
            """
            params.append(clean_limit)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_memory_from_row(row) for row in rows]

    def context(
        self,
        query: str | None = None,
        project: str | None = None,
        tags: list[str] | None = None,
        source_agent: str | None = None,
        limit: int = 8,
    ) -> dict[str, Any]:
        memories = self.search(
            query=query,
            project=project,
            tags=tags,
            source_agent=source_agent,
            limit=limit,
        )
        lines = []
        for memory in memories:
            labels = []
            if memory.project:
                labels.append(memory.project)
            if memory.tags:
                labels.append(", ".join(memory.tags))
            prefix = f"[{'; '.join(labels)}] " if labels else ""
            lines.append(f"- {prefix}{memory.content}")

        return {
            "count": len(memories),
            "context": "\n".join(lines),
            "memories": [memory.to_dict() for memory in memories],
        }

    def update(
        self,
        memory_id: str,
        content: str | None = None,
        tags: list[str] | None = None,
        project: str | None = None,
        source_agent: str | None = None,
        importance: int | None = None,
    ) -> Memory:
        existing = self.get(memory_id, include_archived=True)
        if existing is None:
            raise KeyError(f"Memory not found: {memory_id}")

        next_content = existing.content if content is None else _clean_content(content)
        next_tags = existing.tags if tags is None else _clean_tags(tags)
        next_project = existing.project if project is None else _clean_optional(project)
        next_source_agent = (
            existing.source_agent
            if source_agent is None
            else _clean_optional(source_agent)
        )
        next_importance = (
            existing.importance
            if importance is None
            else _clean_importance(importance)
        )

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE memories
                SET content = ?,
                    tags = ?,
                    project = ?,
                    source_agent = ?,
                    importance = ?,
                    updated_at = ?
                WHERE id = ? AND deleted_at IS NULL
                """,
                (
                    next_content,
                    json.dumps(next_tags),
                    next_project,
                    next_source_agent,
                    next_importance,
                    utc_now(),
                    memory_id,
                ),
            )
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()

        return _memory_from_row(row)

    def forget(self, memory_id: str, hard_delete: bool = False) -> dict[str, Any]:
        existing = self.get(memory_id, include_archived=True)
        if existing is None:
            raise KeyError(f"Memory not found: {memory_id}")

        with self._connect() as conn:
            if hard_delete:
                conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                return {"id": memory_id, "status": "deleted"}

            now = utc_now()
            conn.execute(
                """
                UPDATE memories
                SET archived_at = COALESCE(archived_at, ?),
                    updated_at = ?
                WHERE id = ? AND deleted_at IS NULL
                """,
                (now, now, memory_id),
            )
        return {"id": memory_id, "status": "archived"}

    def get(self, memory_id: str, include_archived: bool = False) -> Memory | None:
        clauses = ["id = ?", "deleted_at IS NULL"]
        params: list[Any] = [memory_id]
        if not include_archived:
            clauses.append("archived_at IS NULL")

        with self._connect() as conn:
            row = conn.execute(
                f"SELECT * FROM memories WHERE {' AND '.join(clauses)}",
                params,
            ).fetchone()
        return None if row is None else _memory_from_row(row)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode = WAL;
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]',
                    project TEXT,
                    source_agent TEXT,
                    importance INTEGER NOT NULL DEFAULT 3
                        CHECK (importance BETWEEN 1 AND 5),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived_at TEXT,
                    deleted_at TEXT
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
                USING fts5(
                    content,
                    tags,
                    project,
                    source_agent,
                    content='memories',
                    content_rowid='rowid'
                );

                CREATE TRIGGER IF NOT EXISTS memories_ai
                AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, content, tags, project, source_agent)
                    VALUES (new.rowid, new.content, new.tags, new.project, new.source_agent);
                END;

                CREATE TRIGGER IF NOT EXISTS memories_ad
                AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(
                        memories_fts, rowid, content, tags, project, source_agent
                    )
                    VALUES (
                        'delete', old.rowid, old.content, old.tags, old.project,
                        old.source_agent
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS memories_au
                AFTER UPDATE ON memories BEGIN
                    INSERT INTO memories_fts(
                        memories_fts, rowid, content, tags, project, source_agent
                    )
                    VALUES (
                        'delete', old.rowid, old.content, old.tags, old.project,
                        old.source_agent
                    );
                    INSERT INTO memories_fts(rowid, content, tags, project, source_agent)
                    VALUES (new.rowid, new.content, new.tags, new.project, new.source_agent);
                END;

                PRAGMA user_version = 1;
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn


def _memory_from_row(row: sqlite3.Row) -> Memory:
    return Memory(
        id=row["id"],
        content=row["content"],
        tags=json.loads(row["tags"]),
        project=row["project"],
        source_agent=row["source_agent"],
        importance=row["importance"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        archived_at=row["archived_at"],
        deleted_at=row["deleted_at"],
    )


def _clean_content(content: str) -> str:
    clean = content.strip()
    if not clean:
        raise ValueError("content cannot be empty")
    return clean


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    clean = value.strip()
    return clean or None


def _clean_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    clean_tags = []
    seen = set()
    for tag in tags:
        clean = tag.strip().lower()
        if clean and clean not in seen:
            clean_tags.append(clean)
            seen.add(clean)
    return clean_tags


def _clean_importance(importance: int) -> int:
    if importance < 1 or importance > 5:
        raise ValueError("importance must be between 1 and 5")
    return importance


def _clean_limit(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def _to_fts_query(query: str | None) -> str | None:
    if not query:
        return None
    terms = re.findall(r"[\w-]+", query.lower())
    if not terms:
        return None
    return " AND ".join(f'"{term}"' for term in terms)
