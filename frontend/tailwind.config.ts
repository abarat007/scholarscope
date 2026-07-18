import type { Config } from "tailwindcss";

/**
 * Minimalist Monochrome design tokens.
 * Semantic colors resolve to CSS custom properties defined in globals.css so
 * the palette is centralized in one place. Border radius is forced to 0
 * everywhere — the architectural sharpness is non-negotiable.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    // Full override — a strictly monochrome palette, no stray Tailwind colors.
    colors: {
      transparent: "transparent",
      current: "currentColor",
      black: "#000000",
      white: "#ffffff",
      background: "var(--background)",
      foreground: "var(--foreground)",
      subtle: "var(--muted)",
      secondary: "var(--muted-foreground)",
      line: "var(--border-light)",
    },
    borderRadius: {
      none: "0",
      sm: "0",
      DEFAULT: "0",
      md: "0",
      lg: "0",
      xl: "0",
      "2xl": "0",
      "3xl": "0",
      full: "0",
    },
    fontFamily: {
      display: ["var(--font-display)", "Playfair Display", "Georgia", "serif"],
      serif: ["var(--font-serif)", "Source Serif 4", "Georgia", "serif"],
      mono: ["var(--font-mono)", "JetBrains Mono", "ui-monospace", "monospace"],
    },
    // Dramatic editorial scale (per the design system, not Tailwind defaults).
    fontSize: {
      xs: ["0.75rem", { lineHeight: "1rem" }],
      sm: ["0.875rem", { lineHeight: "1.25rem" }],
      base: ["1rem", { lineHeight: "1.625" }],
      lg: ["1.125rem", { lineHeight: "1.7" }],
      xl: ["1.25rem", { lineHeight: "1.6" }],
      "2xl": ["1.5rem", { lineHeight: "1.4" }],
      "3xl": ["2rem", { lineHeight: "1.2" }],
      "4xl": ["2.5rem", { lineHeight: "1.1" }],
      "5xl": ["3.5rem", { lineHeight: "1.05" }],
      "6xl": ["4.5rem", { lineHeight: "1" }],
      "7xl": ["6rem", { lineHeight: "1" }],
      "8xl": ["8rem", { lineHeight: "0.95" }],
      "9xl": ["10rem", { lineHeight: "0.9" }],
    },
    extend: {
      maxWidth: {
        editorial: "72rem",
      },
      transitionDuration: {
        instant: "0ms",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.25s ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
