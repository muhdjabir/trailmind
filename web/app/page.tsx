"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ItineraryPanel } from "./components/ItineraryPanel";
import { Sidebar } from "./components/Sidebar";

type Message = {
  role: "user" | "assistant" | "error";
  content: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Canned prompts from the mockup - real and functional (they just send
// the shown text), unlike the static trip/itinerary chrome around them.
const SUGGESTIONS = ["Add a fado night", "Rain plan for day 4", "Where to eat in Porto?"];

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M3 11.5L20 4L12.5 21L10.5 13.5L3 11.5Z" fill="currentColor" />
    </svg>
  );
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `request failed (${res.status})`);
      }

      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: err instanceof Error ? err.message : String(err) },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    send(input);
  }

  return (
    <div className="flex h-screen bg-[#f1efec] text-[#171717]">
      <Sidebar />

      <main className="flex min-w-0 flex-1 flex-col bg-[#faf9f7]">
        {/* Static demo header matching the mockup - not derived from the
            live conversation below (no trip/budget backend yet, v1). */}
        <header className="flex items-center justify-between border-b border-[#e2e0da] px-8 py-5">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold">Lisbon &amp; Porto</h1>
            <span className="rounded-full bg-[#fbe7e2] px-3 py-1 text-xs font-semibold text-[#e2492f]">
              Draft itinerary
            </span>
          </div>
          <p className="text-sm text-[#8a8984]">Budget €2,400 · €1,860 planned</p>
        </header>

        <div className="flex-1 overflow-y-auto px-8 py-6">
          <div className="mx-auto flex max-w-2xl flex-col gap-4">
            {messages.length === 0 && (
              <p className="text-sm text-[#8a8984]">
                Ask about Da Nang, Hoi An, Bangkok, Almaty, or Tokyo/Fuji/Hiroshima.
              </p>
            )}
            {messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="flex justify-end">
                  <div className="max-w-[80%] rounded-2xl bg-[#171717] px-4 py-3 text-white">
                    {m.content}
                  </div>
                </div>
              ) : m.role === "error" ? (
                <div key={i} className="flex items-start gap-3">
                  <span className="mt-1.5 h-2.5 w-2.5 flex-shrink-0 rounded-full bg-red-600" />
                  <p className="text-red-600">{m.content}</p>
                </div>
              ) : (
                <div key={i} className="flex items-start gap-3">
                  <span className="mt-1.5 h-2.5 w-2.5 flex-shrink-0 rounded-full bg-[#e2492f]" />
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  </div>
                </div>
              ),
            )}
            {loading && (
              <div className="flex items-start gap-3">
                <span className="mt-1.5 h-2.5 w-2.5 flex-shrink-0 rounded-full bg-[#e2492f]" />
                <p className="text-sm text-[#8a8984]">Thinking...</p>
              </div>
            )}
          </div>
        </div>

        <div className="border-t border-[#e2e0da] px-8 py-4">
          <div className="mx-auto max-w-2xl">
            <div className="mb-3 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => send(s)}
                  disabled={loading}
                  className="rounded-full border border-[#e2e0da] px-3 py-1.5 text-sm text-[#171717] hover:bg-[#f1efec] disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>
            <form onSubmit={handleSubmit} className="flex items-center gap-2">
              <input
                className="flex-1 rounded-full bg-[#f1efec] px-4 py-3 text-sm outline-none placeholder:text-[#8a8984]"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask Trailmind anything about this trip..."
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading}
                className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full bg-[#e2492f] text-white disabled:opacity-50"
              >
                <SendIcon />
              </button>
            </form>
          </div>
        </div>
      </main>

      <ItineraryPanel />
    </div>
  );
}
