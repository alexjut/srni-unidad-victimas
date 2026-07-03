import { describe, it, expect, vi } from 'vitest';
import { act } from 'react';
import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Button from './Button';

describe('Button', () => {
  it('renderiza con texto', async () => {
    let container: HTMLElement;
    await act(async () => {
      const result = render(<Button>Guardar</Button>);
      container = result.container;
    });
    const btn = container!.querySelector('button');
    expect(btn).not.toBeNull();
    expect(btn!.textContent).toContain('Guardar');
  });

  it('ejecuta onClick', async () => {
    const onClick = vi.fn();
    let container: HTMLElement;
    await act(async () => {
      const result = render(<Button onClick={onClick}>Click</Button>);
      container = result.container;
    });
    const btn = container!.querySelector('button')!;
    await act(async () => {
      await userEvent.click(btn);
    });
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('se deshabilita cuando loading=true', async () => {
    let container: HTMLElement;
    await act(async () => {
      const result = render(<Button loading>Cargando</Button>);
      container = result.container;
    });
    const btn = container!.querySelector('button')!;
    expect(btn.disabled).toBe(true);
  });

  it('se deshabilita cuando disabled=true', async () => {
    let container: HTMLElement;
    await act(async () => {
      const result = render(<Button disabled>No click</Button>);
      container = result.container;
    });
    const btn = container!.querySelector('button')!;
    expect(btn.disabled).toBe(true);
  });

  it('aplica variante danger', async () => {
    let container: HTMLElement;
    await act(async () => {
      const result = render(<Button variant="danger">Eliminar</Button>);
      container = result.container;
    });
    const btn = container!.querySelector('button')!;
    expect(btn.className).toContain('bg-gov-rojo');
  });
});
