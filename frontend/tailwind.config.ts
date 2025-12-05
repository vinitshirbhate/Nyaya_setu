import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./pages/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#C1785A",
          foreground: "#0b090a"
        },
        secondary: {
          DEFAULT: "#305669",
          foreground: "#f8fafc"
        },
        accent: {
          DEFAULT: "#8ABEB9",
          foreground: "#0b090a"
        },
        background: "#0f172a",
        foreground: "#e5e7eb",
        muted: {
          DEFAULT: "#1f2933",
          foreground: "#9ca3af"
        },
        border: "#1f2937"
      },
      borderRadius: {
        lg: "0.75rem",
        md: "0.5rem",
        sm: "0.375rem"
      }
    }
  },
  plugins: []
};

export default config;


