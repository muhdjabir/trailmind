// "Export to calendar" (step 22c) isn't wired yet - the button is inert.

import type { DayChange } from "../lib/itineraryDiff";
import type { ItineraryDay, TripStats } from "../lib/types";
import { TripStatsCards } from "./TripStatsCards";

const BADGE: Record<DayChange, string> = { added: "Just added", updated: "Updated" };

const WEEKDAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];

function dayLabel(day: ItineraryDay): { big: string; small: string } {
  if (!day.date) return { big: String(day.day_number), small: "DAY" };
  // Parse as a local calendar date - `new Date("YYYY-MM-DD")` is UTC and
  // can land on the previous day in negative-offset timezones.
  const [y, m, d] = day.date.split("-").map(Number);
  return { big: String(d), small: WEEKDAYS[new Date(y, m - 1, d).getDay()] };
}

type Props = {
  hasTrip: boolean;
  days: ItineraryDay[];
  changes: Record<number, DayChange>;
  stats: TripStats | null;
};

export function ItineraryPanel({ hasTrip, days, changes, stats }: Props) {
  return (
    <aside className="flex w-80 flex-shrink-0 flex-col border-l border-[#e2e0da] bg-[#f1efec] px-5 py-6">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="text-lg font-bold">Itinerary</h2>
        {days.length > 0 && (
          <span className="text-sm text-[#8a8984]">
            {days.length} {days.length === 1 ? "day" : "days"}
          </span>
        )}
      </div>

      {hasTrip && <TripStatsCards stats={stats} />}

      <div className="flex flex-1 flex-col gap-2 overflow-y-auto">
        {!hasTrip ? (
          <p className="text-sm text-[#8a8984]">Select a trip to see its itinerary.</p>
        ) : days.length === 0 ? (
          <p className="text-sm text-[#8a8984]">
            No days planned yet - ask Trailmind to plan your trip and they&apos;ll show up here.
          </p>
        ) : (
          days.map((d) => {
            const label = dayLabel(d);
            const change = changes[d.day_number];
            const accent = change ? "text-[#e2492f]" : "";
            return (
              <div
                key={d.day_number}
                className={`flex gap-3 rounded-xl p-3 ${change ? "bg-[#fbe7e2]" : "bg-white"}`}
              >
                <div className="flex w-9 flex-shrink-0 flex-col items-center">
                  <span className={`text-2xl font-bold ${accent}`}>{label.big}</span>
                  <span className={`text-[10px] font-semibold ${change ? accent : "text-[#8a8984]"}`}>
                    {label.small}
                  </span>
                </div>
                <div className="min-w-0">
                  <p className={`text-sm font-semibold ${accent}`}>{d.title}</p>
                  {d.items.length > 0 && (
                    <p className="text-xs text-[#8a8984]">{d.items.join(" · ")}</p>
                  )}
                  {change && (
                    <span className="mt-1.5 inline-block rounded-full border border-[#e2492f] px-2 py-0.5 text-[10px] font-semibold text-[#e2492f]">
                      {BADGE[change]}
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      <button type="button" className="mt-4 rounded-xl border border-[#8a8984] py-3 text-sm font-semibold">
        Export to calendar
      </button>
    </aside>
  );
}
