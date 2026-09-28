"""Create a text confusion matrix from evaluation/results.csv."""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ["Account Enquiry", "Loan Enquiry", "Credit-card Enquiry", "Transaction Enquiry", "Investment Enquiry"]

rows = list(csv.DictReader((ROOT / "evaluation" / "results.csv").open(encoding="utf-8")))
matrix = defaultdict(lambda: defaultdict(int))
for row in rows:
    matrix[row["expected_category"]][row["predicted_category"]] += 1

short = {c: c.split()[0][:4] for c in CATEGORIES}
print("Actual \\ Predicted")
print(" | ".join(["Actual"] + [short[c] for c in CATEGORIES]))
for actual in CATEGORIES:
    print(" | ".join([short[actual]] + [str(matrix[actual][pred]) for pred in CATEGORIES]))
