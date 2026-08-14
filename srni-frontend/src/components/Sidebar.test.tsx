/**
 * El ítem «Autorizaciones» del menú (14-ago-2026).
 *
 * Dos cosas tienen que ser ciertas y ninguna es obvia mirando el JSX:
 *
 *   1. Solo lo ve quien puede autorizar. Un menú que aparece de más termina en
 *      un 403 después de que alguien hizo clic.
 *   2. Es un <a> y NO un enlace de react-router. La pantalla la sirve Django,
 *      fuera de esta SPA: con un NavLink, el router intenta resolverla adentro
 *      y muestra su pantalla de error sin salir nunca al backend — que fue
 *      exactamente lo que pasó la primera vez que se probó.
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

function itemAutorizaciones(container: HTMLElement) {
  return Array.from(container.querySelectorAll('a')).find((a) =>
    a.textContent?.includes('Autorizaciones'));
}

describe('Sidebar — Autorizaciones', () => {
  beforeEach(() => {
    useAuthStore.setState({ usuario: null });
  });

  it('no aparece para un encuestador', async () => {
    conPerfil({ codigo: 'ENCUESTADOR', puede_caracterizar: true });
    expect(itemAutorizaciones(await pintar())).toBeUndefined();
  });

  it('no aparece para el documentador, aunque vea reportes', async () => {
    // Se creó de solo lectura a propósito. Colgar el menú de `ver_reportes` le
    // daría por la puerta de atrás lo que se le negó de frente.
    conPerfil({ codigo: 'DOCUMENTADOR', puede_ver_reportes: true });
    expect(itemAutorizaciones(await pintar())).toBeUndefined();
  });

  it('aparece para quien tiene el permiso', async () => {
    conPerfil({ codigo: 'COORDINADOR', puede_autorizar_excepciones: true });
    expect(itemAutorizaciones(await pintar())).toBeDefined();
  });

  it('aparece para el administrador', async () => {
    conPerfil({ codigo: 'ADMINISTRADOR', puede_administrar: true });
    expect(itemAutorizaciones(await pintar())).toBeDefined();
  });

  it('apunta al backend y no a una ruta de la SPA', async () => {
    conPerfil({ codigo: 'COORDINADOR', puede_autorizar_excepciones: true });
    const item = itemAutorizaciones(await pintar());

    // `/api/` es lo único que el nginx del stack y el proxy de Vite mandan al
    // Django. Si algún día esto apunta a `/autorizaciones/` sin que el nginx
    // nuevo esté desplegado, la pantalla vuelve a caer en la SPA.
    expect(item!.getAttribute('href')).toBe('/api/autorizaciones/');
  });
});
