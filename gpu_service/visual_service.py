import modal


app = modal.App("rag-visual-service")


# =========================================================
# Persistent volume for Transformer visual embeddings
# =========================================================

transformer_volume = modal.Volume.from_name(
    "transformer-visual-index",
    create_if_missing=True,
)


# =========================================================
# Modal Image
# =========================================================

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch",
        "transformers",
        "pillow",
        "fastapi",
        "colpali-engine>=0.3.14",
    )
    .add_local_dir(
        "data/visual_index",
        remote_path="/app/visual_index",
    )
    .add_local_dir(
        "data/resnet_visual_index",
        remote_path="/app/resnet_visual_index",
    )
    .add_local_dir(
        "data/transformer_pages",
        remote_path="/app/transformer_pages",
    )
)


# =========================================================
# Global model objects
# =========================================================

model = None
processor = None


# =========================================================
# Visual Search
# =========================================================

@app.function(
    image=image,
    gpu="T4",
    timeout=600,
)
@modal.fastapi_endpoint(method="POST")
def visual_search(request: dict):

    global model, processor

    import os
    import torch
    from colpali_engine.models import (
        ColQwen2,
        ColQwen2Processor,
    )

    # -----------------------------------------------------
    # Load ColQwen2
    # -----------------------------------------------------

    if model is None:

        print("Loading ColQwen2...")

        model = ColQwen2.from_pretrained(
            "vidore/colqwen2-v1.0",
            torch_dtype=torch.bfloat16,
            device_map="cuda:0",
        ).eval()

        processor = ColQwen2Processor.from_pretrained(
            "vidore/colqwen2-v1.0"
        )

        print("ColQwen2 loaded successfully!")

    # -----------------------------------------------------
    # Read request
    # -----------------------------------------------------

    question = request.get(
        "question",
        ""
    )

    source = request.get(
        "source",
        "Java Swing PDF"
    )

    top_k = request.get(
        "top_k",
        5
    )

    # -----------------------------------------------------
    # Select visual index
    #
    # Temporary document-specific routing.
    # This will later become dynamic when we support
    # multiple arbitrary PDFs.
    # -----------------------------------------------------

    if source == "ResNet.pdf":

        index_dir = "/app/resnet_visual_index"
        total_pages = 12

    elif source == "Java Swing PDF":

        index_dir = "/app/visual_index"
        total_pages = 79

    else:

        return {
            "status": "error",
            "message": (
                f"No visual index configured for: {source}"
            )
        }

    # -----------------------------------------------------
    # Encode query
    # -----------------------------------------------------

    batch = processor.process_queries(
        [question]
    )

    batch = {
        key: value.to("cuda:0")
        for key, value in batch.items()
    }

    with torch.no_grad():

        query_embedding = model(
            **batch
        )

    query_embedding = query_embedding.to(
        torch.float32
    )

    # -----------------------------------------------------
    # Search visual pages
    # -----------------------------------------------------

    results = []

    for page_num in range(
        1,
        total_pages + 1
    ):

        path = os.path.join(
            index_dir,
            f"page_{page_num}.pt"
        )

        # -------------------------------------------------
        # Skip missing page embeddings
        # -------------------------------------------------

        if not os.path.exists(path):

            print(
                f"Skipping missing page: "
                f"{page_num}"
            )

            continue

        # -------------------------------------------------
        # Load page embedding
        # -------------------------------------------------

        page_embedding = torch.load(
            path,
            map_location="cuda:0",
            weights_only=True,
        )

        page_embedding = page_embedding.to(
            torch.float32
        )

        # -------------------------------------------------
        # Calculate ColQwen2 similarity
        # -------------------------------------------------

        score = (
            query_embedding
            @ page_embedding.transpose(-1, -2)
        ).max(
            dim=-1
        ).values.sum().item()

        # -------------------------------------------------
        # Store result
        # -------------------------------------------------

        results.append({
            "page": page_num,
            "score": round(score, 4),
            "source": source,
        })

        # -------------------------------------------------
        # Release page embedding from GPU memory
        # -------------------------------------------------

        del page_embedding

    # -----------------------------------------------------
    # Sort by relevance
    # -----------------------------------------------------

    results.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    # -----------------------------------------------------
    # Return top results
    # -----------------------------------------------------

    return {
        "status": "success",
        "question": question,
        "source": source,
        "results": results[:top_k],
    }


# =========================================================
# Build Transformer Visual Index
# =========================================================

@app.function(
    image=image,
    gpu="T4",
    timeout=1800,
    volumes={
        "/vol": transformer_volume,
    },
)
@modal.fastapi_endpoint(method="POST")
def build_transformer_index(request: dict):

    global model, processor

    import os
    import torch
    from PIL import Image

    from colpali_engine.models import (
        ColQwen2,
        ColQwen2Processor,
    )

    # -----------------------------------------------------
    # Load ColQwen2
    # -----------------------------------------------------

    if model is None:

        print(
            "Loading ColQwen2 for index generation..."
        )

        model = ColQwen2.from_pretrained(
            "vidore/colqwen2-v1.0",
            torch_dtype=torch.bfloat16,
            device_map="cuda:0",
        ).eval()

        processor = ColQwen2Processor.from_pretrained(
            "vidore/colqwen2-v1.0"
        )

        print(
            "ColQwen2 loaded successfully!"
        )

    # -----------------------------------------------------
    # Input / output directories
    # -----------------------------------------------------

    input_dir = "/app/transformer_pages"

    output_dir = "/vol"

    total_pages = request.get(
        "total_pages",
        15
    )

    results = []

    # -----------------------------------------------------
    # Process pages one at a time
    # -----------------------------------------------------

    for page_number in range(
        1,
        total_pages + 1
    ):

        image_path = os.path.join(
            input_dir,
            f"page_{page_number}.png"
        )

        output_path = os.path.join(
            output_dir,
            f"page_{page_number}.pt"
        )

        # -------------------------------------------------
        # Don't regenerate existing embeddings
        # -------------------------------------------------

        if os.path.exists(output_path):

            print(
                f"Page {page_number}: "
                f"embedding already exists. "
                f"Skipping."
            )

            results.append({
                "page": page_number,
                "status": "already_exists",
            })

            continue

        # -------------------------------------------------
        # Process page
        # -------------------------------------------------

        print(
            f"\nProcessing Transformer page "
            f"{page_number}/{total_pages}..."
        )

        page_image = Image.open(
            image_path
        ).convert("RGB")

        batch = processor.process_images(
            [page_image]
        )

        batch = {
            key: value.to("cuda:0")
            for key, value in batch.items()
        }

        # -------------------------------------------------
        # Generate visual embedding
        # -------------------------------------------------

        with torch.no_grad():

            page_embedding = model(
                **batch
            )

        # -------------------------------------------------
        # Store embedding on CPU
        # -------------------------------------------------

        page_embedding = page_embedding.cpu()

        torch.save(
            page_embedding,
            output_path,
        )

        print(
            f"Saved page {page_number}: "
            f"{output_path}"
        )

        results.append({
            "page": page_number,
            "status": "created",
            "shape": list(
                page_embedding.shape
            ),
        })

        # -------------------------------------------------
        # Cleanup
        # -------------------------------------------------

        del page_image
        del batch
        del page_embedding

        if torch.cuda.is_available():

            torch.cuda.empty_cache()

    # -----------------------------------------------------
    # Persist generated files
    # -----------------------------------------------------

    transformer_volume.commit()

    print(
        "\nTransformer visual index "
        "generation complete."
    )

    return {
        "status": "success",
        "total_pages": total_pages,
        "results": results,
    }