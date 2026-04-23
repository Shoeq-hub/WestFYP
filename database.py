import sqlite3
import os
#w2096743

DB_FILE = "learning_curator.db"


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    NOT NULL UNIQUE,
            password_hash TEXT  NOT NULL,
            is_admin    INTEGER NOT NULL DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS resources (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id TEXT    NOT NULL UNIQUE,
            title       TEXT    NOT NULL,
            source      TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            keywords    TEXT    NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'pending',
            submitted_by INTEGER REFERENCES users(id),
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            resource_id INTEGER NOT NULL REFERENCES resources(id),
            rating      INTEGER NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, resource_id)
        );

        CREATE TABLE IF NOT EXISTS history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            resource_id INTEGER NOT NULL REFERENCES resources(id),
            viewed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bookmarks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            resource_id INTEGER NOT NULL REFERENCES resources(id),
            saved_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, resource_id)
        );

        CREATE TABLE IF NOT EXISTS reset_requests (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Database ready: {DB_FILE}")


if __name__ == "__main__":
    init_db()
