import base64
import hashlib
import json
from pathlib import Path

import requests


OLLAMA_URL = "http://localhost:11434/api/chat"
VISION_MODEL = "gemma3:4b"

CACHE_DIR = Path("data/figure_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_key(image_path: Path) -> str:
    """
    Create a stable cache key from the image path.
    """

    return hashlib.md5(
        str(image_path.resolve()).encode("utf-8")
    ).hexdigest()


def _cache_path(image_path: Path) -> Path:
    return CACHE_DIR / f"{_cache_key(image_path)}.json"


def analyze_figure(
    image_path: str,
    question: str = ""
) -> str:

    image_path = Path(image_path)

    if not image_path.exists():
        return f"Figure image not found: {image_path}"

    # --------------------------------------------------
    # 1. Check cache
    # --------------------------------------------------

    cache_file = _cache_path(image_path)

    if cache_file.exists():

        try:
            cached = json.loads(
                cache_file.read_text(
                    encoding="utf-8"
                )
            )

            print(
                f"Using cached visual analysis: "
                f"{image_path}"
            )

            return cached["description"]

        except Exception:
            pass

    # --------------------------------------------------
    # 2. Read image
    # --------------------------------------------------

    print(
        f"Running vision model for: "
        f"{image_path}"
    )

    image_base64 = base64.b64encode(
        image_path.read_bytes()
    ).decode("utf-8")

    # --------------------------------------------------
    # 3. Vision prompt
    # --------------------------------------------------

    prompt = f"""
You are a document figure analysis system.

The image is a figure extracted from a research paper.

User question:
{question}

Answer using ONLY information visibly present
in the image.

Requirements:

- Identify the figure's visible title or number if present.
- Read visible labels, text, arrows, boxes, symbols,
  and relationships.
- Explain the actual structure shown in the image.
- Do not guess the domain or architecture if it is
  not supported by the image.
- Do not call it a CNN, RNN, recurrent unit,
  transformer, etc. unless the image provides
  enough evidence.
- Do not invent components or relationships.
- If something is unclear, say that it is unclear.

Give a concise but technically useful description.
"""

    # --------------------------------------------------
    # 4. Call Ollama Vision
    # --------------------------------------------------

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_base64],
                }
            ],
            "stream": False,
        },
        timeout=180,
    )

    response.raise_for_status()

    data = response.json()

    description = data["message"]["content"]

    # --------------------------------------------------
    # 5. Save result
    # --------------------------------------------------

    cache_file.write_text(
        json.dumps(
            {
                "image": str(image_path),
                "description": description
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"Saved visual analysis cache: "
        f"{cache_file}"
    )

    return description