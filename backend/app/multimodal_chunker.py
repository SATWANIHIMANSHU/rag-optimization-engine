from backend.app.chunker import create_chunks


def create_multimodal_chunks(processed_document):
    """
    Convert Docling output into RAG-ready chunks.
    """

    chunks = []

    source = processed_document["source"]

    markdown = processed_document.get(
        "markdown",
        ""
    )

    # --------------------------------------------------
    # TEXT
    # --------------------------------------------------

    text_chunks = create_chunks(markdown)

    for index, chunk in enumerate(text_chunks):

        chunks.append({
            "text": chunk,
            "type": "text",
            "source": source,
            "element_id": f"text_{index}"
        })

    # --------------------------------------------------
    # TABLES
    # --------------------------------------------------

    tables = processed_document.get(
        "tables",
        []
    )

    for table in tables:

        table_text = table.get(
            "markdown",
            ""
        )

        if not table_text.strip():
            continue

        chunks.append({
            "text": (
                f"Table {table['index']} "
                f"from {source}:\n\n"
                f"{table_text}"
            ),
            "type": "table",
            "source": source,
            "element_id": (
                f"table_{table['index']}"
            )
        })

    # --------------------------------------------------
    # FIGURES
    # --------------------------------------------------

    figures = processed_document.get(
        "figures",
        []
    )

    for figure in figures:

        figure_number = figure["index"]

        chunks.append({
            "text": (
                f"Figure {figure_number} "
                f"from {source}.\n"
                f"Figure image available at: "
                f"{figure['path']}"
            ),
            "type": "figure",
            "source": source,
            "element_id": (
                f"figure_{figure_number}"
            )
        })

    return chunks