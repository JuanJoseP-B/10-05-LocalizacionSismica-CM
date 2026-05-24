import React from 'react';
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
