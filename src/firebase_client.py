"""Minimal Firebase client: email/password Authentication + Firestore, over REST.

Why REST instead of the Admin SDK?
* The app acts **as the signed-in user** (with their ID token), so Firestore
  security rules decide what each user can read/write. No service-account
  credentials ever exist in this project.
* No extra heavy dependency: only ``requests``.

Data layout:  users/{uid}/checkins/{checkinId}
Security rules (firestore.rules) allow access only when request.auth.uid == uid.

Configuration (never hard-coded):
    .streamlit/secrets.toml ->  [firebase]  api_key = "..."  project_id = "..."
    or environment variables FIREBASE_API_KEY / FIREBASE_PROJECT_ID
"""
import os
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone

import requests

from src import config

AUTH_URL = "https://identitytoolkit.googleapis.com/v1/accounts:{action}?key={key}"
TOKEN_URL = "https://securetoken.googleapis.com/v1/token?key={key}"
FIRESTORE_URL = "https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents"

# Firebase error codes -> messages that are safe and helpful to show to users.
FRIENDLY_ERRORS = {
    "EMAIL_EXISTS": "An account with this email already exists. Try logging in instead.",
    "INVALID_LOGIN_CREDENTIALS": "Incorrect email or password.",
    "EMAIL_NOT_FOUND": "Incorrect email or password.",
    "INVALID_PASSWORD": "Incorrect email or password.",
    "USER_DISABLED": "This account has been disabled.",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please wait a moment and try again.",
    "WEAK_PASSWORD": "Please choose a password with at least 6 characters.",
    "INVALID_EMAIL": "Please enter a valid email address.",
    "MISSING_PASSWORD": "Please enter a password.",
    "MISSING_EMAIL": "Please enter your email address.",
    "TOKEN_EXPIRED": "Your session has expired. Please log in again.",
    "INVALID_REFRESH_TOKEN": "Your session has expired. Please log in again.",
    "PERMISSION_DENIED": "You don't have permission to access this data.",
    "OPERATION_NOT_ALLOWED": "Email/password sign-in is not enabled for this Firebase project.",
}


class FirebaseError(Exception):
    """Raised with a user-friendly message; ``code`` keeps the raw Firebase code."""

    def __init__(self, message: str, code: str = ""):
        super().__init__(message)
        self.code = code


class CloudStorageError(FirebaseError):
    """A Firestore request failed (not configured, unreachable, denied, ...).

    Cloud storage is optional: callers fall back to local storage instead of failing.
    Authentication errors stay plain ``FirebaseError``.
    """


@dataclass(frozen=True)
class FirebaseUser:
    uid: str
    email: str
    display_name: str
    id_token: str
    refresh_token: str
    expires_at: float  # unix time

    @property
    def expired(self) -> bool:
        return time.time() > self.expires_at - 60  # refresh a minute early


def load_firebase_config() -> dict | None:
    """Return {"api_key", "project_id"} from Streamlit secrets or env vars, else None."""
    api_key = project_id = None
    try:
        import streamlit as st

        section = st.secrets.get("firebase", {})
        api_key, project_id = section.get("api_key"), section.get("project_id")
    except Exception:  # no secrets.toml, or not running under Streamlit
        pass
    api_key = api_key or os.environ.get(config.FIREBASE_API_KEY_ENV)
    project_id = project_id or os.environ.get(config.FIREBASE_PROJECT_ID_ENV)
    if api_key and project_id:
        return {"api_key": api_key, "project_id": project_id}
    return None


