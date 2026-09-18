"""
Jerarquía de equipos: el supervisor supervisa a sus encuestadores.

Pedido el 18-sep-2026: poder organizar y ver la operación por equipos. Hasta hoy
«supervisor» era solo un nombre de perfil —ninguna relación decía a QUIÉN supervisa—,
así que la visibilidad era binaria: o lo propio, o los 1.157 encuestadores del país.

Lo que se fija acá:
· Un encuestador pertenece a UN equipo a la vez; moverlo cierra la pertenencia
  anterior en vez de borrarla, porque el reporte del mes pasado tiene que seguir
  sabiendo de quién era.
· El equipo lo encabeza quien puede supervisar, y nadie se supervisa a sí mismo.
· El supervisor ve y arma el suyo; el encuestador no ve equipos.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.autenticacion.models import Equipo, MiembroEquipo, Perfil

Usuario = get_user_model()


def usuario(codigo, perfil_codigo, **flags):
    perfil, _ = Perfil.objects.get_or_create(
        codigo=perfil_codigo,
        defaults={'nombre': perfil_codigo, 'activo': True, **flags},
    )
    return Usuario.objects.create_user(
        codigo_usuario=codigo, password='SrniTest2026!', email=f'{codigo}@uariv.test',
        nombre_completo=codigo, perfil=perfil, activo=True,
    )


class EquiposTests(APITestCase):
    def setUp(self):
        self.coordinador = usuario(
            'COORD1', 'COORDINADOR',
            puede_ver_reportes=True, puede_caracterizar=False)
        self.supervisor = usuario('SUPER1', 'SUPERVISOR', puede_caracterizar=False)
        self.otro_supervisor = usuario('SUPER2', 'SUPERVISOR2', puede_caracterizar=False)
        self.enc1 = usuario('ENC1', 'ENCUESTADOR', puede_caracterizar=True)
        self.enc2 = usuario('ENC2', 'ENCUESTADOR')
        self.enc3 = usuario('ENC3', 'ENCUESTADOR')

        self.equipo = Equipo.objects.create(nombre='Bogotá 1', supervisor=self.supervisor)
        self.otro = Equipo.objects.create(nombre='Bogotá 2', supervisor=self.otro_supervisor)

    def _asignar(self, equipo, usuarios, como):
        self.client.force_authenticate(como)
        return self.client.post(
            f'/api/equipos/{equipo.id}/miembros/',
            {'usuarios': [str(u.id) for u in usuarios]}, format='json',
        )

    # ── Armar el equipo ──────────────────────────────────────────────────────

    def test_el_supervisor_arma_su_equipo(self):
        r = self._asignar(self.equipo, [self.enc1, self.enc2], self.supervisor)

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['total_encuestadores'], 2)

    def test_el_coordinador_tambien_puede_asignar(self):
        r = self._asignar(self.equipo, [self.enc1], self.coordinador)

        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_un_supervisor_no_toca_el_equipo_de_otro(self):
        r = self._asignar(self.otro, [self.enc1], self.supervisor)

        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND,
                         'el equipo ajeno ni siquiera debería ser visible')

    def test_un_encuestador_no_arma_equipos(self):
        r = self._asignar(self.equipo, [self.enc2], self.enc1)

        self.assertIn(r.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_el_supervisor_no_se_supervisa_a_si_mismo(self):
        r = self._asignar(self.equipo, [self.supervisor], self.coordinador)

        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Una sola pertenencia a la vez, con historia ──────────────────────────

    def test_mover_a_otro_equipo_cierra_la_pertenencia_anterior(self):
        self._asignar(self.equipo, [self.enc1], self.coordinador)

        self._asignar(self.otro, [self.enc1], self.coordinador)

        activas = MiembroEquipo.objects.filter(usuario=self.enc1, hasta__isnull=True)
        self.assertEqual(activas.count(), 1)
        self.assertEqual(activas.first().equipo, self.otro)
        # La anterior NO se borra: es la historia de quién respondía por esa persona.
        cerrada = MiembroEquipo.objects.get(usuario=self.enc1, equipo=self.equipo)
        self.assertEqual(cerrada.hasta, timezone.localdate())

    def test_asignar_dos_veces_al_mismo_equipo_no_duplica(self):
        self._asignar(self.equipo, [self.enc1], self.coordinador)
        r = self._asignar(self.equipo, [self.enc1], self.coordinador)

        self.assertEqual(r.data['total_encuestadores'], 1)
        self.assertEqual(MiembroEquipo.objects.filter(usuario=self.enc1).count(), 1)

    def test_quitar_del_equipo_no_borra_la_historia(self):
        self._asignar(self.equipo, [self.enc1], self.supervisor)

        self.client.force_authenticate(self.supervisor)
        r = self.client.delete(f'/api/equipos/{self.equipo.id}/miembros/{self.enc1.id}/')

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['total_encuestadores'], 0)
        self.assertEqual(MiembroEquipo.objects.filter(usuario=self.enc1).count(), 1)
        self.assertIsNotNone(MiembroEquipo.objects.get(usuario=self.enc1).hasta)

    # ── Qué ve cada quien ────────────────────────────────────────────────────

    def test_el_supervisor_solo_ve_su_equipo(self):
        self.client.force_authenticate(self.supervisor)

        r = self.client.get('/api/equipos/')

        nombres = [e['nombre'] for e in r.data['results']] if 'results' in r.data else \
            [e['nombre'] for e in r.data]
        self.assertEqual(nombres, ['Bogotá 1'])

    def test_el_coordinador_ve_los_equipos(self):
        self.client.force_authenticate(self.coordinador)

        r = self.client.get('/api/equipos/')

        datos = r.data['results'] if 'results' in r.data else r.data
        self.assertEqual(len(datos), 2)

    def test_mio_devuelve_el_equipo_del_supervisor_con_su_gente(self):
        self._asignar(self.equipo, [self.enc1, self.enc2], self.supervisor)
        self.client.force_authenticate(self.supervisor)

        r = self.client.get('/api/equipos/mio/')

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r.data['encuestadores']), 2)

    def test_mio_avisa_cuando_no_tiene_equipo(self):
        self.client.force_authenticate(self.coordinador)

        r = self.client.get('/api/equipos/mio/')

        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_sin_equipo_lista_a_quien_falta_asignar(self):
        self._asignar(self.equipo, [self.enc1], self.coordinador)
        self.client.force_authenticate(self.coordinador)

        r = self.client.get('/api/equipos/sin-equipo/')

        codigos = [u['codigo_usuario'] for u in r.data]
        self.assertNotIn('ENC1', codigos)
        self.assertIn('ENC2', codigos)

    # ── Quién encabeza ───────────────────────────────────────────────────────

    def test_un_encuestador_no_puede_encabezar_un_equipo(self):
        self.client.force_authenticate(self.coordinador)

        r = self.client.post('/api/equipos/', {
            'nombre': 'Equipo malo', 'supervisor': str(self.enc1.id),
        }, format='json')

        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('supervisor', r.data)

    def test_el_equipo_se_desactiva_en_vez_de_borrarse(self):
        self.client.force_authenticate(self.coordinador)

        r = self.client.delete(f'/api/equipos/{self.equipo.id}/')

        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.equipo.refresh_from_db()
        self.assertFalse(self.equipo.activo)
        self.assertTrue(Equipo.objects.filter(pk=self.equipo.pk).exists())


class AlcanceDeEquipoTests(APITestCase):
    """El tercer alcance: «lo de mi equipo», entre «lo mío» y «todo el país»."""

    def setUp(self):
        self.supervisor = usuario('SUPX', 'SUPERVISORX', puede_caracterizar=False)
        self.enc = usuario('ENCX', 'ENCUESTADORX', puede_caracterizar=True)
        self.ajeno = usuario('AJENO', 'ENCUESTADORY', puede_caracterizar=True)
        self.equipo = Equipo.objects.create(nombre='Equipo X', supervisor=self.supervisor)
        MiembroEquipo.objects.create(equipo=self.equipo, usuario=self.enc)

    def test_el_supervisor_alcanza_a_los_suyos_y_a_si_mismo(self):
        from apps.autenticacion.views_equipos import usuarios_visibles_para

        codigos = set(usuarios_visibles_para(self.supervisor).values_list(
            'codigo_usuario', flat=True))

        self.assertEqual(codigos, {'SUPX', 'ENCX'})

    def test_un_encuestador_solo_se_alcanza_a_si_mismo(self):
        from apps.autenticacion.views_equipos import usuarios_visibles_para

        codigos = set(usuarios_visibles_para(self.enc).values_list(
            'codigo_usuario', flat=True))

        self.assertEqual(codigos, {'ENCX'})

    def test_quien_sale_del_equipo_deja_de_alcanzarse(self):
        from apps.autenticacion.views_equipos import usuarios_visibles_para
        MiembroEquipo.objects.filter(usuario=self.enc).update(hasta=timezone.localdate())

        codigos = set(usuarios_visibles_para(self.supervisor).values_list(
            'codigo_usuario', flat=True))

        self.assertEqual(codigos, {'SUPX'})
