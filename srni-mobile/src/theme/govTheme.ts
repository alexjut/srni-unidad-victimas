/**
 * Design System GOV.CO — Unidad para las Víctimas (SRNI)
 * Basado en los lineamientos oficiales del Estado Colombiano.
 */
import { MD3LightTheme } from 'react-native-paper';

// ── Paleta institucional ────────────────────────────────────────────────────
export const GOV = {
  // Colores principales
  amarillo:       '#FFCD00',   // Franja GOV.CO obligatoria
  azul:           '#1565C0',   // Acciones principales, botones, headers
  azulOscuro:     '#004884',   // Títulos, texto énfasis
  rojo:           '#D32F2F',   // Errores, alertas críticas
  verde:          '#2E7D32',   // Completados, confirmaciones
  naranja:        '#E65100',   // Advertencias, offline, borrador

  // Neutros
  fondoApp:       '#F5F5F5',
  superficie:     '#FFFFFF',
  borde:          '#E0E0E0',
  textoP:         '#1A1A1A',   // Texto principal
  textoS:         '#666666',   // Texto secundario
  textoT:         '#9E9E9E',   // Texto terciario

  // Tonos de color (fondos de chips, badges)
  azulTenue:      '#E3F2FD',
  verdeTenue:     '#E8F5E9',
  rojoTenue:      '#FFEBEE',
  naranjaTenue:   '#FFF3E0',
  amarilloTenue:  '#FFFDE7',

  // Alturas
  alturaFranjaGov: 28,
  alturaHeaderAzul: 56,
} as const;

// ── Espaciado ────────────────────────────────────────────────────────────────
export const SPACING = {
  xs:  4,
  sm:  8,
  md:  16,
  lg:  24,
  xl:  32,
  xxl: 48,
} as const;

// ── Radios ───────────────────────────────────────────────────────────────────
export const RADIUS = {
  sm:   8,
  md:   12,
  lg:   16,
  pill: 50,
} as const;

// ── Sombras ──────────────────────────────────────────────────────────────────
export const SHADOW = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  fab: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 6,
  },
} as const;

// ── Tipografía ───────────────────────────────────────────────────────────────
export const FONT = {
  h1:      { fontSize: 24, fontWeight: '700' as const, lineHeight: 32, color: GOV.azulOscuro },
  h2:      { fontSize: 20, fontWeight: '700' as const, lineHeight: 28, color: GOV.azulOscuro },
  h3:      { fontSize: 16, fontWeight: '600' as const, lineHeight: 24, color: GOV.textoP },
  body:    { fontSize: 14, fontWeight: '400' as const, lineHeight: 22, color: GOV.textoP },
  small:   { fontSize: 13, fontWeight: '400' as const, lineHeight: 20, color: GOV.textoS },
  caption: { fontSize: 12, fontWeight: '400' as const, lineHeight: 18, color: GOV.textoT },
  label:   { fontSize: 12, fontWeight: '600' as const, lineHeight: 16, color: GOV.textoS },
} as const;

// ── Tema react-native-paper ──────────────────────────────────────────────────
export const govTheme = {
  ...MD3LightTheme,
  colors: {
    ...MD3LightTheme.colors,
    primary:            GOV.azul,
    primaryContainer:   GOV.azulTenue,
    secondary:          GOV.amarillo,
    secondaryContainer: GOV.amarilloTenue,
    error:              GOV.rojo,
    background:         GOV.fondoApp,
    surface:            GOV.superficie,
    surfaceVariant:     '#F0F4FF',
    onPrimary:          '#FFFFFF',
    onSecondary:        GOV.azulOscuro,
    outline:            GOV.borde,
    onSurfaceVariant:   GOV.textoS,
  },
};
