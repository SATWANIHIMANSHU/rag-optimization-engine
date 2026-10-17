from backend.app.query_decomposer import decompose_query


def get_retrieval_plan(question):
    """
    Determine which retrieval modalities should be executed
    for a user question.
    """

    analysis = decompose_query(question)

    route = analysis.get("route", "text")
    sub_queries = analysis.get("sub_queries", [])

    run_text = route in {"text", "hybrid"}
    run_visual = route in {"visual", "hybrid"}

    return {
        "route": route,
        "run_text": run_text,
        "run_visual": run_visual,
        "sub_queries": sub_queries
    }