import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterable, List, Sequence, Tuple

from .constants import DB_FILE


POST_COLUMNS: dict[str, str] = {
    "id": "INTEGER PRIMARY KEY",
    "topic": "TEXT",
    "title": "TEXT",
    "body": "TEXT",
    "region": "TEXT",
    "tone": "TEXT",
    "persona": "TEXT",
    "length": "TEXT",
    "subreddit": "TEXT",
    "link": "TEXT",
    "auto_posted": "INTEGER DEFAULT 0",
    "upvotes": "INTEGER DEFAULT 0",
    "comments": "INTEGER DEFAULT 0",
    "timestamp": "TEXT",
    "conversation_id": "TEXT",  # Link to conversation memory
}

CONVERSATION_COLUMNS: dict[str, str] = {
    "id": "TEXT PRIMARY KEY",  # UUID for conversation
    "title": "TEXT",
    "created_at": "TEXT",
    "updated_at": "TEXT",
    "persona": "TEXT",
    "tone": "TEXT",
    "topic_pattern": "TEXT",
}

MESSAGE_COLUMNS: dict[str, str] = {
    "id": "INTEGER PRIMARY KEY",
    "conversation_id": "TEXT",
    "role": "TEXT",  # 'user' or 'assistant'
    "content": "TEXT",
    "timestamp": "TEXT",
    "metadata": "TEXT",  # JSON metadata
}


def init_db() -> None:
    with sqlite3.connect(DB_FILE) as conn:
        # Posts table
        columns_sql = ",\n                ".join(f"{name} {definition}" for name, definition in POST_COLUMNS.items())
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS posts (
                {columns_sql}
            )
            """
        )

        # Conversations table
        conv_columns_sql = ",\n                ".join(f"{name} {definition}" for name, definition in CONVERSATION_COLUMNS.items())
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS conversations (
                {conv_columns_sql}
            )
            """
        )

        # Messages table
        msg_columns_sql = ",\n                ".join(f"{name} {definition}" for name, definition in MESSAGE_COLUMNS.items())
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS messages (
                {msg_columns_sql}
            )
            """
        )

        # Backfill missing columns for existing installations ---------------------------------
        existing_columns = {
            row[1]: row[2]
            for row in conn.execute("PRAGMA table_info(posts)").fetchall()
        }
        added_columns: list[str] = []
        for name, definition in POST_COLUMNS.items():
            if name not in existing_columns:
                conn.execute(f"ALTER TABLE posts ADD COLUMN {name} {definition}")
                added_columns.append(name)

        # Normalize legacy rows for newly added nullable columns
        if "persona" in existing_columns or "persona" in added_columns:
            conn.execute("UPDATE posts SET persona = COALESCE(persona, '')")
        if "length" in existing_columns or "length" in added_columns:
            conn.execute("UPDATE posts SET length = COALESCE(length, 'Standard')")
        if "auto_posted" in existing_columns or "auto_posted" in added_columns:
            conn.execute("UPDATE posts SET auto_posted = COALESCE(auto_posted, 0)")
        if "conversation_id" in existing_columns or "conversation_id" in added_columns:
            conn.execute("UPDATE posts SET conversation_id = COALESCE(conversation_id, '')")

        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
    finally:
        conn.close()


def log_post(
    topic: str,
    title: str,
    body: str,
    region: str,
    tone: str,
    persona: str,
    length: str,
    subreddit: str,
    link: str,
    auto_posted: bool,
    conversation_id: str = "",
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO posts (
                topic, title, body, region, tone, persona, length, subreddit, link, auto_posted, timestamp, conversation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic,
                title,
                body,
                region,
                tone,
                persona,
                length,
                subreddit,
                link,
                int(auto_posted),
                datetime.utcnow().isoformat(),
                conversation_id,
            ),
        )
        conn.commit()


def fetch_recent_posts(limit: int = 50) -> List[Tuple]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT topic, title, subreddit, link, upvotes, comments, timestamp
            FROM posts
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def fetch_style_samples(limit: int = 5) -> List[Tuple[str, str, str, str]]:
    """Return the most recent posts for style profiling."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT title, body, tone, persona
            FROM posts
            WHERE body IS NOT NULL AND TRIM(body) <> ''
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def fetch_posts_for_date(date_iso: str) -> List[Tuple]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT topic, title, subreddit, link, upvotes, comments, timestamp
            FROM posts
            WHERE DATE(timestamp) = ?
            ORDER BY timestamp DESC
            """,
            (date_iso,),
        ).fetchall()


def fetch_all_posts() -> Sequence[Tuple]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT id, topic, title, body, region, tone, persona, length, subreddit, link, upvotes, comments, timestamp
            FROM posts
            ORDER BY timestamp DESC
            """
        ).fetchall()


def fetch_stats() -> Tuple[int, int, int]:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        today = conn.execute(
            "SELECT COUNT(*) FROM posts WHERE DATE(timestamp) = DATE('now', 'localtime')"
        ).fetchone()[0]
        auto = conn.execute("SELECT COUNT(*) FROM posts WHERE auto_posted = 1").fetchone()[0]
    return total, today, auto


def iter_posts_for_refresh() -> Iterable[Tuple[int, str]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, link FROM posts WHERE link LIKE 'https://www.reddit.com%'"
        ).fetchall()
    for row in rows:
        yield row


def update_metrics(updates: Iterable[Tuple[int, int, int]]) -> None:
    with get_conn() as conn:
        conn.executemany(
            "UPDATE posts SET upvotes = ?, comments = ? WHERE id = ?",
            [(score, comments, post_id) for post_id, score, comments in updates],
        )
        conn.commit()


# Conversation Memory Functions

def create_conversation(conversation_id: str, title: str, persona: str, tone: str) -> None:
    """Create a new conversation thread."""
    with get_conn() as conn:
        now = datetime.utcnow().isoformat()
        conn.execute(
            """
            INSERT INTO conversations (id, title, created_at, updated_at, persona, tone)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, title, now, now, persona, tone),
        )
        conn.commit()


def add_message(conversation_id: str, role: str, content: str, metadata: str = "") -> None:
    """Add a message to a conversation."""
    with get_conn() as conn:
        now = datetime.utcnow().isoformat()
        conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, role, content, now, metadata),
        )
        conn.commit()


def get_conversation_history(conversation_id: str, limit: int = 50) -> List[Tuple[str, str, str, str]]:
    """Get conversation history for memory context."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT role, content, timestamp, metadata
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
            """,
            (conversation_id, limit),
        ).fetchall()


def get_recent_conversations(limit: int = 10) -> List[Tuple[str, str, str, str, str]]:
    """Get recent conversations for UI display."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT id, title, persona, tone, updated_at
            FROM conversations
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def update_conversation_timestamp(conversation_id: str) -> None:
    """Update conversation's last updated timestamp."""
    with get_conn() as conn:
        now = datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        conn.commit()


def get_memory_context(persona: str, limit: int = 10) -> List[Tuple[str, str, str]]:
    """Get memory context from recent conversations for personalization."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT c.title, m.content, m.timestamp
            FROM conversations c
            JOIN messages m ON c.id = m.conversation_id
            WHERE c.persona = ? AND m.role = 'assistant'
            ORDER BY m.timestamp DESC
            LIMIT ?
            """,
            (persona, limit),
        ).fetchall()
