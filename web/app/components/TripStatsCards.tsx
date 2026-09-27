// Stat cards styled after the mockup's TRAIN/STAYS/WALKING row, but only
// for stats we can actually compute (step 22a). Those three mockup cards
// need flights/hotels data (steps 18/19) and get added once it exists.

import type { TripStats } from "../lib/types";

type Card = { label: string; value: string; detail: string };

function formatDayList(days: number[]): string {
  if (days.length <= 3) return days.join(", ");
  return `${days.slice(0, 3).join(", ")} +${days.length - 3}`;
}

function buildCards(stats: TripStats): Card[] {
  const cards: Card[] = [];

  if (stats.trip_days !== null) {
    cards.push({
      label: "Planned",
      value: `${stats.days_planned}/${stats.trip_days}`,
      detail:
        stats.open_days.length === 0
          ? "every day planned"
          : `open: day ${formatDayList(stats.open_days)}`,
    });
  } else if (stats.days_planned > 0) {
    cards.push({ label: "Planned", value: `${stats.days_planned}`, detail: "days · no dates set" });
  }

  if (stats.weather) {
    const w = stats.weather;
    cards.push({
      label: "Weather",
      value: `${Math.round(w.avg_high_c)}° / ${Math.round(w.avg_low_c)}°`,
      // Never present a historical average as a forecast (see CLAUDE.md).
      detail: `${w.source === "forecast" ? "Forecast" : "Typical for these dates"} · ${Math.round(
        w.total_precipitation_mm,
      )} mm rain`,
    });
  }

  if (stats.budget_planned !== null || stats.budget_total !== null) {
    const fmt = (n: number | null) => (n === null ? "?" : n.toLocaleString());
    cards.push({
      label: "Budget",
      value: fmt(stats.budget_planned),
      detail: `planned of ${fmt(stats.budget_total)}`,
    });
  }

  return cards;
}

export function TripStatsCards({ stats }: { stats: TripStats | null }) {
  if (!stats) return null;
  const cards = buildCards(stats);
  if (cards.length === 0) return null;

  return (
    <div className="mb-4 grid grid-cols-2 gap-2">
      {cards.map((c) => (
        <div key={c.label} className="rounded-xl bg-white p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-[#e2492f]">{c.label}</p>
          <p className="mt-1 text-lg font-bold">{c.value}</p>
          <p className="text-[11px] text-[#8a8984]">{c.detail}</p>
        </div>
      ))}
    </div>
  );
}
