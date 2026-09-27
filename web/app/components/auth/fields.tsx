"use client";

import type { InputHTMLAttributes, ReactNode } from "react";
import { supabase } from "../../lib/supabase";

export function TextField({
  label,
  aside,
  ...input
}: { label: string; aside?: ReactNode } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="flex items-baseline justify-between text-sm text-[#6b6a66]">
        {label}
        {aside}
      </span>
      <input
        {...input}
        className="rounded-2xl bg-[#e9e8e5] px-4 py-3.5 text-[#171717] outline-none placeholder:text-[#9a9994] focus:ring-2 focus:ring-[#e2492f]/40"
      />
    </label>
  );
}

export function PrimaryButton({ children, busy, disabled }: { children: ReactNode; busy: boolean; disabled?: boolean }) {
  return (
    <button
      type="submit"
      disabled={busy || disabled}
      className="rounded-2xl bg-[#e2492f] px-6 py-4 text-left text-lg font-bold text-white disabled:opacity-60"
    >
      {busy ? "One moment..." : children}
    </button>
  );
}

export function Divider({ label }: { label: string }) {
  return (
    <div className="my-6 flex items-center gap-4 text-sm text-[#6b6a66]">
      <span className="h-px flex-1 bg-[#dedcd6]" />
      {label}
      <span className="h-px flex-1 bg-[#dedcd6]" />
    </div>
  );
}

function GoogleMark() {
  return (
    <svg width="20" height="20" viewBox="0 0 48 48" aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.6 5.4 2.6 13.3l7.9 6.1C12.4 13.7 17.7 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.1 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.4c-.5 2.9-2.2 5.3-4.6 6.9l7.4 5.7c4.3-4 6.9-9.9 6.9-17.1z" />
      <path fill="#FBBC05" d="M10.5 28.6c-.5-1.4-.8-3-.8-4.6s.3-3.2.8-4.6l-7.9-6.1C1 16.6 0 20.2 0 24s1 7.4 2.6 10.7l7.9-6.1z" />
      <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.4-5.7c-2.1 1.4-4.8 2.3-8.5 2.3-6.3 0-11.6-4.2-13.5-10l-7.9 6.1C6.6 42.6 14.6 48 24 48z" />
    </svg>
  );
}

export function GoogleButton({ onError }: { onError: (message: string) => void }) {
  async function signIn() {
    if (!supabase) return;
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
    if (error) onError(error.message);
  }

  return (
    <button
      type="button"
      onClick={signIn}
      disabled={!supabase}
      className="flex items-center gap-3 rounded-2xl border border-[#b9b7b1] px-5 py-3.5 font-bold disabled:opacity-60"
    >
      <GoogleMark />
      Continue with Google
    </button>
  );
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="rounded-xl bg-[#fbe7e2] px-4 py-3 text-sm text-[#b8341c]">
      {message}
    </p>
  );
}

export function SetupNotice() {
  if (supabase) return null;
  return (
    <p className="mb-6 rounded-xl border border-dashed border-[#b9b7b1] px-4 py-3 text-sm text-[#6b6a66]">
      Sign-in isn&apos;t set up yet: add <code>NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
      <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> to <code>.env</code>, then restart the web container.
    </p>
  );
}
