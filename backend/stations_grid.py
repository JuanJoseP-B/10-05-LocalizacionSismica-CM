"""Cuadrícula 3x3 de estaciones compartida entre frontend y backend."""
import numpy as np

GRID_STATIONS = np.array([
    [-50, -50, 0], [0, -50, 0], [50, -50, 0],
    [-50,   0, 0], [0,   0, 0], [50,   0, 0],
    [-50,  50, 0], [0,  50, 0], [50,  50, 0],
], dtype=float)

STATION_NAMES = [f"Estación {i + 1}" for i in range(len(GRID_STATIONS))]
