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
          amarilloTenue:'#FFFDE7',  // fondo amarillo suave
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
        sans: ['Nunito Sans', 'system-ui', 'sans-serif'],
        display: ['Nunito Sans', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        // Sombras Apple-style (multi-capa, difusas)
        'soft':    '0 1px 2px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.06)',
        'soft-md': '0 2px 4px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.08)',
        'soft-lg': '0 4px 8px rgba(0,0,0,0.04), 0 8px 32px rgba(0,0,0,0.10)',
        'soft-xl': '0 8px 16px rgba(0,0,0,0.06), 0 16px 48px rgba(0,0,0,0.12)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        'fade-in-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.96)' },
          to:   { opacity: '1', transform: 'scale(1)' },
        },
        'slide-down': {
          from: { opacity: '0', transform: 'translateY(-4px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-up': {
          from: { transform: 'translateY(100%)' },
          to:   { transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in':     'fade-in 0.3s ease-out',
        'fade-in-up':  'fade-in-up 0.35s ease-out',
        'scale-in':    'scale-in 0.25s ease-out',
        'slide-down':  'slide-down 0.2s ease-out',
        'slide-up':    'slide-up 0.25s ease-out',
      },
      transitionTimingFunction: {
        'apple': 'cubic-bezier(0.25, 0.1, 0.25, 1)',       // suave Apple
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',     // rebote sutil
      },
    },
  },
  plugins: [],
} satisfies Config;
