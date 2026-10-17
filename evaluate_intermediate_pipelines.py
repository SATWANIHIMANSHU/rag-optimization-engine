
import csv
import json
from multiprocessing import context
import os
import time
import statistics
from datetime import datetime
from pathlib import Path

import requests

API = os.getenv("RAG_API_BASE", "http://localhost:8000").rstrip("/")
DOCUMENT = os.getenv(
    "RAG_DOCUMENT", "RAG_Multimodal_Demo_Test.pdf"
)

QUESTIONS = [
    (1, "What is the experiment code?",
     ["RAG-DEMO-482"]),
    (2, "Which method has the highest retrieval score?",
     ["multimodal rag"]),
    (3, "What is the retrieval score of Optimized RAG?",
     ["88"]),
    (4, "What is the answer accuracy of Multimodal RAG?",
     ["92"]),
    (5, "Which method has the lowest latency?",
     ["optimized rag"]),
    (6, "What is the figure retrieval score of Multimodal RAG?",
     ["90"]),
    (7, "What are the precision, recall, and F1 score of Multimodal RAG?",
     ["93", "91", "92"]),
    (8, "What does Figure 1 compare?",
     ["standard", "optimized", "multimodal", "retrieval"]),
    (9, "What are the retrieval scores for Standard, Optimized, and Multimodal RAG?",
     ["74", "88", "94"]),
    (10, "Which configuration supports figure retrieval?",
     ["multimodal rag"]),
]


def main():
    session = requests.Session()
    email = os.getenv("RAG_EMAIL") or input("Login email: ").strip()
    import getpass
    password = os.getenv("RAG_PASSWORD") or getpass.getpass("Login password: ")

    response = session.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    token = response.json().get("access_token") or response.json().get("token")
    if not token:
        raise RuntimeError("Login response did not contain an access token.")

    session.headers.update({"Authorization": f"Bearer {token}"})

    rows = []
    pipelines = {
        "reranker": "RAG + reranker",
        "reranker_redundancy": "RAG + reranker + redundancy filter",
    }

    for qid, question, keywords in QUESTIONS:
        print(f"\nQuestion {qid}/10: {question}", flush=True)

        for mode, label in pipelines.items():
            start = time.perf_counter()
            try:
                response = session.post(
                    f"{API}/evaluate-pipeline",
                    json={
                        "question": question,
                        "document_ids": [DOCUMENT],
                        "pipeline": mode,
                    },
                    timeout=300,
                )
                response.raise_for_status()
                data = response.json()
                elapsed = time.perf_counter() - start
                answer = str(data.get("answer") or "")
                normalized = " ".join(answer.lower().split())
                context = data.get("context") or []
                metadata = data.get("metadata") or []

                context_text = json.dumps(context, ensure_ascii=False)
                metadata_text = json.dumps(metadata, ensure_ascii=False)
                match = int(
                    bool(normalized)
                    and all(k.lower() in normalized for k in keywords)
                )

                rows.append({
                    "question_id": qid,
                    "pipeline": label,
                    "question": question,
                    "expected_keywords": " | ".join(keywords),
                    "answer": answer,
                    "keyword_match": match,
                    "latency_seconds": round(elapsed, 3),
                    "tokens_used": data.get("tokens_used", ""),
                    "context_count": len(data.get("context") or []),
                    "error": "",
                    "context_text": context_text,
                    "metadata_text": metadata_text,
                })
                print(
                    f"  {label}: {elapsed:.2f}s | "
                    f"{'MATCH' if match else 'REVIEW'} | "
                    f"contexts={len(data.get('context') or [])}"
                )

            except Exception as exc:
                rows.append({
                    "question_id": qid,
                    "pipeline": label,
                    "question": question,
                    "expected_keywords": " | ".join(keywords),
                    "answer": "",
                    "keyword_match": 0,
                    "latency_seconds": "",
                    "tokens_used": "",
                    "context_count": "",
                    "error": str(exc),
                })
                print(f"  {label} ERROR: {exc}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = Path(f"intermediate_pipeline_results_{stamp}.csv")
    json_path = Path(f"intermediate_pipeline_results_{stamp}.json")

    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(rows, file, indent=2, ensure_ascii=False)

    print("\nSUMMARY — keyword matches are preliminary, not validated accuracy")
    for label in pipelines.values():
        group = [r for r in rows if r["pipeline"] == label]
        successful = [r for r in group if not r["error"]]
        latencies = [
            float(r["latency_seconds"])
            for r in successful
            if r["latency_seconds"] != ""
        ]
        matches = sum(int(r["keyword_match"]) for r in successful)
        print(f"\n{label}: {matches}/{len(successful)} keyword matches")
        if latencies:
            print(
                f"Mean latency: {statistics.mean(latencies):.2f}s; "
                f"median: {statistics.median(latencies):.2f}s"
            )

    print(f"\nCSV:  {csv_path.resolve()}")
    print(f"JSON: {json_path.resolve()}")


if __name__ == "__main__":
    main()
