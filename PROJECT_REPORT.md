# FSIS Project Report and Technical Guide

## 1. Project Overview

**FSIS** means **Financial Services Intelligent System**. It is a Flask web application that accepts a financial customer-service question and assigns it to one of five intent categories. The purpose is routing and intent recognition: it does not answer the customer's question, access bank accounts, make transactions, or provide financial advice.

The application combines:

- A browser interface for signing up, signing in, classifying queries, reviewing history, and submitting feedback.
- A Flask API and server-rendered Jinja pages.
- SQLite persistence through Flask-SQLAlchemy.
- Either a Groq-hosted language model or a deterministic keyword fallback.
- A manually curated 200-query CSV and scripts for evaluating predictions.

The five category strings are shared across classification, validation, filters, and evaluation:

1. `Account Enquiry`
2. `Loan Enquiry`
3. `Credit-card Enquiry`
4. `Transaction Enquiry`
5. `Investment Enquiry`

The project is suitable as an academic demonstration. The current implementation is not production-ready for real banking data or customer service.

## 2. How The Parts Fit Together

```text
Browser pages (Jinja templates + CSS + JavaScript)
                     |
                     | fetch() JSON requests
                     v
       Flask routes in app.py
          |                 |
          |                 +----> llm_service.py
          |                         |-- Groq model
          |                         `-- keyword fallback
          |
          `----> Flask-SQLAlchemy ORM ----> SQLite
                     users, queries,
                     classifications, feedback

CSV dataset ---> evaluation/evaluate_model.py ---> evaluation/results.csv
                                                ---> confusion_matrix.py
```

The browser does not classify text itself. It sends the query to Flask. Flask checks the session and input, calls the classifier, validates its label, saves the query and result, and returns JSON. The browser then displays the response and optionally submits feedback.

## 3. Repository Files And Why They Exist

| Path | Purpose |
| --- | --- |
| [app.py](app.py) | Main Flask application: database models, app factory, schema setup, admin seeding, page routes, JSON API, authentication checks, and persistence. This is the central application module. |
| [llm_service.py](llm_service.py) | Classification boundary: category definitions, model prompt, Groq request and response parsing, deterministic mock classifier, and recovery behavior. |
| [config.py](config.py) | Holds environment-derived settings, but the current application does not import it. Its `MOCK_MODE` default differs from the active classifier's default; see configuration notes below. |
| [extensions.py](extensions.py) | Placeholder for future Flask extensions. The database object is currently created in `app.py`, not here. |
| [requirements.txt](requirements.txt) | Python dependency ranges used by pip. |
| [.env.example](.env.example) | Example local environment configuration. `setup.bat` copies this to `.env`. |
| `.env` | A local environment file is present in this workspace and is ignored by the repository rules. It can contain secrets and machine-specific settings; its values were deliberately not read or reproduced in this report. |
| [.gitignore](.gitignore) | Keeps environment secrets, virtual environments, caches, and local instance/database files out of Git. |
| [setup.bat](setup.bat) | Windows setup helper: creates/activates `.venv`, installs requirements, then force-copies `.env.example` over `.env`. Running it again can overwrite existing local environment settings. |
| [run.bat](run.bat) | Windows run helper: creates/activates `.venv` if needed, installs requirements, then starts `app.py`. |
| [README.md](README.md) | GitHub-facing setup, architecture, categories, routes/API, evaluation results, and repository usage guidance. |
| [PROJECT_CHECKLIST.md](PROJECT_CHECKLIST.md) | Build/sandbox checklist and suggested manual acceptance steps. Its statement that the dataset has 60 rows is outdated: the checked-in CSV has 200. |
| [LICENSE.txt](LICENSE.txt) | Says the project was created for academic coursework and third-party libraries retain their own licenses. |
| [templates/](templates/) | Jinja HTML pages for authentication, dashboard, query history, and admin records. |
| [static/css/style.css](static/css/style.css) | Application layout, colors, components, tables, and responsive rules. |
| [static/js/app.js](static/js/app.js) | Shared browser behavior, currently the logout button handler. Most page-specific interactions are inline in their templates. |
| [data/financial_queries.csv](data/financial_queries.csv) | Labeled examples used as the evaluation input. Each row has an ID, query, expected category, source URL, and query type. |
| [data/SOURCES.md](data/SOURCES.md) | Explains public-source research, paraphrasing/curation, manual labels, and the source URLs. |
| [evaluation/evaluate_model.py](evaluation/evaluate_model.py) | Runs each CSV query through the same Flask classification endpoint used by the web app, prints accuracy, and writes detailed prediction rows. |
| [evaluation/results.csv](evaluation/results.csv) | Detailed output from the completed 200-row live evaluation, including each expected/predicted label, correctness flag, reason, and query type. |
| [evaluation/live_query_examples.csv](evaluation/live_query_examples.csv) | Saved real live Groq smoke-test inputs, classifications, reasons, and model name. |
| [evaluation/confusion_matrix.py](evaluation/confusion_matrix.py) | Prints a text confusion matrix from `results.csv`; it does not train a model or calculate a plotted matrix. |
| [evaluation/confusion_matrix.txt](evaluation/confusion_matrix.txt) | Saved confusion matrix generated from the completed live evaluation, with class abbreviations explained by the report. |
| [evaluation/generate_results_image.py](evaluation/generate_results_image.py) | Rebuilds the evaluation PNG from the structured `results.csv` data using Pillow. |
| [evaluation/results_visualization.png](evaluation/results_visualization.png) | Generated image summarizing overall results, confusion matrix, category scores, and query-type scores. |
| [tests/test_api.py](tests/test_api.py) | Pytest coverage for API routes, sessions, persistence, filtering, admin access, fallback classification, and response parsing. |
| `instance/fsis.db` | The workspace currently contains this local SQLite database. It is runtime state and is ignored by Git; its records were not inspected. Flask-SQLAlchemy resolves the default relative database URI here. |

