import os
import tempfile

import pytest

os.environ["MOCK_MODE"] = "true"

import app as app_module
from app import User, Query, Classification, create_app, db, seed_admin_user


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{path}",
        "SECRET_KEY": "test-secret",
    })
    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
            seed_admin_user()
        yield client
    try:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
        os.remove(path)
    except FileNotFoundError:
        pass


def signup_and_login(client):
    response = client.post(
        "/api/signup",
        json={"name": "Test User", "email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    login_response = client.post(
        "/api/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    return response


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "running"


def test_dashboard_shows_runtime_model_name_in_mock_mode(client):
    login = client.post("/api/login", json={"email": "admin@fsis.local", "password": "Admin@1234"})
    assert login.status_code == 200

    response = client.get("/dashboard")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Rule-based fallback" in html


def test_signup_and_duplicate_signup(client):
    signup_response = client.post(
        "/api/signup",
        json={"name": "Test User", "email": "test@example.com", "password": "password123"},
    )
    assert signup_response.status_code == 201

    duplicate_response = client.post(
        "/api/signup",
        json={"name": "Another User", "email": "test@example.com", "password": "password456"},
    )
    assert duplicate_response.status_code == 409


def test_login_and_incorrect_password(client):
    signup_and_login(client)
    wrong_password = client.post(
        "/api/login",
        json={"email": "test@example.com", "password": "wrong-password"},
    )
    assert wrong_password.status_code == 401


def test_admin_account_is_created_and_can_access_all_history(client):
    with client.application.app_context():
        user = db.session.query(User).filter_by(email="admin@fsis.local").first()
        assert user is not None
        assert user.is_admin is True

    login_response = client.post(
        "/api/login",
        json={"email": "admin@fsis.local", "password": "Admin@1234"},
    )
    assert login_response.status_code == 200

    admin_page = client.get("/admin")
    assert admin_page.status_code == 200

    history = client.get("/api/history")
    assert history.status_code == 200


def test_feedback_submission_and_history_filters(client):
    signup_and_login(client)
    response = client.post("/api/classify", json={"query": "Why was my UPI payment declined?"})
    assert response.status_code == 200
    query_id = response.json["query_id"]

    feedback = client.post(
        "/api/feedback",
        json={"query_id": query_id, "is_correct": True, "note": "Correct classification"},
    )
    assert feedback.status_code == 200
    assert feedback.json["success"] is True

    filtered = client.get("/api/history?category=Transaction%20Enquiry&search=UPI")
    assert filtered.status_code == 200
    assert len(filtered.json["history"]) >= 1


def test_signup_login_and_classification(client):
    signup_and_login(client)
    response = client.post("/api/classify", json={"query": "Why was my UPI transaction declined?"})
    assert response.status_code == 200
    assert response.json["category"] == "Transaction Enquiry"
    assert response.json["reason"]

    with client.application.app_context():
        assert db.session.query(User).count() == 2
        assert db.session.query(Query).count() == 1
        assert db.session.query(Classification).count() == 1

    history = client.get("/api/history")
    assert history.status_code == 200
    assert len(history.json["history"]) == 1


def test_authentication_required(client):
    response = client.post("/api/classify", json={"query": "How do I apply for a loan?"})
    assert response.status_code == 401


def test_empty_query(client):
    signup_and_login(client)
    response = client.post("/api/classify", json={"query": ""})
    assert response.status_code == 400


def test_logout_and_history_auth(client):
    signup_and_login(client)
    logout_response = client.post("/api/logout")
    assert logout_response.status_code == 200

    history_response = client.get("/api/history")
    assert history_response.status_code == 401


def test_invalid_category_is_rejected(client, monkeypatch):
    signup_and_login(client)

    def invalid_classifier(query):
        return {"category": "Made-up Category", "reason": "Invalid test response", "model_name": "unit-test"}

    monkeypatch.setattr(app_module, "classify_financial_query", invalid_classifier)
    response = client.post("/api/classify", json={"query": "What is my loan EMI?"})
    assert response.status_code == 502
    assert response.json["success"] is False


def test_history_page_respects_filters(client):
    signup_and_login(client)
    client.post("/api/classify", json={"query": "Why was my UPI transaction declined?"})
    client.post("/api/classify", json={"query": "How can I view my account statement?"})

    response = client.get("/history?category=Transaction+Enquiry&search=UPI")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Why was my UPI transaction declined?" in html
    assert "Account statement" not in html


def test_mock_mode_classification_returns_allowed_category(client):
    signup_and_login(client)
    response = client.post("/api/classify", json={"query": "How can I view my account statement?"})
    assert response.status_code == 200
    assert response.json["category"] in {
        "Account Enquiry",
        "Loan Enquiry",
        "Credit-card Enquiry",
        "Transaction Enquiry",
        "Investment Enquiry",
    }


def test_mock_classifier_prioritizes_specific_intent_keywords():
    from llm_service import classify_financial_query

    assert classify_financial_query("My UPI payment failed and I need to know why")["category"] == "Transaction Enquiry"
    assert classify_financial_query("How can I increase my credit card limit?")["category"] == "Credit-card Enquiry"
    assert classify_financial_query("How do I check my loan EMI amount?")["category"] == "Loan Enquiry"
    assert classify_financial_query("What is a mutual fund SIP? ")["category"] == "Investment Enquiry"
    assert classify_financial_query("How can I download my bank account statement?")["category"] == "Account Enquiry"
    assert classify_financial_query("How long can a credit card payment take to settle?")["category"] == "Transaction Enquiry"


def test_hindi_query_is_classified_with_mock_mode():
    from llm_service import classify_financial_query

    result = classify_financial_query("mera credit score kaisa badega")
    assert result["category"] in {
        "Credit-card Enquiry",
        "Account Enquiry",
        "Transaction Enquiry",
    }
    assert result["reason"]


def test_parse_classification_payload_accepts_wrapped_json_text():
    from llm_service import _parse_classification_payload

    payload = 'Sure, here is the result: {"category": "Credit-card Enquiry", "reason": "User is asking about credit score improvement."}'
    result = _parse_classification_payload(payload)
    assert result["category"] == "Credit-card Enquiry"
    assert "credit score" in result["reason"].lower()
