"use client";
import { MotionConfig } from "motion/react";
import { IconContext } from "@phosphor-icons/react";
import { I18nProvider } from "@/lib/i18n";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <I18nProvider>
      {/* Every icon here sits beside a text label or inside a labelled button: decorative. */}
      <IconContext.Provider value={{ "aria-hidden": true } as React.SVGProps<SVGSVGElement>}>
        <MotionConfig reducedMotion="user">{children}</MotionConfig>
      </IconContext.Provider>
    </I18nProvider>
  );
}
