// Static demo content matching the design mockup. Real itinerary data
// needs trip-state persistence (v1, see docs/implementation_list.md
// steps 15-16) - the "Export to calendar" button is inert.

const DAYS = [
  { date: "12", dow: "SUN", title: "Arrive Lisbon", detail: "Check in Alfama · Miradouro at sunset" },
  { date: "13", dow: "MON", title: "Baixa & Belém", detail: "Tram 15 · pastéis · LX Factory" },
  { date: "14", dow: "TUE", title: "Sintra day trip", detail: "Train 09:10 · Pena · Quinta da Regaleira" },
  {
    date: "15",
    dow: "WED",
    title: "Train to Porto",
    detail: "Alfa Pendular 10:39 → 13:28",
    highlight: true,
    badge: "Just added",
  },
  { date: "16", dow: "THU", title: "Slow day", detail: "Ribeira · port lodges in Gaia" },
  { date: "17", dow: "FRI", title: "Fly home", detail: "OPO 14:05" },
];

export function ItineraryPanel() {
  return (
    <aside className="flex w-80 flex-shrink-0 flex-col border-l border-[#e2e0da] bg-[#f1efec] px-5 py-6">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="text-lg font-bold">Itinerary</h2>
        <span className="text-sm text-[#8a8984]">6 days</span>
      </div>

      <div className="flex flex-1 flex-col gap-2 overflow-y-auto">
        {DAYS.map((d) => (
          <div key={d.date} className={`flex gap-3 rounded-xl p-3 ${d.highlight ? "bg-[#fbe7e2]" : ""}`}>
            <div className="flex w-9 flex-shrink-0 flex-col items-center">
              <span className={`text-2xl font-bold ${d.highlight ? "text-[#e2492f]" : ""}`}>{d.date}</span>
              <span
                className={`text-[10px] font-semibold ${d.highlight ? "text-[#e2492f]" : "text-[#8a8984]"}`}
              >
                {d.dow}
              </span>
            </div>
            <div className="min-w-0">
              <p className={`text-sm font-semibold ${d.highlight ? "text-[#e2492f]" : ""}`}>{d.title}</p>
              <p className="text-xs text-[#8a8984]">{d.detail}</p>
              {d.badge && (
                <span className="mt-1.5 inline-block rounded-full border border-[#e2492f] px-2 py-0.5 text-[10px] font-semibold text-[#e2492f]">
                  {d.badge}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      <button type="button" className="mt-4 rounded-xl border border-[#8a8984] py-3 text-sm font-semibold">
        Export to calendar
      </button>
    </aside>
  );
}
