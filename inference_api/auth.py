"""Firebase ID-token verification for the inference API.

The web app sends the signed-in user's Firebase ID token as ``Authorization: Bearer <token>``.
Verifying it needs only the (public) project ID: Google's public signing certificates are
fetched over HTTPS. No service-account credentials are used.
"""
import logging

from fastapi import Depends, Header

from inference_api.errors import ApiError
from inference_api.settings import Settings, get_settings

log = logging.getLogger(__name__)


def verify_firebase_token(token: str, project_id: str) -> str:
    """Return the user's uid, or raise ApiError(401)."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    try:
        claims = id_token.verify_firebase_token(token, google_requests.Request(), audience=project_id)
    except Exception as err:  # expired, malformed, wrong signature, network failure fetching certificates
        log.info("Rejected Firebase token: %s", type(err).__name__)
        raise ApiError(401, "unauthorized", "Your session has expired. Please sign in again.") from err
    if not claims or claims.get("iss") != f"https://securetoken.google.com/{project_id}" or not claims.get("sub"):
        raise ApiError(401, "unauthorized", "Your session has expired. Please sign in again.")
    return claims["sub"]


def current_user(authorization: str | None = Header(default=None),
                 settings: Settings = Depends(get_settings)) -> str | None:
    """FastAPI dependency: the caller's uid (None when auth is disabled for local development)."""
    if not settings.require_auth:
        return None
    if not settings.firebase_project_id:
        log.error("REQUIRE_AUTH is on but FIREBASE_PROJECT_ID is not set")
        raise ApiError(503, "not_configured", "The prediction service is not configured yet.")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ApiError(401, "unauthorized", "Please sign in to analyse images.")
    return verify_firebase_token(token.strip(), settings.firebase_project_id)
