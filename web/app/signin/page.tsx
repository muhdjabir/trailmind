"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthShell, SignInShowcase } from "../components/auth/AuthShell";
import { Divider, FormError, GoogleButton, PrimaryButton, SetupNotice, TextField } from "../components/auth/fields";
import { useRedirectIfSignedIn } from "../components/auth/useRedirectIfSignedIn";
import { supabase } from "../lib/supabase";

export default function SignInPage() {
  useRedirectIfSignedIn();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true);
    setError(null);
    const { error } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
    setBusy(false);
    if (error) setError(error.message);
    else router.replace("/");
  }

  return (
    <AuthShell title="Welcome back" subtitle="Pick up your trips where you left them." showcase={<SignInShowcase />}>
      <SetupNotice />
      <GoogleButton onError={setError} />
      <Divider label="or with email" />
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
        <TextField
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          aside={
            <Link href="/forgot-password" className="hidden text-[#e2492f] underline md:inline">
              Forgot?
            </Link>
          }
        />
        <FormError message={error} />
        <PrimaryButton busy={busy} disabled={!supabase}>
          Sign in
        </PrimaryButton>
      </form>
      <p className="mt-6 hidden text-[#6b6a66] md:block">
        New to Trailmind?{" "}
        <Link href="/register" className="font-medium text-[#e2492f] underline">
          Create an account
        </Link>
      </p>
      <div className="mt-auto flex justify-between pt-10 text-[#e2492f] underline md:hidden">
        <Link href="/forgot-password">Forgot password?</Link>
        <Link href="/register">Create account</Link>
      </div>
    </AuthShell>
  );
}
