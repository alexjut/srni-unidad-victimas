/**
 * Sprint 19 — Pantalla de ubicación de atención.
 *
 * Aparece después de crear la sesión y ANTES de entrar al formulario.
 * Recoge los 4 valores que el APK original tenía como capítulo "INFORMACIÓN
 * GENERAL" (Dirección Territorial → Depto → Municipio + Punto de Atención).
 *
 * Cascada UARIV:
 *   DT (21 fijas)  →  Departamento(s) de esa DT
 *                  →  Punto(s) de atención de esa DT
 *   Departamento   →  Municipios de ese depto
 *
 * Una vez los 4 elegidos, hace PATCH /api/encuestas/{id}/ con los IDs y
 * redirige al hub del hogar (donde el encuestador entra al formulario).
 *
 * Si el dispositivo está offline al abrir la pantalla, las listas no se
 * pueden cargar; en ese caso se muestra error y se puede dejar la sesión
 * sin ubicación (la sesión se crea igual; el dato se completa después).
 */
import { useEffect, useState } from 'react';
import { View, StyleSheet, Pressable, Modal, ScrollView, Alert, FlatList } from 'react-native';
import { Text, ActivityIndicator } from 'react-native-paper';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { GovHeader } from '../../../src/components/GovHeader';
import { encuestasApi } from '../../../src/api/encuestas';
import {
  parametricasCacheado,
  type DireccionTerritorial,
  type Departamento,
  type Municipio,
  type PuntoAtencion,
} from '../../../src/api/parametricas';
import { GOV, SPACING, RADIUS, SHADOW, FONT } from '../../../src/theme/govTheme';

// ── Selector reusable estilo bottom-sheet ──────────────────────────────────

interface SelectorProps<T extends { id: number; nombre: string }> {
  label: string;
  placeholder: string;
  valor: T | null;
  opciones: T[];
  cargando: boolean;
  habilitado: boolean;
  icono: string;
  onChange: (v: T) => void;
}

