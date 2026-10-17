from pathlib import Path
import sqlite3

DATABASE_PATH = Path("data/rag.db")

DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            pages INTEGER DEFAULT 0,
            size INTEGER DEFAULT 0,
            status TEXT DEFAULT 'processing',
            chunks INTEGER DEFAULT 0,
            tables_count INTEGER DEFAULT 0,
            figures INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    init_database()
    print(f"Database initialized: {DATABASE_PATH}")