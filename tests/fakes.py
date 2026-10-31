"""In-memory stand-ins for Firebase, used by the tests (no network, no real project)."""
import itertools
import time

from src.firebase_client import CloudStorageError, FirebaseError, FirebaseUser


class FakeFirebaseClient:
    """Mimics FirebaseClient. Data is stored per uid, like users/{uid}/... in Firestore."""

    def __init__(self, firestore_down: bool = False):
        self.accounts = {}   # email -> (password, uid, display_name)
        self.data = {}       # uid -> {collection -> {doc_id -> dict}}
        self._ids = itertools.count(1)
        self.firestore_down = firestore_down  # Auth works, every Firestore call fails
        self.firestore_calls = 0

    def _firestore(self):
        self.firestore_calls += 1
        if self.firestore_down:
            raise CloudStorageError("Something went wrong. Please try again.", "NOT_FOUND")

    # auth -------------------------------------------------------------
    def _user(self, email):
        password, uid, name = self.accounts[email]
        return FirebaseUser(uid, email, name, f"token-{uid}", f"refresh-{uid}", time.time() + 3600)

    def sign_up(self, email, password, display_name=""):
        if email in self.accounts:
            raise FirebaseError("An account with this email already exists. Try logging in instead.", "EMAIL_EXISTS")
        if len(password) < 6:
            raise FirebaseError("Please choose a password with at least 6 characters.", "WEAK_PASSWORD")
        self.accounts[email] = (password, f"uid{next(self._ids)}", display_name)
        return self._user(email)

    def sign_in(self, email, password):
        if email not in self.accounts or self.accounts[email][0] != password:
            raise FirebaseError("Incorrect email or password.", "INVALID_LOGIN_CREDENTIALS")
        return self._user(email)

    def send_password_reset(self, email):
        if email not in self.accounts:
            raise FirebaseError("Incorrect email or password.", "EMAIL_NOT_FOUND")

    def refresh(self, user):
        return user

    # firestore ----------------------------------------------------------
    def _collection(self, user, collection):
        return self.data.setdefault(user.uid, {}).setdefault(collection, {})

    def add_document(self, user, collection, data):
        self._firestore()
        doc_id = f"doc{next(self._ids)}"
        self._collection(user, collection)[doc_id] = dict(data)
        return doc_id

    def list_documents(self, user, collection, limit=500):
        self._firestore()
        return [{**d, "id": i} for i, d in self._collection(user, collection).items()][:limit]

    def delete_document(self, user, collection, doc_id):
        self._firestore()
        self._collection(user, collection).pop(doc_id, None)


SHARED = FakeFirebaseClient()  # one backend for the whole test session (like one Firebase project)
