"""Runtime settings for the inference API, read from environment variables (never hard-coded)."""
import os
from dataclasses import dataclass, field


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    return default if value is None else value.strip().lower() in ("1", "true", "yes", "on")


def _list(name: str, default: str) -> list[str]:
    return [item.strip().rstrip("/") for item in os.environ.get(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    # Browsers may call the API only from these origins (the Vercel site, plus localhost for development).
    allowed_origins: list[str] = field(default_factory=lambda: _list("ALLOWED_ORIGINS", "http://localhost:3000"))
    # Optional regex for Vercel preview deployments, e.g. ^https://emotionsense-[a-z0-9-]+\.vercel\.app$
    allowed_origin_regex: str | None = field(default_factory=lambda: os.environ.get("ALLOWED_ORIGIN_REGEX") or None)
    # Require a valid Firebase ID token on /api/predict. Turn off only for local development.
    require_auth: bool = field(default_factory=lambda: _bool("REQUIRE_AUTH", True))
    # Firebase project whose ID tokens are accepted (public identifier, not a secret).
    firebase_project_id: str = field(default_factory=lambda: os.environ.get("FIREBASE_PROJECT_ID", ""))
    max_upload_mb: float = field(default_factory=lambda: float(os.environ.get("MAX_UPLOAD_MB", "5")))
    max_image_pixels: int = field(default_factory=lambda: int(os.environ.get("MAX_IMAGE_PIXELS", "25000000")))
    max_faces: int = field(default_factory=lambda: int(os.environ.get("MAX_FACES", "10")))

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)


def get_settings() -> Settings:
    return Settings()
