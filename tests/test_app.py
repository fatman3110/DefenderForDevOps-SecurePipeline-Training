"""
機能ユニットテスト。

セキュリティスキャンとは別に、アプリの基本機能が動作することを検証する。
脆弱性を修正した後も、これらのテストが通ることで機能のデグレードがないことを確認できる。
一般的なCI/CDパイプラインでも単体テストや連結テストが行われる。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


def test_index_returns_200(client):
    """トップページが表示できる。"""
    resp = client.get("/")
    assert resp.status_code == 200


def test_login_page_returns_200(client):
    """ログインページが表示できる。"""
    resp = client.get("/login")
    assert resp.status_code == 200


def test_login_success_redirects_to_profile(client):
    """正しい資格情報でログインするとプロフィールへリダイレクトされる。"""
    resp = client.post(
        "/login",
        data={"username": "alice", "password": "alice-password"},
    )
    assert resp.status_code == 302
    assert "/profile/1" in resp.headers["Location"]


def test_login_failure_shows_error(client):
    """誤った資格情報ではログインページに留まる。"""
    resp = client.post(
        "/login",
        data={"username": "alice", "password": "wrong"},
    )
    assert resp.status_code == 200


def test_profile_requires_login(client):
    """未ログインでプロフィールにアクセスするとログインへリダイレクトされる。"""
    resp = client.get("/profile/1")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_shows_own_data_after_login(client):
    """ログイン後は自分のプロフィールを表示できる。"""
    client.post(
        "/login",
        data={"username": "alice", "password": "alice-password"},
    )
    resp = client.get("/profile/1")
    assert resp.status_code == 200
    assert "Alice Anderson" in resp.get_data(as_text=True)


def test_search_returns_200(client):
    """検索ページが表示できる。"""
    resp = client.get("/search?q=test")
    assert resp.status_code == 200
    assert "test" in resp.get_data(as_text=True)
