"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthShell, SignInShowcase } from "../components/auth/AuthShell";
import { FormError, PrimaryButton, SetupNotice, TextField } from "../components/auth/fields";
import { MIN_PASSWORD_LENGTH, passwordStrength } from "../lib/password";
import { supabase } from "../lib/supabase";

// Landing page for the reset email: supabase-js picks up the recovery
// session from the link's URL, then updateUser sets the new password.
export default function ResetPasswordPage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSession, setHasSession] = useState<boolean | null>(null);

  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getSession().then(({ data }) => setHasSession(Boolean(data.session)));
    const { data } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "PASSWORD_RECOVERY" || session) setHasSession(true);
    });
    return () => data.subscription.unsubscribe();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true);
    setError(null);
    const { error } = await supabase.auth.updateUser({ password });
    setBusy(false);
    if (error) setError(error.message);
    else router.replace("/");
  }

  return (
    <AuthShell title="Choose a new password" subtitle="Then you're straight back to your trips." showcase={<SignInShowcase />}>
      <SetupNotice />
      {hasSession === false ? (
        <>
          <p className="text-lg">This reset link is invalid or has expired.</p>
          <Link href="/forgot-password" className="mt-6 font-medium text-[#e2492f] underline">
            Send a new link
          </Link>
        </>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <TextField
            label="New password"
            type="password"
            autoComplete="new-password"
            required
            minLength={MIN_PASSWORD_LENGTH}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <p className="-mt-3 text-sm text-[#6b6a66]">{passwordStrength(password).hint}</p>
          <FormError message={error} />
          <PrimaryButton busy={busy} disabled={!supabase || !hasSession || password.length < MIN_PASSWORD_LENGTH}>
            Save password
          </PrimaryButton>
        </form>
      )}
    </AuthShell>
  );
}
