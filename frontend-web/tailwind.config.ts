import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif"
        ]
      },
      colors: {
        ink: "#17231f",
        pine: "#16614f",
        mint: "#e1efe8",
        linen: "#f6f3ea",
        clay: "#c76643",
        steel: "#60716a",
        slatepanel: "#0f3f35",
        line: "#ded8cb"
      },
      boxShadow: {
        panel: "0 22px 60px rgba(23, 35, 31, 0.14)",
        soft: "0 12px 32px rgba(23, 35, 31, 0.09)"
      }
    }
  },
  plugins: []
};

export default config;
