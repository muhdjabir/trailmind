// Mirror this in Supabase's auth settings (minimum password length) - the
// meter is guidance; the server-side setting is what's enforced.
export const MIN_PASSWORD_LENGTH = 8;

export type Strength = { score: 0 | 1 | 2 | 3 | 4; hint: string };

export function passwordStrength(password: string): Strength {
  if (password.length === 0) return { score: 0, hint: `At least ${MIN_PASSWORD_LENGTH} characters` };
  if (password.length < MIN_PASSWORD_LENGTH) {
    const missing = MIN_PASSWORD_LENGTH - password.length;
    return {
      score: password.length >= MIN_PASSWORD_LENGTH / 2 ? 2 : 1,
      hint: `Add ${missing} more character${missing === 1 ? "" : "s"}`,
    };
  }
  const mixed = /[a-z]/.test(password) && /[A-Z]/.test(password) && /\d/.test(password);
  const symbol = /[^A-Za-z0-9]/.test(password);
  if (mixed && (symbol || password.length >= 12)) return { score: 4, hint: "Strong password" };
  if (mixed || symbol || password.length >= 12) {
    return { score: 3, hint: "Good - a symbol or more length makes it stronger" };
  }
  return { score: 2, hint: "Mix in upper and lowercase letters and a number" };
}
