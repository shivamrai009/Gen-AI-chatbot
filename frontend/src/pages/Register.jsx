import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { apiRegister, saveAuth } from "../auth";

export default function Register() {
  const navigate = useNavigate();
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
      <div className="auth-card">
        <div className="auth-logo" onClick={() => navigate("/")}>
          <span className="logo-icon">⬡</span>
          <span className="logo-text">GitLab <strong>AI</strong></span>
        </div>
        <h2 className="auth-title">Create your account</h2>
        <p className="auth-sub">Start exploring GitLab knowledge instantly</p>

        {error && <div className="auth-error">{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Username
            <input
              type="text"
              placeholder="your_username"
              value={form.username}
              onChange={set("username")}
              pattern="[a-zA-Z0-9_]+"
              minLength={3}
              required
              autoFocus
            />
          </label>
          <label>
            Email
            <input
              type="email"
              placeholder="you@gitlab.com"
              value={form.email}
              onChange={set("email")}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              placeholder="At least 6 characters"
              value={form.password}
              onChange={set("password")}
              minLength={6}
              required
            />
          </label>
          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? <span className="auth-spinner" /> : "Create account →"}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
