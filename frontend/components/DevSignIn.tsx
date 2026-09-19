"use client";
/**
 * Local-mode role picker (lib/auth.ts's dev bearer scheme). Cloud mode
 * replaces this with Firebase Auth sign-in; everything downstream reads
 * the same getToken()/getUser().
 */
import { AuthedUser, login, logout } from "@/lib/auth";
import { useAuth } from "@/lib/useAuth";

const PRESETS: { label: string; role: AuthedUser["role"]; jurisdiction: string }[] = [
  { label: "District officer, Nashik", role: "district", jurisdiction: "mh/nashik" },
  { label: "State officer, Maharashtra", role: "state", jurisdiction: "mh" },
  { label: "District officer, Dhule", role: "district", jurisdiction: "mh/dhule" },
];

export default function DevSignIn() {
  const { user, ready } = useAuth();
  if (!ready) return null;

  if (user) {
    return (
      <span className="ml-auto flex items-center gap-2 text-xs text-gray-600" data-testid="signed-in">
        {user.role} · {user.jurisdiction}
        <button
          className="rounded border px-2 py-0.5"
          onClick={() => {
            logout();
            window.location.reload();
          }}
        >
          Sign out
        </button>
      </span>
    );
  }

  return (
    <label className="ml-auto flex items-center gap-2 text-xs text-gray-600">
      Sign in as
      <select
        className="rounded border px-1 py-0.5"
        defaultValue=""
        data-testid="dev-signin"
        onChange={(e) => {
          const preset = PRESETS[Number(e.target.value)];
          if (!preset) return;
          login(`dev-${preset.role}`, preset.role, preset.jurisdiction);
          window.location.reload();
        }}
      >
        <option value="" disabled>
          choose a role
        </option>
        {PRESETS.map((p, i) => (
          <option key={p.label} value={i}>
            {p.label}
          </option>
        ))}
      </select>
    </label>
  );
}
