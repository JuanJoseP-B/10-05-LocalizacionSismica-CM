import { transpose, multiply, inv, matrix } from 'mathjs';
import { calcularRi } from './model';
import { calcularJacobiano, predecirAmplitudes } from './jacobian';

const DIAG_EPS = 1e-10;
const MAX_PASO_ESPACIAL = 15;
const Z0_SEMILLA = 5;
const A0_MAX_ESTIMADO = 1e7;
const A0_MIN_SEMILLA = 1000;
const MAX_ITER_DEFAULT = 500;

function norm(v) {
  return Math.sqrt(v.reduce((acc, x) => acc + x * x, 0));
}

export function limitesGridEstaciones(stations, marginFrac = 0.2) {
  const xs = stations.map((s) => s.x);
  const ys = stations.map((s) => s.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const mx = (maxX - minX) * marginFrac;
  const my = (maxY - minY) * marginFrac;
  return {
    xMin: minX - mx,
    xMax: maxX + mx,
    yMin: minY - my,
    yMax: maxY + my,
  };
}

export function calcularSemillaInteligente(stations, observaciones) {
  let maxIdx = 0;
  let maxObs = observaciones[0];
  for (let i = 1; i < observaciones.length; i += 1) {
    if (observaciones[i] > maxObs) {
      maxObs = observaciones[i];
      maxIdx = i;
    }
  }

  const peak = stations[maxIdx];
  const x0 = peak.x;
  const y0 = peak.y;
  const z0 = Z0_SEMILLA;

  let A0 = 0;
  for (let i = 0; i < stations.length; i += 1) {
    const s = stations[i];
    const R = calcularRi(s.x, s.y, s.z, x0, y0, z0);
    const est = observaciones[i] * R * Math.exp(R);
    if (Number.isFinite(est) && est > A0) A0 = est;
  }
  if (!Number.isFinite(A0) || A0 <= 0 || A0 > A0_MAX_ESTIMADO) {
    A0 = maxObs * 100;
  }
  if (A0 < A0_MIN_SEMILLA) {
    A0 = A0_MIN_SEMILLA;
  }

  const bounds = limitesGridEstaciones(stations);
  return aplicarDominioFisico([x0, y0, z0, A0], bounds);
}

function errorCuadraticoRelativo(observaciones, predicciones) {
  return observaciones.reduce((acc, obs, i) => {
    const r = (obs - predicciones[i]) / obs;
    return acc + r * r;
  }, 0);
}

function escalarSistemaRelativo(G, deltaAz, observaciones) {
  const GRel = G.map((row, i) => {
    const w = 1 / observaciones[i];
    return row.map((v) => v * w);
  });
  const deltaRel = deltaAz.map((d, i) => d / observaciones[i]);
  return { G: GRel, deltaAz: deltaRel };
}

function aplicarAmortiguamientoDiagonal(gtgArray, lambda) {
  const n = gtgArray.length;
  const damped = gtgArray.map((row) => [...row]);
  for (let i = 0; i < n; i += 1) {
    const d = Math.max(damped[i][i], DIAG_EPS);
    damped[i][i] = d + lambda * d;
  }
  return damped;
}

/** Solo acota Δx, Δy, Δz; ΔA₀ lo dicta LM sin límite porcentual. */
function recortarPasoEspacial(deltaM) {
  return [
    Math.max(-MAX_PASO_ESPACIAL, Math.min(MAX_PASO_ESPACIAL, deltaM[0])),
    Math.max(-MAX_PASO_ESPACIAL, Math.min(MAX_PASO_ESPACIAL, deltaM[1])),
    Math.max(-MAX_PASO_ESPACIAL, Math.min(MAX_PASO_ESPACIAL, deltaM[2])),
    deltaM[3],
  ];
}

function aplicarDominioFisico(m, bounds, mActual = null) {
  let A = m[3];
  if (A <= 0) {
    A = mActual ? mActual[3] * 0.1 : A0_MIN_SEMILLA;
  }
  return [
    Math.max(bounds.xMin, Math.min(bounds.xMax, m[0])),
    Math.max(bounds.yMin, Math.min(bounds.yMax, m[1])),
    Math.max(0.1, m[2]),
    A,
  ];
}

export function inversionGaussNewton(stations, observaciones, options = {}) {
  const {
    maxIter = MAX_ITER_DEFAULT,
    tol = 1e-4,
    lambdaInit = 0.01,
    mInicial: mInicialOpt,
  } = options;

  const bounds = limitesGridEstaciones(stations);
  const mInicial = mInicialOpt
    ? aplicarDominioFisico([...mInicialOpt], bounds)
    : calcularSemillaInteligente(stations, observaciones);

  let m = [...mInicial];
  let lam = lambdaInit;
  const history = [];

  for (let k = 0; k < maxIter; k += 1) {
    const { G, A_pred } = calcularJacobiano(stations, m);
    const deltaAz = observaciones.map((obs, i) => obs - A_pred[i]);
    const err = errorCuadraticoRelativo(observaciones, A_pred);
    history.push({ iteration: k + 1, error: err, m: [...m] });

    const { G: GRel, deltaAz: deltaRel } = escalarSistemaRelativo(G, deltaAz, observaciones);

    const gMatrix = matrix(GRel);
    const gtMatrix = transpose(gMatrix);
    const gtgMatrix = multiply(gtMatrix, gMatrix);
    const gtgDamped = matrix(aplicarAmortiguamientoDiagonal(gtgMatrix.toArray(), lam));

    const invGtg = inv(gtgDamped);
    const gtDelta = multiply(gtMatrix, deltaRel);
    const deltaM = recortarPasoEspacial(multiply(invGtg, gtDelta).toArray());

    if (k === 0) {
      const peakIdx = observaciones.indexOf(Math.max(...observaciones));
      console.log('=== AUDITORÍA INVERSIÓN (Primera Iteración) ===');
      console.log('Estación pico:', stations[peakIdx]?.name);
      console.log('Semilla m^0:', mInicial);
      console.log('Δ_m (espacial recortado, A libre):', deltaM);
      console.log('==============================================');
    }

    const mCandidate = aplicarDominioFisico(
      m.map((val, j) => val + deltaM[j]),
      bounds,
      m,
    );

    const predCandidate = predecirAmplitudes(stations, mCandidate);
    const errCandidate = errorCuadraticoRelativo(observaciones, predCandidate);

    if (errCandidate < err) {
      m = mCandidate;
      lam = Math.max(lam / 10, 1e-10);
    } else {
      lam *= 10;
    }

    if (norm(deltaM) < tol) break;
  }

  const finalPred = predecirAmplitudes(stations, m);
  const finalError = errorCuadraticoRelativo(observaciones, finalPred);

  return {
    estimated: { x0: m[0], y0: m[1], z0: m[2], A0: m[3] },
    vector: m,
    initialSeed: mInicial,
    history,
    residualError: finalError,
  };
}
