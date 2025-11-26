import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand colors
        primary: {
          DEFAULT: "#10B981", // emerald-500
          light: "#D1FAE5",   // emerald-100
          dark: "#059669",    // emerald-600
          foreground: "#FFFFFF",
        },
        // Background colors
        background: "#FFFFFF",
        foreground: "#0F172A", // slate-900
        
        // Muted colors
        muted: {
          DEFAULT: "#F1F5F9", // slate-100
          foreground: "#64748B", // slate-500
        },
        
        // Border
        border: "#E2E8F0", // slate-200
        
        // Semantic colors
        destructive: {
          DEFAULT: "#EF4444", // red-500
          foreground: "#FFFFFF",
        },
        warning: {
          DEFAULT: "#F59E0B", // amber-500
          foreground: "#FFFFFF",
        },
        success: {
          DEFAULT: "#10B981", // emerald-500
          foreground: "#FFFFFF",
        },
        
        // Card
        card: {
          DEFAULT: "#FFFFFF",
          foreground: "#0F172A",
        },
        
        // Popover
        popover: {
          DEFAULT: "#FFFFFF",
          foreground: "#0F172A",
        },
        
        // Secondary
        secondary: {
          DEFAULT: "#F1F5F9",
          foreground: "#0F172A",
        },
        
        // Accent
        accent: {
          DEFAULT: "#F1F5F9",
          foreground: "#0F172A",
        },
        
        // Input
        input: "#E2E8F0",
        
        // Ring
        ring: "#10B981",
      },
      borderRadius: {
        lg: "0.5rem",
        md: "calc(0.5rem - 2px)",
        sm: "calc(0.5rem - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        pulse: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        pulse: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;

