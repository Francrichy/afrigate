/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./pages/**/*.{js,jsx}", "./components/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      colors: {
        base: {
          950: "#050505",
          900: "#0a0a0a",
          850: "#101010",
          800: "#141414",
          700: "#1f1f1f",
          600: "#2c2c2c",
          400: "#6b6b6b",
          200: "#a3a3a3",
          100: "#e5e5e5",
        },
        accent: {
          DEFAULT: "#22c55e",
          hover: "#16a34a",
          soft: "rgba(34,197,94,0.12)",
        },
      },
    },
  },
  plugins: [],
};
