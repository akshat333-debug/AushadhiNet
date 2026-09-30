"use client";
/**
 * Local-mode role picker (lib/auth.ts's dev bearer scheme). Cloud mode
 * replaces this with Firebase Auth sign-in; everything downstream reads
 * the same getToken()/getUser().
 */
import { SignOut, UserCircle } from "@phosphor-icons/react";
import { AuthedUser, login, logout } from "@/lib/auth";
import { useAuth } from "@/lib/useAuth";
import { useI18n, type MessageKey } from "@/lib/i18n";

const PRESETS: { key: MessageKey; role: AuthedUser["role"]; jurisdiction: string }[] = [
  { key: "role_district_nashik", role: "district", jurisdiction: "mh/nashik" },
  { key: "role_state_mh", role: "state", jurisdiction: "mh" },
  { key: "role_district_dhule", role: "district", jurisdiction: "mh/dhule" },
];

export default function DevSignIn() {
  const { user, ready } = useAuth();
  const { t, place } = useI18n();
  if (!ready) return <span className="h-9 w-32" aria-hidden />;

  if (user) {
    return (
      <span className="flex items-center gap-2 text-sm" data-testid="signed-in">
        <UserCircle size={22} weight="duotone" className="text-teal-700 dark:text-teal-400" />
        <span className="hidden leading-tight sm:block">
          <span className="block font-medium">{t(`role_${user.role}` as MessageKey)}</span>
          <span className="block text-xs text-zinc-500 dark:text-zinc-400">{place(user.jurisdiction)}</span>
        </span>
        <button
          className="rounded-lg p-2 text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800"
          onClick={() => {
            logout();
            window.location.reload();
          }}
          aria-label={t("sign_out")}
          title={t("sign_out")}
        >
          <SignOut size={18} />
        </button>
      </span>
    );
  }

  return (
    <label className="flex items-center">
      <span className="sr-only">{t("sign_in_as")}</span>
      <select
        className="rounded-lg bg-teal-700 py-1.5 pl-3 pr-2 text-sm font-medium text-white hover:bg-teal-800 dark:bg-teal-500 dark:text-zinc-950 dark:hover:bg-teal-400"
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
          {t("sign_in_as")}
        </option>
        {PRESETS.map((p, i) => (
          <option key={p.key} value={i}>
            {t(p.key)}
          </option>
        ))}
      </select>
    </label>
  );
}
