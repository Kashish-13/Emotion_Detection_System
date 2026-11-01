"use client";

// Login, sign-up and password-reset forms (Firebase Authentication).
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { friendlyAuthError, logIn, resetPassword, signUp, useAuth } from "@/lib/auth";
import { firebaseConfigured } from "@/lib/firebase";

type Mode = "login" | "signup" | "reset";
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

const COPY: Record<Mode, { title: string; subtitle: string; submit: string }> = {
  login: { title: "Welcome back", subtitle: "Log in to analyse images and see your history.", submit: "Log in" },
  signup: { title: "Create your account", subtitle: "Your predictions are saved privately to your account.", submit: "Create account" },
  reset: { title: "Reset your password", subtitle: "We'll email you a link to choose a new password.", submit: "Send reset link" },
};

/** Only allow redirects to pages inside this app. */
function safeNext(next: string | null) {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard";
}

export default function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"));
  const { user, loading } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && user && mode !== "reset") router.replace(next);
  }, [loading, user, mode, next, router]);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setDone(null);
    const email = form.email.trim();
    if (!EMAIL_RE.test(email)) return setError("Please enter a valid email address.");
    if (mode !== "reset" && form.password.length < 6) return setError("Passwords must be at least 6 characters.");
    if (mode === "signup" && form.password !== form.confirm) return setError("Passwords don't match.");
    setBusy(true);
    try {
      if (mode === "login") await logIn(email, form.password);
      else if (mode === "signup") await signUp(form.name.trim(), email, form.password);
      else {
        await resetPassword(email);
        setDone("If an account exists for that email, a password-reset link has been sent.");
      }
    } catch (err) {
      setError(friendlyAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  const copy = COPY[mode];
  const q = params.get("next") ? `?next=${encodeURIComponent(next)}` : "";
  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <Link href="/" className="brand" style={{ justifyContent: "center", paddingBottom: 22 }}>
          <span className="brand-mark">ES</span>EmotionSense
        </Link>
        <div className="card" style={{ padding: 28 }}>
          <h1 style={{ fontSize: "1.45rem", fontWeight: 700 }}>{copy.title}</h1>
          <p className="muted" style={{ margin: "4px 0 20px" }}>{copy.subtitle}</p>
          {!firebaseConfigured && (
            <div className="alert alert-warning" style={{ marginBottom: 16 }}>
              Firebase isn&apos;t configured. Set the <code>NEXT_PUBLIC_FIREBASE_*</code> environment variables (see web/README.md).
            </div>
          )}
          <form onSubmit={onSubmit} noValidate>
            {mode === "signup" && (
              <label className="field"><span>Name</span>
                <input className="input" value={form.name} onChange={set("name")} maxLength={40}
                       placeholder="What should we call you?" autoComplete="name" />
              </label>
            )}
            <label className="field"><span>Email</span>
              <input className="input" type="email" value={form.email} onChange={set("email")}
                     placeholder="you@example.com" autoComplete="email" required />
            </label>
            {mode !== "reset" && (
              <label className="field"><span>Password</span>
                <input className="input" type="password" value={form.password} onChange={set("password")}
                       autoComplete={mode === "signup" ? "new-password" : "current-password"} required />
              </label>
            )}
            {mode === "signup" && (
              <label className="field"><span>Confirm password</span>
                <input className="input" type="password" value={form.confirm} onChange={set("confirm")}
                       autoComplete="new-password" required />
              </label>
            )}
            {error && <div className="alert alert-error" role="alert" style={{ marginBottom: 14 }}>{error}</div>}
            {done && <div className="alert alert-success" role="status" style={{ marginBottom: 14 }}>{done}</div>}
            <button className="btn btn-primary btn-block" disabled={busy || !firebaseConfigured} type="submit">
              {busy ? <span className="spinner" aria-label="Working" /> : copy.submit}
            </button>
          </form>
          <div className="small muted" style={{ marginTop: 18, display: "grid", gap: 6, textAlign: "center" }}>
            {mode === "login" && <>
              <span>New here? <Link href={`/signup${q}`}>Create an account</Link></span>
              <Link href="/reset-password">Forgot your password?</Link>
            </>}
            {mode === "signup" && <span>Already have an account? <Link href={`/login${q}`}>Log in</Link></span>}
            {mode === "reset" && <Link href="/login">Back to log in</Link>}
          </div>
        </div>
      </div>
    </div>
  );
}
