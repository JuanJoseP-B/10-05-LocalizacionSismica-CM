/** Ecuación 2: distancia euclidiana R_i */
export function calcularRi(x, y, z, x0, y0, z0) {
  const R = Math.sqrt((x - x0) ** 2 + (y - y0) ** 2 + (z - z0) ** 2);
  return Math.max(R, 1e-9);
}

/** A'_zi = A0 * exp(-R_i) / R_i (sin ruido) */
export function amplitudPredicha(R, A0) {
  if (A0 <= 0) return 0;
  return A0 * (Math.exp(-R) / R);
}

/** Ruido gaussiano N(0, sigma) */
export function muestrearRuido(sigma) {
  if (sigma <= 0) return 0;
  const u1 = Math.max(Math.random(), 1e-12);
  const u2 = Math.random();
  return sigma * Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

/**
 * Ecuación 1: A_zi = A0 * exp(-R_i)/R_i + epsilon_i
 * sigma = alpha * A0 * exp(-R_i)/R_i  (alpha en [0,1] desde slider %)
 */
export function simularEstaciones(stations, params) {
  const { x0, y0, z0, A0, alpha } = params;
  const alphaDecimal = alpha / 100;

  const lecturas = stations.map((s) => {
    const R = calcularRi(s.x, s.y, s.z, x0, y0, z0);
    const aPred = amplitudPredicha(R, A0);
    const sigma = alphaDecimal > 0 && A0 > 0 ? alphaDecimal * aPred : 0;
    const epsilon = muestrearRuido(sigma);
    const A_zi = aPred + epsilon;

    return {
      ...s,
      distance: R,
      aPred,
      lecturaAzi: A_zi,
      epsilon,
      error: Math.abs(epsilon),
    };
  });

  const maxPred = Math.max(...lecturas.map((s) => s.aPred), 0);

  return lecturas.map((s) => {
    const signalLevel = A0 > 0 && maxPred > 0 ? (s.aPred / maxPred) * 100 : 0;
    let status = 'idle';
    if (A0 > 0) {
      status = s.aPred > 0 ? 'active' : 'sin_senal';
    }

    return { ...s, signalLevel, status };
  });
}

export function colorSensorPorSenal(signalLevel, status) {
  if (status === 'idle') {
    return { color: 0x64748b, emissive: 0x000000, emissiveIntensity: 0 };
  }
  if (status === 'sin_senal') {
    return { color: 0xef4444, emissive: 0xef4444, emissiveIntensity: 0.35 };
  }

  const t = Math.min(Math.max(signalLevel / 100, 0), 1);
  const r = Math.round(34 + t * (245 - 34));
  const g = Math.round(197 + t * (158 - 197));
  const b = Math.round(94 + t * (11 - 94));
  const hex = (r << 16) | (g << 8) | b;
  return { color: hex, emissive: hex, emissiveIntensity: 0.15 + t * 0.55 };
}
