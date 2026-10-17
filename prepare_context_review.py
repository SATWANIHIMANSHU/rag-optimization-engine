
import csv
from pathlib import Path

source = Path("context_precision_manual_review.csv")
output = Path("context_precision_review_ready.csv")

with source.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
    fields = list(rows[0].keys())

for row in rows:
    text = " ".join(row.get("chunk_text", "").lower().split())
    question = row.get("question", "").lower()

    # Suggestions only; human verification is still required.
    if "experiment code" in question:
        candidate = "1" if "rag-demo-482" in text else ""
    elif "highest retrieval score" in question:
        candidate = (
            "1" if "multimodal rag" in text and "94" in text else ""
        )
    elif "retrieval score of optimized rag" in question:
        candidate = (
            "1" if "optimized rag" in text and "88" in text else ""
        )
    elif "answer accuracy of multimodal rag" in question:
        candidate = (
            "1" if "multimodal rag" in text and "92" in text else ""
        )
    elif "lowest latency" in question:
        candidate = (
            "1" if "optimized rag" in text and "640" in text else ""
        )
    elif "figure retrieval score" in question:
        candidate = (
            "1" if "multimodal rag" in text and "90" in text else ""
        )
    elif "precision, recall, and f1" in question:
        candidate = (
            "1" if all(x in text for x in ["93", "91", "92"]) else ""
        )
    elif "what does figure 1 compare" in question:
        candidate = (
            "1" if all(
                x in text for x in
                ["standard rag", "optimized rag", "multimodal rag"]
            ) and "retrieval" in text else ""
        )
    elif "retrieval scores for standard" in question:
        candidate = (
            "1" if all(x in text for x in ["74", "88", "94"]) else ""
        )
    elif "supports figure retrieval" in question:
        candidate = (
            "1" if "multimodal rag" in text and "figure retrieval" in text
            else ""
        )
    else:
        candidate = ""

    row["suggested_relevance"] = candidate
    row["review_status"] = (
        "VERIFY: candidate relevant" if candidate == "1"
        else "REVIEW: not automatically classified"
    )

fields.extend(["suggested_relevance", "review_status"])

with output.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print(f"Created {output} with {len(rows)} rows.")
print("Suggested labels are not verified relevance judgments.")
