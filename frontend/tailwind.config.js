import typography from '@tailwindcss/typography';

/**
 * "APSIT Heritage" design system - colours taken from the college crest:
 * deep teal ribbon, saffron gold base, crimson flame, on warm paper.
 * (Deliberately no purple / neon "AI app" palette.)
 * @type {import('tailwindcss').Config}
 */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        teal: {
          50: '#eef6f5',
          100: '#d8ebe9',
          200: '#b3d6d3',
          300: '#82b9b6',
          400: '#4f9a98',
          500: '#2a7f80',
          600: '#1b6b6d',
          700: '#145c5f', // primary (crest ribbon)
          800: '#0f4a4d',
          900: '#0d3b3e',
          950: '#082729',
        },
        gold: {
          50: '#fdf8e9',
          100: '#fbefc9',
          200: '#f6dd8e',
          300: '#f0c955',
          400: '#e9b733',
          500: '#e0a91b', // accent (crest base)
          600: '#c08812',
          700: '#9a6812',
          800: '#7d5316',
        },
        crimson: {
          50: '#fdf2f3',
          100: '#fbe2e4',
          200: '#f5c2c7',
          500: '#c22a3b',
          600: '#a51d2d', // used sparingly: errors, destructive actions
          700: '#8a1726',
        },
        paper: {
          DEFAULT: '#f7f4ec', // app background
          50: '#fcfaf5',
          100: '#f7f4ec',
          200: '#efe9dc',
          300: '#e3ddd0',
        },
        ink: {
          DEFAULT: '#1d2526', // main text
          700: '#33403f',
          600: '#46504f',
          500: '#5b6b6c',
          400: '#7c8a8b',
          300: '#a3aeae',
        },
        line: '#e3ddd0', // borders
      },
      fontFamily: {
        sans: ['"Hanken Grotesk Variable"', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'sans-serif'],
        serif: ['"Literata Variable"', 'Georgia', 'Cambria', 'serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(29, 37, 38, 0.04), 0 6px 20px -8px rgba(29, 37, 38, 0.10)',
        lift: '0 2px 4px rgba(29, 37, 38, 0.05), 0 16px 40px -16px rgba(13, 59, 62, 0.28)',
        composer: '0 8px 30px -12px rgba(13, 59, 62, 0.22)',
      },
      backgroundImage: {
        // Faint tiled grid, a nod to the tiled floor in the crest
        'crest-grid':
          'linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)',
        'paper-grid':
          'linear-gradient(to right, rgba(20,92,95,0.045) 1px, transparent 1px), linear-gradient(to bottom, rgba(20,92,95,0.045) 1px, transparent 1px)',
      },
      backgroundSize: {
        grid: '36px 36px',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'dot-bounce': {
          '0%, 80%, 100%': { transform: 'translateY(0)', opacity: '0.4' },
          '40%': { transform: 'translateY(-4px)', opacity: '1' },
        },
        caret: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.35s ease-out both',
        'dot-bounce': 'dot-bounce 1.2s ease-in-out infinite',
        caret: 'caret 1s step-end infinite',
      },
      typography: ({ theme }) => ({
        DEFAULT: {
          css: {
            '--tw-prose-body': theme('colors.ink.700'),
            '--tw-prose-headings': theme('colors.ink.DEFAULT'),
            '--tw-prose-links': theme('colors.teal.700'),
            '--tw-prose-bold': theme('colors.ink.DEFAULT'),
            '--tw-prose-bullets': theme('colors.gold.500'),
            '--tw-prose-counters': theme('colors.teal.600'),
            '--tw-prose-th-borders': theme('colors.line'),
            '--tw-prose-td-borders': theme('colors.paper.200'),
            '--tw-prose-hr': theme('colors.line'),
            '--tw-prose-quote-borders': theme('colors.gold.400'),
            '--tw-prose-code': theme('colors.teal.800'),
            a: { textDecorationColor: theme('colors.gold.400'), textUnderlineOffset: '3px', fontWeight: '500' },
            'h1, h2, h3, h4': { fontFamily: theme('fontFamily.serif').join(', '), fontWeight: '600' },
            code: { backgroundColor: theme('colors.teal.50'), padding: '0.1em 0.35em', borderRadius: '0.3em', fontWeight: '500' },
            'code::before': { content: 'none' },
            'code::after': { content: 'none' },
          },
        },
      }),
    },
  },
  plugins: [typography],
};
