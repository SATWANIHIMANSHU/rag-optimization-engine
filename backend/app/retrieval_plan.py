from backend.app.adaptive_router import get_retrieval_plan


def build_retrieval_plan(question):
    """
    Build separate text and visual queries from the
    adaptive routing decision.
    """

    routing = get_retrieval_plan(question)

    text_queries = []
    visual_queries = []

    for sub_query in routing["sub_queries"]:

        query = sub_query.get("query", "").strip()
        query_type = sub_query.get("type", "").lower()

        if not query:
            continue

        if query_type == "text":
            text_queries.append(query)

        elif query_type == "visual":
            visual_queries.append(query)

    return {
        "route": routing["route"],
        "run_text": routing["run_text"],
        "run_visual": routing["run_visual"],
        "text_queries": text_queries,
        "visual_queries": visual_queries
    }