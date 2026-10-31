"""Reusable UI pieces. Every user-provided string is HTML-escaped before rendering.

Emotion colour is never used on its own: each emotion is shown with its emoji and name.
"""
from html import escape

import streamlit as st

from src import config
from src.ui import state
from src.wellbeing import (ACTIVITIES, DISTRESS_NOTE, FEELING_ICONS, FEELINGS_AFTER, JOURNAL_PROMPTS,
                           describe_expression)


def color(emotion: str | None) -> str:
    return config.EMOTION_COLORS.get(emotion, "#8b7cf6")


def emoji(emotion: str | None) -> str:
    return config.EMOTION_EMOJI.get(emotion, "🙂")


def pct(p: float) -> str:
    return "<1%" if p < 0.01 else f"{p:.0%}"


# ---------------------------------------------------------------------------
# Basic blocks
# ---------------------------------------------------------------------------
def page_header(title: str, subtitle: str = "", eyebrow: str = "", accent: str = "") -> None:
    """Page title; ``accent`` is an optional trailing phrase in the brand gradient."""
    accent_html = f' <span class="es-grad-text">{escape(accent)}</span>' if accent else ""
    st.html(f"""<div class="es-head">
        {f'<div class="es-eyebrow">{escape(eyebrow)}</div>' if eyebrow else ''}
        <div class="es-title">{escape(title)}{accent_html}</div>
        {f'<p class="es-subtitle">{escape(subtitle)}</p>' if subtitle else ''}</div>""")


def section(title: str, text: str = "") -> None:
    st.html(f'<div class="es-section"><h3>{escape(title)}</h3>{f"<p>{escape(text)}</p>" if text else ""}</div>')


def stat_card(label: str, value: str, hint: str = "", emotion: str | None = None, icon: str = "") -> None:
    icon = emoji(emotion) if emotion else icon
    icon_html = f'<div class="es-stat-icon" style="--c:{color(emotion)}">{icon}</div>' if icon else ""
    st.html(f"""<div class="es-glass lift" style="padding:1rem 1.1rem"><div class="es-stat">{icon_html}
        <div style="min-width:0"><div class="es-stat-label">{escape(label)}</div>
        <div class="es-stat-value">{escape(value)}</div>
        <div class="es-stat-hint">{escape(hint) if hint else "&nbsp;"}</div></div></div></div>""")


def emotion_pill(emotion: str) -> str:
    return f'<span class="es-pill" style="--c:{color(emotion)}">{emoji(emotion)} {escape(emotion)}</span>'


def empty_state(title: str, text: str, icon: str = "✨") -> None:
    st.html(f"""<div class="es-glass es-empty"><div class="icon">{icon}</div>
        <div class="t">{escape(title)}</div><div class="d">{escape(text)}</div></div>""")


def note(text: str) -> None:
    st.html(f'<div class="es-muted es-small" style="margin-top:1rem">{escape(text)}</div>')


def soft_notice(text: str) -> None:
    """A calm notice for recoverable problems, instead of a red error block."""
    st.html(f'<div class="es-glass es-small" style="padding:.75rem 1rem;border-color:rgba(232,176,35,.35)">'
            f'☁️ {escape(text)}</div>')


# ---------------------------------------------------------------------------
# Detection results
# ---------------------------------------------------------------------------
LEVEL_TEXT = {"High": "High confidence", "Moderate": "Moderate confidence", "Low": "Low confidence"}


def confidence_level(confidence: float) -> str:
    if confidence >= config.HIGH_CONFIDENCE:
        return "High"
    return "Moderate" if confidence >= config.MODERATE_CONFIDENCE else "Low"


def level_badge(level: str) -> str:
    return f'<span class="es-badge {level.lower()}">{LEVEL_TEXT.get(level, level)}</span>'


def emotion_card(emotion: str, confidence: float, title: str = "Detected expression", text: str = "",
                 meta: str = "") -> None:
    """The dominant result card: emoji orb, emotion name, confidence ring and badge."""
    level = confidence_level(confidence)
    text = text or describe_expression(emotion)
    meta_html = f'<div class="es-small es-muted" style="margin-top:.5rem">{escape(meta)}</div>' if meta else ""
    st.html(f"""<div class="es-glass es-emotion-card" style="--c:{color(emotion)}">
        <div class="es-eyebrow">{escape(title)}</div>
        <div class="es-emotion-main">
          <div class="es-emoji-orb" aria-hidden="true">{emoji(emotion)}</div>
          <div style="flex:1;min-width:10rem">
            <div class="es-emotion-name">{escape(emotion.upper())}</div>
            <div class="es-emotion-conf">{confidence:.0%} confidence {level_badge(level)}</div>
          </div>
          <div class="es-ring" style="--p:{confidence * 100:.1f}" role="img"
               aria-label="Confidence {confidence:.0%}"><span>{confidence:.0%}</span></div>
        </div>
        <p class="es-emotion-text">{escape(text)}</p>{meta_html}</div>""")


