const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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
