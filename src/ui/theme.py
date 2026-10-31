"""Global CSS for EmotionSense (light theme; base colours come from .streamlit/config.toml).

Design system:
* white cards (``.es-glass``) with a thin border and a soft shadow on a light grey page;
* one solid indigo accent; no gradients, glows or blur;
* emotion accents through a ``--c`` custom property, always paired with the emoji and the name;
* motion is limited to small transitions (and the breathing guide), and is switched off for
  ``prefers-reduced-motion``.

Streamlit widgets that need a custom look are given a ``key`` and styled through the
``st-key-<key>`` class Streamlit adds to their container.
"""
import altair as alt
import streamlit as st

CSS = """
<style>
:root {
  --es-primary: #4f46e5; --es-primary-soft: #eef0ff; --es-primary-line: #c7cbfb;
  --es-surface: #ffffff; --es-surface-2: #f5f6fa;
  --es-line: #e6e8ef; --es-line-strong: #d6dae5;
  --es-text: #1f2430; --es-muted: #6b7280; --es-radius: 14px;
  --es-shadow: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.06);
  --es-shadow-hover: 0 4px 12px rgba(16,24,40,.08);
}

/* ---------- canvas ---------- */
.stApp { background: #f5f7fb; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.4rem; padding-bottom: 4rem; max-width: 1180px; }
footer { visibility: hidden; }
h1, h2, h3, h4 { letter-spacing: -.01em; }
hr { border-color: var(--es-line) !important; }

/* ---------- cards ---------- */
.es-glass {
  position: relative; background: var(--es-surface); border: 1px solid var(--es-line);
  border-radius: var(--es-radius); padding: 1.15rem 1.25rem; box-shadow: var(--es-shadow);
  transition: box-shadow .15s ease, border-color .15s ease;
}
.es-glass.lift:hover { box-shadow: var(--es-shadow-hover); border-color: var(--es-line-strong); }
.es-glass + .es-glass { margin-top: .8rem; }
.es-grid { display: grid; gap: .8rem; }
.es-grid > .es-glass, .es-rank-grid > .es-glass { margin-top: 0; }
.es-section { margin: 2.2rem 0 .8rem 0; }
.es-section h3 { font-size: 1.15rem; font-weight: 650; margin: 0; padding: 0; }
.es-section p { color: var(--es-muted); margin: .2rem 0 0 0; font-size: .92rem; }

/* keyed st.container()s that should look like cards */
[data-testid="stVerticalBlock"][class*="st-key-glass"] {
  background: var(--es-surface); border: 1px solid var(--es-line); border-radius: var(--es-radius);
  padding: 1.15rem 1.25rem; box-shadow: var(--es-shadow);
}

/* ---------- type ---------- */
.es-eyebrow { display: inline-block; text-transform: uppercase; letter-spacing: .08em; font-size: .72rem;
  font-weight: 650; color: var(--es-primary); }
.es-grad-text { color: var(--es-primary); }
.es-title { font-size: clamp(1.7rem, 3vw, 2.2rem); font-weight: 700; line-height: 1.15;
  margin: .3rem 0 .4rem 0; letter-spacing: -.02em; color: var(--es-text); }
.es-subtitle { font-size: 1rem; color: var(--es-muted); margin: 0; max-width: 46rem; line-height: 1.55; }
.es-muted { color: var(--es-muted); }
.es-small { font-size: .85rem; }
.es-tag { display: inline-block; font-size: .7rem; font-weight: 650; text-transform: uppercase; letter-spacing: .06em;
  color: var(--es-muted); }
.es-head { margin-bottom: 1.5rem; }

/* ---------- chips & pills ---------- */
.es-chip { display: inline-flex; align-items: center; gap: .4rem; padding: .28rem .7rem; border-radius: 999px;
  font-size: .8rem; font-weight: 550; background: var(--es-surface); border: 1px solid var(--es-line);
  color: var(--es-text); }
.es-chips { display: flex; flex-wrap: wrap; gap: .45rem; }
.es-chips .arrow { color: var(--es-muted); align-self: center; }
.es-pill { display: inline-flex; align-items: center; gap: .35rem; padding: .18rem .65rem; border-radius: 999px;
  font-size: .8rem; font-weight: 600; white-space: nowrap;
  background: color-mix(in srgb, var(--c, #4f46e5) 10%, white);
  border: 1px solid color-mix(in srgb, var(--c, #4f46e5) 30%, white); }
.es-badge { display: inline-flex; align-items: center; padding: .18rem .6rem; border-radius: 999px;
  font-size: .74rem; font-weight: 600; border: 1px solid var(--es-line); background: var(--es-surface-2); }
.es-badge.high { color: #146c43; border-color: #b7e4cb; background: #ecf8f1; }
.es-badge.moderate { color: #8a5a00; border-color: #f1d9a6; background: #fdf6e7; }
.es-badge.low { color: #b42318; border-color: #f5c2bd; background: #fdf0ee; }

/* ---------- stat cards ---------- */
.es-stat { display: flex; gap: .85rem; align-items: center; min-height: 4.6rem; }
.es-stat-icon { flex: none; width: 2.5rem; height: 2.5rem; border-radius: 10px; display: grid; place-items: center;
  font-size: 1.2rem; background: color-mix(in srgb, var(--c, #4f46e5) 9%, white); }
.es-stat-label { font-size: .78rem; font-weight: 550; color: var(--es-muted); }
.es-stat-value { font-size: 1.45rem; font-weight: 700; line-height: 1.25; color: var(--es-text); }
.es-stat-hint { font-size: .75rem; color: var(--es-muted); }

/* ---------- emotion result card ---------- */
.es-emotion-card { padding: 1.5rem 1.6rem; border-top: 4px solid var(--c); }
.es-emotion-main { display: flex; align-items: center; gap: 1.2rem; margin: .7rem 0 .2rem 0; flex-wrap: wrap; }
.es-emoji-orb { flex: none; width: 4.6rem; height: 4.6rem; border-radius: 50%; display: grid; place-items: center;
  font-size: 2.5rem; background: color-mix(in srgb, var(--c) 10%, white); }
.es-emotion-name { font-size: clamp(1.8rem, 3.5vw, 2.4rem); font-weight: 700; letter-spacing: .02em; line-height: 1.05;
  color: var(--es-text); }
.es-emotion-conf { margin-top: .45rem; display: flex; gap: .6rem; align-items: center; flex-wrap: wrap;
  font-weight: 550; font-size: 1rem; color: var(--es-text); }
.es-emotion-text { color: var(--es-muted); margin: .9rem 0 0 0; font-size: .95rem; line-height: 1.55; }

/* confidence ring */
.es-ring { --p: 0; width: 5.2rem; height: 5.2rem; border-radius: 50%; flex: none; display: grid; place-items: center;
  background: conic-gradient(var(--c) calc(var(--p) * 1%), #eceef3 0); }
.es-ring > span { width: 4.3rem; height: 4.3rem; border-radius: 50%; display: grid; place-items: center;
  background: #ffffff; font-weight: 700; font-size: 1.05rem; color: var(--es-text); }

/* ---------- probability bars ---------- */
.es-bar-row { display: grid; grid-template-columns: minmax(6.8rem, 8.5rem) 1fr 3.3rem; align-items: center;
  gap: .75rem; padding: .3rem 0; }
.es-bar-name { display: flex; align-items: center; gap: .45rem; font-weight: 500; font-size: .92rem; white-space: nowrap; }
.es-bar-name .e { font-size: 1.05rem; }
.es-bar-track { height: .5rem; border-radius: 999px; background: #eceef3; overflow: hidden; }
.es-bar-fill { height: 100%; border-radius: 999px; background: var(--c); transform-origin: left center;
  animation: es-grow .6s ease-out both; }
.es-bar-row.top .es-bar-name { font-weight: 650; }
.es-bar-value { text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; font-size: .9rem; }
@keyframes es-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }

/* ---------- ranked top-3 ---------- */
.es-rank-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .8rem; }
.es-rank { padding: 1rem 1.1rem; }
.es-rank .n { position: absolute; top: .85rem; right: 1rem; font-weight: 600; font-size: .8rem; color: var(--es-muted); }
.es-rank .e { font-size: 1.8rem; }
.es-rank .name { font-weight: 650; font-size: 1.02rem; margin-top: .3rem; }
.es-rank .pct { font-size: 1.5rem; font-weight: 700; }
.es-rank.first { border-color: color-mix(in srgb, var(--c) 40%, white); }

/* ---------- landing ---------- */
.es-brand { display: inline-flex; align-items: center; gap: .55rem; font-weight: 700; font-size: 1.15rem; }
.es-brand i { width: 1.8rem; height: 1.8rem; border-radius: 8px; background: var(--es-primary); color: #fff;
  display: grid; place-items: center; font-style: normal; font-size: .9rem; }
.es-landing-title { font-size: clamp(2.2rem, 4.6vw, 3.3rem); font-weight: 700; line-height: 1.08;
  letter-spacing: -.03em; margin: 1rem 0 1rem 0; color: var(--es-text); }
.es-lead { font-size: 1.05rem; color: var(--es-muted); max-width: 33rem; line-height: 1.65; }

/* illustration: a face in a frame with the seven expression labels around it */
.es-scan { position: relative; height: 420px; display: grid; place-items: center; }
.es-scan-frame { position: relative; width: 240px; height: 280px; border-radius: 24px; overflow: hidden;
  background: #ffffff; border: 1px solid var(--es-line); box-shadow: 0 8px 24px rgba(16,24,40,.08); }
.es-scan-frame img { position: absolute; inset: 0; margin: auto; }
.es-scan-line { display: none; }
.es-corner { position: absolute; width: 22px; height: 22px; border: 2px solid var(--es-primary-line); }
.es-corner.tl { top: 14px; left: 14px; border-right: 0; border-bottom: 0; border-radius: 8px 0 0 0; }
.es-corner.tr { top: 14px; right: 14px; border-left: 0; border-bottom: 0; border-radius: 0 8px 0 0; }
.es-corner.bl { bottom: 14px; left: 14px; border-right: 0; border-top: 0; border-radius: 0 0 0 8px; }
.es-corner.br { bottom: 14px; right: 14px; border-left: 0; border-top: 0; border-radius: 0 0 8px 0; }
.es-orbit { position: absolute; padding: .32rem .7rem; border-radius: 999px; font-size: .8rem; font-weight: 550;
  background: #ffffff; border: 1px solid var(--es-line); box-shadow: var(--es-shadow); }
.es-scan-caption { position: absolute; bottom: 4px; left: 50%; transform: translateX(-50%); white-space: nowrap; }

.es-step { display: flex; gap: .9rem; align-items: flex-start; }
.es-step-n { flex: none; width: 2rem; height: 2rem; border-radius: 8px; display: grid; place-items: center;
  font-weight: 700; background: var(--es-primary-soft); color: var(--es-primary); }

/* ---------- empty states ---------- */
.es-empty { text-align: center; padding: 2.4rem 1.2rem; }
.es-empty .icon { width: 3.6rem; height: 3.6rem; margin: 0 auto .8rem auto; border-radius: 50%; display: grid;
  place-items: center; font-size: 1.7rem; background: var(--es-surface-2); }
.es-empty .t { font-size: 1.15rem; font-weight: 650; }
.es-empty .d { color: var(--es-muted); margin-top: .3rem; }

/* ---------- timeline ---------- */
.es-timeline { position: relative; padding-left: 1.3rem; }
.es-timeline::before { content: ""; position: absolute; left: .38rem; top: .5rem; bottom: .5rem; width: 2px;
  background: var(--es-line); border-radius: 2px; }
.es-tl-item { position: relative; padding: .45rem 0 .7rem .4rem; }
.es-tl-item::before { content: ""; position: absolute; left: -1.2rem; top: .8rem; width: .65rem; height: .65rem;
  border-radius: 50%; background: var(--c, #4f46e5); box-shadow: 0 0 0 3px #ffffff; }
.es-tl-time { font-size: .75rem; color: var(--es-muted); }
.es-tl-main { font-weight: 550; margin-top: .1rem; }

/* ---------- live status (webcam view) ---------- */
.es-live { display: inline-flex; align-items: center; gap: .45rem; font-size: .74rem; font-weight: 650;
  letter-spacing: .06em; padding: .28rem .7rem; border-radius: 999px; border: 1px solid var(--es-line);
  background: #fff; }
.es-live i { width: .5rem; height: .5rem; border-radius: 50%; background: #9aa1b2; }
.es-live.on { border-color: #b7e4cb; background: #ecf8f1; color: #146c43; }
.es-live.on i { background: #22a06b; }
.st-key-vision_frame, .st-key-vision_live, .st-key-scan_image { padding: .6rem; border-radius: 16px;
  border: 1px solid var(--es-line); background: #ffffff; box-shadow: var(--es-shadow); }
.st-key-vision_frame img, .st-key-vision_live img, .st-key-scan_image img { border-radius: 10px; }
.es-vision-off { display: grid; place-items: center; text-align: center; min-height: 340px; border-radius: 10px;
  background: var(--es-surface-2); }

/* ---------- breathing guide: inhale 4s, hold 4s, exhale 6s (14s cycle) ---------- */
.es-orb-wrap { display: grid; place-items: center; padding: 1rem 0 .6rem 0; }
.es-orb-ring { width: 200px; height: 200px; border-radius: 50%; display: grid; place-items: center;
  border: 1px dashed var(--es-primary-line); }
.es-orb { width: 180px; height: 180px; border-radius: 50%; background: #c7cbfb;
  animation: es-breathe 14s ease-in-out infinite; transform: scale(.55); }
@keyframes es-breathe { 0% {transform: scale(.55);} 28.6% {transform: scale(1);} 57.1% {transform: scale(1);} 100% {transform: scale(.55);} }
.es-phase { position: relative; height: 2rem; width: 14rem; text-align: center; margin-top: 1rem;
  font-weight: 700; font-size: 1.25rem; letter-spacing: .15em; color: var(--es-primary); }
.es-phase span, .es-count span { position: absolute; inset: 0; opacity: 0; animation: 14s infinite; }
.es-phase .in { animation-name: es-in; } .es-phase .hold { animation-name: es-hold; } .es-phase .out { animation-name: es-out; }
@keyframes es-in   { 0%,27% {opacity:1;} 29%,100% {opacity:0;} }
@keyframes es-hold { 0%,28% {opacity:0;} 30%,56% {opacity:1;} 58%,100% {opacity:0;} }
@keyframes es-out  { 0%,57% {opacity:0;} 59%,98% {opacity:1;} 100% {opacity:0;} }
.es-count { position: relative; height: 1.6rem; width: 6rem; text-align: center; color: var(--es-muted);
  font-variant-numeric: tabular-nums; font-weight: 600; }
.es-count span { animation-name: es-tick; }
@keyframes es-tick { 0%,6.9% {opacity:1;} 7.1%,100% {opacity:0;} }

/* timers */
.es-timer { height: .45rem; border-radius: 999px; overflow: hidden; background: #eceef3; }
.es-timer > span { display: block; height: 100%; width: 100%; background: var(--es-primary); transform-origin: left center;
  animation: es-grow linear both; }

/* ---------- Streamlit widgets ---------- */
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {
  font-weight: 600; box-shadow: 0 1px 2px rgba(16,24,40,.08); transition: background-color .15s ease; }
button[data-testid="stBaseButton-secondary"], button[data-testid="stBaseButton-secondaryFormSubmit"] {
  background: #ffffff; transition: border-color .15s ease, background-color .15s ease; }
button[data-testid="stBaseButton-secondary"]:hover, button[data-testid="stBaseButton-secondaryFormSubmit"]:hover {
  background: var(--es-surface-2); }

/* segmented controls & pills */
[data-testid="stButtonGroup"] button { transition: background-color .15s ease, border-color .15s ease; }
[data-testid="stButtonGroup"] button[data-selected="true"] {
  background: var(--es-primary-soft) !important; border-color: var(--es-primary) !important; }

/* mood cards: the Daily Check-In mood pills become five cards */
.st-key-ci_mood [data-testid="stButtonGroup"] > div { display: grid !important;
  grid-template-columns: repeat(5, minmax(0, 1fr)); gap: .6rem; width: 100%; }
.st-key-ci_mood button { width: 100%; min-height: 6rem; border-radius: 12px !important; flex-direction: column;
  background: #ffffff !important; border: 1px solid var(--es-line-strong) !important; }
.st-key-ci_mood button p { font-size: .95rem !important; font-weight: 600; white-space: normal; line-height: 1.3; }
.st-key-ci_mood button p::first-line { font-size: 2rem; line-height: 1.5; }
.st-key-ci_mood button:hover { border-color: var(--es-primary-line) !important; background: #fafaff !important; }
.st-key-ci_mood button[data-selected="true"] { background: var(--es-primary-soft) !important;
  border: 2px solid var(--es-primary) !important; }
.st-key-ci_factors button { padding-left: .85rem; padding-right: .85rem; }

/* file uploader: a large drop zone */
[data-testid="stFileUploaderDropzone"] { min-height: 8.5rem; border-radius: 14px; border: 1.5px dashed var(--es-line-strong);
  background: #ffffff; transition: border-color .15s ease, background-color .15s ease; }
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--es-primary); background: #fafaff; }

/* text areas */
.st-key-ci_note textarea, .st-key-act_text textarea { font-size: 1rem; line-height: 1.6; }

/* alerts */
[data-testid="stAlertContainer"] { border-radius: 12px; }

/* activity cards (Wellbeing) */
[data-testid="stVerticalBlock"][class*="st-key-act_"] { background: #ffffff; border: 1px solid var(--es-line);
  border-radius: 14px; padding: 1.1rem 1.1rem 1rem 1.1rem; box-shadow: var(--es-shadow); height: 100%;
  transition: box-shadow .15s ease, border-color .15s ease; }
[data-testid="stVerticalBlock"][class*="st-key-act_"]:hover { box-shadow: var(--es-shadow-hover);
  border-color: var(--es-line-strong); }
.es-act-emoji { width: 2.8rem; height: 2.8rem; border-radius: 10px; display: grid; place-items: center; font-size: 1.5rem;
  background: var(--es-surface-2); }
.es-act-title { font-weight: 650; font-size: 1.05rem; margin-top: .75rem; }
.es-act-desc { color: var(--es-muted); font-size: .86rem; margin-top: .3rem; min-height: 2.6rem; }

/* "Feeling overwhelmed?" panel */
.st-key-overwhelmed { border-radius: 16px; padding: 1.4rem 1.4rem 1.1rem 1.4rem; border: 1px solid #cfe8ee;
  background: #f3fafc; }
.st-key-overwhelmed button { min-height: 3.2rem; border-radius: 10px !important; }

/* activity panel */
.st-key-activity_panel { border-radius: 16px; padding: 1.4rem; border: 1px solid var(--es-primary-line);
  background: #ffffff; box-shadow: var(--es-shadow); }

/* ---------- sidebar ---------- */
[data-testid="stNavSectionHeader"] { text-transform: uppercase; letter-spacing: .08em; font-size: .68rem !important;
  font-weight: 650; color: #8a90a2 !important; margin-top: .8rem; }
[data-testid="stSidebarNavLink"] { border-radius: 8px; margin: 1px 0; }
[data-testid="stSidebarNavLink"][aria-current="page"] { background: var(--es-primary-soft) !important; }
[data-testid="stSidebarNavLink"][aria-current="page"] span { color: var(--es-primary) !important; font-weight: 650; }
.es-profile { display: flex; gap: .7rem; align-items: center; }
.es-avatar { flex: none; width: 2.4rem; height: 2.4rem; border-radius: 50%; display: grid; place-items: center;
  font-weight: 700; color: var(--es-primary); background: var(--es-primary-soft); }
.es-status { display: inline-flex; align-items: center; gap: .35rem; margin-top: .55rem; font-size: .72rem;
  font-weight: 600; padding: .18rem .55rem; border-radius: 999px; }
.es-status i { width: .45rem; height: .45rem; border-radius: 50%; background: currentColor; }
.es-status.signed { color: #146c43; background: #ecf8f1; border: 1px solid #b7e4cb; }
.es-status.guest { color: #8a5a00; background: #fdf6e7; border: 1px solid #f1d9a6; }

/* ---------- small screens ---------- */
@media (max-width: 760px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
  .es-rank-grid { grid-template-columns: 1fr; }
  .st-key-ci_mood [data-testid="stButtonGroup"] > div { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .es-scan { height: 360px; transform: scale(.85); }
  .es-bar-row { grid-template-columns: 6.4rem 1fr 3rem; gap: .5rem; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
  .es-orb { transform: scale(.85); } .es-phase .in, .es-count span:first-child { opacity: 1; }
}

/* ---------- theme-independent colours ----------
   Everything below pins the light palette explicitly, so text stays readable even if Streamlit runs
   with another theme (a server started with an older config, or "Dark" chosen in Settings). */
html, body, .stApp { color-scheme: light; }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: #f5f7fb !important;
  color: var(--es-text) !important; }
[data-testid="stHeader"], [data-testid="stBottom"] > div { background: transparent !important; }
[data-testid="stSidebar"] { background: #ffffff !important; border-right: 1px solid var(--es-line) !important; }
[data-testid="stSidebar"] > div, [data-testid="stSidebarContent"], [data-testid="stSidebarHeader"] {
  background: transparent !important; }

/* text */
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 { color: var(--es-text) !important; }
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] strong, [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
[data-testid="stText"], .es-glass, [data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {
  color: var(--es-text) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p, .es-muted, .es-subtitle, .es-lead,
.es-stat-label, .es-stat-hint, .es-section p, .es-tl-time, .es-act-desc, .es-empty .d, .es-emotion-text, .es-tag {
  color: var(--es-muted) !important; }
.es-eyebrow, .es-grad-text { color: var(--es-primary) !important; }
[data-testid="stMarkdownContainer"] a { color: var(--es-primary) !important; }
:not(pre) > code { color: #3730a3 !important; background: var(--es-primary-soft) !important; }
[data-testid="stCode"] pre, [data-testid="stCode"] > div { background: var(--es-surface-2) !important;
  border: 1px solid var(--es-line); border-radius: 12px; }
[data-testid="stCode"] code, [data-testid="stCode"] code * { color: var(--es-text) !important; background: transparent !important; }

/* sidebar navigation */
[data-testid="stSidebarNavLink"] span { color: #374151 !important; }
[data-testid="stSidebarNavLink"]:hover { background: var(--es-surface-2) !important; }
[data-testid="stSidebarNavLink"][aria-current="page"] span { color: var(--es-primary) !important; }
[data-testid="stNavSectionHeader"], [data-testid="stNavSectionHeader"] * { color: #8a90a2 !important; }
[data-testid="stSidebar"] hr, [data-testid="stSidebarNavSeparator"] { border-color: var(--es-line) !important; }

/* buttons */
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--es-primary) !important; border: 1px solid var(--es-primary) !important; }
button[data-testid="stBaseButton-primary"]:hover, button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
  background: #4338ca !important; border-color: #4338ca !important; }
button[data-testid="stBaseButton-primary"] *, button[data-testid="stBaseButton-primaryFormSubmit"] * {
  color: #ffffff !important; }
button[data-testid="stBaseButton-secondary"], button[data-testid="stBaseButton-secondaryFormSubmit"],
button[data-testid="stBaseButton-minimal"] {
  background: #ffffff !important; border: 1px solid var(--es-line-strong) !important; }
button[data-testid="stBaseButton-secondary"]:hover, button[data-testid="stBaseButton-secondaryFormSubmit"]:hover {
  background: var(--es-surface-2) !important; border-color: #c3c8d6 !important; }
button[data-testid^="stBaseButton-secondary"] *, button[data-testid="stBaseButton-minimal"] * { color: var(--es-text) !important; }
button:disabled { opacity: .55; }

/* pills & segmented controls */
[data-testid="stButtonGroup"] button { background: #ffffff !important; border-color: var(--es-line-strong) !important; }
[data-testid="stButtonGroup"] button * { color: var(--es-text) !important; }
[data-testid="stButtonGroup"] button[data-selected="true"] { background: var(--es-primary-soft) !important;
  border-color: var(--es-primary) !important; }
[data-testid="stButtonGroup"] button[data-selected="true"] * { color: var(--es-primary) !important; }

/* tabs */
button[data-baseweb="tab"], button[data-baseweb="tab"] * { color: var(--es-muted) !important; background: transparent !important; }
button[data-baseweb="tab"][aria-selected="true"], button[data-baseweb="tab"][aria-selected="true"] * {
  color: var(--es-primary) !important; }
[data-baseweb="tab-highlight"] { background: var(--es-primary) !important; }
[data-baseweb="tab-border"] { background: var(--es-line) !important; }

/* inputs, text areas, selects */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
  background: #ffffff !important; border-color: var(--es-line-strong) !important; }
.stApp input, .stApp textarea { color: var(--es-text) !important; -webkit-text-fill-color: var(--es-text) !important;
  background: #ffffff !important; caret-color: var(--es-primary); }
.stApp input::placeholder, .stApp textarea::placeholder { color: #9097a8 !important; -webkit-text-fill-color: #9097a8 !important; }
[data-baseweb="select"] *, [data-baseweb="input"] button * { color: var(--es-text) !important; }
[data-baseweb="popover"] ul, [data-baseweb="popover"] li { background: #ffffff !important; color: var(--es-text) !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] { background: var(--es-surface-2) !important; }

/* toggles, uploader, expanders, alerts */
[data-testid="stFileUploaderDropzone"] *, [data-testid="stFileUploaderFile"] * { color: var(--es-text) !important; }
[data-testid="stFileChip"] { background: var(--es-surface-2) !important; border: 1px solid var(--es-line) !important; }
[data-testid="stFileChip"] * { color: var(--es-text) !important; }
[data-testid="stFileChip"] > div:first-child { background: var(--es-primary-soft) !important; }
[data-testid="stFileChip"] > div:first-child svg, [data-testid="stFileChip"] > div:first-child svg * {
  color: var(--es-primary) !important; }
/* coloured markdown such as :gray[...] (suggestion details) */
.stApp [data-testid="stMarkdownContainer"] p span:not([class^="es-"]):not([data-testid]) { color: var(--es-muted) !important; }
[data-testid="stFileUploaderDropzoneInstructions"] small { color: var(--es-muted) !important; }
[data-testid="stExpander"] details { background: #ffffff !important; border: 1px solid var(--es-line) !important;
  border-radius: 12px !important; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) { background: #eef4fd !important; border: 1px solid #c9dcf7; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) { background: #ecf8f1 !important; border: 1px solid #b7e4cb; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) { background: #fdf6e7 !important; border: 1px solid #f1d9a6; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) { background: #fdf0ee !important; border: 1px solid #f5c2bd; }
.stApp [data-testid="stAlertContentInfo"], .stApp [data-testid="stAlertContentInfo"] * { color: #1e4e8c !important; }
.stApp [data-testid="stAlertContentSuccess"], .stApp [data-testid="stAlertContentSuccess"] * { color: #146c43 !important; }
.stApp [data-testid="stAlertContentWarning"], .stApp [data-testid="stAlertContentWarning"] * { color: #8a5a00 !important; }
.stApp [data-testid="stAlertContentError"], .stApp [data-testid="stAlertContentError"] * { color: #b42318 !important; }
[data-testid="stCameraInput"] > div { background: #ffffff !important; }
</style>
"""


def inject_css() -> None:
    st.html(CSS)


# Charts are drawn with this theme (and theme=None in st.altair_chart), so their labels stay
# readable whatever Streamlit theme is active.
@alt.theme.register("emotionsense", enable=True)
def _chart_theme() -> alt.theme.ThemeConfig:
    ink, muted, grid = "#1f2430", "#4b5563", "#eceef3"
    return {"config": {
        "background": "transparent", "font": "Inter, sans-serif",
        "view": {"stroke": None},
        "axis": {"labelColor": muted, "titleColor": muted, "gridColor": grid, "domainColor": "#d6dae5",
                 "tickColor": "#d6dae5", "labelFontSize": 12, "titleFontSize": 12, "titleFontWeight": 500},
        "legend": {"labelColor": muted, "titleColor": muted},
        "title": {"color": ink},
        "text": {"color": ink, "fontSize": 12},
    }}
