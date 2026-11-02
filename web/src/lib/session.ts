"use client";

// This browser tab's session data, like the Streamlit app's st.session_state: the latest analysed face (for the
// dashboard's "Current emotion" card) and the live predictions logged this session. Never saved to history;
// kept in sessionStorage so it survives page navigation and reloads, and cleared on log-out.
import { useSyncExternalStore } from "react";
import type { FacePrediction } from "./emotion/core";

export type LastFace = Pick<FacePrediction, "emotion" | "confidence" | "probabilities" | "top3"> & { source: string };
export type SessionPrediction = { emotion: string; confidence: number; source: string };
type Session = { lastFace: LastFace | null; predictions: SessionPrediction[]; facesDetected: number };

const KEY = "emotionsense:session";
const MAX_PREDICTIONS = 500; // SESSION_HISTORY_SIZE in src/config.py
const EMPTY: Session = { lastFace: null, predictions: [], facesDetected: 0 };

let cache: Session | null = null;
const listeners = new Set<() => void>();

function read(): Session {
  if (cache) return cache;
  try {
    cache = { ...EMPTY, ...JSON.parse(sessionStorage.getItem(KEY) || "{}") };
  } catch {
    cache = EMPTY;
  }
  return cache!;
}

function write(next: Session) {
  cache = next;
  try {
    sessionStorage.setItem(KEY, JSON.stringify(next));
  } catch { /* storage blocked: keep it in memory for this page */ }
  listeners.forEach((l) => l());
}

const pick = (f: FacePrediction, source: string): LastFace =>
  ({ emotion: f.emotion, confidence: f.confidence, probabilities: f.probabilities, top3: f.top3, source });

/** Keep the latest analysed face for the dashboard (this session only). */
export function rememberFace(face: FacePrediction, source: string) {
  write({ ...read(), lastFace: pick(face, source) });
}

/** Log analysed faces for the session summary, keeping the most recent MAX_PREDICTIONS. */
export function logPredictions(faces: FacePrediction[], source: string) {
  const s = read();
  const predictions = [...s.predictions, ...faces.map((f) => ({ emotion: f.emotion, confidence: f.confidence, source }))];
  write({ ...s, predictions: predictions.slice(-MAX_PREDICTIONS), facesDetected: s.facesDetected + faces.length });
}

export function resetSessionPredictions() {
  write({ ...read(), predictions: [], facesDetected: 0 });
}

export function clearSession() {
  write(EMPTY);
  try {
    sessionStorage.removeItem(KEY);
  } catch { /* nothing to clear */ }
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

export function useSession(): Session {
  return useSyncExternalStore(subscribe, read, () => EMPTY);
}
