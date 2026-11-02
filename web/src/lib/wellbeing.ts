// Wellbeing content: suggestions, activities, check-in options and journal prompts (port of src/wellbeing.py).
//
// Wording rule for everything in this file: describe the *facial expression* or the user's *own* report.
// Never state or imply what the user feels, and never diagnose. These are general wellbeing ideas, not
// medical or psychological advice.

export const DISCLAIMER = "EmotionSense reads facial expressions, which are not a reliable measure of what someone "
  + "actually feels. It is not a medical or diagnostic tool, and its suggestions are general wellbeing ideas, not "
  + "professional advice.";

export const DISTRESS_NOTE = "If you're experiencing persistent or severe distress, consider reaching out to a "
  + "qualified mental-health professional or someone you trust. If you are in immediate danger, contact your local "
  + "emergency services.";

export type ActivityKind = "breathing" | "grounding" | "timer" | "writing" | "gratitude";
export type Activity = {
  emoji: string; title: string; minutes: number; kind: ActivityKind; summary: string; steps: string[]; seconds?: number;
};

// Wellbeing toolkit activities. "kind" selects how the UI renders it.
export const ACTIVITIES: Record<string, Activity> = {
  breathing: {
    emoji: "🌬️", title: "60-Second Breathing", minutes: 1, kind: "breathing",
    summary: "A slow breathing rhythm with a longer exhale.",
    steps: ["Inhale through your nose — 4 seconds", "Hold gently — 4 seconds",
      "Exhale slowly through your mouth — 6 seconds", "Repeat for about a minute"],
  },
  grounding: {
    emoji: "🧠", title: "5-4-3-2-1 Grounding", minutes: 3, kind: "grounding",
    summary: "Bring attention back to your surroundings using your senses.",
    steps: ["Notice 5 things you can see", "Notice 4 things you can feel or touch", "Notice 3 things you can hear",
      "Notice 2 things you can smell", "Notice 1 thing you can taste"],
  },
  mindful_pause: {
    emoji: "🧘", title: "Quick Mindful Pause", minutes: 1, kind: "timer", seconds: 60,
    summary: "One quiet minute of simply noticing.",
    steps: ["Sit comfortably and soften your shoulders", "Notice your breath without changing it",
      "When your mind wanders, gently return to the breath"],
  },
  stretch: {
    emoji: "🙆", title: "Stretch Break", minutes: 2, kind: "timer", seconds: 120,
    summary: "Release tension from sitting with a few gentle stretches.",
    steps: ["Roll your shoulders back five times", "Gently tilt your head side to side",
      "Stretch your arms overhead and breathe in", "Stand up and reach for your toes, only as far as is comfortable"],
  },
  journaling: {
    emoji: "✍️", title: "Journaling", minutes: 5, kind: "writing",
    summary: "Write freely for a few minutes — no rules, no audience.",
    steps: ["Pick a prompt or just start writing", "Don't edit; let the thoughts flow", "Re-read it later if you like"],
  },
  gratitude: {
    emoji: "💛", title: "Gratitude", minutes: 2, kind: "gratitude",
    summary: "Note three things you appreciate today, big or small.",
    steps: ["Think of three things that went right or that you appreciate",
      "Be specific — a person, a moment, a small comfort"],
  },
  focus_reset: {
    emoji: "🎯", title: "Focus Reset", minutes: 2, kind: "timer", seconds: 120,
    summary: "Clear your head before getting back to work.",
    steps: ["Close unneeded tabs and silence notifications", "Write down the single next task",
      "Take three slow breaths", "Start with just the first two minutes of that task"],
  },
  walk: {
    emoji: "🚶", title: "Take a Short Walk", minutes: 5, kind: "timer", seconds: 300,
    summary: "A few minutes of movement and a change of scenery.",
    steps: ["Step away from your screen", "Walk at a comfortable pace, indoors or outside",
      "Notice what's around you — sounds, light, temperature"],
  },
  one_minute_reset: {
    emoji: "🌬️", title: "1-Minute Reset", minutes: 1, kind: "breathing",
    summary: "Four simple steps to slow things down.",
    steps: ["Relax your shoulders.", "Breathe in slowly.", "Exhale longer than you inhale.", "Repeat."],
  },
};

// "Feeling overwhelmed?" small resets (user-initiated, never triggered by the model).
export const OVERWHELMED_RESETS: { icon: string; label: string; activity: string | null; hint: string }[] = [
  { icon: "🌬️", label: "Slow breathing", activity: "one_minute_reset", hint: "One minute, longer exhale" },
  { icon: "🪟", label: "Step away from the screen", activity: "walk", hint: "Even two minutes helps" },
  { icon: "💧", label: "Drink some water", activity: null, hint: "A small, easy reset" },
  { icon: "🚶", label: "Take a short walk", activity: "walk", hint: "Movement and fresh air" },
  { icon: "✍️", label: "Write down what's bothering you", activity: "journaling", hint: "Get it out of your head" },
  { icon: "🤝", label: "Talk to someone you trust", activity: null, hint: "You don't have to sort it out alone" },
];

export const TOOLKIT_ORDER = ["breathing", "grounding", "mindful_pause", "stretch", "journaling", "gratitude",
  "focus_reset", "walk"];

export const FEELINGS_AFTER = ["Better", "Same", "Still difficult"] as const;
export const FEELING_ICONS: Record<string, string> = { Better: "🙂", Same: "😐", "Still difficult": "😕" };

export type Suggestion = [text: string, activity: string | null];

