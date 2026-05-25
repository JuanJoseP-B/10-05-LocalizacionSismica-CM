import React, { createContext, useContext, useReducer, useEffect, useCallback, useRef } from 'react';
import { buildStationGrid } from '../constants/stations';
import { simularEstaciones } from '../math/model';
import { buildNetworkChartData } from '../math/errorFunction';
import { inversionGaussNewton } from '../math/gaussNewton';
import { checkBackendStatus, syncSimulation, startVideoJob, getVideoJobStatus, getVideoDownloadUrl } from '../services/api';
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
      return { ...state, params, ...computed, inversion: null, inversionHistory: [] };
    }
    case 'RESIMULATE':
      return { ...state, ...recompute(state) };
    case 'INVERSION_START':
      return { ...state, inversionRunning: true };
    case 'INVERSION_DONE':
      return {
        ...state,
        inversionRunning: false,
        inversion: action.inversion,
        inversionHistory: action.history,
      };
    case 'INVERSION_FAIL':
      return { ...state, inversionRunning: false };
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

  const runInversion = useCallback(() => {
    dispatch({ type: 'INVERSION_START' });
    window.setTimeout(() => {
      try {
        const observaciones = state.sensors.map((s) => s.lecturaAzi);
        const result = inversionGaussNewton(baseStations, observaciones);
        dispatch({ type: 'INVERSION_DONE', inversion: result, history: result.history });
      } catch {
        dispatch({ type: 'INVERSION_FAIL' });
      }
    }, 0);
  }, [state.sensors]);

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
