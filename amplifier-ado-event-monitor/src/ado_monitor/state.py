"""State Store - SQLite-based persistence for snapshots and events.

Provides crash recovery and event deduplication. Uses SQLite for atomic
operations and queryable event history.
"""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import Event, EventType, Snapshot


class StateStore:
    """SQLite-based state persistence for the event monitor."""

    def __init__(self, db_path: Path | str = "ado_monitor.db") -> None:
        """Initialize the state store.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Create database tables if they don't exist."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    subscription_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    polled_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscription_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    author TEXT,
                    created_at TEXT NOT NULL,
                    processed_at TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    UNIQUE(subscription_id, event_type, payload)
                );

                CREATE INDEX IF NOT EXISTS idx_events_subscription
                ON events(subscription_id);

                CREATE INDEX IF NOT EXISTS idx_events_status
                ON events(status);
            """)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_snapshot(self, subscription_id: str) -> Snapshot | None:
        """Get the last stored snapshot for a subscription.

        Args:
            subscription_id: The subscription to look up

        Returns:
            The stored Snapshot or None if not found
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data, polled_at FROM snapshots WHERE subscription_id = ?",
                (subscription_id,),
            ).fetchone()

            if row is None:
                return None

            return Snapshot(
                subscription_id=subscription_id,
                data=json.loads(row["data"]),
                polled_at=datetime.fromisoformat(row["polled_at"]),
            )

    def save_snapshot(self, snapshot: Snapshot) -> None:
        """Save a snapshot, replacing any existing one for the subscription.

        Args:
            snapshot: The snapshot to save
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO snapshots (subscription_id, data, polled_at)
                VALUES (?, ?, ?)
                """,
                (
                    snapshot.subscription_id,
                    json.dumps(snapshot.data),
                    snapshot.polled_at.isoformat(),
                ),
            )

    def record_event(self, event: Event) -> int | None:
        """Record an event, returning its ID if new (None if duplicate).

        Uses payload hash to deduplicate events.

        Args:
            event: The event to record

        Returns:
            Event ID if newly inserted, None if duplicate
        """
        with self._connect() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO events
                        (subscription_id, event_type, payload, author, created_at, status)
                    VALUES (?, ?, ?, ?, ?, 'pending')
                    """,
                    (
                        event.subscription_id,
                        event.event_type.value,
                        json.dumps(event.payload, sort_keys=True),
                        event.author,
                        event.created_at.isoformat(),
                    ),
                )
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # Duplicate event
                return None

    def get_pending_events(self, subscription_id: str | None = None) -> list[Event]:
        """Get all pending events, optionally filtered by subscription.

        Args:
            subscription_id: Optional filter for specific subscription

        Returns:
            List of pending events
        """
        with self._connect() as conn:
            if subscription_id:
                rows = conn.execute(
                    """
                    SELECT id, subscription_id, event_type, payload, author, created_at
                    FROM events WHERE status = 'pending' AND subscription_id = ?
                    ORDER BY created_at
                    """,
                    (subscription_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, subscription_id, event_type, payload, author, created_at
                    FROM events WHERE status = 'pending'
                    ORDER BY created_at
                    """,
                ).fetchall()

            return [self._row_to_event(row) for row in rows]

    def mark_event_processed(
        self, event_id: int, status: str = "done", error: str | None = None
    ) -> None:
        """Mark an event as processed.

        Args:
            event_id: The event ID to update
            status: New status ('done', 'failed', 'skipped')
            error: Optional error message for failed events
        """
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE events
                SET status = ?, processed_at = ?
                WHERE id = ?
                """,
                (status, datetime.now(UTC).isoformat(), event_id),
            )

    def get_event_history(
        self,
        subscription_id: str,
        limit: int = 100,
        include_pending: bool = False,
    ) -> list[dict[str, Any]]:
        """Get event history for debugging.

        Args:
            subscription_id: The subscription to query
            limit: Maximum events to return
            include_pending: Whether to include pending events

        Returns:
            List of event records as dicts
        """
        with self._connect() as conn:
            status_filter = "" if include_pending else "AND status != 'pending'"
            rows = conn.execute(
                f"""
                SELECT id, event_type, payload, author, created_at, processed_at, status
                FROM events
                WHERE subscription_id = ? {status_filter}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (subscription_id, limit),
            ).fetchall()

            return [dict(row) for row in rows]

    def _row_to_event(self, row: sqlite3.Row) -> Event:
        """Convert a database row to an Event object."""
        return Event(
            event_type=EventType(row["event_type"]),
            subscription_id=row["subscription_id"],
            payload=json.loads(row["payload"]),
            author=row["author"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