// Suggestions shown after a detected expression.
export const EMOTION_SUGGESTIONS: Record<string, { headline: string; items: Suggestion[] }> = {
  Happy: { headline: "Keep the positive momentum",
    items: [["Write down what's going well today", "gratitude"], ["Capture a good moment to remember later", "journaling"]] },
  Sad: { headline: "Take a gentle pause",
    items: [["Try a slow breathing exercise", "breathing"], ["Answer a journal prompt", "journaling"],
      ["Talk to someone you trust", null]] },
  Angry: { headline: "Create some space",
    items: [["60-second breathing", "breathing"], ["Take a short break away from the screen", "walk"],
      ["Reflect before reacting", "journaling"]] },
  Fear: { headline: "Ground yourself",
    items: [["5-4-3-2-1 grounding", "grounding"], ["Slow breathing with a longer exhale", "breathing"]] },
  Neutral: { headline: "Check in with yourself",
    items: [["A quick mood reflection", null], ["A short mindfulness pause", "mindful_pause"]] },
  Surprise: { headline: "Pause and reflect",
    items: [["Write what caught your attention", "journaling"], ["Take a mindful minute", "mindful_pause"]] },
  Disgust: { headline: "Take a reset",
    items: [["Step away for a few minutes", "walk"],
      ["Refresh your environment — open a window, tidy your space", null], ["A quick focus reset", "focus_reset"]] },
};

export const SELF_CHECK_PROMPT = "This expression may be a good opportunity for a quick self-check.";

// Daily check-in
export const MOODS: Record<string, string> = { Great: "😄", Good: "🙂", Okay: "😐", Low: "😔", Difficult: "😣" };
export const MOOD_SCORE: Record<string, number> = { Great: 5, Good: 4, Okay: 3, Low: 2, Difficult: 1 };
export const MOOD_FACTORS = ["College / Work", "Relationships", "Sleep", "Health", "Exams", "Money", "Family",
  "Personal", "Other"];

// Suggestion after a self-reported mood (the user's own words, not a model output).
export const MOOD_SUGGESTIONS: Record<string, Suggestion> = {
  Great: ["Glad to hear it. Want to note what made today good?", "gratitude"],
  Good: ["Nice. A short gratitude note can help you remember good days.", "gratitude"],
  Okay: ["A mindful minute can be a nice way to check in.", "mindful_pause"],
  Low: ["Thanks for checking in. A gentle breathing exercise might help you slow down.", "breathing"],
  Difficult: ["Thank you for being honest with yourself. A quick reset might help — and talking to someone you trust "
    + "can too.", "one_minute_reset"],
};

// Optional 1–5 ratings in a check-in, saved as energyLevel / stressLevel / sleepQuality (the user's own report).
export type ScaleKey = "energyLevel" | "stressLevel" | "sleepQuality";
export type Scale = { key: ScaleKey; label: string; question: string; low: string; high: string };
export const SCALES: Scale[] = [
  { key: "energyLevel", label: "Energy", question: "How is your energy?", low: "Very low", high: "Very high" },
  { key: "stressLevel", label: "Stress", question: "How stressed do you feel?", low: "Not at all", high: "Very stressed" },
  { key: "sleepQuality", label: "Sleep", question: "How did you sleep last night?", low: "Very poorly", high: "Very well" },
];

// "Ways to feel better": general, evidence-informed self-help ideas by situation. Chosen by the user, never by the
// model, and not a treatment.
export const SITUATIONS: Record<string, { emoji: string; title: string; intro: string; items: Suggestion[] }> = {
  stressed: { emoji: "😮‍💨", title: "Feeling stressed", intro: "When there's too much at once, make the next step smaller.",
    items: [["Try a short breathing exercise", "breathing"], ["Take a short break away from your screen", "walk"],
      ["Break a large task into smaller steps and write down only the next one", "focus_reset"],
      ["Silence unnecessary notifications for a while", null]] },
  anxious: { emoji: "😟", title: "Feeling anxious", intro: "Bring your attention back to the present moment.",
    items: [["Try a grounding exercise", "grounding"], ["Slow your breathing, with a longer exhale", "one_minute_reset"],
      ["Write down one thing you can control right now", "journaling"], ["Talk to someone you trust", null]] },
  low: { emoji: "😔", title: "Feeling low or sad", intro: "Small, familiar actions can make a day feel more manageable.",
    items: [["Keep a basic routine: regular meals, water, getting up at your usual time", null],
      ["Get some daylight or gentle movement", "walk"], ["Connect with someone you trust", null],
      ["Do one small, manageable activity", "focus_reset"]] },
  angry: { emoji: "😤", title: "Feeling angry", intro: "Create a little space between the feeling and your response.",
    items: [["Pause before you respond", "mindful_pause"], ["Step away from the situation for a while", "walk"],
      ["Take a few slow breaths", "breathing"], ["Write down what triggered the reaction", "journaling"]] },
  sleep: { emoji: "🌙", title: "Sleeping poorly", intro: "Sleep usually responds to steady habits more than quick fixes.",
    items: [["Keep consistent sleep and wake times, including weekends", null],
      ["Reduce screen use in the hour before bed", null],
      ["Build a calm wind-down routine before bed", "mindful_pause"],
      ["Avoid caffeine late in the day", null]] },
};

export const JOURNAL_PROMPTS = [
  "What went well today?",
  "What is currently bothering you?",
  "What is one thing you can control right now?",
  "What would make the next hour a little easier?",
  "What are you grateful for today?",
];

/** Suggestions for a detected expression (falls back to the Neutral set). */
export function suggestionsFor(emotion: string) {
  return EMOTION_SUGGESTIONS[emotion] ?? EMOTION_SUGGESTIONS.Neutral;
}
