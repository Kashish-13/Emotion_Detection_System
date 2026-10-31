"""Global CSS for EmotionSense (dark-first; base colours come from .streamlit/config.toml).

Design system:
* glass surfaces (``.es-glass``) on a softly lit background, one violet→blue→cyan brand gradient;
* emotion accents through a ``--c`` custom property, always paired with the emoji and the name;
* motion is limited to cheap transform/opacity transitions and is switched off for
  ``prefers-reduced-motion``.

Streamlit widgets that need a custom look are given a ``key`` and styled through the
``st-key-<key>`` class Streamlit adds to their container.
"""
import streamlit as st

CSS = """
<style>
:root {
  --es-primary: #8b7cf6; --es-blue: #5b8cf6; --es-cyan: #38c6d9;
  --es-grad: linear-gradient(135deg, #8b7cf6 0%, #5b8cf6 55%, #38c6d9 100%);
  --es-surface: rgba(255,255,255,.035); --es-surface-2: rgba(255,255,255,.06);
  --es-line: rgba(255,255,255,.08); --es-line-strong: rgba(255,255,255,.15);
  --es-muted: #9aa1bf; --es-radius: 20px;
  --es-shadow: 0 1px 0 rgba(255,255,255,.04) inset, 0 12px 32px -12px rgba(0,0,0,.55);
}

/* ---------- canvas ---------- */
.stApp {
  background:
    radial-gradient(1100px 600px at 8% -10%, rgba(139,124,246,.16), transparent 60%),
    radial-gradient(900px 520px at 100% 0%, rgba(56,198,217,.08), transparent 60%),
    radial-gradient(800px 600px at 50% 120%, rgba(91,140,246,.08), transparent 60%),
    #0a0c16;
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.4rem; padding-bottom: 4rem; max-width: 1200px; }
footer { visibility: hidden; }
h1, h2, h3, h4 { letter-spacing: -.01em; }
hr { border-color: var(--es-line) !important; }

/* ---------- glass surfaces ---------- */
.es-glass {
  position: relative; background: var(--es-surface); border: 1px solid var(--es-line);
  border-radius: var(--es-radius); padding: 1.15rem 1.25rem; box-shadow: var(--es-shadow);
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
}
.es-glass.lift:hover { transform: translateY(-2px); border-color: var(--es-line-strong);
  box-shadow: var(--es-shadow), 0 0 0 1px rgba(139,124,246,.12), 0 18px 40px -18px rgba(139,124,246,.45); }
.es-glass + .es-glass { margin-top: .8rem; }
.es-grid { display: grid; gap: .8rem; }
.es-grid > .es-glass, .es-rank-grid > .es-glass { margin-top: 0; }
.es-section { margin: 2.1rem 0 .8rem 0; }
.es-section h3 { font-size: 1.2rem; font-weight: 650; margin: 0; padding: 0; }
.es-section p { color: var(--es-muted); margin: .15rem 0 0 0; font-size: .92rem; }

/* bordered st.container()s get the same glass treatment */
[data-testid="stVerticalBlock"][class*="st-key-glass"] {
  background: var(--es-surface); border: 1px solid var(--es-line) !important; border-radius: var(--es-radius);
  padding: 1.15rem 1.25rem; box-shadow: var(--es-shadow);
}

/* ---------- type ---------- */
.es-eyebrow { display: inline-flex; align-items: center; gap: .45rem; text-transform: uppercase;
  letter-spacing: .12em; font-size: .7rem; font-weight: 700; color: var(--es-muted); }
.es-eyebrow::before { content: ""; width: .45rem; height: .45rem; border-radius: 50%; background: var(--es-grad);
  box-shadow: 0 0 10px rgba(139,124,246,.8); }
.es-grad-text { background: var(--es-grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
.es-title { font-family: "Space Grotesk", Inter, sans-serif; font-size: clamp(1.8rem, 3.2vw, 2.45rem);
  font-weight: 700; line-height: 1.1; margin: .35rem 0 .35rem 0; letter-spacing: -.02em; }
.es-subtitle { font-size: 1.02rem; color: var(--es-muted); margin: 0; max-width: 46rem; }
.es-muted { color: var(--es-muted); }
.es-small { font-size: .85rem; }
.es-tag { display: inline-block; font-size: .66rem; font-weight: 700; text-transform: uppercase; letter-spacing: .1em;
  color: var(--es-muted); }
.es-head { margin-bottom: 1.4rem; }

/* ---------- chips & pills ---------- */
.es-chip { display: inline-flex; align-items: center; gap: .4rem; padding: .32rem .75rem; border-radius: 999px;
  font-size: .8rem; font-weight: 600; background: var(--es-surface-2); border: 1px solid var(--es-line); }
.es-chips { display: flex; flex-wrap: wrap; gap: .45rem; }
.es-chips .arrow { color: var(--es-muted); align-self: center; }
.es-pill { display: inline-flex; align-items: center; gap: .35rem; padding: .2rem .7rem; border-radius: 999px;
  font-size: .8rem; font-weight: 650; white-space: nowrap;
  background: color-mix(in srgb, var(--c, #8b7cf6) 16%, transparent);
  border: 1px solid color-mix(in srgb, var(--c, #8b7cf6) 40%, transparent); }
.es-badge { display: inline-flex; align-items: center; gap: .35rem; padding: .22rem .7rem; border-radius: 999px;
  font-size: .74rem; font-weight: 700; letter-spacing: .02em; border: 1px solid var(--es-line-strong);
  background: var(--es-surface-2); }
.es-badge.high { border-color: rgba(70,200,140,.45); background: rgba(70,200,140,.12); }
.es-badge.moderate { border-color: rgba(232,176,35,.45); background: rgba(232,176,35,.12); }
.es-badge.low { border-color: rgba(234,90,58,.5); background: rgba(234,90,58,.12); }

/* ---------- stat cards ---------- */
.es-stat { display: flex; gap: .85rem; align-items: center; min-height: 4.6rem; }
.es-stat-icon { flex: none; width: 2.6rem; height: 2.6rem; border-radius: 14px; display: grid; place-items: center;
  font-size: 1.25rem; background: color-mix(in srgb, var(--c, #8b7cf6) 16%, transparent);
  border: 1px solid color-mix(in srgb, var(--c, #8b7cf6) 30%, transparent); }
.es-stat-label { font-size: .76rem; font-weight: 600; color: var(--es-muted); }
.es-stat-value { font-family: "Space Grotesk", Inter, sans-serif; font-size: 1.5rem; font-weight: 700; line-height: 1.2; }
.es-stat-hint { font-size: .74rem; color: var(--es-muted); }

/* ---------- emotion hero card ---------- */
.es-emotion-card { padding: 1.6rem 1.7rem; overflow: hidden;
  border-color: color-mix(in srgb, var(--c) 38%, transparent);
  background:
    radial-gradient(520px 260px at 0% 0%, color-mix(in srgb, var(--c) 26%, transparent), transparent 70%),
    radial-gradient(420px 220px at 100% 100%, rgba(91,140,246,.10), transparent 70%), var(--es-surface);
  box-shadow: var(--es-shadow), 0 24px 60px -30px color-mix(in srgb, var(--c) 70%, transparent); }
.es-emotion-main { display: flex; align-items: center; gap: 1.3rem; margin: .7rem 0 .2rem 0; flex-wrap: wrap; }
.es-emoji-orb { flex: none; width: 5.2rem; height: 5.2rem; border-radius: 50%; display: grid; place-items: center;
  font-size: 2.9rem; background: radial-gradient(circle at 35% 30%, color-mix(in srgb, var(--c) 45%, transparent),
  color-mix(in srgb, var(--c) 12%, transparent)); border: 1px solid color-mix(in srgb, var(--c) 50%, transparent);
  box-shadow: 0 0 40px -6px color-mix(in srgb, var(--c) 70%, transparent); }
.es-emotion-name { font-family: "Space Grotesk", Inter, sans-serif; font-size: clamp(2rem, 4vw, 2.9rem);
  font-weight: 700; letter-spacing: .04em; line-height: 1; }
.es-emotion-conf { margin-top: .45rem; display: flex; gap: .6rem; align-items: center; flex-wrap: wrap;
  font-weight: 600; font-size: 1.02rem; }
.es-emotion-text { color: var(--es-muted); margin: .9rem 0 0 0; font-size: .96rem; }

/* confidence ring */
.es-ring { --p: 0; width: 5.6rem; height: 5.6rem; border-radius: 50%; flex: none; display: grid; place-items: center;
  background: conic-gradient(var(--c) calc(var(--p) * 1%), rgba(255,255,255,.08) 0); }
.es-ring > span { width: 4.5rem; height: 4.5rem; border-radius: 50%; display: grid; place-items: center;
  background: #10132a; font-family: "Space Grotesk", Inter, sans-serif; font-weight: 700; font-size: 1.15rem; }

/* ---------- probability bars ---------- */
.es-bar-row { display: grid; grid-template-columns: minmax(6.8rem, 8.5rem) 1fr 3.3rem; align-items: center;
  gap: .75rem; padding: .32rem 0; }
.es-bar-name { display: flex; align-items: center; gap: .45rem; font-weight: 550; font-size: .92rem; white-space: nowrap; }
.es-bar-name .e { font-size: 1.05rem; }
.es-bar-track { height: .6rem; border-radius: 999px; background: rgba(255,255,255,.07); overflow: hidden; }
.es-bar-fill { height: 100%; border-radius: 999px; transform-origin: left center;
  background: linear-gradient(90deg, color-mix(in srgb, var(--c) 70%, transparent), var(--c));
  box-shadow: 0 0 12px -2px color-mix(in srgb, var(--c) 70%, transparent); animation: es-grow .8s cubic-bezier(.2,.8,.2,1) both; }
.es-bar-row.top .es-bar-name { font-weight: 750; }
.es-bar-value { text-align: right; font-variant-numeric: tabular-nums; font-weight: 650; font-size: .9rem; }
@keyframes es-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }

/* ---------- ranked top-3 ---------- */
.es-rank-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .8rem; }
.es-rank { padding: 1rem 1.1rem; border-color: color-mix(in srgb, var(--c) 28%, transparent); }
.es-rank .n { position: absolute; top: .8rem; right: 1rem; font-family: "Space Grotesk", Inter, sans-serif;
  font-weight: 700; font-size: .85rem; color: var(--es-muted); }
.es-rank .e { font-size: 1.9rem; }
.es-rank .name { font-weight: 700; font-size: 1.05rem; margin-top: .3rem; }
.es-rank .pct { font-family: "Space Grotesk", Inter, sans-serif; font-size: 1.6rem; font-weight: 700; }
.es-rank.first { background: radial-gradient(300px 160px at 0% 0%, color-mix(in srgb, var(--c) 22%, transparent),
  transparent 70%), var(--es-surface); }

/* ---------- landing ---------- */
.es-brand { display: inline-flex; align-items: center; gap: .55rem; font-family: "Space Grotesk", Inter, sans-serif;
  font-weight: 700; font-size: 1.2rem; }
.es-brand i { width: 1.9rem; height: 1.9rem; border-radius: 10px; background: var(--es-grad); display: grid;
  place-items: center; font-style: normal; font-size: 1rem; box-shadow: 0 0 22px -4px rgba(139,124,246,.9); }
.es-landing-title { font-family: "Space Grotesk", Inter, sans-serif; font-size: clamp(2.3rem, 5vw, 3.7rem);
  font-weight: 700; line-height: 1.04; letter-spacing: -.03em; margin: 1.1rem 0 1rem 0; }
.es-lead { font-size: 1.08rem; color: var(--es-muted); max-width: 33rem; line-height: 1.6; }

/* scanner centerpiece */
.es-scan { position: relative; height: 430px; display: grid; place-items: center; }
.es-scan::before { content: ""; position: absolute; width: 360px; height: 360px; border-radius: 50%;
  background: radial-gradient(circle, rgba(139,124,246,.35), rgba(91,140,246,.12) 45%, transparent 70%);
  filter: blur(8px); animation: es-glow 6s ease-in-out infinite; }
.es-scan-frame { position: relative; width: 250px; height: 290px; border-radius: 34px; overflow: hidden;
  background: linear-gradient(160deg, rgba(255,255,255,.07), rgba(255,255,255,.02));
  border: 1px solid var(--es-line-strong); box-shadow: 0 30px 80px -30px rgba(139,124,246,.7); }
.es-scan-frame img { position: absolute; inset: 0; margin: auto; }
.es-scan-line { position: absolute; left: 0; right: 0; height: 70px; top: -70px;
  background: linear-gradient(180deg, transparent, rgba(56,198,217,.28) 85%, rgba(56,198,217,.9));
  animation: es-scanline 3.6s ease-in-out infinite; }
.es-corner { position: absolute; width: 26px; height: 26px; border: 2.5px solid #38c6d9; opacity: .9; }
.es-corner.tl { top: 14px; left: 14px; border-right: 0; border-bottom: 0; border-radius: 10px 0 0 0; }
.es-corner.tr { top: 14px; right: 14px; border-left: 0; border-bottom: 0; border-radius: 0 10px 0 0; }
.es-corner.bl { bottom: 14px; left: 14px; border-right: 0; border-top: 0; border-radius: 0 0 0 10px; }
.es-corner.br { bottom: 14px; right: 14px; border-left: 0; border-top: 0; border-radius: 0 0 10px 0; }
.es-orbit { position: absolute; padding: .38rem .75rem; border-radius: 999px; font-size: .8rem; font-weight: 650;
  background: rgba(16,19,40,.78); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
  border: 1px solid color-mix(in srgb, var(--c) 45%, transparent);
  box-shadow: 0 8px 24px -10px color-mix(in srgb, var(--c) 80%, transparent); animation: es-float 6s ease-in-out infinite; }
.es-scan-caption { position: absolute; bottom: 4px; left: 50%; transform: translateX(-50%); white-space: nowrap; }
@keyframes es-scanline { 0% { top: -70px; } 55% { top: 100%; } 100% { top: 100%; } }
@keyframes es-float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-7px); } }
@keyframes es-glow { 0%,100% { opacity: .75; transform: scale(1); } 50% { opacity: 1; transform: scale(1.06); } }

.es-step { display: flex; gap: .9rem; align-items: flex-start; }
.es-step-n { flex: none; width: 2.2rem; height: 2.2rem; border-radius: 12px; display: grid; place-items: center;
  font-weight: 800; background: var(--es-grad); color: #0a0c16; }

/* ---------- empty states ---------- */
.es-empty { text-align: center; padding: 2.6rem 1.2rem; }
.es-empty .icon { width: 4.4rem; height: 4.4rem; margin: 0 auto .9rem auto; border-radius: 50%; display: grid;
  place-items: center; font-size: 2rem; background: radial-gradient(circle at 35% 30%, rgba(139,124,246,.4),
  rgba(91,140,246,.08)); border: 1px solid rgba(139,124,246,.35); box-shadow: 0 0 40px -8px rgba(139,124,246,.7); }
.es-empty .t { font-family: "Space Grotesk", Inter, sans-serif; font-size: 1.35rem; font-weight: 700; }
.es-empty .d { color: var(--es-muted); margin-top: .35rem; }

/* ---------- timeline ---------- */
.es-timeline { position: relative; padding-left: 1.3rem; }
.es-timeline::before { content: ""; position: absolute; left: .38rem; top: .4rem; bottom: .4rem; width: 2px;
  background: linear-gradient(180deg, rgba(139,124,246,.6), rgba(56,198,217,.15)); border-radius: 2px; }
.es-tl-item { position: relative; padding: .45rem 0 .7rem .4rem; }
.es-tl-item::before { content: ""; position: absolute; left: -1.22rem; top: .78rem; width: .7rem; height: .7rem;
  border-radius: 50%; background: var(--c, #8b7cf6); box-shadow: 0 0 0 3px #0a0c16, 0 0 12px var(--c, #8b7cf6); }
.es-tl-time { font-size: .74rem; color: var(--es-muted); }
.es-tl-main { font-weight: 600; margin-top: .1rem; }

/* ---------- live status ---------- */
.es-live { display: inline-flex; align-items: center; gap: .45rem; font-size: .74rem; font-weight: 800;
  letter-spacing: .12em; padding: .3rem .7rem; border-radius: 999px; border: 1px solid var(--es-line-strong); }
.es-live i { width: .55rem; height: .55rem; border-radius: 50%; background: #6b7090; }
.es-live.on { border-color: rgba(56,198,217,.5); background: rgba(56,198,217,.1); }
.es-live.on i { background: #38c6d9; box-shadow: 0 0 0 0 rgba(56,198,217,.7); animation: es-pulse 1.6s infinite; }
@keyframes es-pulse { 0% { box-shadow: 0 0 0 0 rgba(56,198,217,.7); } 70% { box-shadow: 0 0 0 9px rgba(56,198,217,0); }
  100% { box-shadow: 0 0 0 0 rgba(56,198,217,0); } }

/* vision frame around the webcam image */
.st-key-vision_frame, .st-key-vision_live { position: relative; padding: .7rem; border-radius: 24px;
  border: 1px solid var(--es-line-strong); background: rgba(8,10,22,.6); overflow: hidden;
  box-shadow: 0 30px 70px -35px rgba(56,198,217,.55); }
.st-key-vision_live { border-color: rgba(56,198,217,.45); }
.st-key-vision_live::after { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 3px; pointer-events: none;
  background: linear-gradient(90deg, transparent, rgba(56,198,217,.95), transparent);
  animation: es-sweep 3.2s linear infinite; }
@keyframes es-sweep { from { transform: translateY(0); } to { transform: translateY(560px); } }
.st-key-vision_frame img, .st-key-vision_live img, .st-key-scan_image img { border-radius: 16px; }
.es-vision-off { display: grid; place-items: center; text-align: center; min-height: 360px; border-radius: 16px;
  background: repeating-linear-gradient(0deg, rgba(255,255,255,.025) 0 1px, transparent 1px 28px),
              repeating-linear-gradient(90deg, rgba(255,255,255,.025) 0 1px, transparent 1px 28px); }

/* uploaded image frame on Detect */
.st-key-scan_image { padding: .7rem; border-radius: 24px; border: 1px solid var(--es-line-strong);
  background: rgba(8,10,22,.55); box-shadow: 0 30px 70px -35px rgba(139,124,246,.6); }

/* ---------- breathing guide: inhale 4s, hold 4s, exhale 6s (14s cycle) ---------- */
.es-orb-wrap { display: grid; place-items: center; padding: 1.2rem 0 .6rem 0; }
.es-orb-ring { width: 210px; height: 210px; border-radius: 50%; display: grid; place-items: center;
  border: 1px dashed rgba(139,124,246,.35); }
.es-orb { width: 190px; height: 190px; border-radius: 50%; display: grid; place-items: center;
  background: radial-gradient(circle at 35% 30%, rgba(169,159,251,.95), rgba(91,140,246,.55) 55%, rgba(56,198,217,.25));
  box-shadow: 0 0 60px -6px rgba(139,124,246,.8); animation: es-breathe 14s ease-in-out infinite; transform: scale(.55); }
@keyframes es-breathe { 0% {transform: scale(.55);} 28.6% {transform: scale(1);} 57.1% {transform: scale(1);} 100% {transform: scale(.55);} }
.es-phase { position: relative; height: 2rem; width: 14rem; text-align: center; margin-top: 1rem;
  font-family: "Space Grotesk", Inter, sans-serif; font-weight: 700; font-size: 1.4rem; letter-spacing: .2em; }
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
.es-timer { height: .5rem; border-radius: 999px; overflow: hidden; background: rgba(255,255,255,.08); }
.es-timer > span { display: block; height: 100%; width: 100%; background: var(--es-grad); transform-origin: left center;
  animation: es-grow linear both; }

/* ---------- Streamlit widgets ---------- */
/* buttons */
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--es-grad); border: 0; color: #0a0c16; font-weight: 700;
  box-shadow: 0 10px 26px -12px rgba(139,124,246,.9); transition: transform .15s ease, box-shadow .15s ease, filter .15s ease; }
button[data-testid="stBaseButton-primary"]:hover, button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
  transform: translateY(-1px); filter: brightness(1.08); color: #0a0c16; box-shadow: 0 14px 30px -12px rgba(139,124,246,1); }
button[data-testid="stBaseButton-primary"] p, button[data-testid="stBaseButton-primaryFormSubmit"] p { font-weight: 700; }
button[data-testid="stBaseButton-secondary"], button[data-testid="stBaseButton-secondaryFormSubmit"] {
  background: var(--es-surface-2); border: 1px solid var(--es-line-strong); transition: all .15s ease; }
button[data-testid="stBaseButton-secondary"]:hover, button[data-testid="stBaseButton-secondaryFormSubmit"]:hover {
  border-color: rgba(139,124,246,.6); background: rgba(139,124,246,.12); transform: translateY(-1px); }

/* segmented controls & pills */
[data-testid="stButtonGroup"] button { transition: all .15s ease; }
[data-testid="stButtonGroup"] button[data-selected="true"] {
  background: rgba(139,124,246,.2) !important; border-color: rgba(139,124,246,.75) !important; }

/* mood cards: the Daily Check-In mood pills become five large cards */
.st-key-ci_mood [data-testid="stButtonGroup"] > div { display: grid !important;
  grid-template-columns: repeat(5, minmax(0, 1fr)); gap: .65rem; width: 100%; }
.st-key-ci_mood button { width: 100%; min-height: 6.4rem; border-radius: 20px !important; flex-direction: column;
  background: var(--es-surface) !important; border: 1px solid var(--es-line-strong) !important; }
.st-key-ci_mood button p { font-size: .95rem !important; font-weight: 650; white-space: normal; line-height: 1.3; }
.st-key-ci_mood button p::first-line { font-size: 2.1rem; line-height: 1.5; }
.st-key-ci_mood button:hover { transform: translateY(-3px); border-color: rgba(139,124,246,.6) !important; }
.st-key-ci_mood button[data-selected="true"] { transform: translateY(-3px);
  background: radial-gradient(circle at 50% 0%, rgba(139,124,246,.45), rgba(91,140,246,.12)) !important;
  border: 1.5px solid #a99ffb !important; box-shadow: 0 16px 36px -14px rgba(139,124,246,.95); }
.st-key-ci_factors button { padding-left: .9rem; padding-right: .9rem; }

/* file uploader: a large drop zone */
[data-testid="stFileUploaderDropzone"] { min-height: 9rem; border-radius: 22px; border: 1.5px dashed rgba(139,124,246,.5);
  background: radial-gradient(500px 160px at 50% 0%, rgba(139,124,246,.12), transparent 70%), rgba(255,255,255,.02);
  transition: border-color .2s ease, background .2s ease; }
[data-testid="stFileUploaderDropzone"]:hover { border-color: #a99ffb; background-color: rgba(139,124,246,.06); }

/* text areas */
.st-key-ci_note textarea, .st-key-j_text textarea { font-size: 1.02rem; line-height: 1.65; }

/* alerts: softer, glassy */
[data-testid="stAlertContainer"] { border-radius: 16px; backdrop-filter: blur(10px); }

/* tabs */
[data-baseweb="tab-list"] { gap: .35rem; }
button[data-baseweb="tab"] { border-radius: 999px; padding: .35rem 1rem !important; }
button[data-baseweb="tab"][aria-selected="true"] { background: rgba(139,124,246,.16); }

/* activity cards (Wellbeing) */
[data-testid="stVerticalBlock"][class*="st-key-act_"] { background: var(--es-surface); border: 1px solid var(--es-line);
  border-radius: 22px; padding: 1.15rem 1.15rem 1rem 1.15rem; box-shadow: var(--es-shadow); height: 100%;
  transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease; }
[data-testid="stVerticalBlock"][class*="st-key-act_"]:hover { transform: translateY(-3px); border-color: rgba(139,124,246,.45);
  box-shadow: var(--es-shadow), 0 20px 40px -20px rgba(139,124,246,.6); }
.es-act-emoji { width: 3rem; height: 3rem; border-radius: 16px; display: grid; place-items: center; font-size: 1.6rem;
  background: rgba(139,124,246,.14); border: 1px solid rgba(139,124,246,.3); }
.es-act-title { font-family: "Space Grotesk", Inter, sans-serif; font-weight: 700; font-size: 1.08rem; margin-top: .75rem; }
.es-act-desc { color: var(--es-muted); font-size: .86rem; margin-top: .3rem; min-height: 2.6rem; }

/* "Feeling overwhelmed?" panel */
.st-key-overwhelmed { border-radius: 26px; padding: 1.5rem 1.5rem 1.2rem 1.5rem; border: 1px solid rgba(56,198,217,.3);
  background: radial-gradient(600px 240px at 0% 0%, rgba(56,198,217,.16), transparent 70%),
              radial-gradient(500px 240px at 100% 100%, rgba(139,124,246,.14), transparent 70%), rgba(255,255,255,.025); }
.st-key-overwhelmed button { min-height: 3.4rem; border-radius: 16px !important; }

/* activity panel */
.st-key-activity_panel { border-radius: 26px; padding: 1.4rem; border: 1px solid rgba(139,124,246,.4);
  background: radial-gradient(700px 300px at 50% 0%, rgba(139,124,246,.14), transparent 70%), rgba(255,255,255,.03);
  box-shadow: 0 30px 70px -40px rgba(139,124,246,.8); }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f1226 0%, #0b0d1a 100%);
  border-right: 1px solid var(--es-line); }
[data-testid="stNavSectionHeader"] { text-transform: uppercase; letter-spacing: .14em; font-size: .66rem !important;
  font-weight: 800; color: #6f7598 !important; margin-top: .9rem; }
[data-testid="stSidebarNavLink"] { border-radius: 12px; margin: 1px 0; transition: background .15s ease; }
[data-testid="stSidebarNavLink"]:hover { background: rgba(255,255,255,.05); }
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: linear-gradient(90deg, rgba(139,124,246,.28), rgba(91,140,246,.08)) !important;
  box-shadow: inset 3px 0 0 #a99ffb; }
[data-testid="stSidebarNavLink"][aria-current="page"] span { color: #fff !important; font-weight: 700; }
.es-profile { display: flex; gap: .7rem; align-items: center; }
.es-avatar { flex: none; width: 2.6rem; height: 2.6rem; border-radius: 50%; display: grid; place-items: center;
  font-weight: 800; color: #0a0c16; background: var(--es-grad); box-shadow: 0 0 18px -4px rgba(139,124,246,.9); }
.es-status { display: inline-flex; align-items: center; gap: .35rem; margin-top: .55rem; font-size: .72rem;
  font-weight: 700; padding: .2rem .6rem; border-radius: 999px; }
.es-status i { width: .45rem; height: .45rem; border-radius: 50%; background: currentColor; }
.es-status.cloud { color: #6fd6a5; background: rgba(70,200,140,.1); border: 1px solid rgba(70,200,140,.3); }
.es-status.guest { color: #e8c15a; background: rgba(232,176,35,.1); border: 1px solid rgba(232,176,35,.3); }

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
  .es-scan-line { display: none; }
}
</style>
"""


def inject_css() -> None:
    st.html(CSS)
