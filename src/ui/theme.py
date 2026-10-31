"""Global CSS for EmotionSense.

Surfaces are built with ``color-mix(... currentColor ...)``, a faint tint of the
current text colour, so the same CSS looks right in both the light and the dark
Streamlit theme (defined in .streamlit/config.toml) without detecting the theme.
"""
import streamlit as st

CSS = """
<style>
:root { --es-primary: #4f5bd5; --es-violet: #8b5cf6; --es-radius: 18px; }

/* layout */
.block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1180px; }
footer { visibility: hidden; }

/* cards */
.es-card {
  border: 1px solid color-mix(in srgb, currentColor 11%, transparent);
  background: color-mix(in srgb, currentColor 3%, transparent);
  border-radius: var(--es-radius); padding: 1.05rem 1.2rem;
  box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 6px 18px rgba(16,24,40,.04);
}
.es-card + .es-card { margin-top: .75rem; }
.es-grid { display: grid; gap: .6rem; }
.es-grid > .es-card { margin-top: 0; }
.es-hero {
  border-radius: 22px; padding: 1.6rem 1.7rem;
  border: 1px solid color-mix(in srgb, var(--es-primary) 22%, transparent);
  background: linear-gradient(135deg,
      color-mix(in srgb, var(--es-primary) 15%, transparent),
      color-mix(in srgb, var(--es-violet) 9%, transparent));
}
.es-eyebrow { text-transform: uppercase; letter-spacing: .08em; font-size: .72rem; font-weight: 700; opacity: .62; }
.es-title { font-size: 2rem; font-weight: 750; line-height: 1.15; margin: .1rem 0 .3rem 0; }
.es-subtitle { font-size: 1.02rem; opacity: .72; margin: 0; }
.es-muted { opacity: .68; }
.es-small { font-size: .85rem; }

/* stat cards */
.es-stat-label { font-size: .8rem; font-weight: 600; opacity: .65; }
.es-stat-value { font-size: 1.65rem; font-weight: 750; margin-top: .15rem; line-height: 1.2; }
.es-stat-hint { font-size: .78rem; opacity: .6; margin-top: .15rem; }

/* emotion accents: colour marks identity, text keeps the text colour */
.es-dot { display: inline-block; width: .62rem; height: .62rem; border-radius: 50%; background: var(--c);
          margin-right: .4rem; vertical-align: baseline; }
.es-pill { display: inline-flex; align-items: center; gap: .35rem; padding: .18rem .65rem; border-radius: 999px;
           font-size: .76rem; font-weight: 650;
           background: color-mix(in srgb, var(--c, currentColor) 14%, transparent);
           border: 1px solid color-mix(in srgb, var(--c, currentColor) 35%, transparent); }
.es-result { border-left: 6px solid var(--c); }
.es-emotion { font-size: 2.6rem; font-weight: 800; letter-spacing: .03em; line-height: 1.1; margin: .2rem 0; }
.es-confidence { font-size: 1.05rem; font-weight: 600; opacity: .8; }

/* top-3 bars */
.es-bar-row { display: grid; grid-template-columns: 6.5rem 1fr 3.2rem; align-items: center; gap: .6rem; margin: .38rem 0; }
.es-bar-track { height: .62rem; border-radius: 999px; background: color-mix(in srgb, currentColor 9%, transparent); overflow: hidden; }
.es-bar-fill { height: 100%; border-radius: 999px; background: var(--c); }
.es-bar-value { text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; font-size: .9rem; }

/* insight + suggestion cards */
.es-tag { font-size: .7rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; opacity: .7; }
.es-suggestion { display: flex; gap: .7rem; align-items: flex-start; }

/* landing */
.es-landing-title { font-size: 2.7rem; font-weight: 800; line-height: 1.1; margin: .4rem 0 .8rem 0; }
.es-feature { display: flex; gap: .55rem; align-items: center; margin: .45rem 0; font-weight: 550; }
.es-check { display: inline-grid; place-items: center; width: 1.35rem; height: 1.35rem; border-radius: 50%;
            background: color-mix(in srgb, var(--es-primary) 18%, transparent); font-size: .78rem; }
.es-brand { font-weight: 800; font-size: 1.15rem; letter-spacing: .01em; }

/* pipeline (About) */
.es-flow { display: flex; flex-wrap: wrap; gap: .45rem; align-items: center; }
.es-flow span.step { padding: .4rem .75rem; border-radius: 12px; font-weight: 600; font-size: .86rem;
  border: 1px solid color-mix(in srgb, currentColor 14%, transparent);
  background: color-mix(in srgb, currentColor 4%, transparent); }
.es-flow span.arrow { opacity: .45; }

/* breathing orb: inhale 4s, hold 4s, exhale 6s (14s cycle) */
.es-orb-wrap { display: grid; place-items: center; padding: 1rem 0 .4rem 0; }
.es-orb { width: 150px; height: 150px; border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, color-mix(in srgb, var(--es-primary) 55%, white),
              color-mix(in srgb, var(--es-primary) 80%, transparent));
  animation: es-breathe 14s ease-in-out infinite; transform: scale(.6); }
@keyframes es-breathe { 0% {transform: scale(.6);} 28.6% {transform: scale(1);} 57.1% {transform: scale(1);} 100% {transform: scale(.6);} }
.es-phase { position: relative; height: 1.6rem; width: 12rem; text-align: center; margin-top: .8rem; font-weight: 700; }
.es-phase span { position: absolute; inset: 0; opacity: 0; animation: 14s infinite; }
.es-phase .in { animation-name: es-in; } .es-phase .hold { animation-name: es-hold; } .es-phase .out { animation-name: es-out; }
@keyframes es-in   { 0%,27% {opacity:1;} 29%,100% {opacity:0;} }
@keyframes es-hold { 0%,28% {opacity:0;} 30%,56% {opacity:1;} 58%,100% {opacity:0;} }
@keyframes es-out  { 0%,57% {opacity:0;} 59%,98% {opacity:1;} 100% {opacity:0;} }

/* timers */
.es-timer { height: .55rem; border-radius: 999px; overflow: hidden; background: color-mix(in srgb, currentColor 10%, transparent); }
.es-timer > span { display: block; height: 100%; width: 0; background: var(--es-primary); animation: es-fill linear forwards; }
@keyframes es-fill { from { width: 0; } to { width: 100%; } }

/* sidebar user card */
.es-user { display: flex; gap: .65rem; align-items: center; }
.es-avatar { width: 2.3rem; height: 2.3rem; border-radius: 50%; display: grid; place-items: center; font-weight: 800;
  color: white; background: linear-gradient(135deg, var(--es-primary), var(--es-violet)); }

@media (prefers-reduced-motion: reduce) {
  .es-orb, .es-phase span, .es-timer > span { animation: none !important; }
  .es-orb { transform: scale(.85); } .es-phase .in { opacity: 1; } .es-timer > span { width: 100%; }
}
</style>
"""


def inject_css() -> None:
    st.html(CSS)
