import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SEED_DATA": False,
            "REQUEUE_EXECUTIONS": False,
        }
    )
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth(client):
    response = client.post("/api/v1/auth/login", json={"email": "admin@test.local"})
    token = response.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