The workspace also contains `.venv/`, `.git/`, Python bytecode/cache directories, and pytest cache. These are environment, version-control, or generated artifacts rather than application source. The virtual environment and caches were not inventoried file-by-file.

## 4. Main Runtime Flow

### 4.1 Application creation

`app.py` defines `create_app(test_config=None)`. It creates the Flask object, loads defaults and optional test overrides, initializes SQLAlchemy, creates any missing tables, and seeds the administrator account. The module then calls `create_app()` at import time to expose the runnable global `app`.

The default database URI is `sqlite:///fsis.db`. With Flask-SQLAlchemy's Flask-relative SQLite behavior, this normally resolves under the Flask instance directory. `DATABASE_URL` can override it. `MAX_CONTENT_LENGTH` caps a request body at 64 KiB and `QUERY_MAX_LENGTH` defaults to 1,000 characters.

### 4.2 Signup and login

The signup form posts JSON to `/api/signup`. The route trims the name and email, lowercases the email, checks required fields, name/email maximum lengths of 120/255 characters, a basic email shape (`@` and a dot after the final `@`), and an eight-character minimum password. It hashes the password with Werkzeug's password-hashing helpers before saving a `User`. Duplicate email is checked before insert and caught again as a database `IntegrityError` to handle a race. A successful signup clears the old session and stores the new user's integer ID in the session, returning HTTP 201.

Login looks up the normalized email and compares the submitted password with its hash. It returns the same error for an unknown email and a wrong password, which avoids revealing which emails are registered. Successful login also clears and resets the session. Logout clears it.

The browser session is Flask's signed cookie session. The cookie contains session data protected by `SECRET_KEY`; the password itself is not stored in the cookie or database.

### 4.3 Classification request

The dashboard's JavaScript sends `{ "query": "..." }` to `POST /api/classify`.

1. `login_required` checks for `user_id` in the session. An unauthenticated API request receives HTTP 401 JSON.
2. The route strips the query and rejects empty input or text longer than the configured maximum (HTTP 400).
3. It invokes `classify_financial_query()` in `llm_service.py`.
4. Classifier exceptions become a generic HTTP 503 response. A non-dictionary or category outside the exact five allowed strings becomes HTTP 502.
5. It inserts a `Query`, flushes the session to obtain its database ID, inserts its `Classification`, and commits both.
6. It returns the ID, category, reason, and model name (the JSON property is called `model`).

The database is written only after classification returns a valid category. Thus a failed classification does not normally leave a saved query record.

### 4.4 History, administration, and feedback

