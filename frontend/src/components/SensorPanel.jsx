import React from 'react';
import { useSimulation } from '../store/SimulationContext';
import { STATUS_LABELS } from '../constants/stations';
import { formatNumber, formatPercent } from '../utils/format';

export default function SensorPanel() {
  const { sensors } = useSimulation();

  return (
    <section className="glass-panel sensor-panel">
      <h2>Analisis de Estaciones (Az)</h2>
      <div className="sensors-list">
        {sensors.map((sensor) => (
          <div
            key={sensor.id}
            className={`sensor-card ${sensor.status === 'sin_senal' ? 'alarm' : ''}`}
          >
            <div className="sensor-header">
              <span>{sensor.name}</span>
              <div className={`status-indicator status-${sensor.status}`} />
            </div>
            <div className="sensor-stats">
              <div className="stat-row"><span>Estado:</span><strong>{STATUS_LABELS[sensor.status]}</strong></div>
              <div className="stat-row"><span>Distancia R:</span><span>{sensor.distance.toFixed(2)} m</span></div>
              <div className="stat-row"><span>Intensidad:</span><span>{formatPercent(sensor.signalLevel)}</span></div>
              <div className="stat-row"><span>Amplitud A_zi:</span><span>{formatNumber(sensor.lecturaAzi)}</span></div>
              <div className="stat-row"><span>Error epsilon:</span><span>{formatNumber(sensor.error)}</span></div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
