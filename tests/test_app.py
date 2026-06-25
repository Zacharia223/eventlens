"""Integration tests for the Flask routes (using the in-memory store)."""

import io

import pytest

import app as app_module


@pytest.fixture()
def client():
    app_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app_module.app.test_client() as client:
        yield client


def test_home_ok(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"EventLens" in resp.data


def test_upload_and_view_report(client):
    csv = b"event,attendees\nwebinar,100\nmeetup,40\nwebinar,75\n"
    data = {"file": (io.BytesIO(csv), "events.csv")}
    resp = client.post("/upload", data=data, content_type="multipart/form-data",
                       follow_redirects=True)
    assert resp.status_code == 200
    # The rendered report should mention the column and the row count card.
    assert b"attendees" in resp.data
    assert b"Rows" in resp.data


def test_upload_rejects_non_csv(client):
    data = {"file": (io.BytesIO(b"nope"), "image.png")}
    resp = client.post("/upload", data=data, content_type="multipart/form-data",
                       follow_redirects=True)
    assert b"Only .csv files are supported." in resp.data


def test_upload_without_file(client):
    resp = client.post("/upload", data={}, content_type="multipart/form-data",
                       follow_redirects=True)
    assert b"Please choose a CSV file" in resp.data


def test_missing_report_404(client):
    resp = client.get("/report/999999")
    assert resp.status_code == 404
