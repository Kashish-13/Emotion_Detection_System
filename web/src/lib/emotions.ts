// Display helpers for emotions. The labels themselves (model output order) and the confidence
// bands live in ./emotion/core, shared with the in-browser inference module.
import type { Emotion } from "./emotion/core";

export { EMOTIONS, confidenceLevel, type Emotion, type Level } from "./emotion/core";

// Same colours and emoji as the Streamlit app (src/config.py). Colour is never used alone:
// every emotion is always shown with its emoji and name.
export const EMOTION_COLORS: Record<Emotion, string> = {
  Angry: "#ea5a3a", Disgust: "#2f9e5c", Fear: "#8156e8", Happy: "#e8b023",
  Sad: "#2f7fe0", Surprise: "#c95bd0", Neutral: "#8394b0",
};

export const EMOTION_EMOJI: Record<Emotion, string> = {
  Angry: "😠", Disgust: "🤢", Fear: "😨", Happy: "😊", Sad: "😢", Surprise: "😮", Neutral: "😐",
};

// Describes the facial *expression*, never what the person feels (src/wellbeing.py EXPRESSION_TEXT).
const EXPRESSION_TEXT: Record<Emotion, string> = {
  Happy: "a positive, smiling facial expression",
  Sad: "a downturned facial expression often associated with sadness",
  Angry: "a tense facial expression often associated with anger",
  Fear: "a wide-eyed facial expression often associated with fear",
  Surprise: "a raised-brow facial expression often associated with surprise",
  Disgust: "a facial expression often associated with disgust",
  Neutral: "a calm, neutral facial expression",
};

export function describeExpression(emotion: string): string {
  return `Facial expression appears consistent with ${EXPRESSION_TEXT[emotion as Emotion] ?? "a neutral expression"}.`;
}

export const color = (emotion: string) => EMOTION_COLORS[emotion as Emotion] ?? "#4f46e5";
export const emoji = (emotion: string) => EMOTION_EMOJI[emotion as Emotion] ?? "🙂";

export const pct = (p: number) => (p < 0.01 ? "<1%" : `${Math.round(p * 100)}%`);
