/**
 * El ítem «Recaracterizaciones» del menú (11-sep-2026).
 *
 * ─── Lo que se protege ────────────────────────────────────────────────────
 * Es el punto de control del retiro de la vigencia. Dos cosas tienen que ser
 * ciertas y ninguna se ve mirando el JSX:
 *
 *   1. **El ENCUESTADOR no lo ve.** Es un instrumento para mirar cómo opera el
 *      equipo de campo; en manos del propio campo no supervisa nada, y además le
 *      diría exactamente qué queda registrado de su trabajo.
 *   2. **El menú pide lo MISMO que la API.** El backend exige `ver_reportes` o
 *      `administrar`. Si el menú pidiera menos, llevaría a un 403 después del
 *      clic; si pidiera más, esconderá la pantalla a quien sí puede entrar. Las
 *      dos fallas son silenciosas y las dos se descubren en la jornada.
 *
 * Es distinto del caso de «Autorizaciones», que se cuelga de un permiso de
 * ESCRITURA (`autorizar_excepciones`) y por eso su menú es más estrecho que
 * `ver_reportes`. Acá la pantalla es de lectura y el permiso coincide.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { act } from 'react';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useAuthStore } from '@/stores/authStore';

const PERFIL_BASE = {
  codigo: 'X',
  nombre: 'Perfil',
  puede_buscar_rni: true,
  puede_caracterizar: false,
};

function conPerfil(extra: Record<string, unknown>) {
  useAuthStore.setState({
    usuario: {
      id: '1',
      codigo_usuario: 'QATEST',
      nombre_completo: 'QA Test',
      email: 'qa@srni.dev',
      perfil: { ...PERFIL_BASE, ...extra },
    } as never,
  });
}

async function pintar() {
  let container!: HTMLElement;
  await act(async () => {
    const r = render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    container = r.container;
  });
  return container;
}

function item(container: HTMLElement) {
  return Array.from(container.querySelectorAll('a')).find((a) =>
    a.textContent?.includes('Recaracterizaciones'));
}

describe('Sidebar — Recaracterizaciones', () => {
  beforeEach(() => {
    useAuthStore.setState({ usuario: null });
  });

  it('NO aparece para el encuestador', async () => {
    conPerfil({ codigo: 'ENCUESTADOR', puede_caracterizar: true });
    expect(item(await pintar())).toBeUndefined();
  });

  it('aparece para el supervisor', async () => {
    conPerfil({ codigo: 'SUPERVISOR', puede_ver_reportes: true });
    expect(item(await pintar())).toBeDefined();
  });

  it('aparece para el coordinador', async () => {
    conPerfil({ codigo: 'COORDINADOR', puede_caracterizar: true, puede_ver_reportes: true });
    expect(item(await pintar())).toBeDefined();
  });

  it('aparece para el documentador, que ve reportes', async () => {
    // Mismo criterio que la API: es un perfil de solo lectura que ya ve los
    // reportes agregados, y este es el informe que se entrega a control interno.
    conPerfil({ codigo: 'DOCUMENTADOR', puede_ver_reportes: true });
    expect(item(await pintar())).toBeDefined();
  });

  it('apunta a la pantalla del panel', async () => {
    conPerfil({ codigo: 'SUPERVISOR', puede_ver_reportes: true });
    expect(item(await pintar())!.getAttribute('href')).toBe('/recaracterizaciones');
  });
});
