# Financial Services Intelligent System (FSIS)

A Flask + SQLite + Groq LLM web application for classifying financial customer queries into five required classes:

1. Account Enquiry
2. Loan Enquiry
3. Credit-card Enquiry
4. Transaction Enquiry
5. Investment Enquiry

## 1. Requirements

- Python 3.10+
- VS Code
- A Groq API key for live LLM mode

The project can also run in **offline demo mode** without an API key. Offline mode uses a deterministic keyword classifier only to prove that the complete Flask + database + UI workflow works. It is **not** the final LLM evaluation mode.

## 2. Create the environment

Windows PowerShell:

```powershell
cd FSIS
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation, use:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 3. Configure environment variables

Copy `.env.example` to `.env`.

For offline demo:

```text
MOCK_MODE=true
```

For the real Groq integration:

```text
MOCK_MODE=false
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

Never commit `.env` or your API key.

## 4. Run

```powershell
python app.py
```

Open http://127.0.0.1:5000

Create an account, sign in, and submit a query.

## 5. Run tests

```powershell
pytest -q
```

The tests use offline mode, so they do not consume Groq requests.

## 6. Run the real LLM

After adding your key and setting `MOCK_MODE=false`:

```powershell
python app.py
```

Example query:

> Why was my UPI payment declined?

The backend uses Groq Chat Completions with a structured JSON Schema response. `openai/gpt-oss-20b` is the default model because Groq currently documents it as supporting strict Structured Outputs.

## 7. Evaluate the 60-query dataset

With live Groq mode enabled:

```powershell
python evaluation/evaluate_model.py
```

This calls the Flask classification API and writes `evaluation/results.csv`.

Then:

```powershell
python evaluation/confusion_matrix.py
```

The CSV contains 60 curated/paraphrased test queries with expected categories, source URLs, and query types. Sources include public banking pages and SEBI Investor education material. The source URLs are retained in the dataset for traceability.

## 8. API endpoints

- `GET /api/health`
- `POST /api/signup`
- `POST /api/login`
- `POST /api/logout`
- `POST /api/classify`
- `GET /api/history`

## 9. Database

SQLite database: `instance/fsis.db` when Flask's instance path is used by the default configuration. If `DATABASE_URL=sqlite:///fsis.db` is used exactly as shown, Flask-SQLAlchemy resolves the relative SQLite path under Flask's instance folder.

Tables:

- `users`
- `queries`
- `classifications`

## 10. Project files

- `app.py` — Flask application, routes, authentication, database models
- `llm_service.py` — Groq integration, prompt, schema and offline fallback
- `templates/` — HTML frontend
- `static/` — CSS and JavaScript
- `data/financial_queries.csv` — 60-query evaluation dataset
- `evaluation/` — evaluation and confusion matrix scripts
- `tests/` — automated API tests

## 11. Important academic note

The application classifies query intent. It is not a financial-advice engine and should not be presented as one.

The final report should describe the dataset as researched/curated/paraphrased from public sources plus deliberately added edge cases. Do not claim that every row was directly scraped verbatim.
