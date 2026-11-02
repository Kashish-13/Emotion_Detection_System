"use client";

import {
  createUserWithEmailAndPassword, onAuthStateChanged, sendPasswordResetEmail, signInWithEmailAndPassword,
  signOut, updateProfile, type User,
} from "firebase/auth";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { firebaseAuth, firebaseConfigured } from "./firebase";
import { clearCloudRetry } from "./history";
import { clearSession } from "./session";

type AuthState = { user: User | null; loading: boolean };
const AuthContext = createContext<AuthState>({ user: null, loading: true });

/** Drop everything this tab kept for the previous account (session data, cloud back-off). */
function clearAccountState() {
  clearSession();
  clearCloudRetry();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, loading: firebaseConfigured });
  useEffect(() => {
    const auth = firebaseAuth();
    if (!auth) return;
    let uid: string | null | undefined; // undefined until Firebase reports the first state
    return onAuthStateChanged(auth, (user) => {
      const next = user?.uid ?? null;
      // Signed out, or a different account (including sign-outs from another tab or an expired session):
      // reset before any page renders with the new user.
      if (next === null || (uid !== undefined && next !== uid)) clearAccountState();
      uid = next;
      setState({ user, loading: false });
    });
  }, []);
  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

export function displayName(user: User | null): string {
  if (!user) return "";
  return user.displayName || user.email?.split("@")[0] || "there";
}

// Firebase error codes -> safe, helpful messages (same wording as src/firebase_client.py).
const FRIENDLY: Record<string, string> = {
  "auth/email-already-in-use": "An account with this email already exists. Try logging in instead.",
  "auth/invalid-credential": "Incorrect email or password.",
  "auth/invalid-login-credentials": "Incorrect email or password.",
  "auth/wrong-password": "Incorrect email or password.",
  "auth/user-not-found": "Incorrect email or password.",
  "auth/user-disabled": "This account has been disabled.",
  "auth/too-many-requests": "Too many attempts. Please wait a moment and try again.",
  "auth/weak-password": "Please choose a password with at least 6 characters.",
  "auth/invalid-email": "Please enter a valid email address.",
  "auth/missing-password": "Please enter a password.",
  "auth/network-request-failed": "Could not reach Firebase. Check your internet connection.",
  "auth/operation-not-allowed": "Email/password sign-in is not enabled for this Firebase project.",
  "auth/admin-restricted-operation": "New sign-ups are currently turned off for this app.",
  "auth/missing-email": "Please enter a valid email address.",
};

// Problems with the app's own Firebase setup (wrong API key, Authentication not set up, blocked domain). Users
// can't fix these, so they get one plain message; the code is logged for whoever deploys the app.
const CONFIG_ERRORS = ["auth/api-key-not-valid", "auth/invalid-api-key", "auth/configuration-not-found",
  "auth/unauthorized-domain", "auth/requests-from-referer", "auth/app-not-authorized", "auth/invalid-app-id",
  "app/not-configured"];
const CONFIG_MESSAGE = "Sign-in is temporarily unavailable because of a configuration problem on our side. "
  + "Please try again later.";

export function friendlyAuthError(err: unknown): string {
  const code = (err as { code?: string })?.code ?? "";
  if (FRIENDLY[code]) return FRIENDLY[code];
  console.warn("Firebase Auth error:", code || err);
  if (CONFIG_ERRORS.some((c) => code.startsWith(c))) return CONFIG_MESSAGE;
  return "Something went wrong. Please try again.";
}

function requireAuth() {
  const auth = firebaseAuth();
  if (!auth) throw Object.assign(new Error("not configured"), { code: "app/not-configured" });
  return auth;
}

export async function logIn(email: string, password: string) {
  await signInWithEmailAndPassword(requireAuth(), email, password);
}

export async function signUp(name: string, email: string, password: string) {
  const cred = await createUserWithEmailAndPassword(requireAuth(), email, password);
  if (name) await updateProfile(cred.user, { displayName: name });
}

export async function logOut() {
  clearAccountState();
  await signOut(requireAuth());
}

// Resolves whether or not the account exists, so the UI never reveals which emails are registered.
export async function resetPassword(email: string) {
  try {
    await sendPasswordResetEmail(requireAuth(), email);
  } catch (err) {
    if ((err as { code?: string })?.code !== "auth/user-not-found") throw err;
  }
}
