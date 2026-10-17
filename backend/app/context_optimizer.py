from transformers import AutoTokenizer


# --------------------------------------------------
# Load Qwen tokenizer
# --------------------------------------------------

tokenizer = AutoTokenizer.from_pretrained(
    "Qwen/Qwen3-1.7B"
)


# --------------------------------------------------
# Count tokens
# --------------------------------------------------

def count_tokens(text):
    """
    Count the actual number of tokens
    using the Qwen tokenizer.
    """

    tokens = tokenizer.encode(
        text,
        add_special_tokens=False
    )

    return len(tokens)


# --------------------------------------------------
# Calculate available retrieval budget
# --------------------------------------------------

def calculate_available_budget(
    model_context_limit,
    prompt_tokens,
    question_tokens,
    answer_reserve
):
    """
    Calculate how many tokens are available
    for retrieved document context.
    """

    available_budget = (
        model_context_limit
        - prompt_tokens
        - question_tokens
        - answer_reserve
    )

    # Never allow a negative budget
    return max(0, available_budget)


# --------------------------------------------------
# Optimize context
# --------------------------------------------------

def optimize_context(
    documents,
    metadata,
    scores,
    max_chunks=5,
    max_tokens=1000
):
    """
    Select the highest-ranked chunks while respecting:

    1. Final Top-N
    2. Token budget

    Returns:

    selected documents
    selected metadata
    selected scores
    total tokens used
    """

    if not documents:
        return [], [], [], 0


    # --------------------------------------------------
    # Keep document, metadata and score together
    # --------------------------------------------------

    results = list(zip(
        documents,
        metadata,
        scores
    ))


    # --------------------------------------------------
    # Sort by reranker score
    # --------------------------------------------------

    results.sort(
        key=lambda x: x[2],
        reverse=True
    )


    selected_documents = []
    selected_metadata = []
    selected_scores = []

    total_tokens = 0


    # --------------------------------------------------
    # Select chunks
    # --------------------------------------------------

    for document, metadata_item, score in results:

        # Stop when Top-N is reached
        if len(selected_documents) >= max_chunks:
            break


        # Count actual tokens
        chunk_tokens = count_tokens(
            document
        )


        # Check token budget
        if total_tokens + chunk_tokens > max_tokens:

            # Skip this chunk and check the next one
            continue


        # Keep chunk
        selected_documents.append(
            document
        )

        selected_metadata.append(
            metadata_item
        )

        selected_scores.append(
            score
        )

        total_tokens += chunk_tokens


    return (
        selected_documents,
        selected_metadata,
        selected_scores,
        total_tokens
    )