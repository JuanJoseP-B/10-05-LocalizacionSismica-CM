import React, { createContext, useContext, useReducer, useEffect, useCallback, useRef } from 'react';
import { buildStationGrid } from '../constants/stations';
import { simularEstaciones } from '../math/model';
import { buildNetworkChartData } from '../math/errorFunction';
import { inversionGaussNewton } from '../math/gaussNewton';
import {
  checkBackendStatus, syncSimulation, startVideoJob, getVideoJobStatus,
  getVideoDownloadUrl, fetchErrorMinimoZ,
} from '../services/api';
import { calcularCurvaErrorMinimoZ } from '../math/eMinCurve';
import { generatePdfReport } from '../services/pdfExport';

const baseStations = buildStationGrid();

const initialState = {
  params: { x0: 10, y0: -15, z0: 30, A0: 5000, alpha: 5 },
  sensors: baseStations.map((s) => ({
    ...s, distance: 0, aPred: 0, lecturaAzi: 0, epsilon: 0, error: 0, signalLevel: 0, status: 'idle',
  })),
  globalError: 0,
  networkChart: [],
  inversion: null,
  inversionHistory: [],
  inversionRunning: false,
  eMinCurve: [],
  eMinCurveLoading: false,
  backendOnline: false,
  video: { status: 'idle', progress: 0, message: '' },
};

function recompute(state) {
  const sensors = simularEstaciones(baseStations, state.params);
  const globalError = sensors.reduce((acc, s) => acc + s.error ** 2, 0);
  const networkChart = buildNetworkChartData(sensors);
  return { sensors, globalError, networkChart };
}

function reducer(state, action) {
  switch (action.type) {
    case 'SET_PARAM': {
      const params = { ...state.params, [action.key]: action.value };
      const computed = recompute({ ...state, params });
      return {
        ...state, params, ...computed, inversion: null, inversionHistory: [], eMinCurve: [],
      };
    }
    case 'RESIMULATE':
      return { ...state, ...recompute(state) };
    case 'INVERSION_START':
      return { ...state, inversionRunning: true, eMinCurveLoading: true };
    case 'INVERSION_DONE':
      return {
        ...state,
        inversionRunning: false,
        inversion: action.inversion,
        inversionHistory: action.history,
        eMinCurve: action.eMinCurve ?? state.eMinCurve,
        eMinCurveLoading: false,
      };
    case 'INVERSION_FAIL':
      return { ...state, inversionRunning: false, eMinCurveLoading: false };
    case 'SET_EMIN_CURVE':
      return { ...state, eMinCurve: action.curve, eMinCurveLoading: false };
    case 'SET_BACKEND':
      return { ...state, backendOnline: action.online };
    case 'VIDEO_UPDATE':
      return { ...state, video: { ...state.video, ...action.payload } };
    default:
      return state;
  }
}

const SimulationContext = createContext(null);

