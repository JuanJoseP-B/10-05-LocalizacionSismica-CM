import { calcularRi, amplitudPredicha } from './model';

/** Predicciones A'_zi para vector m = [x0,y0,z0,A0] */
export function predecirAmplitudes(stations, m) {
  const [x0, y0, z0, A0] = m;
  return stations.map((s) => {
    const R = calcularRi(s.x, s.y, s.z, x0, y0, z0);
    return amplitudPredicha(R, A0);
  });
}

/**
 * Jacobiano analítico G (M × 4) — Derivadas parciales exactas.
 *
 * Definiciones base:
 *   R_i  = sqrt((x_i - x_0)² + (y_i - y_0)² + (z_i - z_0)²)
 *   A_zi = A_0 · exp(-R_i) / R_i
 *
 * Columnas: [∂A/∂x₀, ∂A/∂y₀, ∂A/∂z₀, ∂A/∂A₀]
 *
 *   ∂A/∂A₀  = exp(-R_i) / R_i
 *   ∂A/∂R_i = -A_0 · exp(-R_i) · (R_i + 1) / R_i²
 *   ∂R/∂x₀  = -(x_i - x_0) / R_i
 *
 *   ∂A/∂x₀  = A_0 · exp(-R_i) · (R_i + 1) / R_i³ · (x_i - x_0)
 *   ∂A/∂y₀  = A_0 · exp(-R_i) · (R_i + 1) / R_i³ · (y_i - y_0)
 *   ∂A/∂z₀  = A_0 · exp(-R_i) · (R_i + 1) / R_i³ · (z_i - z_0)
 */
export function calcularJacobiano(stations, m) {
  const [x0, y0, z0, A0] = m;
  const M = stations.length;
  const G = Array.from({ length: M }, () => [0, 0, 0, 0]);
  const A_pred = [];

  for (let i = 0; i < M; i += 1) {
    const s = stations[i];
    const R = calcularRi(s.x, s.y, s.z, x0, y0, z0);
    const expR = Math.exp(-R);

    // Amplitud predicha para esta estación
    A_pred.push(A0 * expR / R);

    // Factor común para las derivadas espaciales:
    // A_0 · exp(-R_i) · (R_i + 1) / R_i³
    const spatialFactor = A0 * expR * (R + 1) / (R * R * R);

    // Columna 1 (j=0): ∂A/∂x₀
    G[i][0] = spatialFactor * (s.x - x0);

    // Columna 2 (j=1): ∂A/∂y₀
    G[i][1] = spatialFactor * (s.y - y0);

    // Columna 3 (j=2): ∂A/∂z₀
    G[i][2] = spatialFactor * (s.z - z0);

    // Columna 4 (j=3): ∂A/∂A₀ = exp(-R_i) / R_i
    G[i][3] = expR / R;
  }

  return { G, A_pred };
}
