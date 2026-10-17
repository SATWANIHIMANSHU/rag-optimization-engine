import csv
import re
from pathlib import Path

source = Path("context_precision_manual_review.csv")
output = Path("context_precision_candidates.csv")

# Evidence terms used to identify possible relevance.
expected = {
    1: ["RAG-DEMO-482"],
    2: ["Multimodal RAG", "94"],
    3: ["88"],
    4: ["92"],
    5: ["Optimized RAG", "640 milliseconds"],
    6: ["90"],
    7: ["93", "91", "92"],
    8: ["Standard RAG", "Optimized RAG", "Multimodal RAG"],
    9: ["74", "88", "94"],
    10: ["Multimodal RAG", "figure retrieval"],
}

with source.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

if not rows:
    raise SystemExit(f"No rows found in {source}")

fields = list(rows[0].keys())

for row in rows:
    qid = int(row["question_id"])
    text = row.get("chunk_text", "").lower()
    terms = expected.get(qid, [])

    matches = [
        term for term in terms
        if re.search(
            r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)",
            text
        )
    ]

    row["candidate_terms_found"] = " | ".join(matches)
    row["candidate_review"] = (
        "POSSIBLE_RELEVANT" if matches else "NEEDS_REVIEW"
    )

for name in ["candidate_terms_found", "candidate_review"]:
    if name not in fields:
        fields.append(name)

with output.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print(f"Created {output}: {len(rows)} chunks")
print("Candidate flags are estimates, not verified relevance labels.")