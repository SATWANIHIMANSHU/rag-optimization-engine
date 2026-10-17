from sentence_transformers import CrossEncoder


# Load reranker model once
model = CrossEncoder(
    "BAAI/bge-reranker-base"
)


def rerank(question, documents):

    pairs = [
        [question, document]
        for document in documents
    ]

    scores = model.predict(pairs)

    results = list(zip(documents, scores))

    # Higher score = more relevant
    results.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return results