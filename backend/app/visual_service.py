from fastapi import FastAPI
from pydantic import BaseModel
import torch
import os

from colpali_engine.models import (
    ColQwen2,
    ColQwen2Processor
)


# --------------------------------------------------
# FastAPI
# --------------------------------------------------

app = FastAPI(
    title="Visual Retrieval Service"
)


# --------------------------------------------------
# Visual Model Configuration
# --------------------------------------------------

VISUAL_MODEL_NAME = "vidore/colqwen2-v1.0"

VISUAL_DEVICE = "cpu"

VISUAL_INDEX_DIR = "data/visual_index"

TOTAL_PAGES = 79

VISUAL_SOURCE = "Module I - Java Swing.pdf"


# --------------------------------------------------
# Load ColQwen2
# --------------------------------------------------

print("Loading ColQwen2...")

visual_model = ColQwen2.from_pretrained(
    VISUAL_MODEL_NAME,
    torch_dtype=torch.bfloat16,
).to(VISUAL_DEVICE)

visual_model.eval()

visual_processor = (
    ColQwen2Processor.from_pretrained(
        VISUAL_MODEL_NAME
    )
)

print("ColQwen2 loaded.")


# --------------------------------------------------
# Request Model
# --------------------------------------------------

class VisualSearchRequest(BaseModel):

    question: str

    top_k: int = 3

    source: str | None = None


# --------------------------------------------------
# Visual Search
# --------------------------------------------------

def visual_search(
    question,
    top_k=3,
    source=None
):

    # ----------------------------------------------
    # Check requested document
    # ----------------------------------------------

    if source is not None:

        if source != VISUAL_SOURCE:

            return []


    # ----------------------------------------------
    # Encode query
    # ----------------------------------------------

    query_inputs = (
        visual_processor.process_queries(
            [question]
        )
    )

    query_inputs = {
        key: value.to(VISUAL_DEVICE)
        for key, value in query_inputs.items()
    }


    # ----------------------------------------------
    # Generate query embedding
    # ----------------------------------------------

    with torch.no_grad():

        query_embedding = (
            visual_model(**query_inputs)
        )


    # ----------------------------------------------
    # Search visual index
    # ----------------------------------------------

    results = []


    for page_number in range(
        1,
        TOTAL_PAGES + 1
    ):

        embedding_path = os.path.join(
            VISUAL_INDEX_DIR,
            f"page_{page_number}.pt"
        )


        if not os.path.exists(
            embedding_path
        ):

            continue


        # ------------------------------------------
        # Load page embedding
        # ------------------------------------------

        page_embedding = torch.load(
            embedding_path,
            map_location=VISUAL_DEVICE
        )


        # ------------------------------------------
        # Calculate visual similarity
        # ------------------------------------------

        scores = (
            visual_processor.score_multi_vector(
                query_embedding,
                page_embedding
            )
        )


        score = float(
            scores[0][0]
        )


        # ------------------------------------------
        # Store unified result
        # ------------------------------------------

        results.append({

            "source": VISUAL_SOURCE,

            "page": page_number,

            "score": score,

            "type": "visual"

        })


        del page_embedding


    # ----------------------------------------------
    # Sort by visual similarity
    # ----------------------------------------------

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )


    return results[:top_k]


# --------------------------------------------------
# API Endpoint
# --------------------------------------------------

@app.post("/visual-search")
def visual_search_endpoint(
    request: VisualSearchRequest
):

    results = visual_search(

        question=request.question,

        top_k=request.top_k,

        source=request.source

    )


    return {

        "results": results

    }