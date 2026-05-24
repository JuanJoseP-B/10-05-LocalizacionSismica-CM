from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
control = ROOT / 'frontend/src/components/ControlPanel.jsx'

content = """import React from 'react';
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
      <motion segment>
        <motion segment>
          <motion segment>
          <div className="stat-value">{formatNumber(globalError)}</div>
        </motion segment>
        {inversion && (
          <p className="meta-line">
            Estimado: ({formatNumber(inversion.estimated.x0, 1)}, {formatNumber(inversion.estimated.y0, 1)},
            {' '}{formatNumber(inversion.estimated.z0, 1)}) A0={formatNumber(inversion.estimated.A0, 1)}
          </p>
        )}
        <p className={`meta-line ${backendOnline ? 'online' : 'offline'}`}>
          Backend: {backendOnline ? 'conectado' : 'desconectado (inversion local activa)'}
        </p>
        <button type="button" className="btn btn-primary" onClick={runInversion} disabled={inversionRunning}>
          {inversionRunning ? 'Calculando...' : 'Ejecutar Inversion'}
        </button>
        <button type="button" className="btn btn-video" onClick={generateVideo} disabled={video.status === 'running' || !backendOnline}>
          Generar Video (100 cortes z)
        </button>
        {video.status !== 'idle' && (
          <motion segment>
            <motion segment>
              <div className="progress-fill" style={{ width: `${video.progress}%` }} />
            </motion segment>
            <span className="progress-text">{video.message || `${video.progress}%`}</span>
          </motion segment>
        )}
        <button type="button" className="btn btn-pdf" onClick={downloadPdf}>Descargar PDF</button>
      </motion segment>
    </section>
  );
}
"""

replacements = [
    ('<motion segment>\n        <motion segment>\n          <motion segment>', '<div className="stats-box">\n        <div>\n          <motion segment>'),
]
# Use explicit tokens
content = content.replace('MOTION_STATS_BOX', '<div className="stats-box">')
content = content.replace('MOTION_INNER', '<div>')
content = content.replace('MOTION_STAT_LABEL', '<div className="stat-label">Error Residual Total (E_rr)</div>')
content = content.replace('MOTION_CLOSE', '</div>')
content = content.replace('MOTION_VIDEO_WRAP', '<div className="video-progress">')
content = content.replace('MOTION_PROGRESS_BAR', '<div className="progress-bar">')

# Rewrite without any bad tokens - use chr to build 'div'
d = 'd' + 'iv'
open_div = f'<{d}>'
close_div = f'</{d}>'
open_stats = f'<{d} className="stats-box">'
open_cg = f'<{d} className="control-group" key={{key}}>'

control.write_text(f"""import React from 'react';
import {{ useSimulation }} from '../store/SimulationContext';
import {{ formatNumber }} from '../utils/format';

export default function ControlPanel() {{
  const {{
    params, setParam, globalError, inversion, inversionRunning,
    backendOnline, video, runInversion, generateVideo, downloadPdf,
  }} = useSimulation();

  const sliders = [
    {{ key: 'x0', label: 'Coordenada X (x0)', min: -100, max: 100, step: 1 }},
    {{ key: 'y0', label: 'Coordenada Y (y0)', min: -100, max: 100, step: 1 }},
    {{ key: 'z0', label: 'Profundidad (z0)', min: 1, max: 200, step: 1 }},
    {{ key: 'A0', label: 'Amplitud (A0)', min: 0, max: 10000, step: 100 }},
    {{ key: 'alpha', label: 'Ruido Gaussiano (alpha %)', min: 0, max: 50, step: 1 }},
  ];

  return (
    <section className="glass-panel">
      <h2>Parametros Fuente (m)</h2>
      {{sliders.map(({{ key, label, min, max, step }}) => (
        {open_cg}
          <label><span>{{label}}</span><span>{{params[key]}}{{key === 'alpha' ? '%' : ''}}</span></label>
          <input type="range" min={{min}} max={{max}} step={{step}} value={{params[key]}} onChange={{(e) => setParam(key, e.target.value)}} />
        {close_div}
      ))}}
      {open_stats}
        {open_div}
          {open_div.replace('<div>', '<div className="stat-label">Error Residual Total (E_rr)</motion segment>') if False else '<div className="stat-label">Error Residual Total (E_rr)</div>'}
          <div className="stat-value">{{formatNumber(globalError)}}</div>
        {close_div}
        {{inversion && (
          <p className="meta-line">
            Estimado: ({{formatNumber(inversion.estimated.x0, 1)}}, {{formatNumber(inversion.estimated.y0, 1)}},
            {{' '}}{{formatNumber(inversion.estimated.z0, 1)}}) A0={{formatNumber(inversion.estimated.A0, 1)}}
          </p>
        )}}
        <p className={{`meta-line ${{backendOnline ? 'online' : 'offline'}}`}}>
          Backend: {{backendOnline ? 'conectado' : 'desconectado (inversion local activa)'}}
        </p>
        <button type="button" className="btn btn-primary" onClick={{runInversion}} disabled={{inversionRunning}}>
          {{inversionRunning ? 'Calculando...' : 'Ejecutar Inversion'}}
        </button>
        <button type="button" className="btn btn-video" onClick={{generateVideo}} disabled={{video.status === 'running' || !backendOnline}}>
          Generar Video (100 cortes z)
        </button>
        {{video.status !== 'idle' && (
          <div className="video-progress">
            <div className="progress-bar">
              <motion segment>
            </div>
            <span className="progress-text">{{video.message || `${{video.progress}}%`}}</span>
          </div>
        )}}
        <button type="button" className="btn btn-pdf" onClick={{downloadPdf}}>Descargar PDF</button>
      {close_div}
    </section>
  );
}}
""".replace('<motion segment>', '<div className="progress-fill" style={{ width: `${video.progress}%` }} />'), encoding='utf-8')

print('done')
