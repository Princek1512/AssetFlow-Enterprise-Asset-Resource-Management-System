/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      // No custom color palette on purpose — the whole app is restricted to
      // Tailwind's default black/white/gray scale (see STYLING RULE in the spec).
      // Adding brand colors here would just invite accidental use.
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
