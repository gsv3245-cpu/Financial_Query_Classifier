import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///fsis.db")
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