Normal users only see their own query records. Admin users see all records through both history views and the admin page. The category and text filters are applied in Python after rows are retrieved; search is a case-insensitive substring match on query text. There is no pagination, so all matching user's records (or all records for an admin) are loaded before filtering.

Feedback is one-to-one with a query. The API checks that the target query exists and belongs to the caller, unless the caller is an admin. A missing `query_id` or missing `is_correct` returns HTTP 400; a nonexistent or unauthorized query returns HTTP 404. It then creates or updates the feedback row. `is_correct` is converted with Python's `bool()` (so a nonempty string such as `"false"` becomes true), and an empty submitted note preserves any previously stored note. Feedback does not currently retrain or modify the classifier; it is recorded data only.

## 5. Database Design

The SQLAlchemy models in `app.py` represent four tables:

| Table / model | Important data | Relationship and reason |
| --- | --- | --- |
| `users` / `User` | Integer primary key; required `name` (`String(120)`); required unique/indexed `email` (`String(255)`); required `password_hash` (`String(255)`); required `is_admin` boolean (Python default false); required UTC `created_at`. | One user can own many queries. `queries` has ORM `all, delete-orphan` cascade from its user. |
| `queries` / `Query` | Integer primary key; required indexed `user_id` foreign key; required `query_text` (`Text`); required UTC `created_at`. | Each submitted text has one-to-zero-or-one classification and feedback relationships; both child relationships use `all, delete-orphan` cascade. |
| `classifications` / `Classification` | Integer primary key; required unique/indexed `query_id` foreign key; required `category` (`String(60)`), `reason` (`Text`), `model_name` (`String(120)`), and UTC `created_at`. | Separate result record; unique `query_id` enforces at most one classification per query. |
| `feedback` / `Feedback` | Integer primary key; required unique/indexed `query_id` foreign key; required `is_correct` boolean (Python default true); optional `note` (`Text`); required UTC `created_at`. | Separate human assessment; unique `query_id` enforces at most one feedback record per query. |

IDs are integer primary keys. Foreign keys connect the records. Timestamps use UTC-aware `datetime.now(timezone.utc)` defaults. `db.create_all()` creates tables, but it is not a complete migration system; the only explicit compatibility migration adds `users.is_admin` if an older database lacks it.

## 6. Classification Methods And Algorithms

### 6.1 Live Groq language-model path

`llm_service.py` defines `SYSTEM_PROMPT` with the five category descriptions and instructions to select one primary intent, avoid giving advice, and return structured fields. The live call uses the configured Groq model, temperature `0`, and a 256-token completion budget. The request includes the system instructions and the user's query.

The response parser:

- Trims the response and removes a surrounding Markdown JSON code fence if present.
- Tries parsing the complete text as JSON, then tries to extract a JSON object from surrounding text.
- Requires an object with an allowed `category` and non-empty string `reason`.
- Adds the configured model name to the returned internal dictionary.

If the first completion request or response parse fails, the code retries with a slightly more permissive instruction and temperature `0.1`. If the second completion/parse attempt fails, it uses the keyword fallback and labels the result `Rule-based fallback (API recovery)`. This recovery block does not cover every possible setup failure: missing key, failure to import the Groq SDK, or failure constructing the `Groq` client happens before the request retry block and propagates to the Flask route as HTTP 503.

There is an important exception to that recovery behavior: if `GROQ_API_KEY` is missing, the function raises before the retry block. In that case the Flask endpoint returns HTTP 503; it does not automatically switch to mock mode. To guarantee offline behavior, set `MOCK_MODE=true`.

### 6.2 Deterministic offline keyword method

When `MOCK_MODE=true`, `_mock_classify()` lowercases the query, normalizes punctuation with `[^a-z0-9\s]` replacement for token matching, and defines weighted phrase lists for each category. Phrase-substring matches use the lowercased original text; token matching uses the normalized word set. There is no stemming, stop-word removal, or language detection. A small list of Romanized Hindi/Hinglish phrases is present, but the live prompt only explicitly asks for English or Hindi classification.

The scoring procedure is:

1. Start each category at score zero.
2. Add 5 for every configured phrase that occurs as a substring in the lowercased query.
3. Add 2 when a one-word phrase appears as a token in the normalized word set.
4. Apply additional hand-written boosts or penalties for known conflicts, such as credit score, failed UPI/payment, account statement, card payment settlement, or a query containing both transaction and loan terms.
5. Select the category with the largest score. Python's `max` resolves ties by first occurrence in `ALLOWED_CATEGORIES` order.
6. If every score is zero, return `Account Enquiry` as a default.

