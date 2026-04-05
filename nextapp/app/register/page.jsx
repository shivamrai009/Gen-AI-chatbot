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

export default function Register() {
  const router = useRouter();
  const { theme, toggle: toggleTheme } = useTheme();
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: form.username, email: form.email, password: form.password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(parseDetail(data.detail, "Registration failed"));
      localStorage.setItem("gitlab_chat_token", data.access_token);
      localStorage.setItem("gitlab_chat_user", data.username);
      router.push("/chat");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function set(field) {
    return (e) => setForm({ ...form, [field]: e.target.value });
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

        <h2 className="auth-title">Create your account</h2>
        <p className="auth-sub">Start exploring GitLab knowledge instantly</p>

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
              onChange={set("username")}
              pattern="[a-zA-Z0-9_]+"
              minLength={3}
              required
              autoFocus
              autoComplete="username"
            />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="email">Email</label>
            <input
              id="email"
              className="form-input"
              type="email"
              placeholder="you@gitlab.com"
              value={form.email}
              onChange={set("email")}
              required
              autoComplete="email"
            />
          </div>
          <div className="form-field">
            <label className="form-label" htmlFor="password">Password</label>
            <input
              id="password"
              className="form-input"
              type="password"
              placeholder="At least 6 characters"
              value={form.password}
              onChange={set("password")}
              minLength={6}
              required
              autoComplete="new-password"
            />
          </div>
          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? <span className="spinner" /> : "Create account →"}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account? <Link href="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
