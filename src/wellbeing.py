"""Wellbeing content: suggestions, activities, check-in options and journal prompts.

Wording rule for everything in this file: describe the *facial expression* or the
user's *own* report. Never state or imply what the user feels, and never diagnose.
These are general wellbeing ideas, not medical or psychological advice.
"""

DISCLAIMER = ("EmotionSense reads facial expressions, which are not a reliable measure of what someone "
              "actually feels. It is not a medical or diagnostic tool, and its suggestions are general "
              "wellbeing ideas, not professional advice.")

DISTRESS_NOTE = ("If you're experiencing persistent or severe distress, consider reaching out to a qualified "
                 "mental-health professional or someone you trust. If you are in immediate danger, contact "
                 "your local emergency services.")

# ---------------------------------------------------------------------------
# Activities (Wellbeing Toolkit). "kind" selects how the UI renders it.
# ---------------------------------------------------------------------------
ACTIVITIES = {
    "breathing": {
        "title": "60-Second Breathing", "icon": ":material/air:", "minutes": 1, "kind": "breathing",
        "summary": "A slow breathing rhythm with a longer exhale.",
        "steps": ["Inhale through your nose — 4 seconds", "Hold gently — 4 seconds",
                  "Exhale slowly through your mouth — 6 seconds", "Repeat for about a minute"],
    },
    "grounding": {
        "title": "5-4-3-2-1 Grounding", "icon": ":material/landscape:", "minutes": 3, "kind": "grounding",
        "summary": "Bring attention back to your surroundings using your senses.",
        "steps": ["Notice 5 things you can see", "Notice 4 things you can feel or touch",
                  "Notice 3 things you can hear", "Notice 2 things you can smell",
                  "Notice 1 thing you can taste"],
    },
    "mindful_pause": {
        "title": "Quick Mindful Pause", "icon": ":material/self_improvement:", "minutes": 1, "kind": "timer",
        "summary": "One quiet minute of simply noticing.", "seconds": 60,
        "steps": ["Sit comfortably and soften your shoulders", "Notice your breath without changing it",
                  "When your mind wanders, gently return to the breath"],
    },
    "stretch": {
        "title": "Stretch Break", "icon": ":material/accessibility_new:", "minutes": 2, "kind": "timer",
        "summary": "Release tension from sitting with a few gentle stretches.", "seconds": 120,
        "steps": ["Roll your shoulders back five times", "Gently tilt your head side to side",
                  "Stretch your arms overhead and breathe in", "Stand up and reach for your toes, only as far as is comfortable"],
    },
    "journaling": {
        "title": "Journaling", "icon": ":material/edit_note:", "minutes": 5, "kind": "writing",
        "summary": "Write freely for a few minutes — no rules, no audience.",
        "steps": ["Pick a prompt or just start writing", "Don't edit; let the thoughts flow",
                  "Re-read it later if you like"],
    },
    "gratitude": {
        "title": "Gratitude", "icon": ":material/favorite:", "minutes": 2, "kind": "gratitude",
        "summary": "Note three things you appreciate today, big or small.",
        "steps": ["Think of three things that went right or that you appreciate",
                  "Be specific — a person, a moment, a small comfort"],
    },
    "focus_reset": {
        "title": "Focus Reset", "icon": ":material/center_focus_strong:", "minutes": 2, "kind": "timer",
        "summary": "Clear your head before getting back to work.", "seconds": 120,
        "steps": ["Close unneeded tabs and silence notifications", "Write down the single next task",
                  "Take three slow breaths", "Start with just the first two minutes of that task"],
    },
    "walk": {
        "title": "Take a Short Walk", "icon": ":material/directions_walk:", "minutes": 5, "kind": "timer",
        "summary": "A few minutes of movement and a change of scenery.", "seconds": 300,
        "steps": ["Step away from your screen", "Walk at a comfortable pace, indoors or outside",
                  "Notice what's around you — sounds, light, temperature"],
    },
}