The extra score rules are additive and run after phrase scoring: `credit` plus `score` adds 10 to Credit-card; `cibil` or (`score` plus `badh`) adds 8; `credit` plus `card` adds 6; `loan` plus `emi` adds 6 to Loan; any of `upi`/`payment`/`transaction` combined with any of `failed`/`pending`/`declined`/`successful` adds 6 to Transaction; `account` plus `statement` adds 5 to Account; `transaction` plus `loan` adds 4 to Transaction; `settle` or `settlement` combined with `payment`/`transaction`/`upi`/`transfer` adds 20 to Transaction and subtracts 8 from Credit-card; `statement` plus `credit card` or `card` adds 2 to Credit-card; `payment` plus `card` adds 6 to Transaction if any of `settle`, `settlement`, `transaction`, `payment failed`, or `payment pending` occurs, otherwise adds 3 to Credit-card; and `payment` plus `loan` adds 2 to Transaction. The Python `or`/`and` expression for the CIBIL rule means it is equivalent to `cibil OR (score AND badh)`.

Every matching phrase entry contributes independently, including duplicate phrases present in the lists. Consequently duplicates can add the same phrase score more than once. The winning score is selected with `max()` over `ALLOWED_CATEGORIES`; equal scores favor the earliest category in that list: Account, Loan, Credit-card, Transaction, then Investment.

This is a rules/keyword classifier, not a trained machine-learning model. Its advantages are that it is instant, deterministic, free to run, and useful for demos/tests without network access. Its weaknesses are that it depends on the hand-written vocabulary, can misunderstand unseen wording or ambiguous requests, and has a potentially misleading Account Enquiry default when no keyword matches. The phrase scan is roughly proportional to the number of configured phrases times query length; token creation and single-word lookups are linear in query length on average.

### 6.3 What the system does not do

There is no local model training, embedding search, neural fine-tuning, financial transaction processing, advice generation, or automatic feedback learning in this repository. The CSV is used by evaluation, not to fit the Groq model or the fallback rules.

## 7. Web Interface And Frontend Behavior

- `base.html` supplies shared navigation, title blocks, CSS links, and the shared JavaScript include. It conditionally displays classifier/history links, an admin link for admins, and logout for signed-in users.
- `login.html` and `signup.html` render authentication forms and use `fetch()` to call the corresponding JSON APIs. A successful response navigates to `/dashboard`; API-declared failures appear in an alert. Their fetch/JSON calls do not have a `try/catch` for network or invalid-JSON failures.
- `dashboard.html` supplies a 1,000-character query textarea, three preset queries (UPI declined, credit limit in Hinglish, and KYC re-verification), a live character counter, static `Tokens: ~24` text, classify button, result/reason/model display, feedback form, and a list of supported intents. Its inline script handles classification and feedback requests, disables the classify button while waiting, and displays API/network errors.
- `history.html` renders category/search filters and a table of date, query, category, model, and feedback status.
- `admin.html` renders total user/query counts and an all-user query table.
- `static/js/app.js` wires the shared logout button to `/api/logout` and returns the browser to `/login`.
- `style.css` defines the blue/white visual theme, panels, forms, tables, and responsive breakpoints for tablet and mobile layouts. Bootstrap CSS and Google Fonts are loaded from external CDNs in `base.html`.

Some dashboard content is presentation-only: the side list labels (`Loan & Credit Enquiry`, `Credit Card Operations`, etc.) do not match the five backend category strings and mark Transaction as active regardless of the current state. The dashboard route also queries up to five recent queries, but the current template does not render that `recent_queries` value. It uses a `material-symbols-outlined` class for the `memory` label, but `base.html` does not load the Material Symbols font, so the icon font is not guaranteed to render. CSS is mostly custom, with Bootstrap 5.3.3 and Google Fonts loaded from CDNs; without network access those external assets may not load.

## 8. API Reference

