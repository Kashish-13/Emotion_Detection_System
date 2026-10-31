"""Reusable UI pieces. Every user-provided string is HTML-escaped before rendering."""
from html import escape

import altair as alt
import pandas as pd
import streamlit as st

from src import config
from src.ui import state
from src.wellbeing import ACTIVITIES, DISTRESS_NOTE, FEELING_ICONS, FEELINGS_AFTER, JOURNAL_PROMPTS


def color(emotion: str) -> str:
    return config.EMOTION_COLORS.get(emotion, "#8a8f9e")


# ---------------------------------------------------------------------------
# Basic blocks
# ---------------------------------------------------------------------------
def page_header(title: str, subtitle: str = "", eyebrow: str = "") -> None:
    st.html(f"""<div style="margin-bottom:1.1rem">
        {f'<div class="es-eyebrow">{escape(eyebrow)}</div>' if eyebrow else ''}
        <div class="es-title">{escape(title)}</div>
        {f'<p class="es-subtitle">{escape(subtitle)}</p>' if subtitle else ''}</div>""")


def stat_card(label: str, value: str, hint: str = "", emotion: str | None = None) -> None:
    dot = f'<span class="es-dot" style="--c:{color(emotion)}"></span>' if emotion else ""
    st.html(f"""<div class="es-card"><div class="es-stat-label">{escape(label)}</div>
        <div class="es-stat-value">{dot}{escape(value)}</div>
        <div class="es-stat-hint">{escape(hint) if hint else "&nbsp;"}</div></div>""")


def emotion_pill(emotion: str) -> str:
    return f'<span class="es-pill" style="--c:{color(emotion)}"><span class="es-dot" style="--c:{color(emotion)};margin:0"></span>{escape(emotion)}</span>'


def empty_state(title: str, text: str) -> None:
    st.html(f"""<div class="es-card" style="text-align:center;padding:2.2rem 1rem">
        <div style="font-size:1.25rem;font-weight:700">{escape(title)}</div>
        <div class="es-muted" style="margin-top:.35rem">{escape(text)}</div></div>""")


def note(text: str) -> None:
    st.html(f'<div class="es-muted es-small" style="margin-top:.6rem">{escape(text)}</div>')


# ---------------------------------------------------------------------------
# Detection results
# ---------------------------------------------------------------------------
LEVEL_TEXT = {"High": "High confidence", "Moderate": "Moderate confidence", "Low": "Low confidence"}


def result_card(face, title: str = "Detected expression") -> None:
    st.html(f"""<div class="es-card es-result" style="--c:{color(face.emotion)}">
        <div class="es-eyebrow">{escape(title)}</div>
        <div class="es-emotion">{escape(face.emotion.upper())}</div>
        <div class="es-confidence">{face.confidence:.0%} confidence &nbsp;
          <span class="es-pill">{LEVEL_TEXT[face.level]}</span></div></div>""")


def low_confidence_warning() -> None:
    st.warning("**Low-confidence prediction.** The model isn't very certain about this expression. "
               "Lighting, pose, face angle, or image quality can affect the result.", icon=":material/info:")


def top_bars(pairs: list[tuple[str, float]]) -> None:
    rows = "".join(
        f"""<div class="es-bar-row"><div>{escape(e)}</div>
            <div class="es-bar-track"><div class="es-bar-fill" style="--c:{color(e)};width:{p * 100:.1f}%"></div></div>
            <div class="es-bar-value">{'<1%' if p < 0.01 else f'{p:.0%}'}</div></div>""" for e, p in pairs)
    st.html(f'<div class="es-card"><div class="es-stat-label" style="margin-bottom:.3rem">Top predictions</div>{rows}</div>')


def probability_chart(probabilities: dict, height: int = 240) -> None:
    df = pd.DataFrame({"Emotion": list(probabilities), "Probability": list(probabilities.values())})
    df["Label"] = df["Probability"].map(lambda p: "<1%" if p < 0.01 else f"{p:.0%}")
    base = alt.Chart(df).encode(
        y=alt.Y("Emotion:N", sort="-x", title=None),
        x=alt.X("Probability:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%", grid=False), title=None),
        tooltip=["Emotion", alt.Tooltip("Probability:Q", format=".1%")],
    )
    bars = base.mark_bar(cornerRadiusEnd=4, height=14).encode(
        color=alt.Color("Emotion:N", scale=alt.Scale(domain=list(config.EMOTION_COLORS),
                                                      range=list(config.EMOTION_COLORS.values())), legend=None))
    text = base.mark_text(align="left", dx=4, fontSize=12).encode(text="Label:N")
    st.altair_chart((bars + text).properties(height=height), width="stretch")


