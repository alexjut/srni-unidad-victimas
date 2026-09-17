/**
 * Remonta una pantalla desde cero cuando cambian los parámetros que la identifican.
 *
 * Todo el flujo de caracterización vive como pestañas ocultas de `(main)/_layout`
 * (Tabs). Una pestaña NO se desmonta al salir de ella: la próxima vez que se
 * navega ahí, React reutiliza el mismo componente con los parámetros nuevos y
 * TODO el estado viejo (borrador, respuestas, miembros, "creando…").
 *
 * Eso es lo que reportó campo: «por más que busque otras cédulas me sale la
 * entrevista que estaba haciendo; solo se quita cerrando sesión». Cerrar sesión
 * desmonta las pestañas; nada más lo hacía. En el capítulo era peor que visual:
 * su carga depende solo de `temaId`, así que al abrir OTRA entrevista en el mismo
 * capítulo seguía el borrador anterior y las respuestas se guardaban en él.
 *
 * En vez de perseguir cada `useState` y cada lista de dependencias, la pantalla
 * se envuelve con una `key` hecha de sus parámetros de identidad: si cambian, React
 * la desmonta y la vuelve a montar limpia. Si no cambian (volver a la misma
 * entrevista), se conserva como antes.
 */
import type { ComponentType } from 'react';
import { useLocalSearchParams } from 'expo-router';

export function claveDeParams(
  params: Record<string, string | string[] | undefined>,
  nombres: readonly string[],
): string {
  return nombres
    .map((n) => {
      const v = params[n];
      return Array.isArray(v) ? v.join(',') : (v ?? '');
    })
    .join('|');
}

export function remontarPorParams<P extends object>(
  Pantalla: ComponentType<P>,
  nombres: readonly string[],
): ComponentType<P> {
  function PantallaConClave(props: P) {
    const params = useLocalSearchParams();
    return <Pantalla key={claveDeParams(params, nombres)} {...props} />;
  }
  PantallaConClave.displayName = `remontarPorParams(${Pantalla.displayName ?? Pantalla.name ?? 'Pantalla'})`;
  return PantallaConClave;
}
