"use client";
import { useEffect, useState } from "react";
import { AuthedUser, getUser } from "./auth";

/**
 * Client-only auth hook. Reading localStorage synchronously during
 * render causes a server/client hydration mismatch (the server always
 * renders as "no window", the client might already have a session) --
 * this hook renders null on the first pass everywhere (matching SSR) and
 * updates via useEffect after mount, avoiding the mismatch. Found as a
 * real bug via the Playwright e2e run: pages checking `typeof window !==
 * "undefined"` directly during render triggered a Next.js "Fast Refresh
 * had to perform a full reload due to a runtime error".
 */
export function useAuth(): { user: AuthedUser | null; ready: boolean } {
  const [user, setUser] = useState<AuthedUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setUser(getUser());
    setReady(true);
  }, []);

  return { user, ready };
}
