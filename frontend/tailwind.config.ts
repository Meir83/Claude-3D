import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand blue matching preview.py model colour (0.42, 0.62, 0.92)
        brand: {
          50:  "#eef4fd",
          100: "#d5e6fa",
          200: "#aecdf5",
          300: "#7daeee",
          400: "#6b9eeb",   // ← main model colour
          500: "#4a82e0",
          600: "#3467c8",
          700: "#2a52a0",
          800: "#1e3a72",
          900: "#122244",
        },
        surface: {
          900: "#0d0f14",   // darkest background
          800: "#13161e",   // sidebar / panels
          700: "#1a1e28",   // card backgrounds
          600: "#222736",   // hover states
          500: "#2e3548",   // borders
          400: "#3d4560",   // muted borders
          300: "#8892a4",   // muted text
          200: "#c4cad6",   // secondary text
          100: "#e8eaf0",   // primary text
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "cursor-blink": "cursor-blink 1s step-end infinite",
        "fade-in": "fade-in 0.2s ease-out",
        "slide-up": "slide-up 0.3s ease-out",
      },
      keyframes: {
        "cursor-blink": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
