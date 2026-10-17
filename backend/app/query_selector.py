import re


# Common words that don't provide much information
STOP_WORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "do",
    "does",
    "did",
    "how",
    "what",
    "when",
    "where",
    "why",
    "who",
    "which",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "for",
    "from",
    "with",
    "get",
    "gets",
    "can",
    "could",
    "would",
    "should"
}


def extract_keywords(text):

    words = re.findall(
        r"\b[a-zA-Z0-9]+\b",
        text.lower()
    )

    keywords = [
        word
        for word in words
        if word not in STOP_WORDS
        and len(word) > 2
    ]

    return set(keywords)


def calculate_query_coverage(
    question,
    document
):

    question_keywords = extract_keywords(question)

    document_words = extract_keywords(document)

    if not question_keywords:
        return 0.0

    matched_words = (
        question_keywords
        & document_words
    )

    coverage = (
        len(matched_words)
        / len(question_keywords)
    )

    return coverage