| Method and path | Authentication | Purpose |
| --- | --- | --- |
| `GET /api/health` | No | Returns service name and running status. It is a simple liveness response, not a deep database/model health check. |
| `POST /api/signup` | No | Creates an account; accepts JSON or form data. Returns 201 on success, 400 for invalid input, and 409 for a duplicate email. |
| `POST /api/login` | No | Validates credentials and starts a session. Returns 401 for invalid credentials. |
| `POST /api/logout` | No | Clears the session. |
| `POST /api/classify` | Yes | Validates and classifies a query, saves query/result, returns classification JSON. |
| `GET /api/history` | Yes | Returns the caller's history, or all history for an admin; accepts optional `category` and `search` query parameters. |
| `POST /api/feedback` | Yes | Creates/updates feedback for an owned query (or any query for an admin). |

Classification request JSON has the form `{ "query": "Why was my UPI transaction declined?" }`. Successful `/api/classify` JSON contains `success`, `query_id`, `category`, `reason`, and `model` (the implementation does not call this field `model_name`). `/api/history` returns `success` and a `history` array; each item contains `id`, `query`, `category`, `reason`, `model`, and ISO-formatted `created_at`. Signup returns HTTP 201 on success; login, logout, feedback, health, and successful classification return HTTP 200.

The browser-facing pages are `GET /`, `/login`, `/signup`, `/dashboard`, `/history`, and `/admin`. Protected page routes redirect unauthenticated users to login. A non-admin requesting `/admin` is redirected to the dashboard.

## 9. Data And Evaluation

### Dataset

The current `data/financial_queries.csv` has columns `id`, `query`, `expected_category`, `source`, and `query_type`. A full CSV parse found **200 rows**, sequential unique IDs 1-200, no missing values in any column, and no duplicate query text. Every row has an expected category, source URL, and query type. The observed category distribution is:

| Category | Rows |
| --- | ---: |
| Account Enquiry | 40 |
| Loan Enquiry | 40 |
| Credit-card Enquiry | 40 |
| Transaction Enquiry | 39 |
| Investment Enquiry | 41 |

The observed query-type distribution is 125 `Normal`, 32 `Curated`, 29 `Edge case`, and 14 `Informal`. `data/SOURCES.md` identifies HDFC Bank, ICICI Bank, SEBI Investor, NPCI, and RBI public pages as sources for topic discovery and paraphrasing. Topics include accounts/KYC, loans, cards, NEFT/RTGS/UPI, mutual funds, bonds, ETFs, investment risks, complaints, and investor awareness. The project describes its process as public-source research, curation/paraphrasing, manual labeling, and edge-case creation. It explicitly says this is not a verbatim scrape or raw live customer data; see [data/SOURCES.md](data/SOURCES.md) for the complete URL list.

### Evaluation scripts

`evaluate_model.py` loads the CSV and creates a Flask test client with an in-memory SQLite database. It signs up a temporary evaluation user, sends every query to `/api/classify`, compares each prediction with `expected_category`, prints overall and category-level accuracy, writes every outcome to `evaluation/results.csv`, and prints incorrect examples. This is useful because it exercises the same API path as the web app. It also means running it overwrites the checked-in results file.

`confusion_matrix.py` reads `results.csv` and prints a compact table where rows are expected classes and columns are predicted classes. It uses the standard-library `csv` and `collections` modules; scikit-learn is not used by this script. The command only prints the matrix; its output from this run was separately saved in `evaluation/confusion_matrix.txt`.

`generate_results_image.py` reads the same results CSV and computes the displayed metrics from its rows, then writes `evaluation/results_visualization.png`. Install the declared Pillow dependency and run `python evaluation/generate_results_image.py` to regenerate the image after a new evaluation. The PNG is a visualization, not a separate evaluation run.

### Live LLM query examples

Five smoke-test prompts were submitted directly to the project's live `classify_financial_query()` service while `MOCK_MODE=false` and the configured model was `openai/gpt-oss-20b`. Each returned the shown classification and a reason; the full exact text is saved in [evaluation/live_query_examples.csv](evaluation/live_query_examples.csv).

| Query | Live result |
| --- | --- |
| Why was my UPI payment debited but the recipient did not receive it? | Transaction Enquiry |
| How can I check whether I am eligible for a personal loan? | Loan Enquiry |
| What is the difference between a direct and regular mutual fund? | Investment Enquiry |
| How do I report an unauthorized credit card transaction? | Credit-card Enquiry |
| How can I update the mobile number linked to my bank account? | Account Enquiry |

