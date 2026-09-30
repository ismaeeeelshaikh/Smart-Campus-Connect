/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
  colors: {
    // Dashboard dark background
    background: {
      dark: '#131827',   // main bg
      card: '#23263b',   // chat cards/sidebar
    },
    // Accent
    accent: {
      DEFAULT: '#a78bfa', // soft purple for highlights and headings
      light: '#c8b6ff'
    },
    // Primary button and chat bubble
    primary: {
      50: '#f5f3ff',
      100: '#ede9fe',
      500: '#a78bfa',    // violet-400 (for buttons, main highlight)
      600: '#7c3aed',    // violet-600 (for hover, active)
      700: '#6d28d9',    // violet-700 (for dark accent)
    },
    // Optional for info boxes and clickable links
    blue: {
      400: '#60a5fa',
      500: '#3b82f6',
      600: '#2563eb',
    }
  }
},
  },
  plugins: [],
}
