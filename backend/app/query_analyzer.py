def analyze_query(question):
    """
    Analyze question complexity and determine:
    1. How many text chunks should initially be retrieved.
    2. Whether visual retrieval is useful.
    """

    words = question.split()
    word_count = len(words)

    question_lower = question.lower()

    # --------------------------------------------------
    # Complexity detection
    # --------------------------------------------------

    complexity_words = [
        "compare",
        "difference",
        "differences",
        "explain",
        "analyze",
        "analysis",
        "relationship",
        "advantages",
        "disadvantages",
        "all",
        "multiple"
    ]

    multi_part_words = [
        " and ",
        " also ",
        " as well as ",
        "along with"
    ]

    complexity_score = 0

    if word_count > 20:
        complexity_score += 2

    elif word_count > 10:
        complexity_score += 1

    for word in complexity_words:
        if word in question_lower:
            complexity_score += 2

    for phrase in multi_part_words:
        if phrase in question_lower:
            complexity_score += 1

    # --------------------------------------------------
    # Determine complexity
    # --------------------------------------------------

    if complexity_score >= 3:

        complexity = "complex"
        top_k = 10

    elif complexity_score >= 1:

        complexity = "medium"
        top_k = 5

    else:

        complexity = "simple"
        top_k = 3

    # --------------------------------------------------
    # Visual query detection
    # --------------------------------------------------

    visual_keywords = [
        "figure",
        "fig.",
        "diagram",
        "architecture",
        "flowchart",
        "chart",
        "graph",
        "plot",
        "image",
        "illustration",
        "shown",
        "shown in",
        "visual",
        "block diagram",
        "structure",
        "layout"
    ]

    needs_visual = any(
        keyword in question_lower
        for keyword in visual_keywords
    )

    # --------------------------------------------------
    # Return analysis
    # --------------------------------------------------

    return {
        "complexity": complexity,
        "top_k": top_k,
        "needs_visual": needs_visual
    }