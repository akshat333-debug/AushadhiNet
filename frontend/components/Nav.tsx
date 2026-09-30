"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ClipboardText, Eye, FirstAidKit, Robot, SquaresFour, WhatsappLogo } from "@phosphor-icons/react";
import { useI18n, type MessageKey } from "@/lib/i18n";
import DevSignIn from "./DevSignIn";
import LanguageSwitcher from "./LanguageSwitcher";
import ThemeToggle from "./ThemeToggle";

const LINKS: { href: string; key: MessageKey; Icon: typeof SquaresFour }[] = [
  { href: "/", key: "nav_overview", Icon: SquaresFour },
  { href: "/orders", key: "nav_orders", Icon: ClipboardText },
  { href: "/agent", key: "nav_agent", Icon: Robot },
  { href: "/sim", key: "nav_whatsapp", Icon: WhatsappLogo },
  { href: "/public", key: "nav_public", Icon: Eye },
];

export default function Nav() {
  const { t } = useI18n();
  const path = usePathname();
  const active = (href: string) => (href === "/" ? path === "/" || path.startsWith("/facility") : path.startsWith(href));

  const links = LINKS.map(({ href, key, Icon }) => (
    <Link
      key={href}
      href={href}
      className={`flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm transition ${
        active(href)
          ? "bg-teal-50 font-medium text-teal-800 dark:bg-teal-950/60 dark:text-teal-300"
          : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
      }`}
    >
      <Icon size={16} weight={active(href) ? "fill" : "regular"} />
      {t(key)}
    </Link>
  ));

  return (
    <>
    <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-teal-700 focus:px-3 focus:py-2 focus:text-sm focus:text-white">
      {t("skip_to_content")}
    </a>
    <header className="sticky top-0 z-40 border-b border-zinc-200/80 bg-zinc-50/85 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/85">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 md:px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-teal-700 text-white dark:bg-teal-500 dark:text-zinc-950">
            <FirstAidKit size={18} weight="fill" />
          </span>
          <span className="leading-tight">
            <span className="block text-[15px] font-semibold tracking-tight" translate="no">AushadhiNet</span>
            <span className="hidden text-[11px] text-zinc-500 xl:block dark:text-zinc-400">{t("brand_tagline")}</span>
          </span>
        </Link>
        <nav className="hidden items-center gap-1 lg:flex">{links}</nav>
        <div className="ml-auto flex items-center gap-2">
          <LanguageSwitcher />
          <ThemeToggle />
          <DevSignIn />
        </div>
      </div>
      <nav className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-4 pb-2 lg:hidden">{links}</nav>
    </header>
    </>
  );
}
