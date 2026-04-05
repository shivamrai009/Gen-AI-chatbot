"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useTheme } from "../../components/ThemeProvider";

function parseDetail(detail, fallback) {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e) => e.msg || JSON.stringify(e)).join(", ");
  return fallback;
}

export default function Login() {
  const router = useRouter();
  const { theme, toggle: toggleTheme } = useTheme();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const body = new URLSearchParams({ username: form.username, password: form.password });
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(parseDetail(data.detail, "Login failed"));
      localStorage.setItem("gitlab_chat_token", data.access_token);
      localStorage.setItem("gitlab_chat_user", data.username);
      router.push("/chat");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <button className="auth-theme-btn theme-toggle" onClick={toggleTheme} title="Toggle theme">
        {theme === "dark" ? "☀️" : "🌙"}
      </button>

      <div className="auth-card">
        <div className="auth-logo" onClick={() => router.push("/")} style={{ cursor: "pointer" }}>
          <div className="logo-icon" style={{ width: 26, height: 26, fontSize: ".85rem", borderRadius: 7 }}>⬡</div>
          <span className="logo-text">GitLab <strong>AI</strong></span>
        </div>

        <h2 className="auth-title">Welcome back</h2>
        <p className="auth-sub">Sign in to your account to continue</p>

        {error && (
          <div className="auth-error">
            <span>⚠</span> {error}
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-field">
            <label className="form-label" htmlFor="username">Username</label>
            <input
              id="username"
              className="form-input"
              type="text"
              placeholder="your_username"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              required
              autoFocus
              autoComplete="username"
            />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="password">Password</label>
            <input
              id="password"
              className="form-input"
              type="password"
              placeholder="••••••••"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
              autoComplete="current-password"
            />
          </div>
          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? <span className="spinner" /> : "Sign in →"}
          </button>
        </form>

        <p className="auth-switch">
          Don&apos;t have an account? <Link href="/register">Create one</Link>
        </p>
      </div>
    </div>
  );
}
