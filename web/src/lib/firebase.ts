// Firebase client initialisation. All values come from NEXT_PUBLIC_* environment variables.
// The Web API key identifies the project and is public by design; access to data is
// controlled by Firebase Auth and the Firestore security rules (firestore.rules).
import { getApp, getApps, initializeApp, type FirebaseApp } from "firebase/app";
import { connectAuthEmulator, getAuth, type Auth } from "firebase/auth";
import { getFirestore, type Firestore } from "firebase/firestore";

const config = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
    || (process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID ? `${process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID}.firebaseapp.com` : undefined),
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || undefined,
};

export const firebaseConfigured = Boolean(config.apiKey && config.projectId);

let app: FirebaseApp | null = null;
let auth: Auth | null = null;
let db: Firestore | null = null;

function init() {
  if (!firebaseConfigured || typeof window === "undefined") return;
  if (!app) {
    app = getApps().length ? getApp() : initializeApp(config);
    auth = getAuth(app);
    const emulator = process.env.NEXT_PUBLIC_FIREBASE_AUTH_EMULATOR_HOST; // local development only
    if (emulator) connectAuthEmulator(auth, `http://${emulator}`, { disableWarnings: true });
    db = getFirestore(app);
  }
}

export function firebaseAuth(): Auth | null {
  init();
  return auth;
}

export function firestore(): Firestore | null {
  init();
  return db;
}
