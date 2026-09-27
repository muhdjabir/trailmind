// "Just added" highlighting (step 20a) and "Export to calendar" (step
// 22c) aren't wired yet - the export button is inert.

import type { ItineraryDay } from "../lib/types";

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
};

export function ItineraryPanel({ hasTrip, days }: Props) {
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
            return (
              <div key={d.day_number} className="flex gap-3 rounded-xl bg-white p-3">
                <div className="flex w-9 flex-shrink-0 flex-col items-center">
                  <span className="text-2xl font-bold">{label.big}</span>
                  <span className="text-[10px] font-semibold text-[#8a8984]">{label.small}</span>
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold">{d.title}</p>
                  {d.items.length > 0 && (
                    <p className="text-xs text-[#8a8984]">{d.items.join(" · ")}</p>
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
