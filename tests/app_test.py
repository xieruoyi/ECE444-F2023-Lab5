import os
import pytest
import json
from pathlib import Path

from project.app import app, db

TEST_DB = "test.db"


@pytest.fixture
def client():
    BASE_DIR = Path(__file__).resolve().parent.parent
    app.config["TESTING"] = True
    app.config["DATABASE"] = BASE_DIR.joinpath(TEST_DB)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR.joinpath(TEST_DB)}"

    with app.app_context():
        db.create_all()  # setup
        yield app.test_client()  # tests run here
        db.drop_all()  # teardown


def login(client, username, password):
    """Login helper function"""
    return client.post(
        "/login",
        data=dict(username=username, password=password),
        follow_redirects=True,
    )


def logout(client):
    """Logout helper function"""
    return client.get("/logout", follow_redirects=True)


def test_index(client):
    response = client.get("/", content_type="html/text")
    assert response.status_code == 200


def test_database(client):
    """initial test. ensure that the database exists"""
    tester = Path("test.db").is_file()
    assert tester


def test_empty_db(client):
    """Ensure database is blank"""
    rv = client.get("/")
    assert b"No entries yet. Add some!" in rv.data


def test_login_logout(client):
    """Test login and logout using helper functions"""
    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"])
    assert b"You were logged in" in rv.data
    rv = logout(client)
    assert b"You were logged out" in rv.data
    rv = login(client, app.config["USERNAME"] + "x", app.config["PASSWORD"])
    assert b"Invalid username" in rv.data
    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"] + "x")
    assert b"Invalid password" in rv.data


def test_messages(client):
    """Ensure that user can post messages"""
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv = client.post(
        "/add",
        data=dict(title="<Hello>", text="<strong>HTML</strong> allowed here"),
        follow_redirects=True,
    )
    assert b"No entries here so far" not in rv.data
    assert b"&lt;Hello&gt;" in rv.data
    assert b"<strong>HTML</strong> allowed here" in rv.data

def test_delete_message(client):
    """Ensure the messages are being deleted"""
    rv = client.get("/delete/1")
    data = json.loads(rv.data)
    assert data["status"] == 0
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv = client.get("/delete/1")
    data = json.loads(rv.data)
    assert data["status"] == 1

def test_login_required(client):
    #add a message, then log out try deleting, then log in try deleting
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv1 = client.post(
        "/add",
        data=dict(title="<Hello>", text="<strong>HTML</strong> allowed here"),
        follow_redirects=True,
    )
    assert b"No entries here so far" not in rv1.data
    assert b"&lt;Hello&gt;" in rv1.data
    assert b"<strong>HTML</strong> allowed here" in rv1.data
    rv = logout(client)
    assert b"You were logged out" in rv.data
    rv2 = client.get("/delete/1")
    data = json.loads(rv2.data)
    assert data["status"] == 0
    assert data["message"] == "Please log in."
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv3 = client.get("/delete/1")
    data = json.loads(rv3.data)
    assert data["status"] == 1

def test_search(client):
    # add a random message, test if it can be searched, then delete it
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv1 = client.post(
        "/add",
        data=dict(title="random message", text="test random message"),
        follow_redirects=True,
    )
    assert b"No entries here so far" not in rv1.data
    assert b"random message" in rv1.data
    assert b"test random message" in rv1.data
    rv2 = client.get('/search/?query=random', content_type="html/text")
    assert rv2.status_code == 200
    assert b"random message" in rv2.data
    assert b"test random message" in rv1.data
    rv3 = client.get('/search/?query=message', content_type="html/text")
    assert rv2.status_code == 200
    assert b"random message" in rv3.data
    assert b"test random message" in rv3.data
    rv4 = client.get('/search/?query=random message', content_type="html/text")
    assert rv2.status_code == 200
    assert b"random message" in rv4.data
    assert b"test random message" in rv4.data
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv = client.get("/delete/1")
    data = json.loads(rv.data)
    assert data["status"] == 1