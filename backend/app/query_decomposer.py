import json
import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

DECOMPOSER_MODEL = "openai/gpt-oss-20b"


def decompose_query(question):
    """
    Decompose a user question into text and/or visual information needs.
    """

    prompt = f"""
You are a query analyzer for a multimodal RAG system.

Analyze the user's question and determine what information
is required to answer it.

The system has two retrieval modalities:

1. TEXT
   Used for definitions, explanations, descriptions,
   facts, concepts, and information available in extracted text.

2. VISUAL
   Used for diagrams, charts, tables, figures, screenshots,
   layouts, images, flowcharts, and information that must
   be understood from the visual appearance of a PDF page.

A question may require:
- only TEXT
- only VISUAL
- both TEXT and VISUAL

If both are required, split the question into separate
sub-queries.

Return ONLY valid JSON in exactly this structure:

{{
    "route": "text | visual | hybrid",
    "sub_queries": [
        {{
            "query": "sub-question",
            "type": "text | visual"
        }}
    ]
}}

IMPORTANT ROUTING RULES:

1. If the question asks ONLY about a visual object
   such as a diagram, chart, table, figure, flowchart,
   screenshot, or image, classify it as "visual".

2. Do NOT create a separate TEXT sub-query merely because
   textual information could help explain a visual object.

   Example:
   "Explain the JDBC architecture diagram in detail."

   Correct:
   {{
       "route": "visual",
       "sub_queries": [
           {{
               "query": "Explain the JDBC architecture diagram in detail.",
               "type": "visual"
           }}
       ]
   }}

3. If the question contains two independent information needs,
   and one requires text while the other requires visual
   information, classify it as "hybrid".

   Example:
   "What is JDBC and explain its architecture diagram?"

   Correct:
   {{
       "route": "hybrid",
       "sub_queries": [
           {{
               "query": "What is JDBC?",
               "type": "text"
           }},
           {{
               "query": "Explain the JDBC architecture diagram.",
               "type": "visual"
           }}
       ]
   }}

4. If the question can be answered from textual information
   alone, classify it as "text".

5. If the question explicitly refers to a page, diagram,
   figure, chart, table, image, or other visual content,
   consider whether the visual content itself is necessary
   to answer the question.

6. Do not answer the user's question.
   Only analyze and classify it.

7. Preserve the original meaning of the question.

8. For VISUAL sub-queries, enrich the query with useful
   visual retrieval terms.

   Include:
   - names of visible objects or components
   - important labels or text likely visible on the page
   - names of diagrams, screenshots, figures, tables, or layouts
   - important entities explicitly mentioned in the question

   Do NOT invent information that is not supported by the
   user's question.

   Example:

   User question:
   "Describe the GUI shown in the Swing example and identify
   the visible components."

   A useful visual query could be:
   "Swing GUI example screenshot visible components JFrame
   JButton JLabel JPanel JFileChooser"

9. For visual queries, prefer concrete searchable terms
   over generic phrases such as:
   "visual information", "the image", "the diagram",
   "the GUI", or "the screenshot".

10. For hybrid questions, apply the same visual-query
    enrichment to the VISUAL sub-query while keeping
    the TEXT sub-query focused on textual information.
User question:
{question}
"""

    response = groq_client.chat.completions.create(
        model=DECOMPOSER_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    content = response.choices[0].message.content.strip()

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(
            f"Query decomposer returned invalid JSON:\n{content}"
        )

    return result