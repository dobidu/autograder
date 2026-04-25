"""Shared test fixtures."""
import os
import sys
import tempfile

import pytest

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use temp database for tests
_tmpdir = tempfile.mkdtemp()
os.environ["STORAGE_DIR"] = _tmpdir
os.environ["SUBMISSION_RATE_LIMIT"] = "0"  # Disable rate limit in tests

from app.database import Base, engine, SessionLocal
from app.models import User
from app.security import hash_password


@pytest.fixture(autouse=True)
def reset_db():
    """Recreate all tables before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    from main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def professor(db):
    user = User(
        name="Prof Test",
        email="prof@test.com",
        password_hash=hash_password("prof123"),
        role="professor",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def student(db):
    user = User(
        name="Student Test",
        email="student@test.com",
        password_hash=hash_password("stu123"),
        role="student",
        matricula="20210001",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def prof_cookies(client, professor):
    r = client.post("/login", data={"email": "prof@test.com", "password": "prof123"}, follow_redirects=False)
    return r.cookies


@pytest.fixture
def stu_cookies(client, student):
    r = client.post("/login", data={"email": "student@test.com", "password": "stu123"}, follow_redirects=False)
    return r.cookies
