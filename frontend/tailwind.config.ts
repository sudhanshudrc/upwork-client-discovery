import type { Config } from 'tailwindcss';

export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: '#F8F9F3',
          dark: '#15180E',
        },
        moss: {
          DEFAULT: '#636B2F',
          dark: '#3D4127',
          sage: '#BAC095',
          chartreuse: '#D4DE95',
          tint: '#EFF4DC',
          hover: '#505724',
        },
        spruce: {
          DEFAULT: '#3D4127',
          deep: '#202414',
          hover: '#15180E',
          dark: '#15180E',
          light: '#636B2F',
        },
        teal: {
          brand: '#636B2F',
          brandHover: '#505724',
          tint: '#EFF4DC',
        },
        sage: {
          DEFAULT: '#BAC095',
          tint: '#F4F6EA',
          border: '#D8DCC5',
          subtle: '#EFF2E3',
        },
        border: {
          subtle: 'var(--color-border-subtle)',
          DEFAULT: 'var(--color-border-default)',
          strong: 'var(--color-border-strong)',
        },
        surface: {
          card: 'var(--color-surface-card)',
          subtle: 'var(--color-surface-subtle)',
          sunken: 'var(--color-surface-sunken)',
        },
        foreground: {
          DEFAULT: 'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)',
          muted: 'var(--color-text-muted)',
          inverse: 'var(--color-text-inverse)',
        },
        tier: {
          a: {
            bg: 'var(--color-tier-a-bg)',
            border: 'var(--color-tier-a-border)',
            text: 'var(--color-tier-a-text)',
          },
          b: {
            bg: 'var(--color-tier-b-bg)',
            border: 'var(--color-tier-b-border)',
            text: 'var(--color-tier-b-text)',
          },
          c: {
            bg: 'var(--color-tier-c-bg)',
            border: 'var(--color-tier-c-border)',
            text: 'var(--color-tier-c-text)',
          },
        },
      },
      fontFamily: {
        sans: [
          '"Plus Jakarta Sans"',
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
        mono: [
          '"JetBrains Mono"',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        elevated: 'var(--shadow-elevated)',
        modal: 'var(--shadow-modal)',
      },
    },
  },
  plugins: [],
} satisfies Config;

