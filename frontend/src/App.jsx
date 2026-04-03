import { useMemo, useState } from "react";
import { sendChat } from "./api";

const suggestedPrompts = [
  "What is GitLab's handbook-first philosophy?",
  "Summarize GitLab's direction page in simple terms.",
  "How can employees use handbook documentation effectively?",
];

function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Ask anything about GitLab Handbook or Direction pages. I will answer using available sources.",
      sources: [],
    },
  ]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const historyPayload = useMemo(
    () =>
      messages
        .filter((message) => message.role === "user" || message.role === "assistant")
        .map((message) => ({ role: message.role, content: message.content })),
    [messages]
  );

  async function onAsk(text) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setError("");
    setLoading(true);
    setQuestion("");
    setMessages((prev) => [...prev, { role: "user", content: trimmed, sources: [] }]);

    try {
      const result = await sendChat(trimmed, historyPayload);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.answer, sources: result.sources || [] },
      ]);
    } catch (err) {
      setError(err.message || "Unexpected error while contacting the chatbot API.");
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(event) {
    event.preventDefault();
    onAsk(question);
  }

  return (
    <div className="page-shell">
      <header className="hero">
        <h1>GitLab Knowledge Chatbot</h1>
        <p>Grounded answers from handbook and direction content.</p>
      </header>

      <main className="chat-card">
        <div className="suggested-row">
          {suggestedPrompts.map((prompt) => (
            <button key={prompt} type="button" onClick={() => onAsk(prompt)} disabled={loading}>
              {prompt}
            </button>
          ))}
        </div>

        <section className="messages">
          {messages.map((message, index) => (
            <article key={`${message.role}-${index}`} className={`bubble ${message.role}`}>
              <p>{message.content}</p>
              {message.sources?.length > 0 && (
                <ul className="sources">
                  {message.sources.map((source) => (
                    <li key={source.url}>
                      <a href={source.url} target="_blank" rel="noreferrer">
                        {source.title}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </article>
          ))}
          {loading && <p className="status">Thinking...</p>}
          {error && <p className="error">{error}</p>}
        </section>

        <form className="input-row" onSubmit={onSubmit}>
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask a follow-up question..."
            aria-label="chat question"
          />
          <button type="submit" disabled={loading || question.trim().length < 2}>
            Send
          </button>
        </form>
      </main>
    </div>
  );
}

export default App;
