"use client";

import Link from "next/link";
import { useState } from "react";
import { AuthShell, SignInShowcase } from "../components/auth/AuthShell";
import { FormError, PrimaryButton, SetupNotice, TextField } from "../components/auth/fields";
import { supabase } from "../lib/supabase";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true);
    setError(null);
    const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    setBusy(false);
    if (error) setError(error.message);
    else setSent(true);
  }

  return (
    <AuthShell
      title="Reset your password"
      subtitle="We'll email you a link to choose a new one."
      showcase={<SignInShowcase />}
    >
      <SetupNotice />
      {sent ? (
        // Same message whether or not the address has an account, so this
        // page can't be used to check who's signed up.
        <p className="text-lg">
          If <strong>{email.trim()}</strong> has an account, a reset link is on its way.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <TextField
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
          <FormError message={error} />
          <PrimaryButton busy={busy} disabled={!supabase}>
            Send reset link
          </PrimaryButton>
        </form>
      )}
      <Link href="/signin" className="mt-6 font-medium text-[#e2492f] underline">
        Back to sign in
      </Link>
    </AuthShell>
  );
}
