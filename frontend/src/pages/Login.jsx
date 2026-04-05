import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { apiLogin, saveAuth } from "../auth";
import { useTheme } from "../theme";

export default function Login() {
  const navigate = useNavigate();
  const { theme, toggle: toggleTheme } = useTheme();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await apiLogin(form.username, form.password);
      saveAuth(data.access_token, data.username);
      navigate("/chat");
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
        <div className="auth-logo" onClick={() => navigate("/")}>
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
          Don't have an account? <Link to="/register">Create one</Link>
        </p>
      </div>
    </div>
  );
}
