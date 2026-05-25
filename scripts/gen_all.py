from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "frontend" / "src" / "components"
COMP.mkdir(parents=True, exist_ok=True)

def tag(name, cls=None):
    if cls:
        return f'<{name} className="{cls}">'
    return f'<{name}>'

def close(name):
    return f'</{name}>'

D = 'div'

def write_components():
    control = f"""import React from 'react';
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
        {tag(D, 'control-group')}
          <label><span>{{label}}</span><span>{{params[key]}}{{key === 'alpha' ? '%' : ''}}</span></label>
          <input type="range" min={{min}} max={{max}} step={{step}} value={{params[key]}} onChange={{(e) => setParam(key, e.target.value)}} />
        {close(D)}
      ))}}
      {tag(D, 'stats-box')}
        {tag(D)}
          {tag(D, 'stat-label')}Error Residual Total (E_rr){close(D)}
          {tag(D, 'stat-value')}{{formatNumber(globalError)}}{close(D)}
        {close(D)}
        {{inversion && (
          <p className="meta-line">
            Estimado: ({{formatNumber(inversion.estimated.x0, 1)}}, {{formatNumber(inversion.estimated.y0, 1)}},
            {{' '}}{{formatNumber(inversion.estimated.z0, 1)}}) A0={{formatNumber(inversion.estimated.A0, 1)}}
          </p>
        )}}
        <p className={{`meta-line ${{backendOnline ? 'online' : 'offline'}}`}}>
          Backend: {{backendOnline ? 'conectado' : 'desconectado'}}
        </p>
        <button type="button" className="btn btn-primary" onClick={{runInversion}} disabled={{inversionRunning}}>
          {{inversionRunning ? 'Calculando...' : 'Ejecutar Inversion'}}
        </button>
        <button type="button" className="btn btn-video" onClick={{generateVideo}} disabled={{video.status === 'running' || !backendOnline}}>
          Generar Video (100 cortes z)
        </button>
        {{video.status !== 'idle' && (
          {tag(D, 'video-progress')}
            {tag(D, 'progress-bar')}
              <div className="progress-fill" style={{{{ width: `${{video.progress}}%` }}}} />
            {close(D)}
            <span className="progress-text">{{video.message || `${{video.progress}}%`}}</span>
          {close(D)}
        )}}
        <button type="button" className="btn btn-pdf" onClick={{downloadPdf}}>Descargar PDF</button>
      {close(D)}
    </section>
  );
}}
"""
    (COMP / "ControlPanel.jsx").write_text(control, encoding='utf-8')

    sensors = f"""import React from 'react';
import {{ useSimulation }} from '../store/SimulationContext';
import {{ STATUS_LABELS }} from '../constants/stations';
import {{ formatNumber, formatPercent }} from '../utils/format';

export default function SensorPanel() {{
  const {{ sensors }} = useSimulation();

  return (
    <section className="glass-panel sensor-panel">
      <h2>Analisis de Estaciones (Az)</h2>
      {tag(D, 'sensors-list')}
        {{sensors.map((sensor) => (
          <div className={{\`sensor-card ${{sensor.status === 'sin_senal' ? 'alarm' : ''}}\`}}>
            {tag(D, 'sensor-header')}
              <span>{{sensor.name}}</span>
              {tag(D, 'status-indicator')}
            {close(D)}
            {tag(D, 'sensor-stats')}
              {tag(D, 'stat-row')}<span>Estado:</span><strong>{{STATUS_LABELS[sensor.status]}}</strong>{close(D)}
              {tag(D, 'stat-row')}<span>Distancia R:</span><span>{{sensor.distance.toFixed(2)}} m</span>{close(D)}
              {tag(D, 'stat-row')}<span>Intensidad:</span><span>{{formatPercent(sensor.signalLevel)}}</span>{close(D)}
              {tag(D, 'stat-row')}<span>Amplitud A_zi:</span><span>{{formatNumber(sensor.lecturaAzi)}}</span>{close(D)}
              {tag(D, 'stat-row')}<span>Error epsilon:</span><span>{{formatNumber(sensor.error)}}</span>{close(D)}
            {close(D)}
          {close(D)}
        ))}}
      {close(D)}
    </section>
  );
}}
"""
    # fix typo in sensors template
    sensors = sensors.replace("tag(DName='stat-row'", "tag(D, 'stat-row'")
    sensors = sensors.replace("'sensor-card' + ' ${sensor.status", "`sensor-card ${sensor.status")
    (COMP / "SensorPanel.jsx").write_text(sensors, encoding='utf-8')

    charts = """import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area,
} from 'recharts';
import { useSimulation } from '../store/SimulationContext';
import { formatNumber } from '../utils/format';

export default function ChartsPanel() {
  const { networkChart, inversionHistory, params } = useSimulation();

  const errorChartData = networkChart.map((row) => ({
    id: row.id,
    name: row.label,
    error: row.error,
    logAmp: row.logAmp,
    distancia: row.distancia,
  }));

  const convergenceData = inversionHistory.length
    ? inversionHistory.map((h) => ({ iteration: h.iteration, error: h.error }))
    : networkChart.map((row) => ({ iteration: row.id, error: row.error || Math.abs(row.logAmp) }));

  return (
    <div className="graphs-container">
      <div className="glass-panel chart-card">
        <h3>Error por Estacion (epsilon) / log10(A_zi)</h3>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={errorChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} angle={-20} textAnchor="end" height={50} />
            <YAxis stroke="#94a3b8" fontSize={10} tickFormatter={(v) => formatNumber(v, 2)} />
            <Tooltip formatter={(v) => formatNumber(v)} />
            <Line type="monotone" dataKey="error" stroke="#38bdf8" strokeWidth={2} dot />
            <Line type="monotone" dataKey="logAmp" stroke="#f59e0b" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="glass-panel chart-card">
        <h3>{inversionHistory.length ? 'Convergencia Gauss-Newton (E_rr)' : 'RMS Energia Global'}</h3>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={convergenceData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="iteration" stroke="#94a3b8" fontSize={10} />
            <YAxis stroke="#94a3b8" fontSize={10} tickFormatter={(v) => formatNumber(v, 2)} />
            <Tooltip formatter={(v) => formatNumber(v)} />
            <Area type="monotone" dataKey="error" stroke="#a855f7" fill="#a855f7" fillOpacity={0.25} />
          </AreaChart>
        </ResponsiveContainer>
        {params.A0 === 0 && <p className="chart-hint">Sube A0 para ver amplitudes en la red.</p>}
      </div>
    </div>
  );
}
"""
    (COMP / "ChartsPanel.jsx").write_text(charts, encoding='utf-8')

    scene = """import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { useSimulation } from '../store/SimulationContext';
import { colorSensorPorSenal } from '../math/model';

export default function Scene3D() {
  const { params, sensors } = useSimulation();
  const canvasRef = useRef(null);
  const sensorMeshesRef = useRef([]);
  const sourceMeshRef = useRef(null);
  const pulseMeshRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return undefined;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, canvasRef.current.clientWidth / canvasRef.current.clientHeight, 0.1, 1000);
    camera.position.set(0, 90, 110);
    const renderer = new THREE.WebGLRenderer({ canvas: canvasRef.current, antialias: true, alpha: true });
    renderer.setSize(canvasRef.current.clientWidth, canvasRef.current.clientHeight);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.maxPolarAngle = Math.PI / 2 - 0.05;
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const light = new THREE.PointLight(0xffffff, 1.2);
    light.position.set(100, 120, 100);
    scene.add(light);
    scene.add(new THREE.GridHelper(150, 15, 0x38bdf8, 0x1e293b));

    const sensorGeo = new THREE.SphereGeometry(2.5, 16, 16);
    sensorMeshesRef.current = sensors.map((s) => {
      const mat = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.2 });
      const mesh = new THREE.Mesh(sensorGeo, mat);
      mesh.position.set(s.x, 0, s.y);
      scene.add(mesh);
      return { id: s.id, mesh, mat };
    });

    const sourceGeo = new THREE.SphereGeometry(4, 32, 32);
    const sourceMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, emissive: 0xf59e0b, emissiveIntensity: 0.8 });
    const sourceMesh = new THREE.Mesh(sourceGeo, sourceMat);
    sourceMesh.position.set(params.x0, -params.z0, params.y0);
    scene.add(sourceMesh);
    sourceMeshRef.current = sourceMesh;

    const pulseGeo = new THREE.SphereGeometry(Math.max(params.A0 / 250, 0.5), 32, 32);
    const pulseMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, transparent: true, opacity: 0.15, wireframe: true });
    const pulseMesh = new THREE.Mesh(pulseGeo, pulseMat);
    pulseMesh.position.set(params.x0, -params.z0, params.y0);
    scene.add(pulseMesh);
    pulseMeshRef.current = pulseMesh;

    let frameId;
    const clock = new THREE.Clock();
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      controls.update();
      const scale = 1 + Math.sin(clock.getElapsedTime() * 5) * 0.15;
      pulseMesh.scale.set(scale, scale, scale);
      renderer.render(scene, camera);
    };
    animate();

    const onResize = () => {
      if (!canvasRef.current) return;
      camera.aspect = canvasRef.current.clientWidth / canvasRef.current.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(canvasRef.current.clientWidth, canvasRef.current.clientHeight);
    };
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', onResize);
      controls.dispose();
      renderer.dispose();
      sensorGeo.dispose();
      sourceGeo.dispose();
      pulseGeo.dispose();
    };
  }, []);

  useEffect(() => {
    if (sourceMeshRef.current) {
      sourceMeshRef.current.position.set(params.x0, -params.z0, params.y0);
      sourceMeshRef.current.visible = params.A0 > 0;
    }
    if (pulseMeshRef.current) {
      pulseMeshRef.current.position.set(params.x0, -params.z0, params.y0);
      pulseMeshRef.current.visible = params.A0 > 0;
    }
  }, [params.x0, params.y0, params.z0, params.A0]);

  useEffect(() => {
    sensorMeshesRef.current.forEach((item) => {
      const data = sensors.find((s) => s.id === item.id);
      if (!data) return;
      const { color, emissive, emissiveIntensity } = colorSensorPorSenal(data.signalLevel, data.status);
      item.mat.color.setHex(color);
      item.mat.emissive.setHex(emissive);
      item.mat.emissiveIntensity = emissiveIntensity;
    });
  }, [sensors]);

  return (
    <motion segment>
      <canvas ref={canvasRef} className="scene-canvas" />
      <div className="scene-overlay">
        Simulacion 3D: Sismo y Sensores<br />
        <span>Color = intensidad relativa A_zi (Ecuacion 1)</span>
      </div>
    </motion segment>
  );
}
"""
    scene = scene.replace('motion segment', 'motion segment').replace('<motion segment>', '<div className="glass-panel wave-canvas">').replace('</motion segment>', '</div>')
    scene = scene.replace('<motion segment>', '<div className="glass-panel wave-canvas">').replace('</motion segment>', '</div>')
    # fix scene - use tag()
    scene = scene.replace('<motion segment>', '<div className="glass-panel wave-canvas">').replace('</motion segment>', '</motion segment>')
    scene = """import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { useSimulation } from '../store/SimulationContext';
import { colorSensorPorSenal } from '../math/model';

export default function Scene3D() {
  const { params, sensors } = useSimulation();
  const canvasRef = useRef(null);
  const sensorMeshesRef = useRef([]);
  const sourceMeshRef = useRef(null);
  const pulseMeshRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return undefined;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, canvasRef.current.clientWidth / canvasRef.current.clientHeight, 0.1, 1000);
    camera.position.set(0, 90, 110);
    const renderer = new THREE.WebGLRenderer({ canvas: canvasRef.current, antialias: true, alpha: true });
    renderer.setSize(canvasRef.current.clientWidth, canvasRef.current.clientHeight);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.maxPolarAngle = Math.PI / 2 - 0.05;
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const light = new THREE.PointLight(0xffffff, 1.2);
    light.position.set(100, 120, 100);
    scene.add(light);
    scene.add(new THREE.GridHelper(150, 15, 0x38bdf8, 0x1e293b));

    const sensorGeo = new THREE.SphereGeometry(2.5, 16, 16);
    sensorMeshesRef.current = sensors.map((s) => {
      const mat = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.2 });
      const mesh = new THREE.Mesh(sensorGeo, mat);
      mesh.position.set(s.x, 0, s.y);
      scene.add(mesh);
      return { id: s.id, mesh, mat };
    });

    const sourceGeo = new THREE.SphereGeometry(4, 32, 32);
    const sourceMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, emissive: 0xf59e0b, emissiveIntensity: 0.8 });
    const sourceMesh = new THREE.Mesh(sourceGeo, sourceMat);
    sourceMesh.position.set(params.x0, -params.z0, params.y0);
    scene.add(sourceMesh);
    sourceMeshRef.current = sourceMesh;

    const pulseGeo = new THREE.SphereGeometry(Math.max(params.A0 / 250, 0.5), 32, 32);
    const pulseMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, transparent: true, opacity: 0.15, wireframe: true });
    const pulseMesh = new THREE.Mesh(pulseGeo, pulseMat);
    pulseMesh.position.set(params.x0, -params.z0, params.y0);
    scene.add(pulseMesh);
    pulseMeshRef.current = pulseMesh;

    let frameId;
    const clock = new THREE.Clock();
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      controls.update();
      const scale = 1 + Math.sin(clock.getElapsedTime() * 5) * 0.15;
      pulseMesh.scale.set(scale, scale, scale);
      renderer.render(scene, camera);
    };
    animate();

    const onResize = () => {
      if (!canvasRef.current) return;
      camera.aspect = canvasRef.current.clientWidth / canvasRef.current.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(canvasRef.current.clientWidth, canvasRef.current.clientHeight);
    };
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', onResize);
      controls.dispose();
      renderer.dispose();
      sensorGeo.dispose();
      sourceGeo.dispose();
      pulseGeo.dispose();
    };
  }, []);

  useEffect(() => {
    if (sourceMeshRef.current) {
      sourceMeshRef.current.position.set(params.x0, -params.z0, params.y0);
      sourceMeshRef.current.visible = params.A0 > 0;
    }
    if (pulseMeshRef.current) {
      pulseMeshRef.current.position.set(params.x0, -params.z0, params.y0);
      pulseMeshRef.current.visible = params.A0 > 0;
    }
  }, [params.x0, params.y0, params.z0, params.A0]);

  useEffect(() => {
    sensorMeshesRef.current.forEach((item) => {
      const data = sensors.find((s) => s.id === item.id);
      if (!data) return;
      const { color, emissive, emissiveIntensity } = colorSensorPorSenal(data.signalLevel, data.status);
      item.mat.color.setHex(color);
      item.mat.emissive.setHex(emissive);
      item.mat.emissiveIntensity = emissiveIntensity;
    });
  }, [sensors]);

  return (
    <div className="glass-panel wave-canvas">
      <canvas ref={canvasRef} className="scene-canvas" />
      <div className="scene-overlay">
        Simulacion 3D: Sismo y Sensores<br />
        <span>Color = intensidad relativa A_zi (Ecuacion 1)</span>
      </div>
    </div>
  );
}
"""
    (COMP / "Scene3D.jsx").write_text(scene, encoding='utf-8')

    app = """import React from 'react';
import { SimulationProvider } from './store/SimulationContext';
import ControlPanel from './components/ControlPanel';
import Scene3D from './components/Scene3D';
import ChartsPanel from './components/ChartsPanel';
import SensorPanel from './components/SensorPanel';
import './App.css';

export default function App() {
  return (
    <SimulationProvider>
      <main className="app-container">
        <ControlPanel />
        <section className="visualization-center">
          <Scene3D />
          <ChartsPanel />
        </section>
        <SensorPanel />
      </main>
    </SimulationProvider>
  );
}
"""
    (ROOT / "frontend/src/App.jsx").write_text(app, encoding='utf-8')

    main = """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
"""
    (ROOT / "frontend/src/main.jsx").write_text(main, encoding='utf-8')

write_components()
print('Generated all components')
