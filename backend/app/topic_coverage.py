import re


STOP_WORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "what",
    "how",
    "when",
    "where",
    "why",
    "who",
    "which",
    "do",
    "does",
    "did",
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
    "policy",
    "policies"
}


def extract_keywords(text):

    words = re.findall(
        r"\b[a-zA-Z0-9]+\b",
        text.lower()
    )

    return {
        word
        for word in words
        if word not in STOP_WORDS
        and len(word) > 2
    }


def find_question_topics(question):

    keywords = extract_keywords(question)

    topics = []

    # Detect common multi-word topics
    if "annual" in keywords and "leave" in question.lower():
        topics.append("annual leave")

    if "sick" in keywords and "leave" in question.lower():
        topics.append("sick leave")

    if "maternity" in keywords and "leave" in question.lower():
        topics.append("maternity leave")

    return topics


def calculate_topic_coverage(
    question,
    document
):

    topics = find_question_topics(question)

    document_lower = document.lower()

    covered_topics = []

    for topic in topics:

        if topic in document_lower:

            covered_topics.append(topic)

    if not topics:
        return 1.0

    return (
        len(covered_topics)
        / len(topics)
    )