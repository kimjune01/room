/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'theater-bg': '#0e0e10',
        'theater-bg-light': '#1a0e1a',
        'theater-surface': '#18181b',
        'theater-surface-light': '#1f1f23',
        'theater-border': '#2d2d2d',
        'theater-text': '#efeff1',
        'theater-text-muted': '#adadb8',
        'twitch-purple': '#9146ff',
        'twitch-purple-dark': '#772ce8',
      },
      animation: {
        'fade-in-slide': 'fadeInSlide 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
      },
      keyframes: {
        fadeInSlide: {
          '0%': {
            opacity: '0',
            transform: 'translateY(20px)'
          },
          '100%': {
            opacity: '1',
            transform: 'translateY(0)'
          },
        },
      },
      backdropBlur: {
        'xs': '2px',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}