import type { ItineraryDay } from "./types";

export type DayChange = "added" | "updated";

// Diffs the itinerary from before a chat turn against the one after it.
// `updated_at` is bumped on every save (see itinerary_repo.upsert_day),
// so a changed timestamp means the agent rewrote that day. Removed days
// aren't returned - there's no card left to badge; the reply says so.
export function diffItinerary(
  before: ItineraryDay[],
  after: ItineraryDay[],
): Record<number, DayChange> {
  const previous = new Map(before.map((d) => [d.day_number, d.updated_at]));
  const changes: Record<number, DayChange> = {};
  for (const day of after) {
    const was = previous.get(day.day_number);
    if (was === undefined) changes[day.day_number] = "added";
    else if (was !== day.updated_at) changes[day.day_number] = "updated";
  }
  return changes;
}
