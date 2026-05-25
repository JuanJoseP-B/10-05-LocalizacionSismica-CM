import { calcularRi } from './model';

const GRID_MIN = -70;
const GRID_MAX = 70;

function errorRelativoEnPunto(stations, observaciones, m) {
  const [x0, y0, z0, A0] = m;
  let sum = 0;
  for (let i = 0; i < stations.length; i += 1) {
    const s = stations[i];
    const R = calcularRi(s.x, s.y, s.z, x0, y0, z0);
    const aCalc = A0 * Math.exp(-R) / R;
    const obs = observaciones[i];
    const denom = Math.max(Math.abs(obs), 1e-30);
    let rel = (obs - aCalc) / denom;
    rel = Math.max(-50, Math.min(50, rel));
    sum += rel * rel;
  }
  return sum;
}

/**
 * E_min(z) en el cliente (respaldo si el backend no está disponible).
 */
export function calcularCurvaErrorMinimoZ(
  stations,
  observaciones,
  A0,
  { zMin = 1, zMax = 200, numCuts = 40, gridSize = 20 } = {},
) {
  const curva = [];
  const step = (GRID_MAX - GRID_MIN) / Math.max(gridSize - 1, 1);

  for (let k = 0; k < numCuts; k += 1) {
    const z = zMin + ((zMax - zMin) * k) / Math.max(numCuts - 1, 1);
    let errMin = Infinity;

    for (let gi = 0; gi < gridSize; gi += 1) {
      const x = GRID_MIN + gi * step;
      for (let gj = 0; gj < gridSize; gj += 1) {
        const y = GRID_MIN + gj * step;
        const err = errorRelativoEnPunto(stations, observaciones, [x, y, z, A0]);
        if (err < errMin) errMin = err;
      }
    }

    curva.push({ z, error: Number.isFinite(errMin) ? errMin : 0 });
  }

  return curva;
}

export function encontrarMinimoCurva(curva) {
  if (!curva?.length) return null;
  return curva.reduce((best, p) => (p.error < best.error ? p : best), curva[0]);
}
