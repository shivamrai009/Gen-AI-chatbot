import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { apiRegister, saveAuth } from "../auth";
import { useTheme } from "../theme";

export default function Register() {
  const navigate = useNavigate();
  const { theme, toggle: toggleTheme } = useTheme();
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await apiRegister(form.username, form.email, form.password);
      saveAuth(data.access_token, data.username);
      navigate("/chat");
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
        <div className="auth-logo" onClick={() => navigate("/")}>
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
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
