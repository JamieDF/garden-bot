/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: '#0a0a0f',
        card: '#16213e',
        primary: '#64ffda',
        secondary: '#48b8d0',
        accent: '#a8ff78',
        text: '#ccd6f6',
        muted: '#8892b0',
      },
    },
  },
  plugins: [],
}
