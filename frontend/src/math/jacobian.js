import { calcularRi, amplitudPredicha } from './model';

const DELTA = 1e-4;

/** Predicciones A'_zi para vector m = [x0,y0,z0,A0] */
export function predecirAmplitudes(stations, m) {
  const [x0, y0, z0, A0] = m;
  return stations.map((s) => {
    const R = calcularRi(s.x, s.y, s.z, x0, y0, z0);
    return amplitudPredicha(R, A0);
  });
}

/** Jacobiano G (M x 4) por diferencias finitas — Ecuación 8 */
export function calcularJacobiano(stations, m, delta = DELTA) {
  const M = stations.length;
  const G = Array.from({ length: M }, () => [0, 0, 0, 0]);
  const base = predecirAmplitudes(stations, m);

  for (let j = 0; j < 4; j += 1) {
    const pert = [...m];
    pert[j] += delta;
    const pertPred = predecirAmplitudes(stations, pert);
    for (let i = 0; i < M; i += 1) {
      G[i][j] = (pertPred[i] - base[i]) / delta;
    }
  }

  return { G, A_pred: base };
}
