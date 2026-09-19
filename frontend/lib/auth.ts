/**
 * Local-mode dev auth (modular-plan.md step 40; matches backend/deps.py's
 * `dev:<uid>:<role>:<jurisdiction>` bearer token scheme). In cloud mode
 * this would be replaced by a real Firebase Auth sign-in -- the shape of
 * getToken()/getUser() stays the same either way, so lib/api.ts never
 * needs to know which mode is active.
 */

export interface AuthedUser {
  uid: string;
  role: "facility" | "block" | "district" | "state" | "public";
  jurisdiction: string;
}

const STORAGE_KEY = "aushadhinet.devSession";

export function login(uid: string, role: AuthedUser["role"], jurisdiction: string): AuthedUser {
  const user: AuthedUser = { uid, role, jurisdiction };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
  } catch {
    // localStorage unavailable (private browsing, etc.) -- session just
    // won't persist across reloads, which is a degraded but safe fallback
  }
  return user;
}

export function logout(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export function getUser(): AuthedUser | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AuthedUser) : null;
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  const user = getUser();
  if (!user) return null;
  return `dev:${user.uid}:${user.role}:${user.jurisdiction}`;
}
