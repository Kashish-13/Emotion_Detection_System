"""Find Professional Support: urgent help, a verified provider directory, public-listing searches and how to check
a professional's registration. All data comes from src/support.py, where every entry cites an official source."""
from datetime import date
from html import escape

import streamlit as st

from src import support
from src.ui import components as ui


# Links in st.html blocks use the app's primary colour, like the rest of the UI.
LINK = 'style="color:var(--es-primary);text-decoration:none;font-weight:600"'


def _date(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d %b %Y")


def _urgent_help() -> None:
    with st.container(key="glass_urgent"):
        st.html(f"""<div class="es-eyebrow">Need immediate help?</div>
            <p style="margin:.35rem 0 .2rem 0;font-weight:600">{escape(support.EMERGENCY_TEXT)}</p>
            <p class="es-small es-muted" style="margin:0">EmotionSense is not an emergency service, and the model cannot
            tell whether someone is safe.</p>""")
        cols = st.columns(len(support.URGENT_CONTACTS))
        for col, c in zip(cols, support.URGENT_CONTACTS):
            with col:
                numbers = " · ".join(f'<a href="tel:{n.replace("-", "")}" {LINK}>{escape(n)}</a>' for n in c["numbers"])
                st.html(f"""<div style="font-weight:650">{escape(c['name'])}</div>
                    <div style="font-size:1.15rem;margin:.15rem 0">📞 {numbers}</div>
                    <div class="es-small es-muted">{escape(c['detail'])}</div>
                    <a class="es-small" href="{c['source_url']}" target="_blank" rel="noopener noreferrer" {LINK}>
                    Source: {escape(c['source_label'])} ↗</a>""")
        d = support.INTERNATIONAL_DIRECTORY
        st.html(f"""<p class="es-small" style="margin:.6rem 0 0 0">{escape(d['detail'])}
            <a href="{d['url']}" target="_blank" rel="noopener noreferrer" {LINK}>{escape(d['name'])} ↗</a>
            Or call your local emergency number.</p>""")


def _provider_card(p: dict, i: int) -> None:
    with st.container(key=f"glass_provider_{i}"):
        st.html(f'<span class="es-chip">{escape(p["type"])}</span>')
        st.markdown(f"**{p['name']}**")
        rows = [("Qualification", p.get("qualification")), ("Specialty", ", ".join(p["specialties"]) or None),
                ("Clinic / Hospital", p.get("organization")),
                ("Location", ", ".join(x for x in (p["city"], p.get("region"), p["country"]) if x)),
                ("Consultation", p.get("consultation"))]
        st.markdown("\n".join(f"- **{k}:** {v}" for k, v in rows if v))  # only fields the source states
        st.link_button("View Official Profile", p["source_url"], icon=":material/open_in_new:")
        st.caption(f"Checked against the official website on {_date(p['verified_on'])}.")


def render() -> None:
    ui.page_header("Find", support.INTRO, eyebrow="Support · Professional help", accent="professional support")

    _urgent_help()

    ui.section("Search for a professional", "Choose a type and your city.")
    left, right = st.columns(2)
    with left:
        location = st.text_input("City / Location", key="sp_location", placeholder="e.g. Pune, Delhi, Karnataka")
    with right:
        kind = st.selectbox("Professional Type", ["All types", *support.PROFESSIONAL_TYPES], key="sp_type")
    kind = "" if kind == "All types" else kind

    verified = support.filter_providers(support.verified_providers(support.PROVIDERS), location, kind)
    st.markdown("##### Verified directory")
    if verified:
        cols = st.columns(2)
        for i, p in enumerate(verified):
            with cols[i % 2]:
                _provider_card(p, i)
    else:
        ui.empty_state("No verified listings match yet",
                       "We only list providers checked against an official source. Use the public-listing search "
                       "below, or call Tele-MANAS (14416) to be guided to services near you.", icon="🔎")

    st.markdown("##### Search public listings")
    where = f"in {location.strip()}" if location.strip() else "near you"
    st.caption(f"Searches Google Maps {where} in a new tab. Results come from Google's public listings, not from "
               "EmotionSense.")
    cols = st.columns(3)
    for col, t in zip(cols, ["Psychiatrist", "Clinical Psychologist", "Mental Health Professional"]):
        col.link_button(f"{t}s", support.listing_search_url(t, location), icon=":material/search:", width="stretch")
    st.warning(support.EXTERNAL_NOTE, icon=":material/verified_user:")

    ui.section("Check a professional's registration", "Official registers in India.")
    cols = st.columns(len(support.VERIFY_LINKS))
    for col, v in zip(cols, support.VERIFY_LINKS):
        with col.container(key=f"glass_verify_{v['title'][:5].lower()}"):
            st.markdown(f"**{v['title']}**")
            st.caption(v["text"])
            st.link_button(v["label"], v["url"], icon=":material/open_in_new:", width="stretch")

    st.write("")
    st.info(support.MEDICAL_DISCLAIMER, icon=":material/info:")
    st.caption(f"Contacts and links on this page were last checked on {_date(support.CHECKED_ON)}.")
