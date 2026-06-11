from dataclasses import dataclass
from pathlib import Path

import aiosqlite


@dataclass(frozen=True)
class Film:
    code: str
    title: str


def normalize_code(code: str) -> str:
    return code.strip().upper()


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS films (
                    code TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_requests (
                    user_id INTEGER PRIMARY KEY,
                    code TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (code) REFERENCES films(code) ON DELETE CASCADE
                )
                """
            )
            await db.commit()

    async def add_film(self, code: str, title: str) -> Film:
        normalized_code = normalize_code(code)
        clean_title = title.strip()

        if not normalized_code:
            raise ValueError("Movie code cannot be empty")

        if not clean_title:
            raise ValueError("Movie title cannot be empty")

        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO films (code, title)
                VALUES (?, ?)
                ON CONFLICT(code) DO UPDATE SET title = excluded.title
                """,
                (normalized_code, clean_title),
            )
            await db.commit()

        return Film(code=normalized_code, title=clean_title)

    async def delete_film(self, code: str) -> bool:
        normalized_code = normalize_code(code)

        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("DELETE FROM films WHERE code = ?", (normalized_code,))
            await db.commit()
            return cursor.rowcount > 0

    async def get_film(self, code: str) -> Film | None:
        normalized_code = normalize_code(code)

        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT code, title FROM films WHERE code = ?",
                (normalized_code,),
            )
            row = await cursor.fetchone()

        if row is None:
            return None

        return Film(code=row["code"], title=row["title"])

    async def list_films(self) -> list[Film]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT code, title FROM films ORDER BY code")
            rows = await cursor.fetchall()

        return [Film(code=row["code"], title=row["title"]) for row in rows]

    async def set_pending_code(self, user_id: int, code: str) -> None:
        normalized_code = normalize_code(code)

        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO pending_requests (user_id, code, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    code = excluded.code,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, normalized_code),
            )
            await db.commit()

    async def get_pending_code(self, user_id: int) -> str | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT code FROM pending_requests WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()

        if row is None:
            return None

        return str(row[0])

    async def clear_pending_code(self, user_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM pending_requests WHERE user_id = ?", (user_id,))
            await db.commit()
