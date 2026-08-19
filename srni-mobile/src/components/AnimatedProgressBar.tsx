/**
 * Barra de progreso con animación de llenado.
 * Usa Animated nativo (sin reanimated) para animar de 0 al valor objetivo.
 */
import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View } from 'react-native';
import { GOV } from '../theme/govTheme';

interface Props {
  /** Valor entre 0 y 1. */
  progress: number;
  /** Color de la barra llena. Default: GOV.azul */
  color?: string;
  /** Color del track vacío. Default: borde claro */
  trackColor?: string;
  /** Altura en px. Default: 5 */
  height?: number;
  /** Duración de la animación en ms. Default: 800 */
  duration?: number;
}

export function AnimatedProgressBar({
  progress,
  color = GOV.azul,
  trackColor = GOV.borde + '66',
  height = 5,
  duration = 800,
}: Props) {
  const anim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(anim, {
      toValue: Math.max(0, Math.min(1, progress)),
      duration,
      useNativeDriver: false, // width animation requires JS driver
    }).start();
  }, [progress, duration]);

  const width = anim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%'],
    extrapolate: 'clamp',
  });

  return (
    <View style={[styles.track, { height, borderRadius: height / 2, backgroundColor: trackColor }]}>
      <Animated.View
        style={[
          styles.fill,
          { width, height, borderRadius: height / 2, backgroundColor: color },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    width: '100%',
    overflow: 'hidden',
  },
  fill: {
    position: 'absolute',
    left: 0,
    top: 0,
  },
});
