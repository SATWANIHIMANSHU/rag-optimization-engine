from pathlib import Path

from backend.app.database import get_connection


DOCUMENTS_DIR = Path("data/documents")


def migrate_documents():
    connection = get_connection()
    cursor = connection.cursor()

    if not DOCUMENTS_DIR.exists():
        print("Documents directory does not exist.")
        connection.close()
        return

    files = [
        file_path
        for file_path in DOCUMENTS_DIR.iterdir()
        if file_path.is_file()
        and file_path.suffix.lower() in [".pdf", ".txt"]
    ]

    for file_path in files:

        existing = cursor.execute(
            """
            SELECT id
            FROM documents
            WHERE user_id = ?
            AND filename = ?
            """,
            (1, file_path.name)
        ).fetchone()

        if existing:
            print(f"Already exists: {file_path.name}")
            continue

        cursor.execute(
            """
            INSERT INTO documents (
                user_id,
                filename,
                original_name,
                size,
                status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                1,
                file_path.name,
                file_path.name,
                file_path.stat().st_size,
                "indexed"
            )
        )

        print(f"Added: {file_path.name}")

    connection.commit()
    connection.close()

    print("Document migration completed.")


if __name__ == "__main__":
    migrate_documents()