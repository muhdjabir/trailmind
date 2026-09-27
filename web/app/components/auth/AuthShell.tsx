// Layout for the auth screens (docs/auth_signin.png, auth_register.png,
// auth_mobile.png): form on the left, a showcase panel on the right. Below
// md the panel is replaced by the mobile mockup's red hero card.

import type { ReactNode } from "react";

const HEADLINE = "Plan a trip by talking it through.";

function Logo({ inverted = false }: { inverted?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`h-3.5 w-3.5 rounded-full ${inverted ? "bg-white" : "bg-[#e2492f]"}`} />
      <span className={`text-lg font-bold ${inverted ? "text-white" : ""}`}>Trailmind</span>
    </div>
  );
}

// Stands in for the mockups' "destination photo" - no imagery in the repo yet.
function PhotoPlaceholder({ tone }: { tone: "red" | "grey" }) {
  const stripe = tone === "red" ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)";
  return (
    <div
      aria-hidden
      className="min-h-0 flex-1 rounded-2xl"
      style={{
        backgroundImage: `repeating-linear-gradient(135deg, ${stripe} 0 22px, transparent 22px 44px)`,
      }}
    />
  );
}

export function SignInShowcase() {
  return (
    <div className="flex h-full flex-col gap-5 rounded-3xl bg-[#e2492f] p-10 text-white">
      <PhotoPlaceholder tone="red" />
      <div className="flex flex-col gap-3">
        <p className="self-end rounded-2xl bg-white px-4 py-2.5 text-sm text-[#171717]">
          Six days in Portugal, two of us, lots of food.
        </p>
        <p className="self-start rounded-2xl bg-white/15 px-4 py-2.5 text-sm">
          3 nights Lisbon, 2 in Porto, one train between. Want the draft?
        </p>
      </div>
      <h2 className="text-5xl leading-[1.05] font-bold tracking-tight">{HEADLINE}</h2>
    </div>
  );
}

// Only features that exist today - the mockup's "compare stays/trains" and
// "share a trip with a link" cards were left out until those ship.
const FEATURES = [
  { title: "Chat to build a day-by-day plan", detail: "Change anything by asking." },
  { title: "Weather for your dates", detail: "A live forecast, or what's typical that time of year." },
  { title: "Export to your calendar", detail: "Every planned day as a calendar event." },
];

export function RegisterShowcase() {
  return (
    <div className="flex h-full flex-col gap-6 rounded-3xl bg-[#e6e4df] p-10">
      <PhotoPlaceholder tone="grey" />
      <div>
        <p className="mb-3 text-xs font-bold tracking-widest text-[#6b6a66] uppercase">What you can do</p>
        <div className="flex flex-col gap-2">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-2xl bg-[#f4f3f0] px-5 py-4">
              <p className="font-bold">{f.title}</p>
              <p className="text-sm text-[#6b6a66]">{f.detail}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

type Props = {
  title: string;
  subtitle: string;
  showcase: ReactNode;
  children: ReactNode;
};

export function AuthShell({ title, subtitle, showcase, children }: Props) {
  return (
    <div className="flex min-h-screen bg-[#f4f3f0] text-[#171717]">
      <main className="flex w-full flex-col px-5 pt-5 pb-8 md:w-1/2 md:px-16 md:py-12 lg:px-24">
        <div className="mb-8 flex flex-col justify-end rounded-3xl bg-[#e2492f] px-6 pt-24 pb-8 md:hidden">
          <Logo inverted />
          <p className="mt-3 text-4xl leading-[1.05] font-bold tracking-tight text-white">{HEADLINE}</p>
        </div>
        <div className="hidden md:block">
          <Logo />
        </div>
        <div className="mx-auto flex w-full max-w-md flex-1 flex-col md:mx-0 md:justify-center">
          <div className="hidden md:block">
            <h1 className="text-4xl font-bold tracking-tight">{title}</h1>
            <p className="mt-2 mb-8 text-[#6b6a66]">{subtitle}</p>
          </div>
          {children}
        </div>
      </main>
      <aside className="hidden p-4 md:block md:w-1/2">{showcase}</aside>
    </div>
  );
}
