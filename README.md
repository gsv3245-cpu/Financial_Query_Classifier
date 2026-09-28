# Financial Services Intelligent System (FSIS)

FSIS is a Flask-based financial query classification system that helps categorize customer service queries into one of five financial intent classes:

1. Account Enquiry
2. Loan Enquiry
3. Credit-card Enquiry
4. Transaction Enquiry
5. Investment Enquiry

The system combines a web dashboard, user authentication, query storage, admin access, and Groq-powered classification logic. It also includes an offline fallback mode so the project can run and be tested without a live API key.

---

## Purpose

The project is designed to detect the main intent behind a financial customer query. For example:

- "Why was my UPI payment failed?"
- "How can I view my bank account statement?"
- "What is my credit card limit?"
- "I want to apply for a personal loan"
- "What is a mutual fund SIP?"

This helps route the query to the right category instead of replying with financial advice.

---

## Core features

- User signup and login
- Admin account creation
- Dashboard for submitting customer queries
- Real-time classification using Groq
- Offline keyword-based fallback for local testing
- Query history tracking per user
- Admin view for all saved queries
- Feedback collection on classification correctness
- Automated API testing

---

## Technology stack

- Python 3.10+
- Flask
- Flask-SQLAlchemy
- SQLite (local development)
- Groq API
- Jinja templates
- HTML, CSS, and JavaScript frontend
- Pytest

---

## Project structure

```text
FSIS/
├── app.py
├── config.py
├── llm_service.py
├── requirements.txt
├── README.md
├── .env
├── .gitignore
├── data/
│   ├── financial_queries.csv
│   └── SOURCES.md
├── evaluation/
│   ├── confusion_matrix.py
│   ├── evaluate_model.py
│   └── results.csv
├── instance/
├── static/
│   ├── css/
│   └── js/
├── templates/
│   ├── admin.html
│   ├── base.html
│   ├── dashboard.html
│   ├── history.html
│   ├── login.html
│   └── signup.html
├── tests/
│   └── test_api.py
└── .venv/
```

---

## Local setup

### 1) Create a virtual environment

```powershell
cd "C:\path\to\FSIS"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

### 3) Configure environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
SECRET_KEY=your_local_secret_key
MOCK_MODE=false
GROQ_MODEL=openai/gpt-oss-20b
ADMIN_EMAIL=admin@fsis.local
ADMIN_PASSWORD=Admin@1234
```

Important:

- `.env` should not be committed to Git
- `MOCK_MODE=true` turns on offline fallback mode
- `MOCK_MODE=false` enables the live Groq model

---

## Default local admin credentials

For local development, the default admin user is:

- Email: `admin@fsis.local`
- Password: `Admin@1234`

These credentials are intended only for local testing and should not be exposed publicly.

---

## Run the application

Start the app:

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

The application includes:

- login page
- signup page
- dashboard for submitting queries
- history page for previous queries
- admin page for reviewing all records

---

## Mock mode vs live model mode

### Mock mode

When `MOCK_MODE=true`, the app uses a deterministic keyword-based classifier. This is useful for:

- local testing
- demo runs
- verifying the app flow without costs or API dependency
- continuous integration checks

This is not the production inference engine.

### Live Groq mode

When `MOCK_MODE=false`, the app calls the Groq API using the configured model. The default model is:

```text
openai/gpt-oss-20b
```

The app expects a structured JSON response with:

- `category`
- `reason`

---

## Testing

Run the project tests:

```powershell
pytest -q
```

The tests verify:

- health endpoint
- signup/login flow
- dashboard rendering
- classification behavior
- authentication errors
- admin permissions
- invalid response handling

---

## API endpoints

### Authentication and health

- `GET /api/health`
- `POST /api/signup`
- `POST /api/login`
- `POST /api/logout`

### Query operations

- `POST /api/classify`
- `GET /api/history`
- `POST /api/feedback`

Example request:

```http
POST /api/classify
Content-Type: application/json

{
  "query": "Why was my UPI transaction declined?"
}
```

Example response:

```json
{
  "success": true,
  "category": "Transaction Enquiry",
  "reason": "The query is about a failed or declined financial transaction.",
  "query_id": 12,
  "model_name": "openai/gpt-oss-20b"
}
```

---

## Database

The project uses SQLite for the local development database. It creates tables for:

- `users`
- `queries`
- `classifications`
- `feedback`

SQLite is suitable for academic and local testing, but a managed database is recommended for production hosting.

---

## Evaluation dataset

The project includes a curated financial query dataset in:

- `data/financial_queries.csv`

Evaluation scripts are in:

- `evaluation/evaluate_model.py`
- `evaluation/confusion_matrix.py`

These scripts generate classification result files and confusion matrix output for model analysis.

---

## Academic and reporting note

This project is intended to classify financial customer query intent. It is not a financial advice engine and should not be represented as one.

In reports or documentation, describe the dataset as curated, paraphrased, or sourced from public financial information where applicable, rather than claiming it is raw customer data from live banking systems.

---

## Security note

- Keep `.env` private
- Never commit API keys or secrets
- Use a strong secret key in non-local deployments
- Do not expose admin credentials publicly

---

## License

This project is provided for academic and educational use in accordance with the repository license.