These are actual model responses from this run, not hand-written examples. The dedicated CSV preserves each exact `reason`; it is separate from the labeled benchmark and from `results.csv`.

### Verified state of checked-in results

The completed live evaluation processed all **200** dataset rows and wrote them to `results.csv`. Overall, **197 were correct and 3 were incorrect (98.50% accuracy)**. The app was configured with `MOCK_MODE=false`, a configured Groq key, and model `openai/gpt-oss-20b`. The saved output had no API `ERROR` rows. One row (ID 101) has the exact rule-fallback reason signature, so this run used the configured live Groq path with one API-recovery fallback; that fallback still classified the loan query correctly. The evaluation CSV does not have a model-name column, so this recovery case is identified from its reason text.

Category results were Account 39/40 (97.50%), Loan 40/40 (100%), Credit-card 39/40 (97.50%), Transaction 38/39 (97.44%), and Investment 41/41 (100%). By query type, results were Normal 123/125 (98.40%), Curated 32/32 (100%), Edge case 28/29 (96.55%), and Informal 14/14 (100%). The confusion matrix below uses actual categories as rows and predictions as columns. Abbreviations are Acco = Account, Loan = Loan, Cred = Credit-card, Tran = Transaction, and Inve = Investment:

| Actual \\ Predicted | Account | Loan | Credit-card | Transaction | Investment |
| --- | ---: | ---: | ---: | ---: | ---: |
| Account | 39 | 0 | 0 | 1 | 0 |
| Loan | 0 | 40 | 0 | 0 | 0 |
| Credit-card | 0 | 0 | 39 | 1 | 0 |
| Transaction | 0 | 0 | 1 | 38 | 0 |
| Investment | 0 | 0 | 0 | 0 | 41 |

The three misclassified records are: ID 44, expected Transaction but predicted Credit-card (`How long can a credit card payment take to settle?`); ID 70, expected Account but predicted Transaction (`Can I stop payment on a cheque I have already issued?`); and ID 140, expected Credit-card but predicted Transaction (`How can I dispute a cash withdrawal that I did not make on my card?`). The confusion-matrix script only prints columns for the five fixed labels, so any `ERROR` predictions in a future result file would not appear in the displayed category columns.

## 10. Configuration And Local Setup

Important environment variables:

| Variable | Purpose | Current default/source note |
| --- | --- | --- |
| `SECRET_KEY` | Signs Flask session cookies. | Active app fallback is `change-this-secret-key`; use a random private value outside local testing. |
| `DATABASE_URL` | SQLAlchemy connection string. | `sqlite:///fsis.db`. |
| `MOCK_MODE` | Chooses keyword mode versus Groq mode. | `llm_service.py` defaults to `false`; `.env.example` sets `true`; README's manual `.env` example sets `false`; unused `config.py` defaults to `true`. A local `.env` file exists but was not read, so this audit does not assert which mode that file currently selects. |
| `GROQ_API_KEY` | API credential for live classification. | Required when `MOCK_MODE=false`; keep it private. |
| `GROQ_MODEL` | Groq model identifier. | `openai/gpt-oss-20b`. |
| `QUERY_MAX_LENGTH` | Maximum accepted query size. | 1,000 characters; the dashboard textarea also has a literal 1,000-character limit. |
| `ADMIN_EMAIL` | Email for the seeded admin. | `admin@fsis.local`. |
| `ADMIN_PASSWORD` | Password for the seeded admin. | `Admin@1234`; set a private value for local use and never expose it publicly. |
| `FLASK_DEBUG` | Enables Flask debug mode in the direct-run block. | Defaults to `true`, which is for local development only. |

Typical Windows setup is to run `setup.bat`, edit `.env`, and then run `run.bat` or `python app.py`. The documented URL is `http://127.0.0.1:5000`. For offline operation, explicitly keep `MOCK_MODE=true`; for live operation, set it false and provide a valid Groq key. Install dependencies with `pip install -r requirements.txt` and run tests with `python -m pytest -q`.

`setup.bat` copies `.env.example` with `/Y`, so it overwrites an existing `.env`; do not rerun it after adding secrets/settings unless you intend to recreate that file. `run.bat` does not copy `.env.example`; it creates the virtual environment if absent, activates it, reinstalls requirements on every run, and invokes `python app.py`.

