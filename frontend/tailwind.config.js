/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: '#0b0f14',
        card: '#141b24',
        card2: '#1b2531',
        line: '#263242',
        primary: '#64ffda',
        sky: '#79b8ff',
        moss: '#7ee787',
        warn: '#f0b72f',
        danger: '#ff7b72',
        accent: '#a8ff78',
        text: '#e8eef4',
        muted: '#8b98a5',
      },
      fontFamily: {
        mono: ["'IBM Plex Mono'", 'ui-monospace', 'monospace'],
        sans: ["'Space Grotesk'", 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
