from pathlib import Path

script = r'''"""
Export retrieved contexts for manual Context Precision evaluation.

Run from the project root with the backend running. The script calls the
existing baseline and optimized endpoints for the same 10 questions and saves
each returned chunk as one CSV row.

This script does NOT calculate Context Precision automatically. You must label
each chunk's relevance after comparing it with the question and source PDF.
"""
'''

import csv
import getpass
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

API_BASE = os.getenv("RAG_API_BASE", "http://localhost:8000").rstrip("/")
EMAIL = os.getenv("RAG_EMAIL") or input("Login email: ").strip()
PASSWORD = os.getenv("RAG_PASSWORD") or getpass.getpass("Login password: ")
DOCUMENT = os.getenv("RAG_DOCUMENT", "RAG_Multimodal_Demo_Test.pdf")
TIMEOUT = int(os.getenv("RAG_TIMEOUT", "300"))

QUESTIONS = [
    (1, "text", "What is the experiment code?"),
    (2, "table", "Which method has the highest retrieval score?"),
    (3, "table", "What is the retrieval score of Optimized RAG?"),
    (4, "table", "What is the answer accuracy of Multimodal RAG?"),
    (5, "table", "Which method has the lowest latency?"),
    (6, "figure", "What is the figure retrieval score of Multimodal RAG?"),
    (7, "table", "What are the precision, recall, and F1 score of Multimodal RAG?"),
    (8, "figure", "What does Figure 1 compare?"),
    (9, "table", "What are the retrieval scores for Standard, Optimized, and Multimodal RAG?"),
    (10, "figure", "Which configuration supports figure retrieval?"),
]

def login():
    session = requests.Session()
    try:
        resp = session.post(
            f"{API_BASE}/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Login failed: {exc}")
        sys.exit(1)

    payload = resp.json()
    token = payload.get("access_token") or payload.get("token")
    if not token:
        print("Login response did not include an access token.")
        print(payload)
        sys.exit(1)
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session

def main():
    session = login()
    print("Login successful.")
    rows = []
    endpoints = [("baseline", "ask-baseline"), ("optimized", "ask")]

    for qid, qtype, question in QUESTIONS:
        for pipeline, endpoint in endpoints:
            print(f"Question {qid}/10 — {pipeline}: collecting context...", flush=True)
            started = time.perf_counter()
            try:
                resp = session.post(
                    f"{API_BASE}/{endpoint}",
                    json={"question": question, "document_ids": [DOCUMENT]},
                    timeout=TIMEOUT,
                )
                resp.raise_for_status()
                payload = resp.json()
                elapsed = round(time.perf_counter() - started, 3)
                contexts = payload.get("context") or []
                metadata = payload.get("metadata") or []
                scores = payload.get("scores") or []

                for rank, chunk in enumerate(contexts, start=1):
                    meta = metadata[rank - 1] if rank - 1 < len(metadata) else {}
                    score = scores[rank - 1] if rank - 1 < len(scores) else ""
                    rows.append({
                        "question_id": qid,
                        "question_type": qtype,
                        "question": question,
                        "pipeline": pipeline,
                        "rank": rank,
                        "source": meta.get("source", ""),
                        "page": meta.get("page", ""),
                        "element_type": meta.get("type", ""),
                        "element_id": meta.get("element_id", ""),
                        "score": score,
                        "relevant_1_irrelevant_0": "",
                        "relevance_notes": "",
                        "chunk_text": str(chunk),
                        "request_latency_seconds": elapsed,
                        "error": "",
                    })

                if not contexts:
                    rows.append({
                        "question_id": qid, "question_type": qtype,
                        "question": question, "pipeline": pipeline, "rank": 0,
                        "source": "", "page": "", "element_type": "", "element_id": "",
                        "score": "", "relevant_1_irrelevant_0": "",
                        "relevance_notes": "", "chunk_text": "",
                        "request_latency_seconds": elapsed,
                        "error": "No context returned",
                    })
                print(f"    {len(contexts)} chunks collected in {elapsed:.2f}s")
            except requests.RequestException as exc:
                print(f"    ERROR: {exc}")
                rows.append({
                    "question_id": qid, "question_type": qtype,
                    "question": question, "pipeline": pipeline, "rank": 0,
                    "source": "", "page": "", "element_type": "", "element_id": "",
                    "score": "", "relevant_1_irrelevant_0": "",
                    "relevance_notes": "", "chunk_text": "",
                    "request_latency_seconds": "", "error": str(exc),
                })

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = Path(f"context_precision_labels_{stamp}.csv").resolve()
    fields = [
        "question_id", "question_type", "question", "pipeline", "rank",
        "source", "page", "element_type", "element_id", "score",
        "relevant_1_irrelevant_0", "relevance_notes", "chunk_text",
        "request_latency_seconds", "error",
    ]
    with output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved: {output}")
    print(f"Context rows: {len(rows)}")
    print("Next: open the CSV in Excel and label relevance as 1 or 0.")
    print("Do not label based only on whether the final answer was correct.")

if __name__ == "__main__":
    main()
# path = "/mnt/data/export_context_precision_labels.py"
# Path(path).write_text(script, encoding="utf-8")
# print(f"Created: {path}")
