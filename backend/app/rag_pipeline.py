import re
from pathlib import Path

import chromadb
import ollama

from groq import Groq
from dotenv import load_dotenv

from backend.app.reranker import rerank
from backend.app.redundancy_filter import remove_redundant_chunks

from backend.app.context_optimizer import (
    optimize_context,
    count_tokens,
    calculate_available_budget
)

from backend.app.figure_analyzer import analyze_figure

# --------------------------------------------------
# Connect to ChromaDB
# --------------------------------------------------

chroma_client = chromadb.PersistentClient(
    path="./data/chroma"
)

collection = chroma_client.get_collection(
    name="documents"
)


# --------------------------------------------------
# Connect to Groq
# --------------------------------------------------

load_dotenv()

groq_client = Groq()


# --------------------------------------------------
# Configuration
# --------------------------------------------------

RETRIEVE_K = 10

FINAL_TOP_N = 5

MODEL_CONTEXT_LIMIT = 8192

ANSWER_RESERVE = 1000

GROQ_MODEL = "openai/gpt-oss-20b"

def fix_text_encoding(text):
    """
    Fix common UTF-8 / Windows-1252 mojibake.
    """

    if not text:
        return text

    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text

# --------------------------------------------------
# Detect Figure / Table references
# --------------------------------------------------

def extract_element_reference(question):
    """
    Detect references such as:
    Figure 2
    Fig. 2
    Table 2
    Algorithm 1
    """

    question_lower = question.lower()

    # Figure 2 / Fig. 2 / Figure2
    match = re.search(
        r"\b(?:figure|fig\.?)\s*(\d+)\b",
        question_lower
    )

    if match:
        return f"figure_{match.group(1)}"

    # Table 2
    match = re.search(
        r"\btable\s*(\d+)\b",
        question_lower
    )

    if match:
        return f"table_{match.group(1)}"

    # Algorithm 1
    match = re.search(
        r"\balgorithm\s*(\d+)\b",
        question_lower
    )

    if match:
        return f"algorithm_{match.group(1)}"

    return None



def get_figure_image_path(source, element_id):
    """
    Convert a figure metadata entry into its extracted image path.
    """

    if not source or not element_id:
        return None

    if not element_id.startswith("figure_"):
        return None

    source_name = Path(source).stem
    image_path = (
        Path("data")
        / "processed"
        / source_name
        / f"{element_id}.png"
    )

    if image_path.exists():
        return str(image_path)

    return None
# --------------------------------------------------
# Keyword / Exact-Term Boost
# --------------------------------------------------

def keyword_boost(
    question,
    documents,
    metadatas,
    boost=0.15
):
    question_lower = question.lower()

    words = re.findall(
        r"\b[a-zA-Z0-9][a-zA-Z0-9_-]*\b",
        question_lower
    )

    stop_words = {
        "what",
        "does",
        "do",
        "is",
        "are",
        "the",
        "a",
        "an",
        "of",
        "in",
        "on",
        "for",
        "to",
        "and",
        "or",
        "how",
        "why",
        "where",
        "which",
        "show",
        "explain",
        "tell",
        "about",
        "this",
        "that"
    }

    keywords = [
        word
        for word in words
        if word not in stop_words
        and len(word) > 1
    ]

    boosted = []

    for document, metadata in zip(
        documents,
        metadatas
    ):

        text_lower = document.lower()

        matches = sum(
            1
            for keyword in keywords
            if keyword in text_lower
        )

        score = matches * boost

        boosted.append({
            "document": document,
            "metadata": metadata,
            "keyword_score": score
        })

    boosted.sort(
        key=lambda x: x["keyword_score"],
        reverse=True
    )

    return boosted
# --------------------------------------------------
# Build RAG Context
# --------------------------------------------------

