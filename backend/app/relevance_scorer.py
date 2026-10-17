def calculate_final_score(
    reranker_score,
    query_coverage
):
    """
    Combine semantic relevance from the reranker
    with keyword coverage from the query.
    """

    final_score = (
        0.7 * reranker_score
        +
        0.3 * query_coverage
    )

    return final_score