/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'sp-bg':      '#0f1117',
        'sp-surface': '#161b27',
        'sp-border':  '#1f2937',
        'sp-text':    '#e8eaf0',
        'sp-muted':   '#6b7280',
        'sp-accent':  '#10b981',
        'sp-accent-dim': '#064e3b',
      },
      fontFamily: {
        sans: ['DM Sans', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
