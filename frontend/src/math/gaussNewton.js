import { calcularJacobiano } from './jacobian';

function transpose(A) {
  return A[0].map((_, j) => A.map((row) => row[j]));
}

function matMul(A, B) {
  const rows = A.length;
  const cols = B[0].length;
  const inner = B.length;
  const out = Array.from({ length: rows }, () => Array(cols).fill(0));
  for (let i = 0; i < rows; i += 1) {
    for (let j = 0; j < cols; j += 1) {
      let sum = 0;
      for (let k = 0; k < inner; k += 1) {
        sum += A[i][k] * B[k][j];
      }
      out[i][j] = sum;
    }
  }
  return out;
}

function matVec(A, v) {
  return A.map((row) => row.reduce((acc, val, j) => acc + val * v[j], 0));
}

function invert4x4(M) {
  const n = 4;
  const aug = M.map((row, i) => [...row, ...Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))]);

  for (let col = 0; col < n; col += 1) {
    let pivot = col;
    for (let row = col + 1; row < n; row += 1) {
      if (Math.abs(aug[row][col]) > Math.abs(aug[pivot][col])) pivot = row;
    }
    if (Math.abs(aug[pivot][col]) < 1e-12) {
      aug[col][col] += 1e-6;
    }
    [aug[col], aug[pivot]] = [aug[pivot], aug[col]];

    const div = aug[col][col];
    for (let j = 0; j < 2 * n; j += 1) aug[col][j] /= div;

    for (let row = 0; row < n; row += 1) {
      if (row === col) continue;
      const factor = aug[row][col];
      for (let j = 0; j < 2 * n; j += 1) aug[row][j] -= factor * aug[col][j];
    }
  }

  return aug.map((row) => row.slice(n));
}

function norm(v) {
  return Math.sqrt(v.reduce((acc, x) => acc + x * x, 0));
}

/**
 * Gauss-Newton: Delta_m = (G^T G)^(-1) G^T Delta_Az
 * m^(k+1) = m^k + Delta_m
 */
export function inversionGaussNewton(stations, observaciones, mInicial, options = {}) {
  const { maxIter = 50, tol = 1e-4, lambda = 1e-6 } = options;
  let m = [...mInicial];
  const history = [];

  for (let k = 0; k < maxIter; k += 1) {
    const { G, A_pred } = calcularJacobiano(stations, m);
    const deltaAz = observaciones.map((obs, i) => obs - A_pred[i]);
    const err = deltaAz.reduce((acc, d) => acc + d * d, 0);
    history.push({ iteration: k + 1, error: err, m: [...m] });

    const GT = transpose(G);
    const GTG = matMul(GT, G);
    for (let i = 0; i < 4; i += 1) GTG[i][i] += lambda;

    const inv = invert4x4(GTG);
    const GTdelta = matVec(GT, deltaAz);
    const deltaM = matVec(inv, GTdelta);

    m = m.map((val, j) => val + deltaM[j]);

    if (norm(deltaM) < tol) break;
  }

  return {
    estimated: { x0: m[0], y0: m[1], z0: m[2], A0: m[3] },
    vector: m,
    history,
    residualError: history[history.length - 1]?.error ?? 0,
  };
}
