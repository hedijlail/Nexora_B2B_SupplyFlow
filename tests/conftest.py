import os

# Must be set before importing application modules, whose settings are loaded at import time.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/b2b_supplier_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-that-is-long-enough")
