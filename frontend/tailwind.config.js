/** Colours come from CSS variables (src/index.css) so light/dark share one palette. */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter Variable"', 'Inter', 'system-ui', 'Segoe UI', 'sans-serif'],
      },
      colors: {
        canvas: v('canvas'),
        surface: v('surface'),
        subtle: v('subtle'),
        line: v('line'),
        'line-strong': v('line-strong'),
        ink: v('ink'),
        muted: v('muted'),
        faint: v('faint'),
        accent: { DEFAULT: v('accent'), hover: v('accent-hover'), soft: v('accent-soft'), ink: v('accent-ink') },
        go: { DEFAULT: v('go'), hover: v('go-hover'), soft: v('go-soft') },
        danger: { DEFAULT: v('danger'), hover: v('danger-hover'), soft: v('danger-soft') },
        warn: { DEFAULT: v('warn'), soft: v('warn-soft') },
        bar: { track: v('bar-track'), fill: v('bar-fill') },
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
        xs: ['0.75rem', { lineHeight: '1rem' }],
        sm: ['0.8125rem', { lineHeight: '1.25rem' }],
        base: ['0.875rem', { lineHeight: '1.5rem' }],
        md: ['1rem', { lineHeight: '1.5rem' }],
        lg: ['1.125rem', { lineHeight: '1.75rem' }],
        xl: ['1.375rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.75rem', { lineHeight: '2.25rem' }],
        '3xl': ['2.25rem', { lineHeight: '2.5rem' }],
      },
      borderRadius: { DEFAULT: '6px', md: '6px', lg: '8px' },
      boxShadow: {
        pop: '0 8px 24px -8px rgb(15 23 42 / 0.18), 0 1px 2px rgb(15 23 42 / 0.06)',
        panel: '-12px 0 32px -16px rgb(15 23 42 / 0.25)',
      },
      maxWidth: { content: '80rem' },
    },
  },
  plugins: [],
}