One setup caveat: `seed_admin_user()` runs whenever the app initializes. If the admin email already exists, it marks that user as admin and resets its password to the currently configured `ADMIN_PASSWORD` (or the built-in default). This behavior matters when changing local admin credentials.

## 11. Dependencies And Frameworks

- **Flask** provides the WSGI web application, routes, request/response objects, sessions, redirects, and Jinja integration.
- **Flask-SQLAlchemy / SQLAlchemy** provide ORM models, relationships, query building, and database sessions.
- **SQLite** is the zero-service local relational database; it is suitable for a coursework demo, not necessarily concurrent production workloads.
- **Werkzeug** (brought in with Flask) provides password hash generation and verification.
- **python-dotenv** loads `.env` values into process environment variables.
- **Groq SDK** calls the hosted language model when live mode is enabled.
- **Jinja** renders server-side HTML templates.
- **HTML/CSS/JavaScript and Bootstrap CSS** provide the browser UI; page logic uses browser `fetch()` for the API.
- **pytest** runs the test suite.
- The README states Python 3.10 or newer.
- **requests, pandas, and scikit-learn** are listed in requirements but are not imported by the current Python source files. The current evaluation code uses Python's built-in `csv` and `collections` instead.

The declared requirement ranges are Flask `>=3.1,<4`, Flask-SQLAlchemy `>=3.1,<4`, python-dotenv `>=1.1,<2`, groq `>=0.30,<1`, pytest `>=8,<9`, requests `>=2.31,<3`, pandas `>=2.2,<3`, and scikit-learn `>=1.6,<2`. These are version constraints, not pinned exact versions.

The project has no separate frontend build system, package.json, Docker configuration, Alembic migration setup, or test database service.

## 12. Tests And Verified Checks

`tests/test_api.py` sets `MOCK_MODE=true` before importing the app, creates a temporary SQLite database per fixture, and uses Flask's test client. Its 16 test functions cover health, the dashboard model label, signup/duplicate signup, valid and invalid login, seeded-admin access, feedback and API history filters, signup/login/classify persistence, unauthenticated classification, empty query, logout/history authentication, invalid category rejection, rendered history filters, allowed mock output, six keyword-priority examples, a Hinglish credit-score example, and JSON parsing with surrounding text. The suite does not call Groq or test live network/model behavior.

Verification performed while preparing this revised report: `python -m pytest -q` completed successfully with **16 passed** in the active workspace. A full CSV parse found 200 complete unique rows; `python evaluation/confusion_matrix.py` reproduced the matrix printed above. No live Groq request was part of the test run. `PROJECT_CHECKLIST.md` records an earlier sandbox where dependencies could not be installed because package-index network access was unavailable, and its 60-row count is stale relative to the current CSV. The `.env` values and SQLite records were intentionally not examined.
Verification performed for this report: `python -m pytest -q` passed all **16 tests** in offline mode. The complete CSV has 200 unique, populated rows; `python evaluation/evaluate_model.py` completed in live mode and saved 200 results; `python evaluation/confusion_matrix.py` produced the matrix above. Five live Groq smoke tests were saved separately. `PROJECT_CHECKLIST.md` reflects an earlier sandbox/build state and its 60-row count is stale. The `.env` values and SQLite records were intentionally not examined.

## 13. Important Limitations And Risks

