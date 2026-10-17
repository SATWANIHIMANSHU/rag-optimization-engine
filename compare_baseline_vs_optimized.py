"""
Compare the same questions using:
  A) baseline RAG: vector retrieval -> generation
  B) optimized RAG: existing /ask pipeline

IMPORTANT:
- This script assumes you add a separate /ask-baseline endpoint to your FastAPI app.
- The endpoint must use the same document ingestion, embedding model, vector store,
  generation model, and question set as /ask, but bypass reranking, redundancy filtering,
  and context optimization.
- Do not point both endpoints to the same full pipeline, or the comparison is invalid.

Expected endpoint contract:
POST /ask-baseline
JSON: {"question": "...", "document_ids": ["RAG_Multimodal_Demo_Test.pdf"]}
Response: {"answer": "...", "context": [...], "metadata": [...], "tokens_used": 123}

POST /ask
Same request/response shape for the optimized pipeline.

Run:
  python -m pip install requests
  $env:RAG_API_BASE="http://localhost:8000"
  $env:RAG_EMAIL="test@example.com"
  $env:RAG_PASSWORD="123456"
  $env:RAG_DOCUMENT="RAG_Multimodal_Demo_Test.pdf"
  python compare_baseline_vs_optimized.py
"""
import csv
import getpass
import json
import os
import re
import statistics
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

def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()

def keyword_match(answer, keywords):
    a = norm(answer)
    return int(bool(a) and all(norm(k) in a for k in keywords))

def login():
    sess = requests.Session()
    try:
        r = sess.post(f"{API_BASE}/auth/login",
                      json={"email": EMAIL, "password": PASSWORD}, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"Login failed: {e}")
        sys.exit(1)
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        print("No access token in login response:", json.dumps(data, indent=2))
        sys.exit(1)
    sess.headers.update({"Authorization": f"Bearer {token}"})
    return sess

def call_endpoint(sess, endpoint, question):
    start = time.perf_counter()
    r = sess.post(f"{API_BASE}/{endpoint}",
                  json={"question": question, "document_ids": [DOCUMENT]},
                  timeout=TIMEOUT)
    elapsed = time.perf_counter() - start
    r.raise_for_status()
    return r.json(), elapsed

def main():
    print(f"API: {API_BASE}")
    print(f"Document: {DOCUMENT}")
    sess = login()
    print("Login successful.")
    # Fail early with a helpful message if baseline endpoint hasn't been added.
    try:
        r = sess.post(f"{API_BASE}/ask-baseline",
                      json={"question": "health check", "document_ids": [DOCUMENT]},
                      timeout=TIMEOUT)
        if r.status_code == 404 or r.status_code == 405:
            print("\nERROR: /ask-baseline is not available.")
            print("You must implement a genuine baseline endpoint that bypasses the")
            print("reranker, redundancy filter, and context optimizer before running comparison.")
            sys.exit(2)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"\nBaseline endpoint check failed: {e}")
        print("Add /ask-baseline in backend/app/main.py, then restart FastAPI.")
        sys.exit(2)

    rows = []
    print("\nRunning same questions through baseline and optimized RAG...")
    for q in QUESTIONS:
        print(f"\n[{q['id']}/10] {q['question']}", flush=True)
        row = {
            "id": q["id"], "type": q["type"], "question": q["question"],
            "expected_answer": q["expected"],
        }
        for label, endpoint in [("baseline", "ask-baseline"), ("optimized", "ask")]:
            try:
                data, elapsed = call_endpoint(sess, endpoint, q["question"])
                answer = str(data.get("answer") or "")
                row[f"{label}_answer"] = answer
                row[f"{label}_keyword_match"] = keyword_match(answer, q["keywords"])
                row[f"{label}_latency_seconds"] = round(elapsed, 3)
                row[f"{label}_tokens_used"] = data.get("tokens_used", "")
                row[f"{label}_context_count"] = len(data.get("context") or [])
                row[f"{label}_metadata_count"] = len(data.get("metadata") or [])
                row[f"{label}_error"] = ""
                print(f"  {label}: {elapsed:.2f}s | keyword heuristic "
                      f"{'MATCH' if row[f'{label}_keyword_match'] else 'CHECK'}")
                print(f"    {answer[:180].replace(chr(10), ' ')}")
            except requests.RequestException as e:
                row[f"{label}_answer"] = ""
                row[f"{label}_keyword_match"] = 0
                row[f"{label}_latency_seconds"] = ""
                row[f"{label}_tokens_used"] = ""
                row[f"{label}_context_count"] = ""
                row[f"{label}_metadata_count"] = ""
                row[f"{label}_error"] = str(e)
                print(f"  {label} ERROR: {e}")
        rows.append(row)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = Path(f"rag_baseline_vs_optimized_{stamp}.csv").resolve()
    json_path = Path(f"rag_baseline_vs_optimized_{stamp}.json").resolve()
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with json_path.open("w", encoding="utf-8") as f:
        json.dump({"document": DOCUMENT, "questions": rows,
                   "warning": "Keyword matches are heuristics; manually score answers before reporting accuracy."},
                  f, indent=2, ensure_ascii=False)

    print("\n" + "="*65 + "\nSUMMARY (keyword heuristic, NOT validated accuracy)\n" + "="*65)
    for label in ["baseline", "optimized"]:
        successful = [x for x in rows if not x.get(f"{label}_error")]
        if successful:
            matches = sum(int(x.get(f"{label}_keyword_match", 0)) for x in successful)
            lat = [float(x[f"{label}_latency_seconds"]) for x in successful
                   if x.get(f"{label}_latency_seconds") not in ("", None)]
            print(f"{label.title()}: {matches}/{len(successful)} keyword matches "
                  f"({matches/len(successful)*100:.1f}%)")
            if lat:
                print(f"  Mean latency: {statistics.mean(lat):.2f}s; "
                      f"median: {statistics.median(lat):.2f}s")
    print(f"\nCSV:  {csv_path}\nJSON: {json_path}")
    print("\nManually review the answers. A valid comparison requires both endpoints to")
    print("use the same documents, retrieval setup, generator, and questions; only the")
    print("optimization stages should differ.")

if __name__ == "__main__":
    main()