# ---------------------------------------------------------------------------
# "Feeling overwhelmed?" quick resets (user-initiated, never triggered by the model)
# ---------------------------------------------------------------------------
QUICK_RESETS = [("one_minute_reset", "1-minute breathing"), ("grounding", "Grounding exercise"),
                ("journaling", "Write it out"), ("stretch", "Take a movement break")]

ACTIVITIES["one_minute_reset"] = {
    "title": "1-Minute Reset", "icon": ":material/spa:", "minutes": 1, "kind": "breathing",
    "summary": "Four simple steps to slow things down.",
    "steps": ["Relax your shoulders.", "Breathe in slowly.", "Exhale longer than you inhale.", "Repeat."],
}

TOOLKIT_ORDER = ["breathing", "grounding", "mindful_pause", "stretch", "journaling", "gratitude", "focus_reset", "walk"]

FEELINGS_AFTER = ["Better", "Same", "Still difficult"]
FEELING_ICONS = {"Better": "🙂", "Same": "😐", "Still difficult": "😕"}

# ---------------------------------------------------------------------------
# Suggestions shown after a detected expression. Each item: (text, activity id or None)
# ---------------------------------------------------------------------------
EMOTION_SUGGESTIONS = {
    "Happy": {"headline": "Keep the positive momentum",
              "items": [("Write down what's going well today", "gratitude"),
                        ("Capture a good moment to remember later", "journaling")]},
    "Sad": {"headline": "Take a gentle pause",
            "items": [("Try a slow breathing exercise", "breathing"),
                      ("Answer a journal prompt", "journaling"),
                      ("Talk to someone you trust", None)]},
    "Angry": {"headline": "Create some space",
              "items": [("60-second breathing", "breathing"),
                        ("Take a short break away from the screen", "walk"),
                        ("Reflect before reacting", "journaling")]},
    "Fear": {"headline": "Ground yourself",
             "items": [("5-4-3-2-1 grounding", "grounding"),
                       ("Slow breathing with a longer exhale", "breathing")]},
    "Neutral": {"headline": "Check in with yourself",
                "items": [("A quick mood reflection", None),
                          ("A short mindfulness pause", "mindful_pause")]},
    "Surprise": {"headline": "Pause and reflect",
                 "items": [("Write what caught your attention", "journaling"),
                           ("Take a mindful minute", "mindful_pause")]},
    "Disgust": {"headline": "Take a reset",
                "items": [("Step away for a few minutes", "walk"),
                          ("Refresh your environment — open a window, tidy your space", None),
                          ("A quick focus reset", "focus_reset")]},
}

SELF_CHECK_PROMPT = "This expression may be a good opportunity for a quick self-check."

# ---------------------------------------------------------------------------
# Daily check-in
# ---------------------------------------------------------------------------
MOODS = {"Great": "😄", "Good": "🙂", "Okay": "😐", "Low": "😔", "Difficult": "😣"}
MOOD_SCORE = {"Great": 5, "Good": 4, "Okay": 3, "Low": 2, "Difficult": 1}
MOOD_FACTORS = ["College / Work", "Relationships", "Sleep", "Health", "Exams", "Money", "Family", "Personal", "Other"]

# Suggestion after a self-reported mood (the user's own words, not a model output)
MOOD_SUGGESTIONS = {
    "Great": ("Glad to hear it. Want to note what made today good?", "gratitude"),
    "Good": ("Nice. A short gratitude note can help you remember good days.", "gratitude"),
    "Okay": ("A mindful minute can be a nice way to check in.", "mindful_pause"),
    "Low": ("Thanks for checking in. A gentle breathing exercise might help you slow down.", "breathing"),
    "Difficult": ("Thank you for being honest with yourself. A quick reset might help — and talking to "
                  "someone you trust can too.", "one_minute_reset"),
}

JOURNAL_PROMPTS = [
    "What went well today?",
    "What is currently bothering you?",
    "What is one thing you can control right now?",
    "What would make the next hour a little easier?",
    "What are you grateful for today?",
]


def suggestions_for(emotion: str) -> dict:
    """Suggestions for a detected expression (falls back to the Neutral set)."""
    return EMOTION_SUGGESTIONS.get(emotion, EMOTION_SUGGESTIONS["Neutral"])
