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
          900: '#090d14',   // Caribbean-tinted (oklch 7% 0.006 95)
          800: '#111820',   // Caribbean-tinted (oklch 11% 0.006 95)
          700: '#1a2332',   // Caribbean-tinted (oklch 15% 0.008 95)
          600: '#2a3444',   // Caribbean-tinted (oklch 19% 0.008 95)
        },
        trade: {
          up: '#22c55e',
          down: '#ef4444',
          neutral: '#5a6a7e'  // Caribbean-tinted (oklch 62% 0 0)
        }
      }
    },
  },
  plugins: [],
}
