import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1200px" },
    },
    extend: {
      colors: {
        ink: "#0A0A0F",
        surface: "#0D0F16",
        panel: "#12141D",
        "panel-2": "#161925",
        line: "rgba(255,255,255,0.08)",
        "line-strong": "rgba(255,255,255,0.14)",
        dim: "#9BA1B0",
        faint: "#5D6270",
        accent: {
          indigo: "#6366F1",
          cyan: "#22D3EE",
        },
        ok: "#34D399",
      },
      fontFamily: {
        sans: ["var(--geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(99,102,241,0.35), 0 0 28px -6px rgba(99,102,241,0.45)",
        "glow-cyan": "0 0 32px -8px rgba(34,211,238,0.5)",
        panel: "0 20px 60px -30px rgba(0,0,0,0.9)",
        /* Neubrutalist offset shadows — flat, no blur */
        brutal: "4px 4px 0px 0px #E7E7EA",
        "brutal-sm": "2px 2px 0px 0px #E7E7EA",
        "brutal-lg": "6px 6px 0px 0px #E7E7EA",
        "brutal-accent": "4px 4px 0px 0px #6366F1",
        "brutal-accent-lg": "6px 6px 0px 0px #6366F1",
        "brutal-cyan": "4px 4px 0px 0px #22D3EE",
      },
      backgroundImage: {
        "accent-gradient":
          "linear-gradient(135deg, #6366F1 0%, #22D3EE 100%)",
        "accent-gradient-soft":
          "linear-gradient(135deg, rgba(99,102,241,0.14) 0%, rgba(34,211,238,0.14) 100%)",
      },
      animation: {
        "pulse-dot": "pulse-dot 2s cubic-bezier(0.4,0,0.6,1) infinite",
        "marquee": "marquee 40s linear infinite",
        "grid-drift": "grid-drift 60s linear infinite",
        shimmer: "shimmer 2.2s linear infinite",
      },
      keyframes: {
        "pulse-dot": {
          "0%,100%": { boxShadow: "0 0 0 0 rgba(52,211,153,0.5)" },
          "50%": { boxShadow: "0 0 0 5px rgba(52,211,153,0)" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        "grid-drift": {
          "0%": { backgroundPosition: "0 0" },
          "100%": { backgroundPosition: "0 400px" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-400px 0" },
          "100%": { backgroundPosition: "400px 0" },
        },
      },
      transitionTimingFunction: {
        expo: "cubic-bezier(0.16,1,0.3,1)",
      },
    },
  },
  plugins: [],
}

export default config
