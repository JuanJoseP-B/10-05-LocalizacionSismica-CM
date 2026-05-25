import { calcularRi, amplitudPredicha } from './model';

/** E_rr = sum_i (A_zi - A'_zi)^2 */
export function calcularErrorGlobal(stations, observaciones, m) {
  const [x0, y0, z0, A0] = m;
  let total = 0;

  for (let i = 0; i < stations.length; i += 1) {
    const s = stations[i];
    const R = calcularRi(s.x, s.y, s.z, x0, y0, z0);
    const pred = amplitudPredicha(R, A0);
    const diff = observaciones[i] - pred;
    total += diff * diff;
  }

  return total;
}

/** Datos para gráfica de error en red (log10 para amplitudes pequeñas) */
export function buildNetworkChartData(sensors) {
  const pick = (idx) => {
    const s = sensors[idx];
    if (!s) return 0;
    return s.error > 0 ? s.error : Math.log10(Math.max(Math.abs(s.lecturaAzi), 1e-40));
  };

  return sensors.map((s, i) => ({
    id: s.id,
    label: s.name,
    distancia: s.distance,
    amplitud: s.lecturaAzi,
    logAmp: Math.log10(Math.max(Math.abs(s.lecturaAzi), 1e-40)),
    error: s.error,
    est1: pick(0),
    est5: pick(4),
    est9: pick(8),
    energiaRMS: Math.sqrt(
      sensors.reduce((acc, item) => acc + item.error ** 2, 0) / sensors.length
    ),
    index: i,
  }));
}
