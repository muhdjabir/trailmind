"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ItineraryPanel } from "./components/ItineraryPanel";
import { Sidebar } from "./components/Sidebar";
import { diffItinerary, type DayChange } from "./lib/itineraryDiff";
import type { ItineraryDay, Trip, TripStats } from "./lib/types";

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

  const [trips, setTrips] = useState<Trip[]>([]);
  const [tripsLoading, setTripsLoading] = useState(true);
  const [selectedTripId, setSelectedTripId] = useState<number | null>(null);
  const [itinerary, setItinerary] = useState<ItineraryDay[]>([]);
  // Days the agent changed in the latest turn - cleared on the next send
  // or trip switch, so the badges mean "this reply did that".
  const [dayChanges, setDayChanges] = useState<Record<number, DayChange>>({});
  const [stats, setStats] = useState<TripStats | null>(null);
  // Lets async results from a previous trip's request be ignored after
  // the user has switched trips.
  const activeTripRef = useRef<number | null>(null);

  async function loadItinerary(tripId: number): Promise<ItineraryDay[] | null> {
    try {
      const res = await fetch(`${API_URL}/trips/${tripId}/itinerary`);
      if (!res.ok || activeTripRef.current !== tripId) return null;
      const days: ItineraryDay[] = await res.json();
      if (activeTripRef.current !== tripId) return null;
      setItinerary(days);
      return days;
    } catch {
      // Keep whatever's shown rather than blanking the panel on a blip.
      return null;
    }
  }

  async function loadStats(tripId: number) {
    try {
      const res = await fetch(`${API_URL}/trips/${tripId}/stats`);
      if (!res.ok) return;
      const data: TripStats = await res.json();
      if (activeTripRef.current === tripId) setStats(data);
    } catch {
      // Cards just stay as they were; nothing to tell the user.
    }
  }

  async function refreshTrip(tripId: number) {
    try {
      const res = await fetch(`${API_URL}/trips/${tripId}`);
      if (!res.ok) return;
      const updated: Trip = await res.json();
      setTrips((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } catch {
      // Stale dates in the sidebar aren't worth an error message.
    }
  }

  useEffect(() => {
    fetch(`${API_URL}/trips`)
      .then((res) => res.json())
      .then((data: Trip[]) => setTrips(data))
      .catch(() => setTrips([]))
      .finally(() => setTripsLoading(false));
  }, []);

  async function selectTrip(id: number) {
    activeTripRef.current = id;
    setSelectedTripId(id);
    setMessages([]);
    setItinerary([]);
    setDayChanges({});
    setStats(null);
    loadItinerary(id);
    loadStats(id);
    try {
      const res = await fetch(`${API_URL}/trips/${id}/messages`);
      if (!res.ok) return;
      const history: { role: string; content: string }[] = await res.json();
      setMessages(
        history.map((m) => ({
          role: m.role === "assistant" ? "assistant" : "user",
          content: m.content,
        })),
      );
    } catch {
      // Leave the chat empty rather than blocking trip selection on this.
    }
  }

  async function createTrip(name: string) {
    try {
      const res = await fetch(`${API_URL}/trips`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) throw new Error(`request failed (${res.status})`);
      const created: Trip = await res.json();
      setTrips((prev) => [created, ...prev]);
      activeTripRef.current = created.id;
      setSelectedTripId(created.id);
      setMessages([]);
      setItinerary([]);
      setDayChanges({});
      setStats(null);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: err instanceof Error ? err.message : String(err) },
      ]);
    }
  }

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    setLoading(true);
    setDayChanges({});
    const tripId = selectedTripId;
    const itineraryBefore = itinerary;

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed, trip_id: tripId }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `request failed (${res.status})`);
      }

      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      // The agent may have changed itinerary days or trip dates this turn.
      if (tripId !== null) {
        refreshTrip(tripId);
        loadStats(tripId);
        const itineraryAfter = await loadItinerary(tripId);
        if (itineraryAfter) setDayChanges(diffItinerary(itineraryBefore, itineraryAfter));
      }
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

  const selectedTrip = trips.find((t) => t.id === selectedTripId) ?? null;

  return (
    <div className="flex h-screen bg-[#f1efec] text-[#171717]">
      <Sidebar
        trips={trips}
        selectedTripId={selectedTripId}
        loading={tripsLoading}
        onSelect={selectTrip}
        onCreate={createTrip}
      />

      <main className="flex min-w-0 flex-1 flex-col bg-[#faf9f7]">
        <header className="flex items-center justify-between border-b border-[#e2e0da] px-8 py-5">
          {selectedTrip ? (
            <>
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-bold">{selectedTrip.name}</h1>
                <span className="rounded-full bg-[#fbe7e2] px-3 py-1 text-xs font-semibold text-[#e2492f]">
                  {selectedTrip.status}
                </span>
              </div>
              {(selectedTrip.budget_planned || selectedTrip.budget_total) && (
                <p className="text-sm text-[#8a8984]">
                  Budget {selectedTrip.budget_total ?? "?"} · {selectedTrip.budget_planned ?? "?"}{" "}
                  planned
                </p>
              )}
            </>
          ) : (
            <h1 className="text-sm text-[#8a8984]">Select or create a trip to get started</h1>
          )}
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

      <ItineraryPanel hasTrip={selectedTripId !== null} days={itinerary} changes={dayChanges} stats={stats} />
    </div>
  );
}
