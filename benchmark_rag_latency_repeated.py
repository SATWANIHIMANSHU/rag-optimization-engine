"""
Repeated latency benchmark for the RAG Optimization Engine.

Runs the same 10 questions through /ask-baseline and /ask for 3 repetitions.
It alternates endpoint order to reduce simple order bias, records each call,
and writes raw CSV/JSON plus a summary CSV.

Important:
- This measures warm/repeated-use behavior in the current running app. It does
  not clear figure caches or restart Ollama/Groq between runs.
- Do not call keyword matches verified accuracy.
- The two endpoints currently differ in more than one component (baseline skips
  targeted figure/table retrieval and visual analysis too), so interpret this as
  a whole-pipeline comparison, not a component ablation.
"""

import csv
import getpass
import json
import os
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests

API_BASE = os.getenv("RAG_API_BASE", "http://localhost:8000").rstrip("/")
EMAIL = os.getenv("RAG_EMAIL") or input("Login email: ").strip()
PASSWORD = os.getenv("RAG_PASSWORD") or getpass.getpass("Login password: ")
DOCUMENT = os.getenv("RAG_DOCUMENT", "RAG_Multimodal_Demo_Test.pdf")
TIMEOUT = int(os.getenv("RAG_TIMEOUT", "300"))
REPETITIONS = int(os.getenv("RAG_REPETITIONS", "3"))

QUESTIONS = [
    {"id": 1, "type": "text", "question": "What is the experiment code?",
     "expected": "RAG-DEMO-482", "keywords": ["RAG-DEMO-482"]},
    {"id": 2, "type": "table", "question": "Which method has the highest retrieval score?",
     "expected": "Multimodal RAG", "keywords": ["multimodal rag"]},
    {"id": 3, "type": "table", "question": "What is the retrieval score of Optimized RAG?",
     "expected": "88", "keywords": ["88"]},
    {"id": 4, "type": "table", "question": "What is the answer accuracy of Multimodal RAG?",
     "expected": "92", "keywords": ["92"]},
    {"id": 5, "type": "table", "question": "Which method has the lowest latency?",
     "expected": "Optimized RAG", "keywords": ["optimized rag"]},
    {"id": 6, "type": "figure", "question": "What is the figure retrieval score of Multimodal RAG?",
     "expected": "90", "keywords": ["90"]},
    {"id": 7, "type": "table", "question": "What are the precision, recall, and F1 score of Multimodal RAG?",
     "expected": "Precision 93; Recall 91; F1 92", "keywords": ["93", "91", "92"]},
    {"id": 8, "type": "figure", "question": "What does Figure 1 compare?",
     "expected": "Retrieval scores of Standard RAG, Optimized RAG, and Multimodal RAG",
     "keywords": ["standard", "optimized", "multimodal", "retrieval"]},
    {"id": 9, "type": "table", "question": "What are the retrieval scores for Standard, Optimized, and Multimodal RAG?",
     "expected": "Standard 74; Optimized 88; Multimodal 94", "keywords": ["74", "88", "94"]},
    {"id": 10, "type": "figure", "question": "Which configuration supports figure retrieval?",
     "expected": "Multimodal RAG", "keywords": ["multimodal rag"]},
]

