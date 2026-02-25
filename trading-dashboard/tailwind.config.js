/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0f172a',
          800: '#1e293b',
          700: '#334155',
        },
        trade: {
          up: '#22c55e',
          down: '#ef4444',
          neutral: '#64748b'
        }
      }
    },
  },
  plugins: [],
}
