const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export async function sendChat(question, history = []) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Request failed: ${detail}`);
  }

  return response.json();
}

export async function sendChatStream(question, history = [], handlers = {}) {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });

  if (!response.ok || !response.body) {
    const detail = await response.text();
    throw new Error(`Stream request failed: ${detail}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";

    for (const chunk of chunks) {
      const lines = chunk.split("\n");
      let event = "message";
      let data = "";

      for (const line of lines) {
        if (line.startsWith("event: ")) event = line.replace("event: ", "").trim();
        if (line.startsWith("data: ")) data += line.replace("data: ", "");
      }

      if (event === "message" && handlers.onToken) handlers.onToken(data.replace(/\\n/g, "\n"));
      if (event === "meta" && handlers.onMeta) handlers.onMeta(data);
      if (event === "sources" && handlers.onSources) handlers.onSources(data);
      if (event === "followups" && handlers.onFollowups) handlers.onFollowups(data);
      if (event === "done" && handlers.onDone) handlers.onDone();
      if (event === "error" && handlers.onError) handlers.onError(data);
    }
  }
}

export async function sendFeedback(traceId, vote, comment = "") {
  const response = await fetch(`${API_BASE}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trace_id: traceId, vote, comment: comment || null }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Feedback request failed: ${detail}`);
  }

  return response.json();
}
