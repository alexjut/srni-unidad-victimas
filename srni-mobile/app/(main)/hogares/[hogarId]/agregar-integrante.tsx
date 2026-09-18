/**
 * Agregar un integrante al hogar A MITAD de la caracterización.
 *
 * QA, 16-sep-2026: «cuando creamos el hogar y nos salimos por error, o llega una
 * persona del hogar a mitad de la caracterización, no la podemos agregar».
 * El formulario de integrantes solo existía al conformar el hogar; una vez
 * creado no había por dónde volver a él.
 *
 * Se abre desde la lista de capítulos (formulario/index) y vuelve a ella. No
 * hace falta rehacer nada: las preguntas por persona se arman con los miembros
 * que tenga el hogar en cada momento, y el progreso los cuenta. Por eso los
 * capítulos por persona que ya estaban completos vuelven a quedar pendientes:
 * a la persona nueva le faltan sus respuestas.
 */
import { useCallback, useState } from 'react';
import {
  View, ScrollView, StyleSheet, KeyboardAvoidingView, Platform, Alert,
} from 'react-native';
import { Text, Chip } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams, useFocusEffect } from 'expo-router';
import { remontarPorParams } from '../../../../src/navegacion/remontarPorParams';
import { GovHeader } from '../../../../src/components/GovHeader';
import {
  FormularioIntegrante, type IntegranteNuevo,
} from '../../../../src/components/FormularioIntegrante';
import { cargarMiembrosHogar } from '../../../../src/services/miembrosHogar';
import * as hogaresOfflineDao from '../../../../src/db/hogaresOfflineDao';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../../src/theme/govTheme';
import type { MiembroHogarResumen } from '../../../../src/types';

function AgregarIntegranteScreen() {
  const { hogarId, sesionServerId, instrumentoId, borradorId } = useLocalSearchParams<{
    hogarId: string;
    sesionServerId?: string;
    instrumentoId?: string;
    borradorId?: string;
  }>();

  const [miembros, setMiembros] = useState<MiembroHogarResumen[]>([]);
  // Hogar creado sin red y todavía sin subir: su id es local y el alta va a la cola.
  const [hogarEsLocal, setHogarEsLocal] = useState(false);
  const [agregados, setAgregados] = useState<IntegranteNuevo[]>([]);

  useFocusEffect(
    useCallback(() => {
      if (!hogarId) return;
      let activo = true;
      (async () => {
        try {
          const local = await hogaresOfflineDao.obtenerPorIdLocal(hogarId);
          if (activo) setHogarEsLocal(!!local && local.estado_sync !== 'enviado');
        } catch { /* sin fila local: hogar del servidor */ }
        try {
          const ms = await cargarMiembrosHogar(hogarId);
          if (activo) setMiembros(ms);
        } catch { /* la lista queda vacía; el alta igual funciona */ }
      })();
      return () => { activo = false; };
    }, [hogarId]),
  );

  function volverALaEntrevista() {
    router.replace({
      pathname: '/(main)/formulario',
      params: {
        hogarId: String(hogarId),
        ...(sesionServerId ? { sesionServerId } : {}),
        ...(instrumentoId ? { instrumentoId } : {}),
        ...(borradorId ? { borradorId } : {}),
      },
    });
  }

  function alAgregar(nuevo: IntegranteNuevo) {
    setAgregados((prev) => [...prev, nuevo]);
    Alert.alert(
      'Integrante agregado',
      `${nuevo.nombre_display} ya hace parte del hogar`
      + (nuevo.offline ? ' (se enviará al recuperar la señal)' : '')
      + '.\n\nSus preguntas por persona aparecen en los capítulos. Los capítulos '
      + 'por persona que ya estaban completos quedan pendientes hasta completarle '
      + 'sus datos.',
      [
        { text: 'Agregar otro', style: 'cancel' },
        { text: 'Volver a la entrevista', onPress: volverALaEntrevista },
      ],
    );
  }

  const documentosExistentes = [
    ...miembros.map((m) => m.numero_documento ?? ''),
    ...agregados.map((a) => a.numero_documento),
  ].filter(Boolean);

  const total = miembros.length + agregados.length;

  return (
    <View style={styles.root}>
      <GovHeader
        title="Agregar integrante"
        subtitle={`${total} integrante${total !== 1 ? 's' : ''} en el hogar`}
        onBack={volverALaEntrevista}
      />

      <View style={styles.miga}>
        <Text style={styles.migaTxt}>Entrevista  ›  Agregar integrante</Text>
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {hogarEsLocal && (
            <Chip icon="wifi-off" mode="flat" style={styles.offlineBanner} textStyle={styles.offlineBannerTxt}>
              Sin conexión — el integrante se guarda en el teléfono y se sincroniza al recuperar señal
            </Chip>
          )}

          <View style={styles.aviso}>
            <MaterialCommunityIcons name="information-outline" size={18} color={GOV.azulOscuro} />
            <Text style={styles.avisoTxt}>
              Use esto cuando llega una persona del hogar a mitad de la entrevista o
              faltó registrarla. Después complete sus preguntas en los capítulos por persona.
            </Text>
          </View>

          <Text style={styles.secTitulo}>Integrantes actuales ({total})</Text>
          {miembros.map((m) => (
            <View key={m.id} style={styles.fila}>
              <MaterialCommunityIcons
                name={m.es_autorizado ? 'account-star' : 'account'}
                size={18}
                color={GOV.azul}
              />
              <Text style={styles.filaTxt} numberOfLines={1}>
                {m.nombre_completo || 'Sin nombre'}
                {m.es_autorizado ? '  ·  Autorizado' : ''}
              </Text>
            </View>
          ))}
          {agregados.map((a, i) => (
            <View key={`nuevo-${i}`} style={styles.fila}>
              <MaterialCommunityIcons name="account-plus" size={18} color={GOV.verde} />
              <Text style={styles.filaTxt} numberOfLines={1}>
                {a.nombre_display}  ·  {a.offline ? 'nuevo, sin enviar' : 'nuevo'}
              </Text>
            </View>
          ))}

          <Text style={[styles.secTitulo, { marginTop: SPACING.md }]}>Nuevo integrante</Text>
          <FormularioIntegrante
            hogarId={hogarId ?? null}
            hogarEsLocal={hogarEsLocal}
            onAgregado={alAgregar}
            documentosExistentes={documentosExistentes}
            pantalla="hogares/agregar-integrante"
          />
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: GOV.fondoApp },
  miga: {
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  migaTxt: { ...FONT.caption, color: GOV.azulOscuro },
  content: { padding: SPACING.md, paddingBottom: 48 },
  offlineBanner: { marginBottom: SPACING.md, backgroundColor: '#FFF3E0' },
  offlineBannerTxt: { color: '#E65100', fontSize: 12 },
  aviso: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    backgroundColor: GOV.azulTenue,
    borderRadius: RADIUS.sm,
    padding: SPACING.sm,
    marginBottom: SPACING.md,
  },
  avisoTxt: { ...FONT.caption, color: GOV.azulOscuro, flex: 1 },
  secTitulo: {
    ...FONT.label,
    color: GOV.textoT,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: SPACING.sm,
  },
  fila: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.sm,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 10,
    marginBottom: 6,
    ...SHADOW.card,
  },
  filaTxt: { ...FONT.body, color: GOV.textoP, flex: 1 },
});

// Pestaña oculta: sin esto conserva el estado de otro hogar
// (ver src/navegacion/remontarPorParams.tsx).
export default remontarPorParams(AgregarIntegranteScreen, ['hogarId', 'sesionServerId', 'borradorId']);
