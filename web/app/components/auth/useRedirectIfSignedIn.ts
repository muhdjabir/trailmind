"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { supabase } from "../../lib/supabase";

// Also catches the return from Google OAuth, which lands with a fresh session.
export function useRedirectIfSignedIn() {
  const router = useRouter();
  useEffect(() => {
    if (!supabase) return;
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) router.replace("/");
    });
  }, [router]);
}
