"""
database.py — Persistence Layer
===========================================
Pure, stateless functions for all SQLite interactions.
Every SQL statement uses parameter bindings (? placeholders) — never
string interpolation — to eliminate SQL injection vulnerabilities.

All functions accept an explicit `db_name` argument so they remain
fully testable in isolation without touching global state.

Typical usage:
    from config import DB_NAME
    from database.db_manager import init_db, save_summary, \
        get_summaries_by_category, get_summary_by_id

    init_db(DB_NAME)
    save_summary(DB_NAME, "report.pdf", "Quarterly review...", 4, "finance")
    rows = get_summaries_by_category(DB_NAME, "finance")
    row  = get_summary_by_id(DB_NAME, 1)
"""

import sqlite3
from typing import Optional


def _connect(db_name: str) -> sqlite3.Connection:
    """
    Open a connection to *db_name* with two quality-of-life settings:
    - Row factory: rows behave like dicts (column access by name).
    - Foreign keys: enforced at the connection level (SQLite default is OFF).
    """
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_name: str) -> None:
    """
    Create the `summaries` table if it does not already exist.

    Schema
    ------
    id         INTEGER  Primary key, auto-incremented by SQLite.
    filename   TEXT     Source file the summary was generated from. Required.
    summary    TEXT     Full generated summary text. Required.
    rating     INTEGER  Numeric quality/relevance rating (e.g. 1-5).
    category   TEXT     Tier/topic label used for filtered retrieval.
    created_at TEXT     ISO-8601 timestamp, set automatically on insert.

    Safe to call multiple times — CREATE TABLE IF NOT EXISTS is idempotent.
    """
    ddl = """
        CREATE TABLE IF NOT EXISTS summaries (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            filename   TEXT    NOT NULL,
            summary    TEXT    NOT NULL,
            rating     INTEGER,
            category   TEXT,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """
    with _connect(db_name) as conn:
        conn.execute(ddl)
        conn.commit()


def save_summary(
    db_name: str,
    filename: str,
    summary: str,
    rating: int,
    category: str,
) -> int:
    """
    Insert one summary record and return its auto-assigned primary key.

    Parameters
    ----------
    db_name  : Path / name of the SQLite database file.
    filename : Name of the source document (e.g. "q3_report.pdf").
    summary  : Generated summary text to persist.
    rating   : Numeric score assigned to the summary (e.g. 1-5).
    category : Tier label for grouping (e.g. "finance", "legal").

    Returns
    -------
    int  The `id` of the newly inserted row.
    """
    sql = """
        INSERT INTO summaries (filename, summary, rating, category)
        VALUES (?, ?, ?, ?)
    """
    with _connect(db_name) as conn:
        cursor = conn.execute(sql, (filename, summary, rating, category))
        conn.commit()
        return cursor.lastrowid


def get_summaries_by_category(
    db_name: str,
    category: str,
) -> list[sqlite3.Row]:
    """
    Return every summary row whose `category` matches the given tier label,
    ordered newest-first.

    Parameters
    ----------
    db_name  : Path / name of the SQLite database file.
    category : Exact tier label to filter by (case-sensitive).

    Returns
    -------
    list[sqlite3.Row]
        Possibly empty list of rows. Each row supports both index access
        (row[0]) and key access (row["filename"]) via the Row factory.
    """
    sql = """
        SELECT id, filename, summary, rating, category, created_at
        FROM   summaries
        WHERE  category = ?
        ORDER  BY created_at DESC
    """
    with _connect(db_name) as conn:
        cursor = conn.execute(sql, (category,))
        return cursor.fetchall()


def get_summary_by_id(
    db_name: str,
    summary_id: int,
) -> Optional[sqlite3.Row]:
    """
    Return the single summary row matching the given primary key, or None
    if no such row exists.

    Parameters
    ----------
    db_name    : Path / name of the SQLite database file.
    summary_id : Integer primary key of the target row.

    Returns
    -------
    sqlite3.Row | None
        The matched row (key-accessible), or None when not found.
    """
    sql = """
        SELECT id, filename, summary, rating, category, created_at
        FROM   summaries
        WHERE  id = ?
    """
    with _connect(db_name) as conn:
        cursor = conn.execute(sql, (summary_id,))
        return cursor.fetchone()