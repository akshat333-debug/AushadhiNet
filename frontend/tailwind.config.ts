import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // Latin first, then one Noto family per Indian script: the browser picks per glyph.
        sans: ["var(--font-geist)", "var(--font-deva)", "var(--font-beng)", "var(--font-taml)", "var(--font-telu)", "var(--font-knda)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgb(24 24 27 / 0.04), 0 8px 24px -12px rgb(24 24 27 / 0.12)",
      },
    },
  },
  plugins: [],
};
export default config;
