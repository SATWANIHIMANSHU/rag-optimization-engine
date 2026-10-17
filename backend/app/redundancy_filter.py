import ollama


def remove_redundant_chunks(
    documents,
    metadata,
    scores,
    similarity_threshold=0.95
):
    """
    Remove chunks that contain highly similar information.

    Higher similarity means the chunks are more likely
    to contain redundant information.
    """

    if not documents:
        return [], [], []

    # Create embeddings for all documents
    response = ollama.embed(
        model="nomic-embed-text",
        input=documents
    )

    embeddings = response["embeddings"]

    selected_documents = []
    selected_metadata = []
    selected_scores = []
    selected_embeddings = []

    for i, embedding in enumerate(embeddings):

        is_redundant = False

        for selected_embedding in selected_embeddings:

            similarity = cosine_similarity(
                embedding,
                selected_embedding
            )

            if similarity >= similarity_threshold:

                is_redundant = True
                break

        if not is_redundant:

            selected_documents.append(
                documents[i]
            )

            selected_metadata.append(
                metadata[i]
            )

            selected_scores.append(
                scores[i]
            )

            selected_embeddings.append(
                embedding
            )

    return (
        selected_documents,
        selected_metadata,
        selected_scores
    )


def cosine_similarity(vector_a, vector_b):

    dot_product = sum(
        a * b
        for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = sum(
        a * a
        for a in vector_a
    ) ** 0.5

    magnitude_b = sum(
        b * b
        for b in vector_b
    ) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0

    return dot_product / (
        magnitude_a * magnitude_b
    )