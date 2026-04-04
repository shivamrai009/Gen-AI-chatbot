import { useNavigate } from "react-router-dom";
import { isLoggedIn } from "../auth";

const features = [
  {
    icon: "🧠",
    title: "Knowledge Graph RAG",
    desc: "Hybrid vector + entity graph retrieval surfaces the most relevant handbook context, not just keyword matches.",
  },
  {
    icon: "🔍",
    title: "Source-Grounded Answers",
    desc: "Every answer is verified against cited sources by an AI critic before it reaches you.",
  },
  {
    icon: "🔀",
    title: "Intelligent Query Routing",
    desc: "Questions are automatically classified and routed to the optimal retrieval strategy.",
  },
  {
    icon: "💬",
    title: "Multi-Turn Conversations",
    desc: "Full conversation history is maintained so follow-up questions get contextual answers.",
  },
  {
    icon: "🛡️",
    title: "Built-in Guardrails",
    desc: "Off-topic and unsafe queries are detected and gracefully rejected before reaching the LLM.",
  },
  {
    icon: "📊",
    title: "Transparent Telemetry",
    desc: "Every response shows its route, source confidence, and critic result so you always know why.",
  },
];

const steps = [
  { num: "01", title: "Ask anything", desc: "Type a question about GitLab's processes, values, strategy, or teams." },
  { num: "02", title: "AI retrieves context", desc: "Hybrid RAG searches the indexed handbook and direction pages." },
  { num: "03", title: "Verified answer", desc: "An AI critic validates the answer against sources before delivery." },
];

export default function Landing() {
  const navigate = useNavigate();

  function handleStart() {
    if (isLoggedIn()) navigate("/chat");
    else navigate("/login");
  }

  return (
    <div className="landing">
      {/* Nav */}
      <nav className="landing-nav">
        <div className="landing-nav-logo">
          <span className="logo-icon">⬡</span>
          <span className="logo-text">GitLab <strong>AI</strong></span>
        </div>
        <div className="landing-nav-links">
          <button className="nav-btn-ghost" onClick={() => navigate("/login")}>Sign in</button>
          <button className="nav-btn-primary" onClick={() => navigate("/register")}>Get started</button>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero">
        <div className="hero-badge">✦ Powered by Gemini 2.0 Flash + Knowledge Graph RAG</div>
        <h1 className="hero-title">
          Your GitLab Knowledge<br />
          <span className="hero-gradient">Intelligence Layer</span>
        </h1>
        <p className="hero-sub">
          Instantly surface answers from GitLab's Handbook and Direction pages.<br />
          Grounded in sources. Verified by AI. Built for GitLab team members.
        </p>
        <div className="hero-actions">
          <button className="btn-primary-lg" onClick={handleStart}>
            Start exploring →
          </button>
          <a className="btn-ghost-lg" href="https://handbook.gitlab.com" target="_blank" rel="noreferrer">
            View Handbook ↗
          </a>
        </div>

        {/* Fake terminal preview */}
        <div className="hero-terminal">
          <div className="terminal-bar">
            <span /><span /><span />
            <p>gitlab-ai — chat</p>
          </div>
          <div className="terminal-body">
            <p><span className="t-user">you</span> What are GitLab's core values?</p>
            <p className="t-gap" />
            <p><span className="t-ai">ai</span> GitLab's six core values are:</p>
            <p className="t-indent">🤝 <strong>Collaboration</strong> — help each other succeed</p>
            <p className="t-indent">📈 <strong>Results for Customers</strong> — focus on impact</p>
            <p className="t-indent">⏱️ <strong>Efficiency</strong> — boring solutions, fast delivery</p>
            <p className="t-indent">🌐 <strong>Diversity, Inclusion &amp; Belonging</strong></p>
            <p className="t-indent">🐾 <strong>Iteration</strong> — ship, learn, improve</p>
            <p className="t-indent">👁️ <strong>Transparency</strong> — default to public</p>
            <p className="t-gap" />
            <p className="t-meta">📎 3 sources · route: vector · critic ✓</p>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="features">
        <h2 className="section-title">Beyond a basic chatbot</h2>
        <p className="section-sub">Production-grade retrieval architecture, not a simple search wrapper.</p>
        <div className="features-grid">
          {features.map((f) => (
            <div className="feature-card" key={f.title}>
              <div className="feature-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="how">
        <h2 className="section-title">How it works</h2>
        <div className="steps">
          {steps.map((s, i) => (
            <div className="step" key={s.num}>
              <div className="step-num">{s.num}</div>
              <div>
                <h3>{s.title}</h3>
                <p>{s.desc}</p>
              </div>
              {i < steps.length - 1 && <div className="step-arrow">→</div>}
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <h2>Ready to explore the handbook?</h2>
        <p>Join thousands of GitLab team members getting instant, grounded answers.</p>
        <button className="btn-primary-lg" onClick={handleStart}>Get started for free →</button>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p>Built with ❤️ using Gemini 2.0 Flash · FastAPI · React</p>
        <p>Data sourced from <a href="https://handbook.gitlab.com" target="_blank" rel="noreferrer">handbook.gitlab.com</a></p>
      </footer>
    </div>
  );
}
