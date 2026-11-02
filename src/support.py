"""Professional and urgent support: verified contacts, a provider directory and public-listing searches.

Nothing here may be invented. Every contact and provider cites an official public source and the date it was
checked; a provider without ``source_url`` (https) and ``verified_on`` (YYYY-MM-DD) is never shown. Live provider
data is not fetched: there is no free, official API for individual practitioners, so the app links to public
listings for searching and to official registers for checking credentials.
"""
import re
from urllib.parse import quote_plus

CHECKED_ON = "2026-11-02"

MEDICAL_DISCLAIMER = ("EmotionSense provides AI-based emotion estimates for informational and self-awareness purposes "
                      "only. It does not diagnose mental-health conditions or replace professional medical advice.")
INTRO = ("If you feel that you need more support than an AI-based tool can provide, consider speaking with a "
         "qualified mental-health professional.")
EXTERNAL_NOTE = ("Provider information is sourced from external/public listings. Please verify credentials, "
                 "availability and consultation details before booking.")
EMERGENCY_TEXT = ("If you feel unsafe or are experiencing an emergency, contact your local emergency service or a "
                  "trusted person and seek immediate professional help.")

# Verified urgent contacts (India), each with its official source.
URGENT_CONTACTS = [
    {"name": "Emergency services (India)", "numbers": ["112"],
     "detail": "Single emergency number for police, fire and ambulance.",
     "source_url": "https://www.mha.gov.in/en/commoncontent/emergency-response-support-system-erss",
     "source_label": "Ministry of Home Affairs"},
    {"name": "Tele-MANAS mental health helpline", "numbers": ["14416", "1-800-891-4416"],
     "detail": "Free, 24×7 mental-health support from the Government of India, in many Indian languages.",
     "source_url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1866498",
     "source_label": "Press Information Bureau"},
]
INTERNATIONAL_DIRECTORY = {
    "name": "Find A Helpline", "url": "https://findahelpline.com/",
    "detail": "Outside India? Find free, confidential helplines in your country, verified by ThroughLine.",
}

# Official registers for checking a professional's registration.
VERIFY_LINKS = [
    {"title": "Psychiatrists (medical doctors)", "label": "National Medical Commission: Indian Medical Register",
     "url": "https://nmc.org.in/information-desk/indian-medical-register",
     "text": "Search by name or registration number. You can also check with the State Medical Council."},
    {"title": "Clinical psychologists", "label": "Rehabilitation Council of India",
     "url": "https://rehabcouncil.nic.in/",
     "text": "Clinical psychologists in India should be RCI-registered. Ask for their CRR number and confirm it."},
]

PROFESSIONAL_TYPES = ["Psychiatrist", "Clinical Psychologist", "Mental Health Professional", "Hospital / Institute"]

# Verified directory. Only add entries copied from an official source (the provider's own or a government website).
PROVIDERS = [
    {"id": "nimhans-bengaluru", "name": "National Institute of Mental Health and Neurosciences (NIMHANS)",
     "type": "Hospital / Institute", "qualification": None, "specialties": ["Psychiatry", "Clinical psychology"],
     "organization": None, "city": "Bengaluru", "region": "Karnataka", "country": "India",
     "consultation": "Outpatient and specialty clinics. Check the official website for current registration and "
                     "timings.",
     "source_url": "https://nimhans.ac.in/", "verified_on": "2026-11-02"},
]

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def verified_providers(providers: list) -> list[dict]:
    """Only well-formed entries that cite an official https source and a verification date."""
    def ok(p) -> bool:
        return (isinstance(p, dict) and bool(p.get("id")) and bool(p.get("name")) and bool(p.get("city"))
                and bool(p.get("country")) and p.get("type") in PROFESSIONAL_TYPES
                and isinstance(p.get("specialties"), list)
                and str(p.get("source_url", "")).startswith("https://")
                and bool(_DATE.match(str(p.get("verified_on", "")))))
    return [p for p in providers if ok(p)]


def filter_providers(providers: list[dict], location: str = "", professional_type: str = "") -> list[dict]:
    """Case-insensitive location match on city / region / country, plus an exact professional type."""
    loc = location.strip().lower()
    return [p for p in providers
            if (not loc or any(loc in (p.get(k) or "").lower() for k in ("city", "region", "country")))
            and (not professional_type or p["type"] == professional_type)]


def listing_search_url(professional_type: str, location: str) -> str:
    """A Google Maps search for public listings. Results come from Google, not from this app."""
    what = {"Hospital / Institute": "mental health hospital"}.get(professional_type,
                                                                   professional_type or "mental health professional")
    query = f"{what} in {location.strip()}" if location.strip() else f"{what} near me"
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query.lower())}"
