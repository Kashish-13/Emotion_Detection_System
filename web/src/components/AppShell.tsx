"use client";

// Signed-in layout: sidebar navigation + a client-side guard that sends signed-out visitors to /login.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { displayName, logOut, useAuth } from "@/lib/auth";

const NAV = [
  { section: "Home", items: [{ href: "/dashboard", label: "Dashboard", icon: "▦" }] },
  { section: "Analyze", items: [{ href: "/detect", label: "Detect Emotion", icon: "◉" }] },
  { section: "Wellbeing", items: [
    { href: "/checkin", label: "Daily Check-In", icon: "✎" },
    { href: "/tracker", label: "Wellbeing Tracker", icon: "∿" },
    { href: "/wellbeing", label: "Wellbeing Toolkit", icon: "❀" },
    { href: "/history", label: "History & Insights", icon: "↺" },
  ] },
  { section: "Support", items: [{ href: "/support", label: "Find Professional Support", icon: "✚" }] },
  { section: "Learn", items: [
    { href: "/model", label: "Model Insights", icon: "◈" },
    { href: "/about", label: "About", icon: "ⓘ" },
  ] },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [leaving, setLeaving] = useState(false); // logging out: go home, not to the login redirect

  useEffect(() => {
    if (!loading && !user && !leaving) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [loading, user, leaving, router, pathname]);

  useEffect(() => setOpen(false), [pathname]);

  if (loading || !user) {
    return <div className="center"><span className="spinner muted" aria-label="Loading" /></div>;
  }

  const name = displayName(user);
  return (
    <div className="shell">
      <header className="topbar">
        <Link href="/dashboard" className="brand" style={{ padding: 0 }}><span className="brand-mark">ES</span>EmotionSense</Link>
        <button className="btn btn-sm" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls="sidebar">Menu</button>
      </header>
      <aside id="sidebar" className={`sidebar${open ? " open" : ""}`}>
        <Link href="/dashboard" className="brand"><span className="brand-mark">ES</span>EmotionSense</Link>
        <nav className="nav" aria-label="Main">
          {NAV.map((group) => (
            <div key={group.section}>
              <div className="nav-label">{group.section}</div>
              {group.items.map((item) => (
                <Link key={item.href} href={item.href} className={pathname === item.href ? "active" : ""}
                      aria-current={pathname === item.href ? "page" : undefined}>
                  <span aria-hidden="true" style={{ width: 18, textAlign: "center" }}>{item.icon}</span>{item.label}
                </Link>
              ))}
            </div>
          ))}
        </nav>
        <Link href="/support#urgent" className="nav-help">
          <strong>Need immediate help?</strong>
          <span className="small">Emergency and helpline contacts</span>
        </Link>
        <div className="profile">
          <div className="row" style={{ flexWrap: "nowrap" }}>
            <div className="avatar">{name.slice(0, 1).toUpperCase()}</div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 650 }} className="ellipsis">{name}</div>
              <div className="muted small ellipsis">{user.email}</div>
            </div>
          </div>
          <button className="btn btn-sm btn-block" style={{ marginTop: 12 }}
                  onClick={async () => { setLeaving(true); await logOut(); router.replace("/"); }}>Log out</button>
        </div>
        <p className="muted small" style={{ marginTop: 12, padding: "0 4px" }}>
          Facial-expression analysis only — not a diagnostic tool.
        </p>
      </aside>
      <main className="main"><div className="container page">{children}</div></main>
    </div>
  );
}