# ---------------------------------------------------------------------------
# Firestore value encoding (REST uses typed values)
# ---------------------------------------------------------------------------
def to_firestore(value) -> dict:
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, datetime):
        return {"timestampValue": value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")}
    if isinstance(value, str):
        return {"stringValue": value}
    if isinstance(value, (list, tuple)):
        return {"arrayValue": {"values": [to_firestore(v) for v in value]}}
    if isinstance(value, dict):
        return {"mapValue": {"fields": {k: to_firestore(v) for k, v in value.items()}}}
    raise TypeError(f"Unsupported Firestore value type: {type(value).__name__}")


def from_firestore(value: dict):
    kind, inner = next(iter(value.items()))
    if kind == "nullValue":
        return None
    if kind == "integerValue":
        return int(inner)
    if kind in ("doubleValue", "booleanValue", "stringValue", "timestampValue"):
        return inner
    if kind == "arrayValue":
        return [from_firestore(v) for v in inner.get("values", [])]
    if kind == "mapValue":
        return {k: from_firestore(v) for k, v in inner.get("fields", {}).items()}
    return inner


def _decode_document(doc: dict) -> dict:
    data = {k: from_firestore(v) for k, v in doc.get("fields", {}).items()}
    data["id"] = doc["name"].rsplit("/", 1)[-1]
    return data


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class FirebaseClient:
    def __init__(self, api_key: str, project_id: str, session: requests.Session | None = None,
                 timeout: float = config.FIREBASE_TIMEOUT_S):
        self.api_key = api_key
        self.project_id = project_id
        self.http = session or requests.Session()
        self.timeout = timeout

    # -- low level -----------------------------------------------------------
    def _request(self, method: str, url: str, **kwargs) -> dict:
        try:
            response = self.http.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException as err:
            raise FirebaseError("Could not reach Firebase. Check your internet connection.", "NETWORK") from err
        if response.status_code >= 400:
            try:
                error = response.json().get("error", {})
            except ValueError:
                error = {}
            # Auth puts a code in "message" ("WEAK_PASSWORD : Password should be..."); Firestore puts a
            # sentence there and the code in "status" ("NOT_FOUND" when the database doesn't exist).
            code = str(error.get("message") or "").split(" ")[0].split(":")[0]
            if not code.isupper():
                code = str(error.get("status") or "") or f"HTTP_{response.status_code}"
            raise FirebaseError(FRIENDLY_ERRORS.get(code, "Something went wrong. Please try again."), code)
        try:
            return response.json() if response.content else {}
        except ValueError as err:
            raise FirebaseError("Something went wrong. Please try again.", "BAD_RESPONSE") from err

    def _auth(self, action: str, payload: dict) -> dict:
        return self._request("POST", AUTH_URL.format(action=action, key=self.api_key), json=payload)

    @staticmethod
    def _user_from(data: dict, display_name: str | None = None) -> FirebaseUser:
        return FirebaseUser(
            uid=data["localId"],
            email=data.get("email", ""),
            display_name=display_name if display_name is not None else data.get("displayName", ""),
            id_token=data["idToken"],
            refresh_token=data["refreshToken"],
            expires_at=time.time() + int(data.get("expiresIn", 3600)),
        )

    # -- authentication ------------------------------------------------------
    def sign_up(self, email: str, password: str, display_name: str = "") -> FirebaseUser:
        data = self._auth("signUp", {"email": email, "password": password, "returnSecureToken": True})
        user = self._user_from(data, display_name)
        if display_name:
            self._auth("update", {"idToken": user.id_token, "displayName": display_name, "returnSecureToken": False})
        return user

    def sign_in(self, email: str, password: str) -> FirebaseUser:
        data = self._auth("signInWithPassword", {"email": email, "password": password, "returnSecureToken": True})
        return self._user_from(data)

    def send_password_reset(self, email: str) -> None:
        self._auth("sendOobCode", {"requestType": "PASSWORD_RESET", "email": email})

    def refresh(self, user: FirebaseUser) -> FirebaseUser:
        """Exchange the refresh token for a new ID token (ID tokens expire after 1 hour)."""
        data = self._request("POST", TOKEN_URL.format(key=self.api_key),
                             data={"grant_type": "refresh_token", "refresh_token": user.refresh_token})
        return replace(user, id_token=data["id_token"], refresh_token=data["refresh_token"],
                       expires_at=time.time() + int(data.get("expires_in", 3600)))

    # -- Firestore (always scoped to the signed-in user's own path) -----------
    def _collection_url(self, user: FirebaseUser, collection: str) -> str:
        return f"{FIRESTORE_URL.format(project=self.project_id)}/users/{user.uid}/{collection}"

    @staticmethod
    def _headers(user: FirebaseUser) -> dict:
        return {"Authorization": f"Bearer {user.id_token}"}

    def _firestore(self, method: str, url: str, user: FirebaseUser, **kwargs) -> dict:
        """A Firestore request; any failure is raised as CloudStorageError (cloud storage is optional)."""
        try:
            return self._request(method, url, headers=self._headers(user), **kwargs)
        except FirebaseError as err:
            raise CloudStorageError(str(err), err.code) from err

    def add_document(self, user: FirebaseUser, collection: str, data: dict) -> str:
        body = {"fields": {k: to_firestore(v) for k, v in data.items()}}
        doc = self._firestore("POST", self._collection_url(user, collection), user, json=body)
        try:
            return doc["name"].rsplit("/", 1)[-1]
        except (KeyError, AttributeError) as err:
            raise CloudStorageError("Something went wrong. Please try again.", "BAD_RESPONSE") from err

    def list_documents(self, user: FirebaseUser, collection: str, limit: int = config.HISTORY_FETCH_LIMIT) -> list[dict]:
        docs, token = [], None
        while len(docs) < limit:
            params = {"pageSize": min(300, limit - len(docs))}
            if token:
                params["pageToken"] = token
            page = self._firestore("GET", self._collection_url(user, collection), user, params=params)
            try:
                docs.extend(_decode_document(d) for d in page.get("documents", []))
            except (KeyError, AttributeError, StopIteration) as err:
                raise CloudStorageError("Something went wrong. Please try again.", "BAD_RESPONSE") from err
            token = page.get("nextPageToken")
            if not token:
                break
        return docs

    def delete_document(self, user: FirebaseUser, collection: str, doc_id: str) -> None:
        if not doc_id or "/" in doc_id or doc_id in (".", ".."):
            raise FirebaseError("Invalid entry id.", "INVALID_ID")  # never let an id escape the user's path
        self._firestore("DELETE", f"{self._collection_url(user, collection)}/{doc_id}", user)
