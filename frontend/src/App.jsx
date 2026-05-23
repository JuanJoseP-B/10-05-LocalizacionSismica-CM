import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import jsPDF from 'jspdf';
import 'jspdf-autotable';
import './App.css';

// 9 Estaciones en la superficie (z=0) organizadas en una cuadrícula 3x3
const initialSensors = Array.from({ length: 9 }, (_, i) => {
  const row = Math.floor(i / 3);
  const col = i % 3;
  return {
    id: i + 1,
    name: `Estación ${i + 1}`,
    x: (col - 1) * 50, 
    y: (row - 1) * 50,
    z: 0,
    dataTraffic: Math.random() * 40 + 20, // Mbps
    error: 0,
    energyDirection: Math.floor(Math.random() * 360)
  };
});

function App() {
  const [params, setParams] = useState({
    x0: 10,
    y0: -15,
    z0: 30, // Profundidad
    A0: 5000, // Amplitud original
    alpha: 5 // Ruido Gaussiano (%)
  });

  const [sensors, setSensors] = useState(initialSensors);
  const [chartData, setChartData] = useState([]);
  const [globalError, setGlobalError] = useState(0);

  const canvasRef = useRef(null);
  const sceneRef = useRef(null);
  const sourceMeshRef = useRef(null);
  const pulseMeshRef = useRef(null);
  const sensorMeshesRef = useRef([]);

  // 1. Efecto para inicializar Three.js
  useEffect(() => {
    if (!canvasRef.current) return;

    // Escena
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    // Cámara
    const camera = new THREE.PerspectiveCamera(
      45, 
      canvasRef.current.clientWidth / canvasRef.current.clientHeight, 
      0.1, 
      1000
    );
    camera.position.set(0, 90, 110);

    // Renderizador
    const renderer = new THREE.WebGLRenderer({ 
      canvas: canvasRef.current, 
      antialias: true, 
      alpha: true 
    });
    renderer.setSize(canvasRef.current.clientWidth, canvasRef.current.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Controles de Cámara (OrbitControls)
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.maxPolarAngle = Math.PI / 2 - 0.05; // Evita ir por debajo del plano terrestre

    // Iluminación
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0xffffff, 1.2);
    pointLight.position.set(100, 120, 100);
    scene.add(pointLight);

    // Malla de Superficie (z = 0)
    const gridHelper = new THREE.GridHelper(150, 15, 0x38bdf8, 0x1e293b);
    gridHelper.position.y = 0;
    scene.add(gridHelper);

    // Estaciones (Sensores)
    const sensorGeo = new THREE.SphereGeometry(2.5, 16, 16);
    const meshes = sensors.map(s => {
      const mat = new THREE.MeshStandardMaterial({
        color: s.dataTraffic > 80 ? 0xef4444 : 0x22c55e,
        emissive: s.dataTraffic > 80 ? 0xef4444 : 0x000000,
        emissiveIntensity: s.dataTraffic > 80 ? 0.8 : 0,
        roughness: 0.2
      });
      const mesh = new THREE.Mesh(sensorGeo, mat);
      mesh.position.set(s.x, 0, s.y); // Usamos XZ para la superficie terrestre en 3D
      scene.add(mesh);
      return { id: s.id, mesh, mat };
    });
    sensorMeshesRef.current = meshes;

    // Fuente Sísmica (Y es la profundidad negativa en Three.js)
    const sourceGeo = new THREE.SphereGeometry(4, 32, 32);
    const sourceMat = new THREE.MeshStandardMaterial({ 
      color: 0xf59e0b, 
      emissive: 0xf59e0b, 
      emissiveIntensity: 0.8,
      roughness: 0.1
    });
    const sourceMesh = new THREE.Mesh(sourceGeo, sourceMat);
    sourceMesh.position.set(params.x0, -params.z0, params.y0);
    scene.add(sourceMesh);
    sourceMeshRef.current = sourceMesh;

    // Onda Sísmica (Esfera Wireframe pulsante)
    const pulseGeo = new THREE.SphereGeometry(params.A0 / 250, 32, 32);
    const pulseMat = new THREE.MeshBasicMaterial({ 
      color: 0xf59e0b, 
      transparent: true, 
      opacity: 0.15, 
      wireframe: true 
    });
    const pulseMesh = new THREE.Mesh(pulseGeo, pulseMat);
    pulseMesh.position.set(params.x0, -params.z0, params.y0);
    scene.add(pulseMesh);
    pulseMeshRef.current = pulseMesh;

    // Bucle de Animación
    let animationFrameId;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      
      // Actualizar amortiguación de controles
      controls.update();

      // Efecto pulsante de la onda sísmica
      const elapsed = clock.getElapsedTime();
      const scale = 1 + Math.sin(elapsed * 5) * 0.15;
      pulseMesh.scale.set(scale, scale, scale);

      renderer.render(scene, camera);
    };
    animate();

    // Redimensionado del canvas
    const handleResize = () => {
      if (!canvasRef.current) return;
      camera.aspect = canvasRef.current.clientWidth / canvasRef.current.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(canvasRef.current.clientWidth, canvasRef.current.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      controls.dispose();
      renderer.dispose();
      sensorGeo.dispose();
      sourceGeo.dispose();
      pulseGeo.dispose();
    };
  }, []);

  // 2. Efecto para actualizar posiciones de sismo y onda
  useEffect(() => {
    if (sourceMeshRef.current) {
      sourceMeshRef.current.position.set(params.x0, -params.z0, params.y0);
    }
    if (pulseMeshRef.current) {
      pulseMeshRef.current.position.set(params.x0, -params.z0, params.y0);
      // Re-crear geometría del pulso al cambiar la Amplitud (A0)
      pulseMeshRef.current.geometry.dispose();
      pulseMeshRef.current.geometry = new THREE.SphereGeometry(params.A0 / 250, 32, 32);
    }
  }, [params.x0, params.y0, params.z0, params.A0]);

  // 3. Efecto para actualizar colores de estaciones según alarma
  useEffect(() => {
    sensorMeshesRef.current.forEach(item => {
      const sensorData = sensors.find(s => s.id === item.id);
      if (sensorData) {
        const isAlarm = sensorData.dataTraffic > 80;
        item.mat.color.setHex(isAlarm ? 0xef4444 : 0x22c55e);
        item.mat.emissive.setHex(isAlarm ? 0xef4444 : 0x000000);
        item.mat.emissiveIntensity = isAlarm ? 0.8 : 0;
      }
    });
  }, [sensors]);

  // 4. Efecto de actualización de datos matemáticos e historial
  useEffect(() => {
    const generateData = () => {
      const data = [];
      let currentGlobalError = 0;
      
      const updatedSensors = sensors.map(s => {
        const R_i = Math.sqrt(Math.pow(s.x - params.x0, 2) + Math.pow(s.y - params.y0, 2) + Math.pow(s.z - params.z0, 2));
        const A_ideal = params.A0 * (Math.exp(-R_i / 100) / (R_i || 1)); 
        
        const sigma = (params.alpha / 100) * A_ideal;
        const epsilon = (Math.random() * 2 - 1) * sigma * 2; 
        
        const A_zi = A_ideal + epsilon;
        const errorCuadratico = Math.pow(A_zi - A_ideal, 2);
        currentGlobalError += errorCuadratico;
        
        let newTraffic = s.dataTraffic + (Math.random() * 10 - 5);
        if (Math.random() > 0.95) newTraffic = 85 + Math.random() * 15;

        return {
          ...s,
          error: Math.sqrt(errorCuadratico),
          dataTraffic: Math.max(0, Math.min(100, newTraffic)),
          lecturaAzi: A_zi
        };
      });
      
      setSensors(updatedSensors);
      setGlobalError(currentGlobalError);

      for(let i=0; i<30; i++) {
        data.push({
          time: i,
          est1: updatedSensors[0].error * Math.random(),
          est5: updatedSensors[4].error * Math.random(),
          est9: updatedSensors[8].error * Math.random(),
          energiaRMS: Math.sqrt(currentGlobalError / 9) * (Math.sin(i/5) * 0.5 + 1)
        });
      }
      return data;
    };
    
    setChartData(generateData());

    const interval = setInterval(() => {
      setChartData(generateData());
    }, 2000);

    return () => clearInterval(interval);
  }, [params]);

  const handleParamChange = (e) => {
    setParams({
      ...params,
      [e.target.name]: parseFloat(e.target.value)
    });
  };

  const exportReport = () => {
    const doc = new jsPDF();
    
    // Título y Metadatos
    doc.setFontSize(18);
    doc.text("Reporte de Localización Sísmica - Datos Simulados", 14, 22);
    doc.setFontSize(11);
    doc.text(`Fecha de Simulación: ${new Date().toLocaleString()}`, 14, 30);
    doc.text(`Error Residual Total (Err): ${globalError.toFixed(4)}`, 14, 36);

    // Parámetros Fuente (La Solución del Problema Inverso)
    doc.setFontSize(14);
    doc.text("Parámetros de la Fuente (Solución Oculta a Estimar)", 14, 48);
    doc.autoTable({
      startY: 52,
      head: [['X (x0)', 'Y (y0)', 'Z (z0)', 'Amplitud (A0)', 'Ruido (α %)']],
      body: [[params.x0, params.y0, params.z0, params.A0, params.alpha]],
      theme: 'grid',
      headStyles: { fillColor: [56, 189, 248] }
    });

    // Vector Az (Lecturas de las Estaciones)
    doc.setFontSize(14);
    doc.text("Vector de Observaciones (Az) - Datos para Inversión", 14, doc.lastAutoTable.finalY + 12);
    
    const tableData = sensors.map(s => [
      s.id,
      s.name,
      s.x.toFixed(2),
      s.y.toFixed(2),
      s.z.toFixed(2),
      s.lecturaAzi ? s.lecturaAzi.toFixed(4) : "0.0000"
    ]);

    doc.autoTable({
      startY: doc.lastAutoTable.finalY + 16,
      head: [['ID', 'Estación', 'Pos X (m)', 'Pos Y (m)', 'Pos Z (m)', 'Amplitud Obs (Azi)']],
      body: tableData,
      theme: 'grid',
      headStyles: { fillColor: [239, 68, 68] }
    });

    // Nota metodológica
    doc.setFontSize(10);
    const notaY = doc.lastAutoTable.finalY + 15;
    doc.text("Nota: Utilice la columna 'Amplitud Obs (Azi)' como el vector real para calcular el", 14, notaY);
    doc.text("Jacobiano y minimizar la función de error E(x,y,z) mediante mínimos cuadrados.", 14, notaY + 6);

    doc.save("Reporte_Simulacion_Sismica.pdf");
  };



  return (
    <div className="app-container">
      
      {/* Panel Izquierdo: Parámetros Fuente */}
      <div className="glass-panel">
        <h2>Parámetros Fuente (m)</h2>
        
        <div className="control-group">
          <label><span>Coordenada X (x₀)</span> <span>{params.x0}</span></label>
          <input type="range" name="x0" min="-100" max="100" value={params.x0} onChange={handleParamChange} />
        </div>
        
        <div className="control-group">
          <label><span>Coordenada Y (y₀)</span> <span>{params.y0}</span></label>
          <input type="range" name="y0" min="-100" max="100" value={params.y0} onChange={handleParamChange} />
        </div>
        
        <div className="control-group">
          <label><span>Profundidad (z₀)</span> <span>{params.z0}</span></label>
          <input type="range" name="z0" min="1" max="200" value={params.z0} onChange={handleParamChange} />
        </div>
        
        <div className="control-group">
          <label><span>Amplitud (A₀)</span> <span>{params.A0}</span></label>
          <input type="range" name="A0" min="0" max="10000" step="100" value={params.A0} onChange={handleParamChange} />
        </div>

        <div className="control-group" style={{ marginTop: '1rem' }}>
          <label><span>Ruido Gaussiano (α %)</span> <span>{params.alpha}%</span></label>
          <input type="range" name="alpha" min="0" max="50" value={params.alpha} onChange={handleParamChange} />
        </div>

        <div style={{ marginTop: 'auto', padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
          <div>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{"Error Residual Total (Err)"}</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#38bdf8' }}>
              {globalError.toFixed(2)}
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
            <button onClick={exportReport} style={{ flex: 1, padding: '0.5rem', background: '#ef4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', fontSize: '0.8rem' }}>
              Descargar PDF
            </button>
          </div>
        </div>
      </div>

      {/* Panel Central: Visualización 3D y Gráficas */}
      <div className="visualization-center">
        <div className="glass-panel wave-canvas" style={{ padding: 0, position: 'relative' }}>
          <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block', outline: 'none' }} />

          <div style={{ position: 'absolute', top: 20, left: 20, color: 'rgba(255,255,255,0.7)', fontWeight: 'bold', textAlign: 'left', pointerEvents: 'none' }}>
            Simulación 3D: Sismo y Sensores<br/>
            <span style={{ fontSize: '0.8rem', fontWeight: 'normal' }}>Arrastra para rotar, usa la rueda para acercar</span>
          </div>
        </div>

        <div className="graphs-container">
          <div className="glass-panel" style={{ padding: '1rem', gap: '0.5rem' }}>
            <h2 style={{ fontSize: '1rem', borderBottom: 'none' }}>Variación del Error en Red</h2>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" hide />
                <YAxis stroke="rgba(255,255,255,0.3)" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }} />
                <Line type="monotone" name="Est. 1" dataKey="est1" stroke="#38bdf8" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="monotone" name="Est. 5" dataKey="est5" stroke="#818cf8" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="monotone" name="Est. 9" dataKey="est9" stroke="#ef4444" strokeWidth={2} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          
          <div className="glass-panel" style={{ padding: '1rem', gap: '0.5rem' }}>
            <h2 style={{ fontSize: '1rem', borderBottom: 'none' }}>RMS de Energía Global</h2>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" hide />
                <YAxis stroke="rgba(255,255,255,0.3)" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }} />
                <Area type="monotone" dataKey="energiaRMS" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.2} strokeWidth={2} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Panel Derecho: Análisis de Sensores */}
      <div className="glass-panel" style={{ overflowY: 'auto' }}>
        <h2>Análisis de Estaciones (Az)</h2>
        <div className="sensors-list" style={{ gap: '0.5rem' }}>
          {sensors.map(sensor => {
            const isAlarm = sensor.dataTraffic > 80;
            return (
              <div key={sensor.id} className={`sensor-card ${isAlarm ? 'alarm' : ''}`} style={{ padding: '0.75rem' }}>
                <div className="sensor-header">
                  <span>{sensor.name}</span>
                  <div className="status-indicator" title={isAlarm ? 'Alarma' : 'Normal'}></div>
                </div>
                <div className="sensor-stats" style={{ marginTop: '0.5rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Tráfico:</span>
                    <strong>{sensor.dataTraffic.toFixed(1)} Mbps</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Amplitud Obs (Az{sensor.id}):</span>
                    <span>{sensor.lecturaAzi?.toFixed(2)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Error (ε):</span>
                    <span style={{ color: isAlarm ? '#ef4444' : '#94a3b8' }}>{sensor.error.toFixed(2)}</span>
                  </div>
                  {isAlarm && <div className="alert-badge" style={{ marginTop: '0.25rem', textAlign: 'center' }}>⚠️ ALTO TRÁFICO</div>}
                </div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}

export default App;
