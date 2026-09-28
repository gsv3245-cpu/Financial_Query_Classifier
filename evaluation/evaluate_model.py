"""Evaluate the FSIS classifier against the curated CSV dataset.

This script calls the Flask API so the evaluation tests the same path used by the web app.
For the final assignment experiment, set MOCK_MODE=false and provide GROQ_API_KEY.
"""
import csv
import os
import sys
import time
import uuid
from pathlib import Path

# Allow importing the project when this file is run directly.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402


def main():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    client = app.test_client()

    with app.app_context():
        client.post("/api/signup", json={
            "name": "Evaluation User",
            "email": f"evaluation-{uuid.uuid4().hex[:8]}@example.com",
            "password": "evaluation123",
        })

    dataset_path = ROOT / "data" / "financial_queries.csv"
    rows = list(csv.DictReader(dataset_path.open(encoding="utf-8")))
    results = []
    for index, row in enumerate(rows, start=1):
        response = client.post("/api/classify", json={"query": row["query"]})
        data = response.get_json()
        if response.status_code != 200:
            prediction = "ERROR"
            reason = data.get("error", "Unknown error") if data else "Unknown error"
        else:
            prediction = data["category"]
            reason = data["reason"]
        results.append({
            "id": row["id"],
            "query": row["query"],
            "expected_category": row["expected_category"],
            "predicted_category": prediction,
            "correct": prediction == row["expected_category"],
            "reason": reason,
            "query_type": row["query_type"],
        })
        # Avoid accidental burst usage if a real API is being used.
        if os.getenv("MOCK_MODE", "true").lower() != "true":
            time.sleep(0.05)

    correct = sum(r["correct"] for r in results)
    total = len(results)
    print("FSIS MODEL EVALUATION")
    print("=" * 60)
    print(f"Total queries: {total}")
    print(f"Correct: {correct}")
    print(f"Incorrect: {total - correct}")
    print(f"Accuracy: {correct / total * 100:.2f}%")
    print("\nCategory-wise results:")

    categories = [
        "Account Enquiry", "Loan Enquiry", "Credit-card Enquiry",
        "Transaction Enquiry", "Investment Enquiry"
    ]
    for category in categories:
        subset = [r for r in results if r["expected_category"] == category]
        c = sum(r["correct"] for r in subset)
        print(f"- {category}: {c}/{len(subset)} ({c / len(subset) * 100:.2f}%)")

    output = ROOT / "evaluation" / "results.csv"
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"\nDetailed results saved to: {output}")

    errors = [r for r in results if not r["correct"]]
    if errors:
        print("\nMisclassified examples:")
        for r in errors:
            print(f"- {r['id']}: expected={r['expected_category']}; predicted={r['predicted_category']}; query={r['query']}")


if __name__ == "__main__":
    main()
