from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "frontend" / "src" / "components"
COMP.mkdir(parents=True, exist_ok=True)

( COMP / "ControlPanel.jsx" ).write_text(r'''import React from 'react';
import { useSimulation } from '../store/SimulationContext';
import { formatNumber } from '../utils/format';

export default function ControlPanel() {
  const {
    params, setParam, globalError, inversion, inversionRunning,
    backendOnline, video, runInversion, generateVideo, downloadPdf,
  } = useSimulation();

  const sliders = [
    { key: 'x0', label: 'Coordenada X (x₀)', min: -100, max: 100, step: 1 },
    { key: 'y0', label: 'Coordenada Y (y₀)', min: -100, max: 100, step: 1 },
    { key: 'z0', label: 'Profundidad (z₀)', min: 1, max: 200, step: 1 },
    { key: 'A0', label: 'Amplitud (A₀)', min: 0, max: 10000, step: 100 },
    { key: 'alpha', label: 'Ruido Gaussiano (α %)', min: 0, max: 50, step: 1 },
  ];

  return (
    <section className="glass-panel">
      <h2>Parámetros Fuente (m)</h2>
      {sliders.map(({ key, label, min, max, step }) => (
        <motion segment>
          <label><span>{label}</span><span>{params[key]}{key === 'alpha' ? '%' : ''}</span></label>
          <input type="range" min={min} max={max} step={step} value={params[key]} onChange={(e) => setParam(key, e.target.value)} />
        </motion segment>
      ))}
      <motion segment>
        <motion segment>
          <div className="stat-label">Error Residual Total (E_rr)</div>
          <div className="stat-value">{formatNumber(globalError)}</div>
        </motion segment>
        {inversion && (
          <p className="meta-line">
            Estimado: ({formatNumber(inversion.estimated.x0, 1)}, {formatNumber(inversion.estimated.y0, 1)},
            {' '}{formatNumber(inversion.estimated.z0, 1)}) A₀={formatNumber(inversion.estimated.A0, 1)}
          </p>
        )}
        <p className={`meta-line ${backendOnline ? 'online' : 'offline'}`}>
          Backend: {backendOnline ? 'conectado' : 'desconectado (inversión local activa)'}
        </p>
        <button type="button" className="btn btn-primary" onClick={runInversion} disabled={inversionRunning}>
          {inversionRunning ? 'Calculando...' : 'Ejecutar Inversión'}
        </button>
        <button type="button" className="btn btn-video" onClick={generateVideo} disabled={video.status === 'running' || !backendOnline}>
          Generar Video (100 cortes z)
        </button>
        {video.status !== 'idle' && (
          <motion segment>
            <motion segment><div className="progress-fill" style={{ width: `${video.progress}%` }} /></motion segment>
            <span className="progress-text">{video.message || `${video.progress}%`}</span>
          </motion segment>
        )}
        <button type="button" className="btn btn-pdf" onClick={downloadPdf}>Descargar PDF</button>
      </motion segment>
    </section>
  );
}
'''.replace('<motion segment>', '<div className="control-group" key={key}>' if False else '<PLACEHOLDER>'), encoding='utf-8')

print("Use manual write")
