import type { Config } from "tailwindcss";
import tailwindcssTypography from "@tailwindcss/typography";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        sans: ["var(--font-ui)"],
        serif: ["var(--font-serif)"],
        mono: ["var(--font-mono)"],
      },
      colors: {
        surface: "var(--surface)",
        "surface-raised": "var(--surface-raised)",
        "surface-hover": "var(--surface-hover)",
        "text-muted": "var(--text-muted)",
        "text-dim": "var(--text-dim)",
        verified: "var(--verified)",
        "verified-bg": "var(--verified-bg)",
        unverified: "var(--unverified)",
        "unverified-bg": "var(--unverified-bg)",
        blocked: "var(--blocked)",
        "blocked-bg": "var(--blocked-bg)",
        progress: "var(--progress)",
        "progress-bg": "var(--progress-bg)",
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
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
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
      typography: {
        DEFAULT: {
          css: {
            "--tw-prose-body": "var(--text)",
            "--tw-prose-headings": "var(--text)",
            "--tw-prose-lead": "var(--text-muted)",
            "--tw-prose-links": "var(--accent-token)",
            "--tw-prose-bold": "var(--text)",
            "--tw-prose-counters": "var(--text-muted)",
            "--tw-prose-bullets": "var(--text-muted)",
            "--tw-prose-hr": "var(--border-subtle)",
            "--tw-prose-quotes": "var(--text-muted)",
            "--tw-prose-quote-borders": "var(--border-token)",
            "--tw-prose-captions": "var(--text-muted)",
            "--tw-prose-code": "var(--text)",
            "--tw-prose-pre-code": "var(--text)",
            "--tw-prose-pre-bg": "var(--surface-raised)",
            "--tw-prose-th-borders": "var(--border-subtle)",
            "--tw-prose-td-borders": "var(--border-subtle)",
            maxWidth: "none",
            lineHeight: "1.7",
            h1: {
              fontFamily: "var(--font-serif), ui-serif, Georgia, serif",
              fontWeight: "600",
              fontSize: "2.125rem",
              lineHeight: "1.25",
              marginTop: "0",
              marginBottom: "0.75em",
            },
            h2: {
              fontFamily: "var(--font-serif), ui-serif, Georgia, serif",
              fontWeight: "600",
              fontSize: "1.625rem",
              lineHeight: "1.3",
              marginTop: "1.75em",
              marginBottom: "0.65em",
            },
            h3: {
              fontFamily: "var(--font-serif), ui-serif, Georgia, serif",
              fontWeight: "600",
              fontSize: "1.3125rem",
              marginTop: "1.5em",
              marginBottom: "0.5em",
            },
            h4: {
              fontFamily: "var(--font-serif), ui-serif, Georgia, serif",
              fontWeight: "600",
              fontSize: "1.125rem",
              marginTop: "1.25em",
              marginBottom: "0.4em",
            },
            a: {
              textDecoration: "underline",
              textUnderlineOffset: "2px",
              fontWeight: "500",
            },
            code: {
              fontWeight: "500",
              backgroundColor: "var(--surface-raised)",
              padding: "0.15em 0.35em",
              borderRadius: "var(--r-sm)",
              border: "1px solid var(--border-subtle)",
            },
            "code::before": { content: '""' },
            "code::after": { content: '""' },
            pre: {
              borderRadius: "var(--r)",
              border: "1px solid var(--border-subtle)",
            },
          },
        },
      },
    },
  },
  plugins: [tailwindcssAnimate, tailwindcssTypography],
};

export default config;
