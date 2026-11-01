// History shared with the Streamlit app: Firestore users/{uid}/checkins, same entry format as
// src/storage.py (kind, ISO-8601 UTC timestamp, detectedEmotion, confidence, topPredictions, ...).
// Images are never stored. If Firestore is unavailable, entries are kept in this browser instead
// (like the Streamlit app's session fallback) and the cloud is retried after a minute.
import {
  addDoc, collection, deleteDoc, doc, getDocs, limit as qLimit, query,
} from "firebase/firestore";
import { firestore } from "./firebase";
import type { FaceResult } from "./emotion";

export type HistoryEntry = {
  id: string;
  kind: "detection" | "checkin" | "journal" | "reset";
  timestamp: string;
  source?: string;
  detectedEmotion?: string;
  confidence?: number;
  topPredictions?: { emotion: string; probability: number }[];
  selfReportedMood?: string;
  moodFactors?: string[];
  journalText?: string;
  prompt?: string;
  activity?: string;
  feelingAfter?: string;
};

const FETCH_LIMIT = 500;
const TIMEOUT_MS = 8000;
const RETRY_MS = 60_000;
const RETRY_KEY = "emotionsense:cloud-retry-at"; // kept for the tab session so reloads don't wait again

function cloudAvailable(): boolean {
  try {
    return Date.now() >= Number(sessionStorage.getItem(RETRY_KEY) || 0);
  } catch {
    return true;
  }
}

/** Forget the Firestore back-off, so the next account starts with a fresh cloud attempt. */
export function clearCloudRetry() {
  try {
    sessionStorage.removeItem(RETRY_KEY);
  } catch { /* nothing to clear */ }
}

const localKey = (uid: string) => `emotionsense:history:${uid}`;
const round4 = (x: number) => Math.round(x * 1e4) / 1e4;

function withTimeout<T>(promise: Promise<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error("timeout")), TIMEOUT_MS);
    promise.then((v) => { clearTimeout(t); resolve(v); }, (e) => { clearTimeout(t); reject(e); });
  });
}

function cloudFailed(err: unknown) {
  console.warn("Firestore unavailable; using browser storage for history.", (err as { code?: string })?.code ?? err);
  try {
    sessionStorage.setItem(RETRY_KEY, String(Date.now() + RETRY_MS));
  } catch { /* storage blocked: we'll simply retry next time */ }
}

function readLocal(uid: string): HistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem(localKey(uid)) || "[]");
  } catch {
    return [];
  }
}

function writeLocal(uid: string, entries: HistoryEntry[]) {
  try {
    localStorage.setItem(localKey(uid), JSON.stringify(entries.slice(-FETCH_LIMIT)));
  } catch { /* storage full or blocked: nothing else we can do */ }
}

const newestFirst = (a: HistoryEntry, b: HistoryEntry) => (b.timestamp || "").localeCompare(a.timestamp || "");

type EntryFields = Omit<HistoryEntry, "id" | "kind" | "timestamp">;

/** An entry with a UTC timestamp, dropping empty optional fields (src/storage.py new_entry). */
export function newEntry(kind: HistoryEntry["kind"], fields: EntryFields = {}): Omit<HistoryEntry, "id"> {
  const kept = Object.entries(fields).filter(([, v]) => v != null && v !== "" && !(Array.isArray(v) && v.length === 0));
  return { kind, timestamp: new Date().toISOString(), ...Object.fromEntries(kept) };
}

/** A detection entry in the Streamlit format (src/storage.py detection_entry). Never contains image data. */
export function detectionEntry(face: FaceResult, source = "web", mood?: string | null) {
  return newEntry("detection", {
    source,
    detectedEmotion: face.emotion,
    confidence: round4(face.confidence),
    topPredictions: face.top3.map((p) => ({ emotion: p.emotion, probability: round4(p.probability) })),
    selfReportedMood: mood ?? undefined,
  });
}

/** Save an entry exactly once. True: saved to Firestore; false: kept in this browser instead. */
export async function saveEntry(uid: string, entry: Omit<HistoryEntry, "id">): Promise<boolean> {
  const db = firestore();
  if (db && cloudAvailable()) {
    try {
      await withTimeout(addDoc(collection(db, "users", uid, "checkins"), { ...entry, userId: uid }));
      return true;
    } catch (err) {
      cloudFailed(err);
    }
  }
  writeLocal(uid, [...readLocal(uid), { ...entry, id: `local-${crypto.randomUUID()}` }]);
  return false;
}

export async function listHistory(uid: string): Promise<HistoryEntry[]> {
  const local = readLocal(uid);
  const db = firestore();
  let cloud: HistoryEntry[] = [];
  if (db && cloudAvailable()) {
    try {
      const snap = await withTimeout(getDocs(query(collection(db, "users", uid, "checkins"), qLimit(FETCH_LIMIT))));
      cloud = snap.docs.map((d) => ({ ...(d.data() as Omit<HistoryEntry, "id">), id: d.id }));
    } catch (err) {
      cloudFailed(err);
    }
  }
  return [...cloud, ...local].sort(newestFirst);
}

export async function deleteEntry(uid: string, id: string): Promise<boolean> {
  if (id.startsWith("local-")) {
    writeLocal(uid, readLocal(uid).filter((e) => e.id !== id));
    return true;
  }
  const db = firestore();
  if (!db) return false;
  try {
    await withTimeout(deleteDoc(doc(db, "users", uid, "checkins", id)));
    return true;
  } catch (err) {
    cloudFailed(err);
    return false;
  }
}

/** Delete everything. False if the browser copy was cleared but some cloud entries couldn't be deleted. */
export async function clearHistory(uid: string): Promise<boolean> {
  writeLocal(uid, []);
  const db = firestore();
  if (!db) return true;
  try {
    for (;;) { // in pages, so histories longer than FETCH_LIMIT are cleared too
      const snap = await withTimeout(getDocs(query(collection(db, "users", uid, "checkins"), qLimit(FETCH_LIMIT))));
      if (snap.empty) return true;
      await withTimeout(Promise.all(snap.docs.map((d) => deleteDoc(d.ref))));
    }
  } catch (err) {
    cloudFailed(err);
    return false;
  }
}
