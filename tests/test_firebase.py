"""FirebaseClient against a fake HTTP session: requests, errors, encoding, per-user scoping."""
import json
import time

import pytest
import requests

from src import config
from src.firebase_client import (FirebaseClient, FirebaseError, FirebaseUser, from_firestore,
                                 load_firebase_config, to_firestore)
from src.storage import FirestoreHistoryStore, new_entry
from tests.fakes import FakeFirebaseClient


class FakeResponse:
    def __init__(self, status=200, body=None):
        self.status_code, self._body = status, body or {}
        self.content = json.dumps(self._body).encode()

    def json(self):
        return self._body


class FakeSession:
    """Records every request; replies from a list of queued responses."""

    def __init__(self, *responses):
        self.calls, self.responses = [], list(responses)

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        reply = self.responses.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


AUTH_OK = {"localId": "uid-A", "email": "a@x.com", "idToken": "id-A", "refreshToken": "rt-A", "expiresIn": "3600"}
USER_A = FirebaseUser("uid-A", "a@x.com", "A", "id-A", "rt-A", time.time() + 3600)


def client(*responses):
    return FirebaseClient("KEY", "proj", session=FakeSession(*responses))


def test_sign_up_creates_account_and_sets_display_name():
    c = client(FakeResponse(body=AUTH_OK), FakeResponse(body={}))
    user = c.sign_up("a@x.com", "secret1", "Kashish")
    first, second = c.http.calls
    assert "accounts:signUp?key=KEY" in first["url"]
    assert first["json"] == {"email": "a@x.com", "password": "secret1", "returnSecureToken": True}
    assert "accounts:update" in second["url"] and second["json"]["displayName"] == "Kashish"
    assert (user.uid, user.display_name, user.id_token) == ("uid-A", "Kashish", "id-A")
    assert not user.expired


def test_sign_in_and_password_reset_payloads():
    c = client(FakeResponse(body={**AUTH_OK, "displayName": "A"}), FakeResponse(body={}))
    assert c.sign_in("a@x.com", "pw1234").display_name == "A"
    c.send_password_reset("a@x.com")
    assert c.http.calls[1]["json"] == {"requestType": "PASSWORD_RESET", "email": "a@x.com"}


@pytest.mark.parametrize("code,expected", [
    ("INVALID_LOGIN_CREDENTIALS", "Incorrect email or password."),
    ("EMAIL_EXISTS", "already exists"),
    ("WEAK_PASSWORD : Password should be at least 6 characters", "at least 6 characters"),
    ("SOMETHING_NEW", "Something went wrong"),
])
def test_firebase_errors_become_friendly_messages(code, expected):
    c = client(FakeResponse(400, {"error": {"message": code}}))
    with pytest.raises(FirebaseError) as err:
        c.sign_in("a@x.com", "bad")
    assert expected in str(err.value) and err.value.code == code.split(" ")[0]


def test_network_failure_is_reported_not_raised_raw():
    c = client(requests.ConnectionError("offline"))
    with pytest.raises(FirebaseError, match="internet connection"):
        c.sign_in("a@x.com", "pw1234")


def test_refresh_replaces_tokens():
    c = client(FakeResponse(body={"id_token": "new-id", "refresh_token": "new-rt", "expires_in": "3600"}))
    stale = FirebaseUser("uid-A", "a@x.com", "A", "old", "rt-A", time.time() - 10)
    assert stale.expired
    fresh = c.refresh(stale)
    assert (fresh.id_token, fresh.refresh_token, fresh.uid) == ("new-id", "new-rt", "uid-A")
    assert c.http.calls[0]["data"] == {"grant_type": "refresh_token", "refresh_token": "rt-A"}


def test_firestore_value_encoding_roundtrip():
    value = {"s": "x", "i": 3, "f": 0.5, "b": True, "n": None, "l": [1, "a"], "m": {"k": [0.1]}}
    assert from_firestore(to_firestore(value)) == value
    assert to_firestore(7) == {"integerValue": "7"} and to_firestore(True) == {"booleanValue": True}


def test_firestore_requests_are_scoped_to_the_signed_in_user():
    doc = {"name": "projects/proj/databases/(default)/documents/users/uid-A/checkins/D1",
           "fields": {"kind": {"stringValue": "checkin"}}}
    c = client(FakeResponse(body=doc),
               FakeResponse(body={"documents": [doc], "nextPageToken": "p2"}),
               FakeResponse(body={"documents": [doc]}),
               FakeResponse(body={}))
    assert c.add_document(USER_A, "checkins", {"kind": "checkin"}) == "D1"
    docs = c.list_documents(USER_A, "checkins")
    assert [d["id"] for d in docs] == ["D1", "D1"] and docs[0]["kind"] == "checkin"  # pagination followed
    c.delete_document(USER_A, "checkins", "D1")
    for call in c.http.calls:
        assert "/documents/users/uid-A/checkins" in call["url"]
        assert call["headers"] == {"Authorization": "Bearer id-A"}
    assert c.http.calls[2]["params"]["pageToken"] == "p2"


@pytest.mark.parametrize("bad_id", ["", "../uid-B/checkins/x", "a/b", ".."])
def test_delete_rejects_ids_that_could_escape_the_users_path(bad_id):
    with pytest.raises(FirebaseError):
        client().delete_document(USER_A, "checkins", bad_id)


def test_config_from_environment(monkeypatch):
    import streamlit as st

    monkeypatch.setattr(st, "secrets", {})  # ignore any local .streamlit/secrets.toml
    monkeypatch.delenv(config.FIREBASE_API_KEY_ENV, raising=False)
    monkeypatch.delenv(config.FIREBASE_PROJECT_ID_ENV, raising=False)
    assert load_firebase_config() is None
    monkeypatch.setenv(config.FIREBASE_API_KEY_ENV, "k")
    monkeypatch.setenv(config.FIREBASE_PROJECT_ID_ENV, "p")
    assert load_firebase_config() == {"api_key": "k", "project_id": "p"}


def test_users_only_see_their_own_history():
    backend = FakeFirebaseClient()
    alice, bob = backend.sign_up("alice@x.com", "secret1"), backend.sign_up("bob@x.com", "secret2")
    store_a = FirestoreHistoryStore(backend, lambda: alice)
    store_b = FirestoreHistoryStore(backend, lambda: bob)
    store_a.add(new_entry("checkin", selfReportedMood="Good"))
    assert len(store_a.list()) == 1 and store_a.list()[0]["userId"] == alice.uid
    assert store_b.list() == []
    store_b.clear()
    assert len(store_a.list()) == 1  # Bob clearing his history never touches Alice's
