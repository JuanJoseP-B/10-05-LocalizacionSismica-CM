import React, { useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area, ReferenceLine, ReferenceDot,
} from 'recharts';
import { useSimulation } from '../store/SimulationContext';
import { formatNumber } from '../utils/format';
import { encontrarMinimoCurva } from '../math/eMinCurve';

export default function ChartsPanel() {
  const {
    networkChart, inversionHistory, inversion, params,
    eMinCurve, eMinCurveLoading,
  } = useSimulation();

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

  const eMinData = useMemo(
    () => (eMinCurve ?? []).map((p) => ({
      z: p.z,
      error: p.error,
      logError: p.error > 0 ? Math.log10(p.error + 1e-15) : -15,
    })),
    [eMinCurve],
  );

  const minCurva = useMemo(() => encontrarMinimoCurva(eMinCurve), [eMinCurve]);
  const zEstimado = inversion?.estimated?.z0;

  const positiveErrors = eMinData.map((d) => d.error).filter((e) => e > 0);
  const useLogScale = positiveErrors.length > 0
    && Math.max(...positiveErrors) / Math.min(...positiveErrors) > 50;

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
      <div className="glass-panel chart-card chart-card--wide">
        <h3>Análisis de Error Mínimo E_min(z)</h3>
        {eMinCurveLoading && (
          <p className="chart-hint">Calculando curva E_min(z)...</p>
        )}
        {!eMinCurveLoading && eMinData.length === 0 && (
          <p className="chart-hint">Ejecuta la inversión para graficar E_min(z).</p>
        )}
        {eMinData.length > 0 && (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={eMinData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="z"
                type="number"
                domain={['dataMin', 'dataMax']}
                stroke="#94a3b8"
                fontSize={10}
                label={{ value: 'Profundidad Z (m)', position: 'insideBottom', offset: -2, fill: '#94a3b8' }}
              />
              <YAxis
                stroke="#94a3b8"
                fontSize={10}
                scale={useLogScale ? 'log' : 'linear'}
                domain={useLogScale ? ['auto', 'auto'] : ['auto', 'auto']}
                tickFormatter={(v) => formatNumber(v, 2)}
                allowDataOverflow
              />
              <Tooltip
                formatter={(v, name) => [
                  formatNumber(v),
                  name === 'logError' ? 'log10(E_min)' : 'E_min relativo',
                ]}
                labelFormatter={(z) => `Z = ${formatNumber(z, 1)} m`}
              />
              <Line
                type="monotone"
                dataKey="error"
                stroke="#22c55e"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
              {minCurva && (
                <ReferenceDot
                  x={minCurva.z}
                  y={minCurva.error}
                  r={6}
                  fill="#ef4444"
                  stroke="#fff"
                  label={{ value: 'mín', position: 'top', fill: '#fca5a5', fontSize: 10 }}
                />
              )}
              {zEstimado != null && (
                <ReferenceLine
                  x={zEstimado}
                  stroke="#fbbf24"
                  strokeDasharray="4 4"
                  label={{
                    value: `Z estimado LM: ${formatNumber(zEstimado, 1)}`,
                    position: 'insideTopRight',
                    fill: '#fbbf24',
                    fontSize: 10,
                  }}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
        {minCurva && zEstimado != null && (
          <p className="chart-hint">
            Valle curva: Z={formatNumber(minCurva.z, 1)} m · LM: Z={formatNumber(zEstimado, 1)} m
            {' '}
            (Δ={formatNumber(Math.abs(minCurva.z - zEstimado), 1)} m)
          </p>
        )}
      </div>
    </div>
  );
}
