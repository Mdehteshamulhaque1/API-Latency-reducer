import type { Config } from "tailwindcss"

/**
 * Instrument light. Color is state, never decoration:
 *   signal  = latency / errors / destructive
 *   relay   = cache hits / healthy / success
 *   warn    = 4xx, medium severity, paused
 *   steel   = neutral data series and interactive focus
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1200px" },
    },
    extend: {
      colors: {
        frost: "#E9EDF2",
        paper: "#FFFFFF",
        ink: "#141B22",
        graphite: "#5B6672",
        faint: "#7A8591",
        dim: "#5B6672",
        rule: "#D3D9E0",
        "rule-strong": "#AEB7C2",
        signal: "#E4572E",
        relay: "#1F8A5B",
        warn: "#B7791F",
        steel: "#2F5D8A",
        /* Legacy aliases still referenced by a few pages. */
        panel: "#FFFFFF",
        surface: "#E9EDF2",
        line: "#D3D9E0",
        "line-strong": "#AEB7C2",
        ok: "#1F8A5B",
        accent: {
          indigo: "#2F5D8A",
          cyan: "#2F5D8A",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "var(--font-sans)", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        DEFAULT: "2px",
        sm: "2px",
        md: "2px",
        lg: "3px",
        xl: "3px",
        "2xl": "4px",
      },
      boxShadow: {
        none: "none",
        glow: "none",
        "glow-cyan": "none",
        panel: "none",
        brutal: "none",
        "brutal-sm": "none",
        "brutal-lg": "none",
        "brutal-accent": "none",
        "brutal-accent-lg": "none",
        "brutal-cyan": "none",
      },
      backgroundImage: {
        "accent-gradient": "none",
        "accent-gradient-soft": "none",
      },
      animation: {
        shimmer: "shimmer 1.6s linear infinite",
      },
      keyframes: {
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
