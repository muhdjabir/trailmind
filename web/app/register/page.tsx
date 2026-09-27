"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthShell, RegisterShowcase } from "../components/auth/AuthShell";
import { Divider, FormError, GoogleButton, PrimaryButton, SetupNotice, TextField } from "../components/auth/fields";
import { useRedirectIfSignedIn } from "../components/auth/useRedirectIfSignedIn";
import { MIN_PASSWORD_LENGTH, passwordStrength } from "../lib/password";
import { supabase } from "../lib/supabase";

function StrengthMeter({ password }: { password: string }) {
  const { score, hint } = passwordStrength(password);
  return (
    <div className="-mt-3">
      <div className="flex gap-1.5" aria-hidden>
        {[1, 2, 3, 4].map((i) => (
          <span key={i} className={`h-1 flex-1 rounded-full ${i <= score ? "bg-[#e2492f]" : "bg-[#dedcd6]"}`} />
        ))}
      </div>
      <p className="mt-1.5 text-sm text-[#6b6a66]" aria-live="polite">
        {hint}
      </p>
    </div>
  );
}

export default function RegisterPage() {
  useRedirectIfSignedIn();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmSentTo, setConfirmSentTo] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true);
    setError(null);
    const { data, error } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: { data: { name: name.trim() }, emailRedirectTo: window.location.origin },
    });
    setBusy(false);
    if (error) setError(error.message);
    // No session means the project requires email confirmation first.
    else if (data.session) router.replace("/");
    else setConfirmSentTo(email.trim());
  }

  if (confirmSentTo) {
    return (
      <AuthShell title="Check your inbox" subtitle="One more step." showcase={<RegisterShowcase />}>
        <p className="text-lg">
          We sent a confirmation link to <strong>{confirmSentTo}</strong>. Open it to finish creating your
          account.
        </p>
        <Link href="/signin" className="mt-6 font-medium text-[#e2492f] underline">
          Back to sign in
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Free to plan. Your trips sync across devices."
      showcase={<RegisterShowcase />}
    >
      <SetupNotice />
      <GoogleButton onError={setError} />
      <Divider label="or with email" />
      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <TextField
          label="Name"
          autoComplete="name"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Maria Rocha"
        />
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="new-password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <StrengthMeter password={password} />
        <FormError message={error} />
        <PrimaryButton busy={busy} disabled={!supabase || password.length < MIN_PASSWORD_LENGTH}>
          Create account
        </PrimaryButton>
      </form>
      <p className="mt-6 text-[#6b6a66]">
        Already have an account?{" "}
        <Link href="/signin" className="font-medium text-[#e2492f] underline">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
