// Static demo content matching the "Trip Planner Chat v2" design mockup.
// Not wired to a real backend yet - trip creation/persistence is v1
// (see docs/implementation_list.md steps 15-16). Buttons here are inert.

const PLANNING_TRIPS = [
  { name: "Lisbon & Porto", detail: "12–17 Oct · 2 people", active: true },
  { name: "Kyoto in spring", detail: "Dates open", active: false },
  { name: "Dolomites hut-to-hut", detail: "Jul 2027 · 4 people", active: false },
];

const PAST_TRIPS = ["Copenhagen weekend", "Mexico City"];

export function Sidebar() {
  return (
    <aside className="flex w-72 flex-shrink-0 flex-col border-r border-[#e2e0da] bg-[#f1efec] px-5 py-6">
      <div className="mb-6 flex items-center gap-2">
        <span className="h-3 w-3 rounded-full bg-[#e2492f]" />
        <span className="text-lg font-bold">Trailmind</span>
      </div>

      <button
        type="button"
        className="mb-6 rounded-xl bg-[#e2492f] py-3 text-sm font-bold text-white"
      >
        + New trip
      </button>

      <p className="mb-2 text-xs font-semibold tracking-wider text-[#8a8984] uppercase">
        Planning
      </p>
      <div className="mb-6 flex flex-col gap-1">
        {PLANNING_TRIPS.map((t) => (
          <div key={t.name} className={`rounded-xl px-3 py-2.5 ${t.active ? "bg-[#e6e4df]" : ""}`}>
            <p className="text-sm font-semibold">{t.name}</p>
            <p className="text-xs text-[#8a8984]">{t.detail}</p>
          </div>
        ))}
      </div>

      <p className="mb-2 text-xs font-semibold tracking-wider text-[#8a8984] uppercase">Past</p>
      <div className="flex flex-col gap-1">
        {PAST_TRIPS.map((name) => (
          <div key={name} className="rounded-xl px-3 py-2.5">
            <p className="text-sm font-semibold">{name}</p>
          </div>
        ))}
      </div>
    </aside>
  );
}