def build_text_context(
    question,
    sources=None,
    use_reranker=True,
    use_redundancy_filter=True,
    use_context_optimizer=True
):

    # --------------------------------------------------
    # 1. Create query embedding
    # --------------------------------------------------

    response = ollama.embed(
        model="nomic-embed-text",
        input=question
    )

    query_embedding = response["embeddings"][0]


    # --------------------------------------------------
    # 2. Semantic Retrieval
    # --------------------------------------------------

    query_kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": RETRIEVE_K
    }

    # Restrict retrieval to selected documents
    if sources:

        query_kwargs["where"] = {
            "source": {
                "$in": sources
            }
        }

    results = collection.query(
        **query_kwargs
    )


    semantic_documents = results["documents"][0]
    semantic_metadatas = results["metadatas"][0]
    semantic_distances = results["distances"][0]


    # --------------------------------------------------
    # 3. Check semantic retrieval
    # --------------------------------------------------

    if not semantic_documents:

        return [], [], [], 0, 0


    # --------------------------------------------------
    # 4. Targeted Figure / Table Retrieval
    # --------------------------------------------------

    element_reference = extract_element_reference(
        question
    )

    documents = list(semantic_documents)
    metadatas = list(semantic_metadatas)
    distances = list(semantic_distances)

    if element_reference:

        element_where = {
            "element_id": element_reference
        }

        if sources:

            element_where = {
                "$and": [
                    {
                        "source": {
                            "$in": sources
                        }
                    },
                    {
                        "element_id": element_reference
                    }
                ]
            }

        element_results = collection.get(
            where=element_where,
            include=[
                "documents",
                "metadatas"
            ]
        )

        targeted_documents = (
            element_results.get("documents")
            or []
        )

        targeted_metadatas = (
            element_results.get("metadatas")
            or []
        )

        # Put targeted figure/table first.
        # Avoid duplicate documents.
        for document, metadata in zip(
            targeted_documents,
            targeted_metadatas
        ):

            if document not in documents:

                documents.insert(
                    0,
                    document
                )

                metadatas.insert(
                    0,
                    metadata
                )

                distances.insert(
                    0,
                    0.0
                )



      # --------------------------------------------------
    # 5. Visual Figure Analysis
    # --------------------------------------------------

    if element_reference and element_reference.startswith("figure_"):

        visual_descriptions = []

        for document, metadata in zip(
            documents,
            metadatas
        ):
            if metadata.get("element_id") != element_reference:
                continue

            source = metadata.get("source")

            image_path = get_figure_image_path(
                source,
                element_reference
            )

            if not image_path:
                continue

            print(
                f"Analyzing {element_reference} visually: "
                f"{image_path}"
            )

            try:
                description = analyze_figure(
                    image_path,
                    question
                )

                if description:
                    visual_descriptions.append(
                        description
                    )

            except Exception as e:
                print(
                    f"Figure analysis failed: {e}"
                )

        # Add visual description to RAG context
        for description in visual_descriptions:

            visual_document = (
                f"Visual analysis of "
                f"{element_reference}:\n"
                f"{description}"
            )

            documents.insert(
                0,
                visual_document
            )

            metadatas.insert(
                0,
                {
                    "source": sources[0]
                    if sources and len(sources) == 1
                    else "visual_analysis",
                    "type": "figure_visual",
                    "element_id": element_reference
                }
            )

            distances.insert(
                0,
                0.0
            )
    # --------------------------------------------------
    # 5. Keyword / Exact-Term Boost
    # --------------------------------------------------

    keyword_results = keyword_boost(
        question,
        documents,
        metadatas
    )

    documents = [
        item["document"]
        for item in keyword_results
    ]

    metadatas = [
        item["metadata"]
        for item in keyword_results
    ]


    # --------------------------------------------------
    # 6. Rerank Candidates
    # --------------------------------------------------

    # reranked = rerank(
    #     question,
    #     documents
    # )

    if use_reranker:
        reranked = rerank(question, documents)
    else:
        # Preserve the current candidate order.
        reranked = [
            (document, 0.0)
            for document in documents
        ]


    # --------------------------------------------------
    # 7. Connect Metadata to Documents
    # --------------------------------------------------

    document_info = {}

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):

        document_info[document] = (
            metadata,
            distance
        )


    reranked_documents = []
    reranked_metadata = []
    reranked_scores = []

    for document, score in reranked:

        if document not in document_info:
            continue

        metadata, distance = (
            document_info[document]
        )

        reranked_documents.append(
            document
        )

        reranked_metadata.append(
            metadata
        )

        reranked_scores.append(
            float(score)
        )


    # --------------------------------------------------
    # 8. Remove Redundant Chunks
    # --------------------------------------------------

    
    # 8. Remove Redundant Chunks (optional)
    if use_redundancy_filter:
        (
            unique_documents,
            unique_metadata,
            unique_scores
        ) = remove_redundant_chunks(
            reranked_documents,
            reranked_metadata,
            reranked_scores
        )
    else:
        unique_documents = reranked_documents
        unique_metadata = reranked_metadata
        unique_scores = reranked_scores



    # --------------------------------------------------
    # 9. Calculate Token Budget
    # --------------------------------------------------

    prompt_instructions = """
Answer the question using ONLY the provided context.

If the answer is not present in the context,
say:

"I don't know based on the provided documents."
"""

    prompt_tokens = count_tokens(
        prompt_instructions
    )

    question_tokens = count_tokens(
        question
    )

    available_budget = calculate_available_budget(
        model_context_limit=MODEL_CONTEXT_LIMIT,
        prompt_tokens=prompt_tokens,
        question_tokens=question_tokens,
        answer_reserve=ANSWER_RESERVE
    )


  
    # 10. Final Context Optimization (optional)
    if use_context_optimizer:
        (
            final_documents,
            final_metadata,
            final_scores,
            tokens_used
        ) = optimize_context(
            unique_documents,
            unique_metadata,
            unique_scores,
            max_chunks=FINAL_TOP_N,
            max_tokens=available_budget
        )
    else:
        final_documents = unique_documents
        final_metadata = unique_metadata
        final_scores = unique_scores
        tokens_used = sum(
            count_tokens(document)
            for document in final_documents
        )


    return (
        final_documents,
        final_metadata,
        final_scores,
        tokens_used,
        available_budget
    )