function Selector<T extends { id: number; nombre: string }>({
  label, placeholder, valor, opciones, cargando, habilitado, icono, onChange,
}: SelectorProps<T>) {
  const [visible, setVisible] = useState(false);

  return (
    <View style={styles.campo}>
      <Pressable
        onPress={() => habilitado && setVisible(true)}
        disabled={!habilitado || cargando}
        style={({ pressed }) => [
          styles.selectTrigger,
          !habilitado && styles.selectTriggerDisabled,
          pressed && habilitado && { opacity: 0.85 },
        ]}
        accessibilityRole="combobox"
        accessibilityLabel={`${label}: ${valor?.nombre ?? placeholder}`}
      >
        <View style={styles.selectIconoWrap}>
          <MaterialCommunityIcons name={icono as any} size={20} color={habilitado ? GOV.azul : GOV.textoT} />
        </View>
        <View style={styles.selectTextos}>
          <Text style={styles.selectLabel}>{label}</Text>
          <Text
            style={[styles.selectValor, !valor && styles.selectValorPlaceholder]}
            numberOfLines={2}
          >
            {valor?.nombre ?? placeholder}
          </Text>
        </View>
        {cargando ? (
          <ActivityIndicator size={18} color={GOV.azul} />
        ) : (
          <MaterialCommunityIcons name="chevron-down" size={22} color={GOV.textoT} />
        )}
      </Pressable>

      <Modal
        visible={visible}
        transparent
        animationType="slide"
        onRequestClose={() => setVisible(false)}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setVisible(false)}>
          <Pressable style={styles.modalCard} onPress={(e) => e.stopPropagation()}>
            <View style={styles.modalHandle} />
            <Text style={styles.modalTitulo}>{label}</Text>
            <FlatList
              data={opciones}
              keyExtractor={(item) => String(item.id)}
              renderItem={({ item }) => {
                const activo = valor?.id === item.id;
                return (
                  <Pressable
                    onPress={() => { onChange(item); setVisible(false); }}
                    style={({ pressed }) => [
                      styles.modalOpcion,
                      activo && styles.modalOpcionActiva,
                      pressed && { opacity: 0.85 },
                    ]}
                  >
                    <Text style={[styles.modalOpcionNombre, activo && styles.modalOpcionNombreActivo]}>
                      {item.nombre}
                    </Text>
                    {activo && (
                      <MaterialCommunityIcons name="check-circle" size={22} color={GOV.azul} />
                    )}
                  </Pressable>
                );
              }}
              ListEmptyComponent={
                <Text style={styles.modalVacio}>No hay opciones disponibles.</Text>
              }
              style={{ maxHeight: 420 }}
            />
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

// ── Pantalla ────────────────────────────────────────────────────────────────

export default function UbicacionAtencionScreen() {
  const { sesionId, hogarId, instrumentoCodigo } = useLocalSearchParams<{
    sesionId: string; hogarId: string; instrumentoCodigo?: string;
  }>();

  const [direcciones, setDirecciones] = useState<DireccionTerritorial[]>([]);
  const [departamentos, setDepartamentos] = useState<Departamento[]>([]);
  const [municipios, setMunicipios] = useState<Municipio[]>([]);
  const [puntos, setPuntos] = useState<PuntoAtencion[]>([]);

  const [dt, setDt] = useState<DireccionTerritorial | null>(null);
  const [depto, setDepto] = useState<Departamento | null>(null);
  const [muni, setMuni] = useState<Municipio | null>(null);
  const [punto, setPunto] = useState<PuntoAtencion | null>(null);

  const [cargandoDT, setCargandoDT] = useState(true);
  const [cargandoDeptos, setCargandoDeptos] = useState(false);
  const [cargandoMuni, setCargandoMuni] = useState(false);
  const [cargandoPuntos, setCargandoPuntos] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [errorRed, setErrorRed] = useState<string | null>(null);

  const esNoPresencial = dt?.codigo === 'DT_NO_PRESENCIAL';

  // 1) Cargar las 21 DTs al abrir
  useEffect(() => {
    parametricasCacheado
      .getDirecciones()
      .then(setDirecciones)
      .catch(() => setErrorRed(
        'No se pudieron cargar las Direcciones Territoriales. Verifica tu conexión y vuelve a intentarlo.',
      ))
      .finally(() => setCargandoDT(false));
  }, []);

  // 2) Cuando elige DT → cargar deptos y puntos en paralelo
  useEffect(() => {
    if (!dt) {
      setDepartamentos([]); setDepto(null);
      setPuntos([]); setPunto(null);
      setMunicipios([]); setMuni(null);
      return;
    }
    setCargandoDeptos(true);
    setCargandoPuntos(true);
    setDepto(null); setMuni(null); setPunto(null);
    setMunicipios([]); setDepartamentos([]); setPuntos([]);

    parametricasCacheado.getDeptosPorDT(dt.id)
      .then(setDepartamentos)
      .catch(() => {})
      .finally(() => setCargandoDeptos(false));
    parametricasCacheado.getPuntosPorDT(dt.id)
      .then(setPuntos)
      .catch(() => {})
      .finally(() => setCargandoPuntos(false));
  }, [dt]);

  // 3) Cuando elige depto → cargar municipios
  useEffect(() => {
    if (!depto) { setMunicipios([]); setMuni(null); return; }
    setCargandoMuni(true); setMuni(null);
    parametricasCacheado.getMunicipiosPorDepto(depto.id)
      .then(setMunicipios)
      .catch(() => {})
      .finally(() => setCargandoMuni(false));
  }, [depto]);

  const completo = esNoPresencial
    ? !!(dt && punto)
    : !!(dt && depto && muni && punto);

  async function guardar() {
    if (!completo || !sesionId) return;
    setGuardando(true);
    try {
      await encuestasApi.actualizar(sesionId, {
        direccion_territorial: dt!.id,
        departamento_atencion: depto?.id ?? null,
        municipio_atencion: muni?.id ?? null,
        punto_atencion: punto!.id,
      });

      router.replace({
        pathname: '/(main)/hogares/[hogarId]/caracterizaciones',
        params: { hogarId: hogarId ?? '' },
      });
    } catch (err: any) {
      const detalle = err?.response?.data?.detail
        ?? (err?.response?.data && JSON.stringify(err.response.data).slice(0, 200))
        ?? 'No se pudo guardar la ubicación.';
      Alert.alert('Error', detalle);
      setGuardando(false);
    }
  }

  function omitir() {
    // Permite saltarse este paso (ej: sin red). La sesión queda sin ubicación
    // y se podrá completar después desde el detalle de sesión.
    Alert.alert(
      'Omitir ubicación',
      'Podrás completar la Dirección Territorial más tarde. ¿Continuar al formulario sin guardarla?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Omitir',
          style: 'destructive',
          onPress: () => router.replace({
            pathname: '/(main)/hogares/[hogarId]/caracterizaciones',
            params: { hogarId: hogarId ?? '' },
          }),
        },
      ],
    );
  }

  if (cargandoDT) {
    return (
      <View style={styles.root}>
        <GovHeader title="Ubicación de atención" subtitle="Cargando…" onBack={() => router.back()} />
        <View style={styles.centrado}><ActivityIndicator size="large" color={GOV.azul} /></View>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <GovHeader
        title="Ubicación de atención"
        subtitle={instrumentoCodigo ? `Sesión · ${instrumentoCodigo}` : 'Información general'}
        onBack={() => router.back()}
      />

      <View style={styles.miga}>
        <Text style={styles.migaTxt}>Caracterizar  ›  Hogar  ›  Ubicación</Text>
      </View>

      <ScrollView contentContainerStyle={styles.contenido} keyboardShouldPersistTaps="handled">
        <Text style={styles.intro}>
          ¿Dónde se realizará esta caracterización? Estos datos identifican el punto de atención
          donde el encuestador atiende al hogar.
        </Text>

        {errorRed && (
          <View style={styles.banner}>
            <MaterialCommunityIcons name="alert-circle-outline" size={20} color={GOV.rojo} />
            <Text style={styles.bannerTxt}>{errorRed}</Text>
          </View>
        )}

        <Selector<DireccionTerritorial>
          label="1. Dirección Territorial"
          placeholder="Seleccionar…"
          valor={dt}
          opciones={direcciones}
          cargando={false}
          habilitado={direcciones.length > 0}
          icono="map-marker-radius"
          onChange={setDt}
        />

        {!esNoPresencial && (
          <Selector<Departamento>
            label="2. Departamento de atención"
            placeholder={dt ? 'Seleccionar…' : 'Primero elige la Dirección Territorial'}
            valor={depto}
            opciones={departamentos}
            cargando={cargandoDeptos}
            habilitado={!!dt && departamentos.length > 0}
            icono="map-outline"
            onChange={setDepto}
          />
        )}

        {!esNoPresencial && (
          <Selector<Municipio>
            label="3. Municipio de atención"
            placeholder={depto ? 'Seleccionar…' : 'Primero elige el Departamento'}
            valor={muni}
            opciones={municipios}
            cargando={cargandoMuni}
            habilitado={!!depto && municipios.length > 0}
            icono="city-variant-outline"
            onChange={setMuni}
          />
        )}

        <Selector<PuntoAtencion>
          label={esNoPresencial ? '2. Punto de atención' : '4. Punto de atención'}
          placeholder={dt ? 'Seleccionar…' : 'Primero elige la Dirección Territorial'}
          valor={punto}
          opciones={puntos}
          cargando={cargandoPuntos}
          habilitado={!!dt && puntos.length > 0}
          icono="office-building-marker-outline"
          onChange={setPunto}
        />

        <View style={styles.botones}>
          <Pressable
            onPress={guardar}
            disabled={!completo || guardando}
            style={({ pressed }) => [
              styles.btnPrincipal,
              (!completo || guardando) && styles.btnPrincipalDisabled,
              pressed && completo && { opacity: 0.88 },
            ]}
          >
            {guardando
              ? <ActivityIndicator color="#FFF" size={18} />
              : <>
                  <Text style={styles.btnTxt}>Continuar al formulario</Text>
                  <MaterialCommunityIcons name="arrow-right" size={18} color="#FFF" />
                </>
            }
          </Pressable>

          <Pressable onPress={omitir} disabled={guardando} style={styles.btnSecundario}>
            <Text style={styles.btnSecundarioTxt}>Omitir por ahora</Text>
          </Pressable>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: GOV.fondoApp },
  centrado: { flex: 1, justifyContent: 'center', alignItems: 'center' },

  miga: {
    backgroundColor: GOV.azulTenue,
    paddingHorizontal: SPACING.md,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: GOV.borde,
  },
  migaTxt: { ...FONT.caption, color: GOV.azulOscuro },

  contenido: {
    padding: SPACING.md,
    gap: SPACING.md,
  },

  intro: {
    ...FONT.body,
    color: GOV.textoP,
    lineHeight: 20,
  },

  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    backgroundColor: '#FEE2E2',
    borderRadius: RADIUS.sm,
    padding: SPACING.sm,
    borderWidth: 1,
    borderColor: '#FCA5A5',
  },
  bannerTxt: { ...FONT.caption, color: GOV.rojo, flex: 1 },

  campo: {},

  selectTrigger: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: GOV.superficie,
    borderRadius: RADIUS.md,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm + 2,
    borderWidth: 1,
    borderColor: GOV.borde,
    ...SHADOW.card,
  },
  selectTriggerDisabled: { opacity: 0.55 },
  selectIconoWrap: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: GOV.azulTenue,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SPACING.sm,
  },
  selectTextos: { flex: 1 },
  selectLabel: { ...FONT.caption, color: GOV.textoT, marginBottom: 2 },
  selectValor: { ...FONT.body, fontWeight: '600', color: GOV.textoP },
  selectValorPlaceholder: { color: GOV.textoT, fontWeight: '400', fontStyle: 'italic' },

  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: GOV.superficie,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: SPACING.md,
    paddingTop: SPACING.sm,
    paddingBottom: SPACING.lg,
  },
  modalHandle: {
    alignSelf: 'center',
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: GOV.borde,
    marginBottom: SPACING.sm,
  },
  modalTitulo: { ...FONT.h3, color: GOV.textoP, marginBottom: SPACING.sm },
  modalOpcion: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: SPACING.sm,
    paddingHorizontal: SPACING.sm,
    borderRadius: RADIUS.sm,
    gap: SPACING.sm,
  },
  modalOpcionActiva: { backgroundColor: GOV.azulTenue },
  modalOpcionNombre: { ...FONT.body, color: GOV.textoP, flex: 1 },
  modalOpcionNombreActivo: { color: GOV.azulOscuro, fontWeight: '700' },
  modalVacio: { ...FONT.caption, color: GOV.textoT, textAlign: 'center', padding: SPACING.md },

  botones: {
    marginTop: SPACING.md,
    gap: SPACING.sm,
  },
  btnPrincipal: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: GOV.azul,
    borderRadius: RADIUS.md,
    paddingVertical: 14,
    gap: SPACING.sm,
  },
  btnPrincipalDisabled: { backgroundColor: GOV.borde },
  btnTxt: { color: '#FFF', fontSize: 15, fontWeight: '700' },
  btnSecundario: {
    alignItems: 'center',
    paddingVertical: 12,
  },
  btnSecundarioTxt: { ...FONT.caption, color: GOV.azul, fontWeight: '600' },
});
