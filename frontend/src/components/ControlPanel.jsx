import React from 'react';
import { useSimulation } from '../store/SimulationContext';
import { formatNumber } from '../utils/format';

export default function ControlPanel() {
  const {
    params, setParam, globalError, inversion, inversionRunning,
    backendOnline, video, runInversion, generateVideo, downloadPdf,
  } = useSimulation();

  const sliders = [
    { key: 'x0', label: 'Coordenada X (x0)', min: -100, max: 100, step: 1 },
    { key: 'y0', label: 'Coordenada Y (y0)', min: -100, max: 100, step: 1 },
    { key: 'z0', label: 'Profundidad (z0)', min: 1, max: 200, step: 1 },
    { key: 'A0', label: 'Amplitud (A0)', min: 0, max: 10000, step: 100 },
    { key: 'alpha', label: 'Ruido Gaussiano (alpha %)', min: 0, max: 50, step: 1 },
  ];

  return (
    <section className="glass-panel">
      <h2>Parametros Fuente (m)</h2>
      {sliders.map(({ key, label, min, max, step }) => (
        <div className="control-group" key={key}>
          <label><span>{label}</span><span>{params[key]}{key === 'alpha' ? '%' : ''}</span></label>
          <input type="range" min={min} max={max} step={step} value={params[key]} onChange={(e) => setParam(key, e.target.value)} />
        </div>
      ))}
      <div className="stats-box">
        <div>
          <div className="stat-label">Error Residual Total (E_rr)</div>
          <div className="stat-value">{formatNumber(globalError)}</div>
        </div>
        {inversion && (
          <p className="meta-line">
            Estimado: ({formatNumber(inversion.estimated.x0, 1)}, {formatNumber(inversion.estimated.y0, 1)},
            {' '}{formatNumber(inversion.estimated.z0, 1)}) A0={formatNumber(inversion.estimated.A0, 1)}
          </p>
        )}
        <p className={`meta-line ${backendOnline ? 'online' : 'offline'}`}>
          Backend: {backendOnline ? 'conectado' : 'desconectado'}
        </p>
        <button type="button" className="btn btn-primary" onClick={runInversion} disabled={inversionRunning}>
          {inversionRunning ? 'Calculando...' : 'Ejecutar Inversion'}
        </button>
        <button type="button" className="btn btn-video" onClick={generateVideo} disabled={video.status === 'running' || !backendOnline}>
          Generar Video (100 cortes z)
        </button>
        {video.status !== 'idle' && (
          <div className="video-progress">
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${video.progress}%` }} />
            </div>
            <span className="progress-text">{video.message || `${video.progress}%`}</span>
          </div>
        )}
        <button type="button" className="btn btn-pdf" onClick={downloadPdf}>Descargar PDF</button>
      </div>
    </section>
  );
}
