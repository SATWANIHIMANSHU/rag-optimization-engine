import os
import base64
import re

from dotenv import load_dotenv
from groq import Groq


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# Groq client
# --------------------------------------------------

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


# --------------------------------------------------
# Configuration
# --------------------------------------------------

VISION_MODEL = "qwen/qwen3.6-27b"

PAGE_IMAGE_DIR = "./data/colpali_pages"


# --------------------------------------------------
# Clean Groq Vision response
# --------------------------------------------------

def clean_visual_response(response):
    """
    Remove model reasoning/thinking sections
    from the final visual answer.
    """

    if not response:
        return ""

    response = re.sub(
        r"<think>.*?</think>",
        "",
        response,
        flags=re.DOTALL
    )

    return response.strip()


# --------------------------------------------------
# Analyze a single PDF page
# --------------------------------------------------

def analyze_page_image(page_number, question):
    """
    Analyze a PDF page image using a
    vision-capable Groq model.
    """

    # --------------------------------------------------
    # Locate page image
    # --------------------------------------------------

    image_path = os.path.join(
        PAGE_IMAGE_DIR,
        f"page_{page_number}.png"
    )

    # --------------------------------------------------
    # Check whether image exists
    # --------------------------------------------------

    if not os.path.exists(image_path):

        return "Page image not found."


    # --------------------------------------------------
    # Read image
    # --------------------------------------------------

    with open(
        image_path,
        "rb"
    ) as image_file:

        image_base64 = base64.b64encode(
            image_file.read()
        ).decode("utf-8")


    # --------------------------------------------------
    # Create visual analysis prompt
    # --------------------------------------------------

    prompt = f"""
Answer the question using the provided PDF page image.

Question:
{question}

Describe only information that can be seen or clearly
understood from the page image.

Do not invent information.

If the page does not contain enough information to answer
the question, say:

"I don't know based on the provided page."
"""


    # --------------------------------------------------
    # Send image + question to Groq Vision
    # --------------------------------------------------

    response = groq_client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                "data:image/png;base64,"
                                f"{image_base64}"
                            )
                        }
                    }
                ]
            }
        ],
        temperature=0,
        max_tokens=800
    )


    # --------------------------------------------------
    # Extract answer
    # --------------------------------------------------

    answer = response.choices[0].message.content


    # --------------------------------------------------
    # Remove thinking/reasoning text
    # --------------------------------------------------

    answer = clean_visual_response(
        answer
    )


    # --------------------------------------------------
    # Return clean answer
    # --------------------------------------------------

    return answer


# --------------------------------------------------
# Analyze highest-scoring visual page
# --------------------------------------------------

def analyze_top_visual_page(
    visual_results,
    question
):
    """
    Analyze only the highest-scoring visual page.
    """

    if not visual_results:

        return None


    # --------------------------------------------------
    # Get highest-scoring page
    # --------------------------------------------------

    top_result = visual_results[0]

    page_number = top_result["page"]


    # --------------------------------------------------
    # Analyze page
    # --------------------------------------------------

    answer = analyze_page_image(
        page_number=page_number,
        question=question
    )


    # --------------------------------------------------
    # Return result
    # --------------------------------------------------

    return {
        "page": page_number,
        "score": top_result["score"],
        "answer": answer
    }