import os
from datetime import datetime, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from llm_service import classify_financial_query, ALLOWED_CATEGORIES, MODEL_NAME, MOCK_MODE

load_dotenv()

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    queries = db.relationship("Query", backref="user", lazy=True, cascade="all, delete-orphan")


class Query(db.Model):
    __tablename__ = "queries"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    query_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    classification = db.relationship("Classification", backref="query", uselist=False, cascade="all, delete-orphan")
    feedback = db.relationship("Feedback", backref="query", uselist=False, cascade="all, delete-orphan")


class Classification(db.Model):
    __tablename__ = "classifications"
    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey("queries.id"), nullable=False, unique=True, index=True)
    category = db.Column(db.String(60), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    model_name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Feedback(db.Model):
    __tablename__ = "feedback"
    id = db.Column(db.Integer, primary_key=True)
    query_id = db.Column(db.Integer, db.ForeignKey("queries.id"), nullable=False, unique=True, index=True)
    is_correct = db.Column(db.Boolean, nullable=False, default=True)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


def ensure_admin_column():
    inspector = db.inspect(db.engine)
    columns = inspector.get_columns("users")
    names = {column["name"] for column in columns}
    if "is_admin" not in names:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))


def seed_admin_user():
    ensure_admin_column()
    admin_email = os.getenv("ADMIN_EMAIL", "admin@fsis.local")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@1234")
    admin = User.query.filter_by(email=admin_email).first()
    if admin is None:
        db.session.add(User(
            name="Admin User",
            email=admin_email,
            password_hash=generate_password_hash(admin_password),
            is_admin=True,
        ))
        db.session.commit()
    else:
        admin.is_admin = True
        admin.name = admin.name or "Admin User"
        admin.password_hash = generate_password_hash(admin_password)
        db.session.commit()


