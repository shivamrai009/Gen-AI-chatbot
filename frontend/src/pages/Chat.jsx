import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { sendChatStream, sendFeedback } from "../api";
import { getUser, getToken, clearAuth } from "../auth";
import { useTheme } from "../theme";

const GREETINGS = [
  "What would you like to explore in the GitLab Handbook today?",
  "Ask me anything about GitLab's strategy, values, or processes.",
  "What GitLab knowledge can I surface for you?",
  "Ready to dive into the handbook. What's on your mind?",
];

const SUGGESTED = [
  "What are GitLab's core values?",
  "How does GitLab approach remote work?",
  "What is GitLab's product vision?",
  "How does GitLab handle engineering culture?",
  "What is GitLab's mission?",
  "How does GitLab practice transparency?",
];

// ── API helpers ────────────────────────────────────────────────
async function apiConv(method, path, body) {
  const res = await fetch(`/conversations${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok && res.status !== 204) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.detail || "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Markdown components ────────────────────────────────────────
const mdComponents = {
  a: ({ node, ...props }) => (
    <a {...props} target="_blank" rel="noreferrer" />
  ),
  code: ({ node, inline, className, children, ...props }) => {
    if (inline) {
      return <code className={className} {...props}>{children}</code>;
    }
    return (
      <pre>
        <code className={className} {...props}>{children}</code>
      </pre>
    );
  },
};

// ── Sub-components ─────────────────────────────────────────────
function SourceCard({ source }) {
  const [open, setOpen] = useState(false);
  const isHandbook = source.url?.includes("handbook");
  return (
    <div className="source-card" onClick={() => setOpen(!open)}>
      <div className="source-card-header">
        <span className="source-favicon">{isHandbook ? "📖" : "🔗"}</span>
        <div className="source-info">
          <span className="source-title">{source.title}</span>
          {source.section && <span className="source-section">{source.section}</span>}
        </div>
        <span className="source-chevron">{open ? "▲" : "▼"}</span>
      </div>
      {open && (
        <div className="source-body">
          {source.snippet && <p className="source-snippet">{source.snippet}</p>}
          <a href={source.url} target="_blank" rel="noreferrer" className="source-link">
            Open page ↗
          </a>
        </div>
      )}
    </div>
  );
}

function Message({ msg, onFeedback, onFollowup }) {
  const [copied, setCopied] = useState(false);
  const [voted, setVoted] = useState(null);

  function copy() {
    navigator.clipboard.writeText(msg.answer || msg.content || "");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function vote(v) {
    if (voted || !msg.traceId) return;
    setVoted(v);
    onFeedback(msg.traceId, v);
  }

  if (msg.role === "user") {
    return (
      <div className="msg-row msg-user-row">
        <div className="msg-bubble msg-user">{msg.content}</div>
      </div>
    );
  }

  const text = msg.answer ?? msg.content ?? "";

  return (
    <div className="msg-row msg-ai-row">
      <div className="msg-avatar">⬡</div>
      <div className="msg-ai-block">
        {msg.route && (
          <div className="msg-meta-bar">
            <span className={`badge badge-route route-${msg.route}`}>{msg.route}</span>
            {msg.criticPassed !== undefined && (
              <span className={`badge ${msg.criticPassed ? "badge-critic-ok" : "badge-critic-fail"}`}>
                {msg.criticPassed ? "✓ verified" : "⚠ unverified"}
              </span>
            )}
          </div>
        )}

        <div className={`msg-bubble msg-ai ${msg.streaming ? "streaming" : ""}`}>
          {msg.streaming && !text ? (
            <span className="typing-dots"><span /><span /><span /></span>
          ) : (
            <div className="prose">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                {text}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {msg.sources?.length > 0 && (
          <div className="sources-section">
            <p className="sources-label">
              📎 {msg.sources.length} source{msg.sources.length > 1 ? "s" : ""}
            </p>
            {msg.sources.map((s, i) => <SourceCard key={i} source={s} />)}
          </div>
        )}

        {!msg.streaming && msg.followups?.length > 0 && (
          <div className="followup-section">
            <p className="followup-label">Continue exploring</p>
            <div className="followup-chips">
              {msg.followups.map((q, i) => (
                <button key={i} className="followup-chip" onClick={() => onFollowup(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {!msg.streaming && text && (
          <div className="msg-actions">
            <button className="action-btn" onClick={copy}>
              {copied ? "✓ Copied" : "⎘ Copy"}
            </button>
            <button
              className={`action-btn ${voted === "up" ? "voted" : ""}`}
              onClick={() => vote("up")}
              disabled={!!voted}
            >👍 Helpful</button>
            <button
              className={`action-btn ${voted === "down" ? "voted" : ""}`}
              onClick={() => vote("down")}
              disabled={!!voted}
            >👎 Not helpful</button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────
export default function Chat() {
  const navigate = useNavigate();
  const { theme, toggle: toggleTheme } = useTheme();
  const username = getUser();
  const greeting = GREETINGS[Math.floor(Math.random() * GREETINGS.length)];

  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [convLoading, setConvLoading] = useState(true);

  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 160)}px`;
    }
  }, [input]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    apiConv("GET", "")
      .then(setConversations)
      .catch(() => {})
      .finally(() => setConvLoading(false));
  }, []);

  async function openConversation(conv) {
    setActiveConvId(conv.id);
    setSidebarOpen(false);
    const msgs = await apiConv("GET", `/${conv.id}/messages`).catch(() => []);
    setMessages(
      msgs.map((m) => ({
        id: m.id,
        role: m.role === "assistant" ? "ai" : "user",
        content: m.content,
        answer: m.role === "assistant" ? m.content : undefined,
        sources: m.sources || [],
        route: m.route,
        traceId: m.trace_id,
      }))
    );
  }

  function startNewConversation() {
    setActiveConvId(null);
    setMessages([]);
    setSidebarOpen(false);
  }

  function buildHistory() {
    return messages
      .filter((m) => !m.streaming)
      .map((m) => ({
        role: m.role === "user" ? "user" : "assistant",
        content: m.role === "user" ? m.content : (m.answer || ""),
      }));
  }

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim() || loading) return;
      const question = text.trim();
      setInput("");
      setLoading(true);

      const userMsg = { id: `u-${Date.now()}`, role: "user", content: question };
      const aiMsg = {
        id: `a-${Date.now()}`, role: "ai", answer: "", streaming: true,
        sources: [], route: null, criticPassed: null, traceId: null, followups: [],
      };

      setMessages((prev) => [...prev, userMsg, aiMsg]);

      let convId = activeConvId;
      if (!convId) {
        try {
          const title = question.slice(0, 60);
          const conv = await apiConv("POST", "", { title });
          convId = conv.id;
          setActiveConvId(convId);
          setConversations((prev) => [conv, ...prev]);
        } catch {}
      }

      if (convId) {
        apiConv("POST", `/${convId}/messages`, { role: "user", content: question }).catch(() => {});
      }

      const streamData = { answer: "", sources: [], route: null, traceId: null };

      try {
        await sendChatStream(question, buildHistory(), {
          onToken: (token) => {
            streamData.answer += token;
            setMessages((prev) =>
              prev.map((m) => m.id === aiMsg.id ? { ...m, answer: m.answer + token } : m)
            );
          },
          onMeta: (data) => {
            const [, route, traceId] = data.split("|");
            streamData.route = route;
            streamData.traceId = traceId;
            setMessages((prev) =>
              prev.map((m) => m.id === aiMsg.id ? { ...m, route, traceId } : m)
            );
          },
          onSources: (data) => {
            try {
              const sources = JSON.parse(data);
              streamData.sources = sources;
              setMessages((prev) =>
                prev.map((m) => m.id === aiMsg.id ? { ...m, sources } : m)
              );
            } catch {}
          },
          onFollowups: (data) => {
            try {
              const followups = JSON.parse(data);
              setMessages((prev) =>
                prev.map((m) => m.id === aiMsg.id ? { ...m, followups } : m)
              );
            } catch {}
          },
          onDone: () => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiMsg.id ? { ...m, streaming: false, criticPassed: true } : m
              )
            );
            setLoading(false);

            if (convId) {
              apiConv("POST", `/${convId}/messages`, {
                role: "assistant",
                content: streamData.answer,
                sources: streamData.sources,
                route: streamData.route,
                trace_id: streamData.traceId,
              }).catch(() => {});

              if (conversations.find((c) => c.id === convId)?.title === question.slice(0, 60)) {
                const title = question.length > 50 ? question.slice(0, 50) + "…" : question;
                apiConv("PATCH", `/${convId}/title`, { title }).catch(() => {});
                setConversations((prev) =>
                  prev.map((c) => c.id === convId ? { ...c, title } : c)
                );
              }
            }
          },
          onError: (err) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiMsg.id ? { ...m, answer: `Error: ${err}`, streaming: false } : m
              )
            );
            setLoading(false);
          },
        });
      } catch (err) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === aiMsg.id
              ? { ...m, answer: `Failed to connect: ${err.message}`, streaming: false }
              : m
          )
        );
        setLoading(false);
      }
    },
    [loading, activeConvId, messages, conversations]
  );

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  function handleFeedback(traceId, vote) {
    sendFeedback(traceId, vote).catch(() => {});
  }

  async function deleteConversation(e, id) {
    e.stopPropagation();
    await apiConv("DELETE", `/${id}`).catch(() => {});
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConvId === id) {
      setActiveConvId(null);
      setMessages([]);
    }
  }

  function handleLogout() {
    clearAuth();
    navigate("/");
  }

  const isEmpty = messages.length === 0;
  const hour = new Date().getHours();
  const timeGreeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className="chat-page">
      {/* ── Sidebar ── */}
      <aside className={`chat-sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <div className="logo-wrap" style={{ cursor: "pointer" }} onClick={() => navigate("/")}>
            <div className="logo-icon">⬡</div>
            <span className="logo-text">GitLab <strong>AI</strong></span>
          </div>
          <button className="theme-toggle" onClick={toggleTheme} title="Toggle theme">
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
        </div>

        <div className="sidebar-body">
          <button className="new-chat-btn" onClick={startNewConversation}>
            <span>＋</span> New conversation
          </button>

          {convLoading ? (
            <p className="sidebar-loading">Loading history…</p>
          ) : conversations.length === 0 ? (
            <p className="sidebar-empty">No conversations yet</p>
          ) : (
            <>
              <div className="sidebar-section-label">Recent</div>
              {conversations.map((c) => (
                <div
                  key={c.id}
                  className={`conv-item ${activeConvId === c.id ? "active" : ""}`}
                  onClick={() => openConversation(c)}
                >
                  <span className="conv-title">{c.title}</span>
                  <button
                    className="conv-delete"
                    onClick={(e) => deleteConversation(e, c.id)}
                    title="Delete conversation"
                  >×</button>
                </div>
              ))}
            </>
          )}
        </div>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="avatar avatar-md">{username?.[0]?.toUpperCase() || "U"}</div>
            <span className="sidebar-username">{username}</span>
          </div>
          <button className="logout-btn" onClick={handleLogout}>Sign out</button>
        </div>
      </aside>

      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}

      {/* ── Main ── */}
      <main className="chat-main">
        <header className="chat-topbar">
          <button className="topbar-menu" onClick={() => setSidebarOpen(!sidebarOpen)}>☰</button>
          <div className="topbar-title">
            <div className="logo-wrap small">
              <div className="logo-icon">⬡</div>
              <span className="logo-text">GitLab <strong>AI</strong></span>
            </div>
          </div>
          <div className="topbar-right">
            <button className="theme-toggle" onClick={toggleTheme} title="Toggle theme">
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
            <div className="avatar avatar-sm">{username?.[0]?.toUpperCase() || "U"}</div>
          </div>
        </header>

        <div className="chat-messages">
          {isEmpty && (
            <div className="chat-empty">
              <div className="empty-glyph">⬡</div>
              <h2 className="empty-greeting-title">{timeGreeting}, {username}!</h2>
              <p className="empty-greeting-sub">{greeting}</p>
              <div className="suggestion-grid">
                {SUGGESTED.map((s) => (
                  <button key={s} className="suggestion-chip" onClick={() => sendMessage(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <Message
              key={msg.id}
              msg={msg}
              onFeedback={handleFeedback}
              onFollowup={(q) => sendMessage(q)}
            />
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="chat-input-area">
          <div className="chat-input-wrap">
            <textarea
              ref={inputRef}
              className="chat-textarea"
              placeholder="Ask about GitLab handbook or direction… (Enter to send, Shift+Enter for newline)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={loading}
            />
            <button
              className="send-btn"
              onClick={() => sendMessage(input)}
              disabled={loading || !input.trim()}
            >
              {loading ? <span className="spinner sm" /> : "↑"}
            </button>
          </div>
          <p className="input-hint">
            GitLab AI may make mistakes — verify with the source links provided.
          </p>
        </div>
      </main>
    </div>
  );
}