def result_card(face, title: str = "Detected expression") -> None:
    emotion_card(face.emotion, face.confidence, title)


def low_confidence_warning() -> None:
    st.warning("**Low-confidence prediction.** The model isn't very certain about this expression. "
               "Lighting, pose, face angle, or image quality can affect the result.", icon=":material/info:")


def emotion_bars(probabilities: dict, title: str = "") -> None:
    """Emotions as horizontal bars (highest first), each labelled with emoji, name and percentage."""
    items = sorted(probabilities.items(), key=lambda kv: -kv[1])
    rows = "".join(
        f"""<div class="es-bar-row{' top' if i == 0 else ''}" style="--c:{color(e)}">
            <div class="es-bar-name"><span class="e" aria-hidden="true">{emoji(e)}</span>{escape(e)}</div>
            <div class="es-bar-track"><div class="es-bar-fill" style="width:{max(p * 100, 0.8):.1f}%"></div></div>
            <div class="es-bar-value">{pct(p)}</div></div>""" for i, (e, p) in enumerate(items))
    head = f'<div class="es-stat-label" style="margin-bottom:.4rem">{escape(title)}</div>' if title else ""
    st.html(f'<div class="es-glass">{head}{rows}</div>')


def rank_cards(pairs: list[tuple[str, float]]) -> None:
    """Top predictions as ranked cards."""
    cards = "".join(
        f"""<div class="es-glass lift es-rank{' first' if i == 1 else ''}" style="--c:{color(e)}">
            <div class="n">#{i}</div><div class="e" aria-hidden="true">{emoji(e)}</div>
            <div class="name">{escape(e)}</div><div class="pct">{pct(p)}</div>
            <div class="es-bar-track" style="margin-top:.45rem"><div class="es-bar-fill"
                 style="width:{max(p * 100, 0.8):.1f}%"></div></div></div>""" for i, (e, p) in enumerate(pairs, 1))
    st.html(f'<div class="es-rank-grid">{cards}</div>')


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


COUNTDOWN = [4, 3, 2, 1, 4, 3, 2, 1, 6, 5, 4, 3, 2, 1]  # inhale 4s, hold 4s, exhale 6s


def breathing_orb() -> None:
    ticks = "".join(f'<span style="animation-delay:{i}s">{n}…</span>' for i, n in enumerate(COUNTDOWN))
    st.html(f"""<div class="es-orb-wrap"><div class="es-orb-ring"><div class="es-orb"></div></div>
        <div class="es-phase"><span class="in">INHALE</span><span class="hold">HOLD</span>
        <span class="out">EXHALE</span></div><div class="es-count">{ticks}</div></div>""")


def timer_bar(seconds: int, label: str) -> None:
    st.html(f"""<div class="es-small es-muted" style="margin:.4rem 0 .3rem 0">{escape(label)}</div>
        <div class="es-timer"><span style="animation-duration:{seconds}s"></span></div>""")


def render_activity(activity_id: str) -> None:
    """Interactive panel for one wellbeing activity, followed by a 'how do you feel' reflection."""
    act = ACTIVITIES[activity_id]
    with st.container(key="activity_panel"):
        head, close = st.columns([6, 1], vertical_alignment="center")
        head.markdown(f"### {act['emoji']} {act['title']}")
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


def save_message(saved_to_cloud: bool, text: str) -> None:
    """Confirmation after state.save_entry(); says so when the entry was only saved locally."""
    if saved_to_cloud:
        st.success(text, icon=":material/check_circle:")
    else:
        st.success(f"{text}  \n✓ {state.SAVED_LOCALLY}", icon=":material/cloud_off:")


def journal_save_button(prompt: str, text: str, key: str) -> None:
    from src.storage import new_entry

    # Not disabled while empty: a disabled button swallows the click that also commits the text area.
    if st.button("Save to my journal", key=key, icon=":material/bookmark_add:"):
        if not text.strip():
            st.warning("Write something first, then save.", icon=":material/edit:")
        else:
            save_message(state.save_entry(new_entry("journal", prompt=prompt, journalText=text.strip())),
                         "✓ Journal saved.")


def feeling_after(activity_id: str) -> None:
    from src.storage import new_entry

    st.markdown("**How do you feel after this?**")
    choice = st.pills("How do you feel after this?", FEELINGS_AFTER, key=f"feel_{activity_id}",
                      format_func=lambda f: f"{FEELING_ICONS[f]} {f}", label_visibility="collapsed")
    if choice and st.button("Save reflection", key=f"save_feel_{activity_id}", icon=":material/check:"):
        save_message(state.save_entry(new_entry("reset", activity=activity_id, feelingAfter=choice)),
                     "✓ Reflection saved.")
    if choice == "Still difficult":
        st.info(DISTRESS_NOTE, icon=":material/favorite:")
    st.caption("This is a self-reflection, not a test or an assessment.")
