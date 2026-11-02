"""EmotionSense: facial-expression detection + personal reflection and wellbeing dashboard.

Run from the project root:
    streamlit run app.py

This file only wires things together: theme, sign-in gate, sidebar and navigation.
Pages live in src/ui/views/, the ML pipeline in src/ (predict.py, gradcam.py, ...).
"""
from html import escape

import streamlit as st

from src import config
from src.ui import state, theme
from src.ui.views import about, checkin, dashboard, detect, history, landing, model_insights, support, toolkit

st.set_page_config(page_title=config.APP_NAME, page_icon=str(config.ASSETS_DIR / "icon.svg"), layout="wide")


def build_pages() -> dict:
    pages = {
        "dashboard": st.Page(dashboard.render, title="Dashboard", icon=":material/space_dashboard:",
                             url_path="dashboard", default=True),
        "detect": st.Page(detect.render, title="Detect Emotion", icon=":material/photo_camera:", url_path="detect"),
        "checkin": st.Page(checkin.render, title="Daily Check-In", icon=":material/edit_note:", url_path="checkin"),
        "wellbeing": st.Page(toolkit.render, title="Wellbeing", icon=":material/spa:", url_path="wellbeing"),
        "history": st.Page(history.render, title="History & Insights", icon=":material/insights:",
                           url_path="history"),
        "support": st.Page(support.render, title="Find Professional Support", icon=":material/support_agent:",
                           url_path="support"),
        "insights": st.Page(model_insights.render, title="Model Insights", icon=":material/model_training:",
                            url_path="model"),
        "about": st.Page(about.render, title="About", icon=":material/info:", url_path="about"),
    }
    state.PAGES.clear()
    state.PAGES.update(pages)
    return pages


def sidebar() -> None:
    with st.sidebar:
        name = state.display_name()
        if state.is_guest():
            subtitle, status = "Not signed in", '<span class="es-status guest"><i></i>Guest · this session only</span>'
        else:
            subtitle, status = state.email(), '<span class="es-status signed"><i></i>Signed in</span>'
        st.html(f"""<div class="es-glass" style="padding:.85rem .9rem"><div class="es-profile">
            <div class="es-avatar">{escape(name[:1].upper())}</div>
            <div style="min-width:0"><div style="font-weight:700">{escape(name)}</div>
            <div class="es-small es-muted" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
            {escape(subtitle)}</div></div></div>{status}</div>""")
        if st.button("Log out", icon=":material/logout:", width="stretch", key="logout"):
            state.logout()
            st.rerun()
        st.caption("Facial-expression analysis only — not a diagnostic tool.")


def main() -> None:
    state.init()
    theme.inject_css()
    st.logo(str(config.ASSETS_DIR / "logo.svg"), icon_image=str(config.ASSETS_DIR / "icon.svg"), size="large")

    if not state.signed_in():
        landing.render()
        return

    pages = build_pages()
    nav = st.navigation({
        "Home": [pages["dashboard"]],
        "Analyze": [pages["detect"]],
        "Reflect": [pages["checkin"], pages["wellbeing"], pages["history"]],
        "Support": [pages["support"]],
        "Learn": [pages["insights"], pages["about"]],
    })
    sidebar()
    start = st.session_state.pop("start_page", None)  # set by the landing page's call-to-action buttons
    if start in pages:
        st.switch_page(pages[start])
    nav.run()


if __name__ == "__main__":  # `streamlit run app.py` executes this file as __main__
    main()
