import json
import os
import re
from typing import Dict

from dotenv import load_dotenv

load_dotenv()

ALLOWED_CATEGORIES = [
    "Account Enquiry",
    "Loan Enquiry",
    "Credit-card Enquiry",
    "Transaction Enquiry",
    "Investment Enquiry",
]

MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

SYSTEM_PROMPT = """
You are FSIS, a financial-services query classification system.

Classify the customer's query into exactly ONE of these five categories:
1. Account Enquiry
2. Loan Enquiry
3. Credit-card Enquiry
4. Transaction Enquiry
5. Investment Enquiry

Classification rules:
- Account Enquiry: questions about opening, closing, maintaining, accessing, or understanding a bank account, balance, statements, KYC for a bank account, account details, or account services.
- Loan Enquiry: questions about borrowing, loan eligibility, application, EMI, interest, tenure, repayment, or loan status.
- Credit-card Enquiry: questions specifically about credit cards, credit limits, card bills, card rewards, card eligibility, card PIN, card activation, or card fees.
- Transaction Enquiry: questions about a specific payment, transfer, UPI/NEFT/RTGS/IMPS transaction, pending/failed/reversed transaction, or money sent/received.
- Investment Enquiry: questions about investing, shares, bonds, mutual funds, ETFs, SIPs, portfolio, investment risk, or investment products.

If multiple categories appear, choose the customer's primary intent. Do not provide financial advice or recommendations. Return only the requested structured fields.
"""


def _mock_classify(query: str) -> Dict[str, str]:
    """Deterministic offline fallback so the project can run without an API key."""
    text = query.lower()
    normalized = re.sub(r"[^a-z0-9\s]", " ", text)
    terms = set(normalized.split())

    weights = {category: 0 for category in ALLOWED_CATEGORIES}
    phrases = {
        "Account Enquiry": [
            "account statement", "bank account", "savings account", "current account",
            "balance", "account balance", "kyc", "passbook", "account details",
            "open account", "close account", "update mobile", "statement"
        ],
        "Loan Enquiry": [
            "loan", "loan emi", "emi", "home loan", "personal loan", "education loan",
            "loan repayment", "repayment schedule", "loan eligibility", "borrow",
            "borrowing", "interest rate", "tenure", "outstanding loan"
        ],
        "Credit-card Enquiry": [
            "credit card", "card limit", "credit limit", "credit-card", "card bill",
            "pay credit card", "credit card statement", "card payment", "reward points",
            "card pin", "card activation", "minimum amount due", "due date"
        ],
        "Transaction Enquiry": [
            "transaction", "upi", "neft", "rtgs", "imps", "transfer", "payment failed",
            "payment pending", "reversed transaction", "merchant", "debited", "failed payment",
            "pending transaction", "settlement", "refund", "receiver", "sender", "transaction status"
        ],
        "Investment Enquiry": [
            "invest", "investment", "mutual fund", "sip", "shares", "stocks", "bond",
            "etf", "portfolio", "demat", "nav", "risk", "return", "investing"
        ],
    }

    for category, category_phrases in phrases.items():
        for phrase in category_phrases:
            if phrase in text:
                weights[category] += 5

    for category, category_phrases in phrases.items():
        for phrase in category_phrases:
            words = phrase.split()
            if len(words) == 1 and words[0] in terms:
                weights[category] += 2

    if "credit" in text and "card" in text:
        weights["Credit-card Enquiry"] += 6
    if "loan" in text and "emi" in text:
        weights["Loan Enquiry"] += 6
    if ("upi" in text or "payment" in text or "transaction" in text) and ("failed" in text or "pending" in text or "declined" in text or "successful" in text):
        weights["Transaction Enquiry"] += 6
    if "account" in text and "statement" in text:
        weights["Account Enquiry"] += 5
    if "transaction" in text and "loan" in text:
        weights["Transaction Enquiry"] += 4
    if "settle" in text or "settlement" in text:
        if "payment" in text or "transaction" in text or "upi" in text or "transfer" in text:
            weights["Transaction Enquiry"] += 20
            weights["Credit-card Enquiry"] -= 8
    if "statement" in text and ("credit card" in text or "card" in text):
        weights["Credit-card Enquiry"] += 2
    if "payment" in text and "card" in text:
        if "settle" in text or "settlement" in text or "transaction" in text or "payment failed" in text or "payment pending" in text:
            weights["Transaction Enquiry"] += 6
        else:
            weights["Credit-card Enquiry"] += 3
    if "payment" in text and "loan" in text:
        weights["Transaction Enquiry"] += 2

    category = max(weights, key=weights.get)
    if max(weights.values()) == 0:
        category = "Account Enquiry"

    return {
        "category": category,
        "reason": f"The query contains terms and intent that most strongly match {category.lower()}.",
        "model_name": "Rule-based fallback",
    }


def _parse_classification_payload(raw_content: str) -> Dict[str, str]:
    text = (raw_content or "").strip()
    if not text:
        raise RuntimeError("Groq returned an empty response.")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise RuntimeError("Groq returned a response that could not be parsed as JSON.") from None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Groq returned a response that could not be parsed as JSON.") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("Groq returned an invalid classification payload.")

    category = parsed.get("category")
    reason = parsed.get("reason")
    if category not in ALLOWED_CATEGORIES or not isinstance(reason, str) or not reason.strip():
        raise RuntimeError("Groq returned an invalid classification payload.")

    return {"category": category, "reason": reason.strip(), "model_name": MODEL_NAME}


def classify_financial_query(query: str) -> Dict[str, str]:
    if MOCK_MODE:
        return _mock_classify(query)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured. Add it to your .env file or set MOCK_MODE=true for offline demo mode.")

    try:
        from groq import Groq
    except ImportError as exc:
        raise RuntimeError("The groq package is not installed. Run: pip install -r requirements.txt") from exc

    client = Groq(api_key=api_key)
    system_message = (
        SYSTEM_PROMPT
        + "\nReturn only valid JSON with exactly two keys: 'category' and 'reason'."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_completion_tokens=256,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "financial_query_classification",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "enum": ALLOWED_CATEGORIES},
                            "reason": {"type": "string"},
                        },
                        "required": ["category", "reason"],
                        "additionalProperties": False,
                    },
                },
            },
        )
        content = response.choices[0].message.content
        return _parse_classification_payload(content)
    except Exception:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_completion_tokens=256,
        )
        content = response.choices[0].message.content
        return _parse_classification_payload(content)
