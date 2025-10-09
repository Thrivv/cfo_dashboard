"""Database utilities for the CFO dashboard."""

import os
import sqlite3
from typing import Dict, List

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chat_history.db")


def init_database():
    """Initialize database with chat history table only."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS chat_history")

    cursor.execute(
        """
        CREATE TABLE chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    conn.commit()
    conn.close()


def save_chat_message(message: str, response: str = None):
    """Save chat message to database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT message, response FROM chat_history LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("DROP TABLE IF EXISTS chat_history")
        cursor.execute(
            """
            CREATE TABLE chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        conn.commit()

    cursor.execute(
        """
        INSERT INTO chat_history (message, response)
        VALUES (?, ?)
    """,
        (message, response),
    )

    conn.commit()
    conn.close()


def get_chat_history(limit: int = 50) -> List[Dict]:
    """Get chat history."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT message, response, created_at
            FROM chat_history
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        history = []
        for row in cursor.fetchall():
            history.append(
                {"message": row[0], "response": row[1], "created_at": row[2]}
            )

        conn.close()
        return history

    except sqlite3.OperationalError:
        conn.close()
        return []


if __name__ == "__main__":
    init_database()
    print("Chat database initialized")
