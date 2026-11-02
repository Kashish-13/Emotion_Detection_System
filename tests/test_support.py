"""Professional support: only verified providers are shown, filters work, and contacts cite official sources."""
from urllib.parse import parse_qs, urlparse

from src import support

VALID = {"id": "x", "name": "Example Hospital", "type": "Hospital / Institute", "specialties": ["Psychiatry"],
         "city": "Pune", "region": "Maharashtra", "country": "India", "source_url": "https://example.org/",
         "verified_on": "2026-11-02"}


def test_unverified_entries_are_never_shown():
    assert support.verified_providers([VALID]) == [VALID]
    for broken in ({**VALID, "source_url": None}, {**VALID, "source_url": "http://insecure.example"},
                   {**VALID, "verified_on": "recently"}, {**VALID, "type": "Healer"}, {**VALID, "name": ""}):
        assert support.verified_providers([broken]) == []
    assert support.verified_providers([None, "x", 3]) == []


def test_every_listed_provider_is_valid_and_unique():
    assert support.verified_providers(support.PROVIDERS) == support.PROVIDERS
    assert len({p["id"] for p in support.PROVIDERS}) == len(support.PROVIDERS)


def test_filters():
    other = {**VALID, "id": "y", "type": "Psychiatrist", "city": "Delhi", "region": "Delhi"}
    providers = [VALID, other]
    assert support.filter_providers(providers) == providers
    assert support.filter_providers(providers, " pune") == [VALID]
    assert support.filter_providers(providers, "INDIA") == providers
    assert support.filter_providers(providers, professional_type="Psychiatrist") == [other]
    assert support.filter_providers(providers, "Mumbai") == []


def test_listing_search_links_go_to_google_maps_search():
    url = support.listing_search_url("Clinical Psychologist", " Pune ")
    parsed = urlparse(url)
    assert (parsed.scheme, parsed.netloc, parsed.path) == ("https", "www.google.com", "/maps/search/")
    assert parse_qs(parsed.query) == {"api": ["1"], "query": ["clinical psychologist in pune"]}
    assert parse_qs(urlparse(support.listing_search_url("Psychiatrist", "")).query)["query"] == ["psychiatrist near me"]


def test_contacts_and_links_cite_official_https_sources():
    assert [n for c in support.URGENT_CONTACTS for n in c["numbers"]] == ["112", "14416", "1-800-891-4416"]
    assert all(c["source_url"].startswith("https://") for c in support.URGENT_CONTACTS)
    assert support.INTERNATIONAL_DIRECTORY["url"].startswith("https://")
    assert all(v["url"].startswith("https://") for v in support.VERIFY_LINKS)


def test_no_diagnostic_claims():
    text = " ".join([support.MEDICAL_DISCLAIMER, support.INTRO, support.EXTERNAL_NOTE, support.EMERGENCY_TEXT]).lower()
    assert "does not diagnose" in text
    for claim in ("diagnoses", "can diagnose", "treats", "cures", "replaces a doctor"):
        assert claim not in text