# ---------------------------------------------------------------------------
# Wellbeing
# ---------------------------------------------------------------------------
def suggestion_list(items: list[tuple[str, str | None]], key_prefix: str, compact: bool = False) -> None:
    """Suggestion rows; those linked to an activity get a 'Try it' button.

    ``compact`` stacks the button under the text, for narrow columns.
    """
    for i, (text, activity_id) in enumerate(items):
        meta = (f"  \n:gray[{ACTIVITIES[activity_id]['minutes']} min · {ACTIVITIES[activity_id]['title']}]"
                if activity_id else "")
        if compact:
            left = right = st.container()
        else:
            left, right = st.columns([5, 1.3], vertical_alignment="center")
        left.markdown(f"**{text}**{meta}")
        if activity_id and right.button("Try it", key=f"{key_prefix}_{i}", icon=":material/play_arrow:",
                                        width="content" if compact else "stretch"):
            open_activity(activity_id)


def open_activity(activity_id: str) -> None:
    st.session_state.activity = activity_id
    st.session_state.pop("grounding_step", None)
    state.go("wellbeing")


def breathing_orb() -> None:
    st.html("""<div class="es-orb-wrap"><div class="es-orb"></div>
        <div class="es-phase"><span class="in">Inhale · 4s</span><span class="hold">Hold · 4s</span>
        <span class="out">Exhale · 6s</span></div></div>""")


def timer_bar(seconds: int, label: str) -> None:
    st.html(f"""<div class="es-small es-muted" style="margin:.4rem 0 .3rem 0">{escape(label)}</div>
        <div class="es-timer"><span style="animation-duration:{seconds}s"></span></div>""")


def render_activity(activity_id: str) -> None:
    """Interactive panel for one wellbeing activity, followed by a 'how do you feel' reflection."""
    act = ACTIVITIES[activity_id]
    with st.container(border=True):
        head, close = st.columns([6, 1], vertical_alignment="center")
        head.markdown(f"### {act['title']}")
        head.caption(f"{act['summary']} · about {act['minutes']} min")
        if close.button("Close", key=f"close_{activity_id}", icon=":material/close:"):
            st.session_state.activity = None
            st.rerun()

        kind = act["kind"]
        if kind == "breathing":
            left, right = st.columns([1, 1.2], vertical_alignment="center")
            with left:
                breathing_orb()
            with right:
                for n, step in enumerate(act["steps"], 1):
                    st.markdown(f"**Step {n}** — {step}")
                timer_bar(60, "One minute")
        elif kind == "grounding":
            step = st.session_state.setdefault("grounding_step", 0)
            st.progress((step + 1) / len(act["steps"]), text=f"Step {step + 1} of {len(act['steps'])}")
            st.markdown(f"#### {act['steps'][step]}")
            st.caption("Take your time. Name them silently or out loud.")
            back, nxt = st.columns(2)
            if back.button("Back", disabled=step == 0, width="stretch", key="g_back"):
                st.session_state.grounding_step -= 1
                st.rerun()
            if nxt.button("Next" if step < len(act["steps"]) - 1 else "Start again", type="primary",
                          width="stretch", key="g_next"):
                st.session_state.grounding_step = (step + 1) % len(act["steps"])
                st.rerun()
        elif kind == "timer":
            for n, step in enumerate(act["steps"], 1):
                st.markdown(f"{n}. {step}")
            timer_bar(act["seconds"], f"{act['seconds'] // 60} minute timer")
        elif kind == "writing":
            prompt = st.selectbox("Prompt", JOURNAL_PROMPTS, key="act_prompt")
            text = st.text_area("Write freely", key="act_text", height=150, placeholder="Start typing…")
            journal_save_button(prompt, text, key="act_journal_save")
        elif kind == "gratitude":
            items = [st.text_input(f"{n}.", key=f"grat_{n}", placeholder="Something I appreciate…") for n in (1, 2, 3)]
            text = "\n".join(f"• {t}" for t in items if t.strip())
            journal_save_button("Three things I'm grateful for", text, key="act_grat_save")

        st.divider()
        feeling_after(activity_id)


def journal_save_button(prompt: str, text: str, key: str) -> None:
    from src.storage import new_entry

    if st.button("Save to my journal", key=key, icon=":material/bookmark_add:", disabled=not text.strip()):
        error = state.save_entry(new_entry("journal", prompt=prompt, journalText=text.strip()))
        if error:
            st.error(error)
        else:
            st.success("Saved privately to your journal.")


def feeling_after(activity_id: str) -> None:
    from src.storage import new_entry

    st.markdown("**How do you feel after this?**")
    choice = st.pills("How do you feel after this?", FEELINGS_AFTER, key=f"feel_{activity_id}",
                      format_func=lambda f: f"{FEELING_ICONS[f]} {f}", label_visibility="collapsed")
    if choice and st.button("Save reflection", key=f"save_feel_{activity_id}", icon=":material/check:"):
        error = state.save_entry(new_entry("reset", activity=activity_id, feelingAfter=choice))
        if error:
            st.error(error)
        else:
            st.success("Reflection saved.")
    if choice == "Still difficult":
        st.info(DISTRESS_NOTE, icon=":material/favorite:")
    st.caption("This is a self-reflection, not a test or an assessment.")
