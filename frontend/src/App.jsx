import React from 'react';
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
