"use client";

import { useState } from "react";
import { initialsOf } from "../lib/supabase";
import type { Trip } from "../lib/types";

type SidebarProps = {
  trips: Trip[];
  selectedTripId: number | null;
  loading: boolean;
  onSelect: (id: number) => void;
  onCreate: (name: string) => void;
  // null when signed out or auth isn't configured - no account row then.
  accountName: string | null;
  onSignOut: () => void;
};

function tripDetail(t: Trip): string {
  const parts: string[] = [];
  if (t.destinations.length > 0) parts.push(t.destinations.join(", "));
  if (t.start_date && t.end_date) parts.push(`${t.start_date} – ${t.end_date}`);
  if (t.party_size) parts.push(`${t.party_size} people`);
  return parts.length > 0 ? parts.join(" · ") : "No details yet";
}

export function Sidebar({
  trips,
  selectedTripId,
  loading,
  onSelect,
  onCreate,
  accountName,
  onSignOut,
}: SidebarProps) {
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    onCreate(trimmed);
    setName("");
    setCreating(false);
  }

  return (
    <aside className="flex w-72 flex-shrink-0 flex-col border-r border-[#e2e0da] bg-[#f1efec] px-5 py-6">
      <div className="mb-6 flex items-center gap-2">
        <span className="h-3 w-3 rounded-full bg-[#e2492f]" />
        <span className="text-lg font-bold">Trailmind</span>
      </div>

      {creating ? (
        <form onSubmit={handleCreate} className="mb-6 flex flex-col gap-2">
          <input
            autoFocus
            className="rounded-xl bg-white px-3 py-2.5 text-sm outline-none placeholder:text-[#8a8984]"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Trip name..."
            onKeyDown={(e) => {
              if (e.key === "Escape") setCreating(false);
            }}
          />
          <div className="flex gap-2">
            <button
              type="submit"
              className="flex-1 rounded-xl bg-[#e2492f] py-2 text-sm font-bold text-white disabled:opacity-50"
              disabled={!name.trim()}
            >
              Create
            </button>
            <button
              type="button"
              onClick={() => setCreating(false)}
              className="rounded-xl border border-[#8a8984] px-3 py-2 text-sm"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setCreating(true)}
          className="mb-6 rounded-xl bg-[#e2492f] py-3 text-sm font-bold text-white"
        >
          + New trip
        </button>
      )}

      <p className="mb-2 text-xs font-semibold tracking-wider text-[#8a8984] uppercase">
        Your trips
      </p>
      <div className="flex flex-col gap-1 overflow-y-auto">
        {loading && <p className="px-3 py-2.5 text-sm text-[#8a8984]">Loading...</p>}
        {!loading && trips.length === 0 && (
          <p className="px-3 py-2.5 text-sm text-[#8a8984]">No trips yet - create one above.</p>
        )}
        {trips.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => onSelect(t.id)}
            className={`rounded-xl px-3 py-2.5 text-left ${
              t.id === selectedTripId ? "bg-[#e6e4df]" : "hover:bg-[#e6e4df]/60"
            }`}
          >
            <p className="text-sm font-semibold">{t.name}</p>
            <p className="text-xs text-[#8a8984]">{tripDetail(t)}</p>
          </button>
        ))}
      </div>

      {accountName && (
        <div className="mt-auto flex items-center gap-3 border-t border-[#e2e0da] pt-4">
          <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-[#171717] text-xs font-bold text-white">
            {initialsOf(accountName)}
          </span>
          <p className="min-w-0 flex-1 truncate text-sm font-semibold">{accountName}</p>
          <button type="button" onClick={onSignOut} className="text-xs text-[#8a8984] hover:text-[#171717]">
            Sign out
          </button>
        </div>
      )}
    </aside>
  );
}