def build_baseline_context(question, sources=None):
    """
    Baseline RAG:
    - Query embedding
    - Semantic retrieval from ChromaDB
    - No keyword boosting
    - No reranking
    - No redundancy filtering
    - No context optimization
    - No targeted figure/table retrieval
    """

    response = ollama.embed(
        model="nomic-embed-text",
        input=question
    )

    query_embedding = response["embeddings"][0]

    query_kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": RETRIEVE_K,
        "include": ["documents", "metadatas", "distances"]
    }

    if sources:
        query_kwargs["where"] = {
            "source": {"$in": sources}
        }

    results = collection.query(**query_kwargs)

    documents = results["documents"][0] or []
    metadata = results["metadatas"][0] or []
    distances = results["distances"][0] or []

    scores = [
        float(distance) for distance in distances
    ]

    prompt_instructions = """
Answer the question using ONLY the provided context.
If the answer is not present in the context,
say: "I don't know based on the provided documents."
"""

    prompt_tokens = count_tokens(prompt_instructions)
    question_tokens = count_tokens(question)

    available_budget = calculate_available_budget(
        model_context_limit=MODEL_CONTEXT_LIMIT,
        prompt_tokens=prompt_tokens,
        question_tokens=question_tokens,
        answer_reserve=ANSWER_RESERVE
    )

    # Keep the retrieved chunks in their original
    # semantic-retrieval order. Do not optimize them.
    tokens_used = sum(
        count_tokens(document) for document in documents
    )

    return (
        documents,
        metadata,
        scores,
        tokens_used,
        available_budget
    )

# --------------------------------------------------
# Ask Question
# --------------------------------------------------

def ask_question(
    question,
    sources=None
):

    (
        final_documents,
        final_metadata,
        final_scores,
        tokens_used,
        available_budget
    ) = build_text_context(
        question,
        sources=sources
    )


    # --------------------------------------------------
    # No relevant context
    # --------------------------------------------------

    if not final_documents:

        return {
            "answer":
                "I don't know based on the provided documents.",
            "context": [],
            "metadata": [],
            "scores": []
        }


    # --------------------------------------------------
    # Build Context
    # --------------------------------------------------

    context = "\n\n".join(
        final_documents
    )


    # --------------------------------------------------
    # Final Prompt
    # --------------------------------------------------

    prompt = f"""
Answer the question using ONLY the provided context.

The context may contain:
- normal text
- tables
- figure information

Use table information when relevant to the question.

If the answer is not present in the context,
say:

"I don't know based on the provided documents."

Context:
{context}

Question:
{question}
"""


    # --------------------------------------------------
    # Ask Groq
    # --------------------------------------------------

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )


    # --------------------------------------------------
    # Extract Answer
    # --------------------------------------------------

    answer = (
    response
    .choices[0]
    .message
    .content
 )
    answer = fix_text_encoding(answer)


    # --------------------------------------------------
    # Return Result
    # --------------------------------------------------

    return {
        "answer": answer,
        "context": final_documents,
        "metadata": final_metadata,
        "scores": final_scores,
        "available_budget": available_budget,
        "tokens_used": tokens_used,
        "tokens_remaining":
            available_budget - tokens_used
    }