1. **Development security defaults:** debug mode defaults on, the fallback secret is public, and the default admin password is known. Set private values and disable debug before any deployment.
2. **Admin password reset at startup:** the seed function resets an existing seeded admin's password on each app creation using the current environment setting.
3. **No explicit CSRF mechanism:** there are no CSRF tokens or CSRF extension. State-changing API routes primarily expect JSON and Flask's default cookie behavior may mitigate some cross-site requests, but this should be reviewed before deployment.
4. **No rate limiting or account verification:** signup and login have no throttling, email verification, password reset, or lockout controls.
5. **Classifier uncertainty:** the fallback's unknown-query default is Account Enquiry; model output is constrained by prompt and validated for category, but classification remains probabilistic in live mode.
6. **No production migration/operations setup:** `create_all()` plus one manual column addition is not a full schema migration strategy. There is no monitoring, structured audit trail, or deployment configuration.
7. **Evaluation evidence is stale:** the committed 60-row result does not cover the complete checked-in 200-row dataset. Evaluation accuracy depends on mode and configured model.
7. **Evaluation is model/configuration dependent:** the new 98.50% result measures this particular 200-query run and includes one rule-based recovery result; it is not a guarantee of future or production accuracy.
8. **Configuration duplication:** `config.py` is currently unused and disagrees with `llm_service.py` about the default for `MOCK_MODE`. The `.env.example` default also differs from the README's manual `.env` example, so use the value matching the intended mode.
9. **Setup can overwrite local settings:** `setup.bat` uses `copy /Y` to replace `.env` with `.env.example` each time it runs.
10. **Feedback is not a learning loop:** recorded feedback is not used to update the prompt, rules, model, or evaluation labels.
11. **Minor interface/API inconsistencies:** README's sample response uses `model_name`, while the implementation returns `model`; the dashboard's displayed intent names do not exactly match backend labels. Its Material Symbols icon font is not loaded, and the shown token estimate is static text.
12. **Potential feedback type pitfall:** the route uses `bool(is_correct)` rather than strictly validating a JSON boolean. The included UI sends true/false booleans, but a string such as `"false"` would be truthy if another client sends it.
13. **Classifier result validation boundary:** `llm_service.py` validates both `category` and `reason`, but `app.py` only revalidates `category`. A malformed alternate classifier result missing `reason` or `model_name` could fail while building the database row rather than receiving the intended HTTP 502 response.

## 14. Likely Viva Questions And Answers

**What problem does FSIS solve?**

It categorizes financial customer-service text by its primary intent so a downstream service team could route it. It does not answer the question or perform banking operations.

**Why are there two classifiers?**

The Groq path demonstrates an LLM integration. The deterministic keyword path provides an offline/demo mode and makes automated tests independent of an API key or network.

**Is this a machine-learning model trained on the CSV?**

No. The live path calls a configured hosted model; the local fallback is hand-written weighted keyword logic. The CSV is a labeled evaluation set only.

**How does the app stop arbitrary model categories from being stored?**

The parser and API route both check that the returned category belongs to the fixed allowed-category list. The API returns an error instead of saving an invalid category.

**Why store query, classification, and feedback separately?**

They represent different facts: the user's input, the system's result, and a later human assessment. Separate related tables preserve that distinction and allow each record to have its own fields and timestamps.

**How is each user's data protected in the app?**

Protected routes require a session. History queries are filtered to the current user, and feedback checks ownership. Admins have explicit access to all records. This is application-level access control, not a claim of production-grade security.

**What does `db.session.flush()` do in classification?**

It sends pending ORM changes to the database within the current transaction so the newly inserted query receives an ID. The classification row then uses that ID; the final commit saves both together.

**How is evaluation accuracy calculated?**

For each row, compare the predicted label with `expected_category`; divide the number of equal labels by the number of evaluated rows and multiply by 100. The checked-in 93.33% result is for 60 older rows, not the current 200-row dataset.

**Why not use accuracy alone?**

Accuracy can hide class-specific failures. The per-category results and confusion matrix show which intents are confused, though a more complete evaluation could add precision, recall, F1, confidence intervals, and a held-out dataset.

**What happens if the Groq service is unavailable?**

The code retries once with a modified prompt. If that second attempt fails, it uses the keyword fallback. Missing API credentials are detected before this retry/recovery block and produce an API error unless offline mode was enabled explicitly.

**What would need to change before production use?**

Use managed secrets and a strong secret key, disable debug, replace default credentials, add CSRF defenses and rate limiting, adopt a production database and migrations, add operational monitoring, evaluate on a representative independently labeled dataset, and review privacy/data-retention requirements.

## 15. One-Minute Project Summary

FSIS is a Flask and SQLite web application for classifying financial-service queries into five intent categories. Users authenticate, submit text, receive a category and reason from either Groq or an offline weighted-keyword fallback, and can review past queries and leave feedback. SQLAlchemy stores users, queries, results, and feedback. A 200-row curated CSV is available for evaluation, while the checked-in results file is an earlier 60-row run. The tests pass in offline mode. The project demonstrates web/API integration and intent classification, but its development credentials, debug defaults, basic rule classifier, and limited deployment/security controls mean it should remain an educational prototype.