def create_app(test_config=None):
    database_url = os.getenv("NEON_DATABASE_URL") or os.getenv("DATABASE_URL", "sqlite:///fsis.db")
    if database_url.startswith(("postgres://", "postgresql://")):
        database_url = "postgresql+psycopg://" + database_url.split("://", 1)[1]
    if os.getenv("VERCEL") == "1":
        if not database_url.startswith("postgresql+psycopg://"):
            raise RuntimeError("Vercel deployments require a persistent PostgreSQL DATABASE_URL.")
        secret_key = os.getenv("SECRET_KEY", "")
        if len(secret_key) < 32 or secret_key == "change-this-secret-key":
            raise RuntimeError("Set a random SECRET_KEY of at least 32 characters in Vercel.")
        admin_email = os.getenv("ADMIN_EMAIL", "").lower()
        if not admin_email or admin_email == "admin@fsis.local":
            raise RuntimeError("Set a non-default ADMIN_EMAIL in Vercel.")
        admin_password = os.getenv("ADMIN_PASSWORD", "")
        if len(admin_password) < 12 or admin_password == "Admin@1234":
            raise RuntimeError("Set a unique ADMIN_PASSWORD of at least 12 characters in Vercel.")

    app = Flask(__name__, static_folder="public/static", static_url_path="/static")
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "change-this-secret-key"),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=64 * 1024,
        QUERY_MAX_LENGTH=int(os.getenv("QUERY_MAX_LENGTH", "1000")),
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    with app.app_context():
        db.create_all()
        seed_admin_user()

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                if request.path.startswith("/api/"):
                    return jsonify({"success": False, "error": "Authentication required."}), 401
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    @app.context_processor
    def inject_user():
        user = db.session.get(User, session.get("user_id")) if session.get("user_id") else None
        runtime_model_name = "Rule-based fallback" if MOCK_MODE else MODEL_NAME
        return {"current_user": user, "runtime_model_name": runtime_model_name}

    @app.get("/")
    def index():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.get("/login")
    def login():
        return render_template("login.html")

    @app.get("/signup")
    def signup():
        return render_template("signup.html")

    @app.get("/dashboard")
    @login_required
    def dashboard():
        recent = (
            Query.query.filter_by(user_id=session["user_id"])
            .order_by(Query.created_at.desc())
            .limit(5)
            .all()
        )
        runtime_model_name = "Rule-based fallback" if MOCK_MODE else MODEL_NAME
        return render_template("dashboard.html", recent_queries=recent, runtime_model_name=runtime_model_name)

    @app.get("/history")
    @login_required
    def history():
        user = db.session.get(User, session["user_id"])
        if user and user.is_admin:
            rows = Query.query.order_by(Query.created_at.desc()).all()
        else:
            rows = Query.query.filter_by(user_id=session["user_id"]).order_by(Query.created_at.desc()).all()

        category = request.args.get("category", "").strip()
        search = request.args.get("search", "").strip().lower()
        filtered = []
        for row in rows:
            if category and (not row.classification or row.classification.category != category):
                continue
            if search and search not in row.query_text.lower():
                continue
            filtered.append(row)

        return render_template(
            "history.html",
            rows=filtered,
            categories=ALLOWED_CATEGORIES,
            current_category=category,
            current_search=search,
        )

    @app.get("/admin")
    @login_required
    def admin_dashboard():
        user = db.session.get(User, session["user_id"])
        if not user or not user.is_admin:
            return redirect(url_for("dashboard"))
        rows = Query.query.order_by(Query.created_at.desc()).all()
        return render_template("admin.html", rows=rows, total_users=User.query.count(), total_queries=Query.query.count())

    @app.post("/api/signup")
    def api_signup():
        data = request.get_json(silent=True) or request.form
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not name or not email or not password:
            return jsonify({"success": False, "error": "Name, email and password are required."}), 400
        if len(name) > 120 or len(email) > 255:
            return jsonify({"success": False, "error": "Name or email is too long."}), 400
        if len(password) < 8:
            return jsonify({"success": False, "error": "Password must contain at least 8 characters."}), 400
        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            return jsonify({"success": False, "error": "Please enter a valid email address."}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({"success": False, "error": "An account with this email already exists."}), 409

        user = User(name=name, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({"success": False, "error": "An account with this email already exists."}), 409

        session.clear()
        session["user_id"] = user.id
        return jsonify({"success": True, "message": "Account created successfully."}), 201

    @app.post("/api/login")
    def api_login():
        data = request.get_json(silent=True) or request.form
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"success": False, "error": "Invalid email or password."}), 401

        session.clear()
        session["user_id"] = user.id
        return jsonify({"success": True, "message": "Login successful."})

    @app.post("/api/logout")
    def api_logout():
        session.clear()
        return jsonify({"success": True, "message": "Logged out successfully."})

    @app.post("/api/classify")
    @login_required
    def api_classify():
        data = request.get_json(silent=True) or {}
        query_text = (data.get("query") or "").strip()
        if not query_text:
            return jsonify({"success": False, "error": "Please enter a financial query."}), 400
        if len(query_text) > app.config["QUERY_MAX_LENGTH"]:
            return jsonify({"success": False, "error": f"Query must be {app.config['QUERY_MAX_LENGTH']} characters or fewer."}), 400

        try:
            result = classify_financial_query(query_text)
        except Exception:
            app.logger.exception("LLM classification failed")
            return jsonify({"success": False, "error": "The classifier is temporarily unavailable. Please try again later."}), 503

        if not isinstance(result, dict):
            return jsonify({"success": False, "error": "The model returned an invalid classification."}), 502

        category = result.get("category")
        if category not in ALLOWED_CATEGORIES:
            return jsonify({"success": False, "error": "The model returned an invalid classification."}), 502

        q = Query(user_id=session["user_id"], query_text=query_text)
        db.session.add(q)
        db.session.flush()
        c = Classification(
            query_id=q.id,
            category=result["category"],
            reason=result["reason"],
            model_name=result["model_name"],
        )
        db.session.add(c)
        db.session.commit()

        return jsonify({
            "success": True,
            "query_id": q.id,
            "category": c.category,
            "reason": c.reason,
            "model": c.model_name,
        })

    @app.get("/api/history")
    @login_required
    def api_history():
        user = db.session.get(User, session["user_id"])
        if user and user.is_admin:
            rows = Query.query.order_by(Query.created_at.desc()).all()
        else:
            rows = Query.query.filter_by(user_id=session["user_id"]).order_by(Query.created_at.desc()).all()

        category = request.args.get("category", "").strip()
        search = request.args.get("search", "").strip().lower()
        filtered = []
        for row in rows:
            if category and (not row.classification or row.classification.category != category):
                continue
            if search and search not in row.query_text.lower():
                continue
            filtered.append(row)

        return jsonify({
            "success": True,
            "history": [
                {
                    "id": row.id,
                    "query": row.query_text,
                    "category": row.classification.category if row.classification else None,
                    "reason": row.classification.reason if row.classification else None,
                    "model": row.classification.model_name if row.classification else None,
                    "created_at": row.created_at.isoformat(),
                }
                for row in filtered
            ],
        })

    @app.post("/api/feedback")
    @login_required
    def api_feedback():
        data = request.get_json(silent=True) or {}
        query_id = data.get("query_id")
        is_correct = data.get("is_correct")
        note = (data.get("note") or "").strip()

        if query_id is None:
            return jsonify({"success": False, "error": "Query ID is required."}), 400

        row = db.session.get(Query, query_id)
        current_user = db.session.get(User, session["user_id"])
        if row is None or (not current_user.is_admin and row.user_id != session["user_id"]):
            return jsonify({"success": False, "error": "Query not found."}), 404

        if is_correct is None:
            return jsonify({"success": False, "error": "Feedback value is required."}), 400

        feedback = row.feedback or Feedback(query_id=row.id)
        feedback.is_correct = bool(is_correct)
        feedback.note = note or feedback.note
        db.session.add(feedback)
        db.session.commit()

        return jsonify({"success": True, "message": "Feedback saved."})

    @app.get("/api/health")
    def health():
        return jsonify({"success": True, "service": "FSIS", "status": "running"})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "true").lower() == "true")
