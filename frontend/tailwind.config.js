// tailwind.config.js
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      colors: {
        'space-black': '#0f172a',
        'deep-purple': '#4c1d95',
        'cosmic-blue': '#1e293b',
        'nebula-purple': '#7e22ce'
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}