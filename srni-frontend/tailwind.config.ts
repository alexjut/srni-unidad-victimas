import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Paleta GOV.CO institucional
        gov: {
          azul:         '#1565C0',
          azulOscuro:   '#003A80',
          azulTenue:    '#E3F2FD',
          amarillo:     '#F5BF04',  // franja GOV.CO
          verde:        '#2E7D32',
          verdeTenue:   '#E8F5E9',
          rojo:         '#C62828',
          rojoTenue:    '#FFEBEE',
          naranja:      '#E65100',
          naranjaTenue: '#FFF3E0',
          gris:         '#616161',
          grisTenue:    '#F5F5F5',
          borde:        '#E0E0E0',
        },
      },
      fontFamily: {
        sans: ['Work Sans', 'system-ui', 'sans-serif'],
        display: ['Montserrat', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
} satisfies Config;
