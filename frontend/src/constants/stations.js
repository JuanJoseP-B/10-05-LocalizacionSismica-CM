/** Cuadrícula 3x3 compartida con backend/stations_grid.py */
export function buildStationGrid() {
  return Array.from({ length: 9 }, (_, i) => {
    const row = Math.floor(i / 3);
    const col = i % 3;
    return {
      id: i + 1,
      name: `Estación ${i + 1}`,
      x: (col - 1) * 50,
      y: (row - 1) * 50,
      z: 0,
    };
  });
}

export const STATUS_LABELS = {
  idle: 'Inactivo (A₀ = 0)',
  active: 'Señal detectada',
  sin_senal: 'Sin señal',
};
