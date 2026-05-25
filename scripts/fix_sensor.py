from pathlib import Path

p = Path(__file__).resolve().parents[1] / "frontend/src/components/SensorPanel.jsx"
d = "div"
content = f"""import React from 'react';
import {{ useSimulation }} from '../store/SimulationContext';
import {{ STATUS_LABELS }} from '../constants/stations';
import {{ formatNumber, formatPercent }} from '../utils/format';

export default function SensorPanel() {{
  const {{ sensors }} = useSimulation();

  return (
    <section className="glass-panel sensor-panel">
      <h2>Analisis de Estaciones (Az)</h2>
      <{d} className="sensors-list">
        {{sensors.map((sensor) => (
          <{d}
            key={{sensor.id}}
            className={{`sensor-card ${{sensor.status === 'sin_senal' ? 'alarm' : ''}}`}}
          >
            <{d} className="sensor-header">
              <span>{{sensor.name}}</span>
              <{d} className={{`status-indicator status-${{sensor.status}}`}} />
            </{d}>
            <{d} className="sensor-stats">
              <{d} className="stat-row"><span>Estado:</span><strong>{{STATUS_LABELS[sensor.status]}}</strong></{d}>
              <{d} className="stat-row"><span>Distancia R:</span><span>{{sensor.distance.toFixed(2)}} m</span></{d}>
              <{d} className="stat-row"><span>Intensidad:</span><span>{{formatPercent(sensor.signalLevel)}}</span></{d}>
              <{d} className="stat-row"><span>Amplitud A_zi:</span><span>{{formatNumber(sensor.lecturaAzi)}}</span></{d}>
              <{d} className="stat-row"><span>Error epsilon:</span><span>{{formatNumber(sensor.error)}}</span></{d}>
            </{d}>
          </{d}>
        ))}}
      </{d}>
    </section>
  );
}}
"""
p.write_text(content, encoding="utf-8")
print("SensorPanel OK")