def norm(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()

def keyword_match(answer, keywords):
    answer_norm = norm(answer)
    return int(bool(answer_norm) and all(norm(k) in answer_norm for k in keywords))

def login():
    session = requests.Session()
    try:
        response = session.post(
            f"{API_BASE}/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Login failed: {exc}")
        sys.exit(1)

    data = response.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        print("No access token in login response:", json.dumps(data, indent=2))
        sys.exit(1)
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session

def call_endpoint(session, endpoint, question):
    started = time.perf_counter()
    response = session.post(
        f"{API_BASE}/{endpoint}",
        json={"question": question, "document_ids": [DOCUMENT]},
        timeout=TIMEOUT,
    )
    elapsed = time.perf_counter() - started
    response.raise_for_status()
    return response.json(), elapsed

def main():
    if REPETITIONS < 2:
        print("Set RAG_REPETITIONS to at least 2 (recommended: 3).")
        sys.exit(2)

    print(f"API: {API_BASE}")
    print(f"Document filter: {DOCUMENT}")
    print(f"Repetitions: {REPETITIONS}")
    print("Mode: repeated-use benchmark; cache is not cleared.")
    session = login()
    print("Login successful.")

    # Check endpoint availability before the longer run.
    for endpoint in ("ask-baseline", "ask"):
        try:
            response = session.post(
                f"{API_BASE}/{endpoint}",
                json={"question": "health check", "document_ids": [DOCUMENT]},
                timeout=TIMEOUT,
            )
            if response.status_code in (404, 405):
                print(f"ERROR: /{endpoint} is unavailable.")
                sys.exit(2)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"Endpoint check failed for /{endpoint}: {exc}")
            sys.exit(2)

    raw_rows = []
    total = len(QUESTIONS) * REPETITIONS * 2
    call_number = 0
    print(f"\nStarting {total} measured API calls. Figure questions may be slow.\n")

    for repetition in range(1, REPETITIONS + 1):
        print(f"\n========== REPETITION {repetition}/{REPETITIONS} ==========")
        for question in QUESTIONS:
            # Alternate order each repetition to reduce systematic order bias.
            endpoints = [("baseline", "ask-baseline"), ("optimized", "ask")]
            if (question["id"] + repetition) % 2 == 0:
                endpoints.reverse()

            for label, endpoint in endpoints:
                call_number += 1
                print(
                    f"[{call_number}/{total}] Run {repetition}, Q{question['id']}, "
                    f"{label} ...",
                    flush=True,
                )
                row = {
                    "repetition": repetition,
                    "call_number": call_number,
                    "question_id": question["id"],
                    "type": question["type"],
                    "question": question["question"],
                    "expected_answer": question["expected"],
                    "pipeline": label,
                    "endpoint": f"/{endpoint}",
                }
                try:
                    data, elapsed = call_endpoint(session, endpoint, question["question"])
                    answer = str(data.get("answer") or "")
                    row.update({
                        "answer": answer,
                        "keyword_match_heuristic": keyword_match(answer, question["keywords"]),
                        "latency_seconds": round(elapsed, 3),
                        "tokens_used_reported": data.get("tokens_used", ""),
                        "context_count": len(data.get("context") or []),
                        "metadata_count": len(data.get("metadata") or []),
                        "error": "",
                    })
                    print(
                        f"    {elapsed:.2f}s | keyword heuristic "
                        f"{'MATCH' if row['keyword_match_heuristic'] else 'CHECK'}"
                    )
                except requests.RequestException as exc:
                    row.update({
                        "answer": "",
                        "keyword_match_heuristic": 0,
                        "latency_seconds": "",
                        "tokens_used_reported": "",
                        "context_count": "",
                        "metadata_count": "",
                        "error": str(exc),
                    })
                    print(f"    ERROR: {exc}")
                raw_rows.append(row)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_csv = Path(f"rag_latency_repeated_raw_{stamp}.csv").resolve()
    raw_json = Path(f"rag_latency_repeated_raw_{stamp}.json").resolve()
    summary_csv = Path(f"rag_latency_repeated_summary_{stamp}.csv").resolve()

    fields = list(raw_rows[0].keys()) if raw_rows else []
    with raw_csv.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(raw_rows)
    with raw_json.open("w", encoding="utf-8") as file:
        json.dump({
            "document_filter": DOCUMENT,
            "repetitions": REPETITIONS,
            "mode": "repeated-use; cache not cleared",
            "warning": "Keyword heuristic is not validated answer accuracy.",
            "measurements": raw_rows,
        }, file, indent=2, ensure_ascii=False)

    grouped = defaultdict(list)
    for row in raw_rows:
        if not row["error"] and row["latency_seconds"] != "":
            grouped[row["pipeline"]].append(float(row["latency_seconds"]))

    summary_rows = []
    print("\n================ LATENCY SUMMARY ================")
    for pipeline in ("baseline", "optimized"):
        values = grouped[pipeline]
        if values:
            mean_value = statistics.mean(values)
            median_value = statistics.median(values)
            summary_rows.append({
                "pipeline": pipeline,
                "successful_calls": len(values),
                "mean_latency_seconds": round(mean_value, 3),
                "median_latency_seconds": round(median_value, 3),
                "min_latency_seconds": round(min(values), 3),
                "max_latency_seconds": round(max(values), 3),
                "mode": "repeated-use; cache not cleared",
            })
            print(
                f"{pipeline.title()}: n={len(values)}, mean={mean_value:.2f}s, "
                f"median={median_value:.2f}s, min={min(values):.2f}s, "
                f"max={max(values):.2f}s"
            )

    # Per-question means make the slow figure question visible.
    print("\nPer-question mean latency:")
    for q in QUESTIONS:
        parts = []
        for pipeline in ("baseline", "optimized"):
            vals = [
                float(r["latency_seconds"]) for r in raw_rows
                if r["question_id"] == q["id"] and r["pipeline"] == pipeline
                and not r["error"] and r["latency_seconds"] != ""
            ]
            if vals:
                parts.append(f"{pipeline}={statistics.mean(vals):.2f}s")
        print(f"  Q{q['id']}: " + ", ".join(parts))

    with summary_csv.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print("\nFiles saved:")
    print(f"Raw CSV:     {raw_csv}")
    print(f"Raw JSON:    {raw_json}")
    print(f"Summary CSV: {summary_csv}")
    print("\nReport these as repeated-use latency results, not cold-start latency.")
    print("Review answers separately; keyword matches are not verified accuracy.")

if __name__ == "__main__":
    main()