export function SimulationProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState, (s) => ({ ...s, ...recompute(s) }));
  const videoPollRef = useRef(null);

  useEffect(() => {
    checkBackendStatus().then((online) => dispatch({ type: 'SET_BACKEND', online }));
  }, []);

  useEffect(() => {
    if (state.params.alpha <= 0 || state.params.A0 <= 0) return undefined;
    const id = setInterval(() => dispatch({ type: 'RESIMULATE' }), 3000);
    return () => clearInterval(id);
  }, [state.params.alpha, state.params.A0, state.params.x0, state.params.y0, state.params.z0]);

  const setParam = useCallback((key, value) => {
    dispatch({ type: 'SET_PARAM', key, value: parseFloat(value) });
  }, []);

  const loadEMinCurve = useCallback(async (A0) => {
    const observaciones = state.sensors.map((s) => s.lecturaAzi);
    const payload = { a0: A0, z_min: 1, z_max: 200, num_cuts: 50, grid_size: 40 };

    if (state.backendOnline) {
      await syncSimulation({
        stations: state.sensors.map((s) => [s.x, s.y, s.z]),
        x: state.params.x0,
        y: state.params.y0,
        z: state.params.z0,
        a0: state.params.A0,
        alpha: state.params.alpha,
        amplitudes: observaciones,
      });
      const data = await fetchErrorMinimoZ(payload);
      return data.curva_error_minimo ?? [];
    }

    return calcularCurvaErrorMinimoZ(baseStations, observaciones, A0, {
      zMin: 1, zMax: 200, numCuts: 40, gridSize: 18,
    });
  }, [state.sensors, state.params, state.backendOnline]);

  const runInversion = useCallback(() => {
    dispatch({ type: 'INVERSION_START' });
    window.setTimeout(async () => {
      try {
        const observaciones = state.sensors.map((s) => s.lecturaAzi);
        const result = inversionGaussNewton(baseStations, observaciones);
        const a0Curve = result.estimated?.A0 ?? state.params.A0;
        let eMinCurve = [];
        try {
          eMinCurve = await loadEMinCurve(a0Curve);
        } catch {
          eMinCurve = calcularCurvaErrorMinimoZ(baseStations, observaciones, a0Curve, {
            zMin: 1, zMax: 200, numCuts: 40, gridSize: 18,
          });
        }
        dispatch({
          type: 'INVERSION_DONE',
          inversion: result,
          history: result.history,
          eMinCurve,
        });
      } catch {
        dispatch({ type: 'INVERSION_FAIL' });
      }
    }, 0);
  }, [state.sensors, state.params.A0, loadEMinCurve]);

  const downloadPdf = useCallback(() => {
    generatePdfReport({
      params: state.params,
      sensors: state.sensors,
      globalError: state.globalError,
      inversion: state.inversion,
    });
  }, [state]);

  const generateVideo = useCallback(async () => {
    if (!state.backendOnline) {
      dispatch({ type: 'VIDEO_UPDATE', payload: { status: 'error', message: 'Backend no disponible' } });
      return;
    }

    dispatch({ type: 'VIDEO_UPDATE', payload: { status: 'running', progress: 0, message: 'Iniciando...' } });

    try {
      await syncSimulation({
        stations: state.sensors.map((s) => [s.x, s.y, s.z]),
        x: state.params.x0,
        y: state.params.y0,
        z: state.params.z0,
        a0: state.params.A0,
        alpha: state.params.alpha,
        amplitudes: state.sensors.map((s) => s.lecturaAzi),
      });

      const { job_id: jobId } = await startVideoJob({
        z_min: 1,
        z_max: 200,
        num_cuts: 100,
        a0: state.params.A0,
      });

      if (videoPollRef.current) clearInterval(videoPollRef.current);

      videoPollRef.current = setInterval(async () => {
        try {
          const status = await getVideoJobStatus(jobId);
          dispatch({
            type: 'VIDEO_UPDATE',
            payload: { status: status.state, progress: status.progress, message: status.message },
          });

          if (status.state === 'done') {
            clearInterval(videoPollRef.current);
            if (status.curva_error_minimo?.length) {
              dispatch({ type: 'SET_EMIN_CURVE', curve: status.curva_error_minimo });
            }
            const a = document.createElement('a');
            a.href = getVideoDownloadUrl(jobId);
            a.download = 'cortes_z.mp4';
            a.click();
          }
          if (status.state === 'error') clearInterval(videoPollRef.current);
        } catch (err) {
          clearInterval(videoPollRef.current);
          dispatch({ type: 'VIDEO_UPDATE', payload: { status: 'error', message: err.message } });
        }
      }, 800);
    } catch (e) {
      dispatch({ type: 'VIDEO_UPDATE', payload: { status: 'error', message: e.message } });
    }
  }, [state]);

  useEffect(() => () => {
    if (videoPollRef.current) clearInterval(videoPollRef.current);
  }, []);

  const value = {
    ...state,
    baseStations,
    setParam,
    runInversion,
    downloadPdf,
    generateVideo,
  };

  return (
    <SimulationContext.Provider value={value}>
      {children}
    </SimulationContext.Provider>
  );
}

export function useSimulation() {
  const ctx = useContext(SimulationContext);
  if (!ctx) throw new Error('useSimulation debe usarse dentro de SimulationProvider');
  return ctx;
}
