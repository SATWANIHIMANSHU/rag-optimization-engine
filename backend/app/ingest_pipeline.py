from pathlib import Path

from backend.app.ingest import load_documents
from backend.app.document_processor import process_pdf
from backend.app.multimodal_chunker import (
    create_multimodal_chunks
)
from backend.app.vector_store import (
    store_chunks,
    reset_collection
)


DOCUMENTS_DIR = Path(
    "data/documents"
)


def ingest_file(file_path):

    file_path = Path(file_path)

    print()
    print("=" * 50)
    print(
        f"Processing: {file_path.name}"
    )
    print("=" * 50)

    # --------------------------------------------------
    # PDF
    # --------------------------------------------------

    if file_path.suffix.lower() == ".pdf":

        processed = process_pdf(
            file_path
        )

        chunks = create_multimodal_chunks(
            processed
        )

        store_chunks(
            chunks
        )

        print(
            f"Text + tables + figures processed."
        )

        print(
            f"Total chunks: {len(chunks)}"
        )

        print(
            f"Tables: "
            f"{len(processed['tables'])}"
        )

        print(
            f"Figures: "
            f"{len(processed['figures'])}"
        )

        return {
            "source": file_path.name,
            "chunks": len(chunks),
            "tables": len(
                processed["tables"]
            ),
            "figures": len(
                processed["figures"]
            ),
            "status": "indexed"
        }

    # --------------------------------------------------
    # TXT
    # --------------------------------------------------

    elif file_path.suffix.lower() == ".txt":

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            text = file.read()

        from backend.app.chunker import (
            create_chunks
        )

        text_chunks = create_chunks(
            text
        )

        chunks = []

        for index, chunk in enumerate(
            text_chunks
        ):

            chunks.append({
                "text": chunk,
                "type": "text",
                "source": file_path.name,
                "element_id": (
                    f"text_{index}"
                )
            })

        store_chunks(
            chunks
        )

        return {
            "source": file_path.name,
            "chunks": len(chunks),
            "tables": 0,
            "figures": 0,
            "status": "indexed"
        }

    else:

        raise ValueError(
            "Only PDF and TXT files are supported."
        )


def ingest_all_documents():

    documents = load_documents()

    print(
        f"Documents found: "
        f"{len(documents)}"
    )

    for document in documents:

        source = document["source"]

        file_path = (
            DOCUMENTS_DIR /
            source
        )

        ingest_file(
            file_path
        )


if __name__ == "__main__":

    reset_collection()

    ingest_all_documents()