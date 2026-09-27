import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// null until a Supabase project is configured (see .env.example). Auth
// screens then show a setup notice, and the planner isn't gated - the real
// lock on trips is the backend's ownership checks (step 23a), not this.
export const supabase: SupabaseClient | null = url && anonKey ? createClient(url, anonKey) : null;

export function displayNameOf(user: { email?: string; user_metadata?: Record<string, unknown> }): string {
  const meta = user.user_metadata ?? {};
  // `name` is set on email sign-up; Google provides `full_name`.
  const name = (meta.name ?? meta.full_name) as string | undefined;
  return name?.trim() || user.email || "Account";
}

export function initialsOf(name: string): string {
  const parts = name.split(/[\s@.]+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}
