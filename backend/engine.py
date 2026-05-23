import numpy as np
from scipy.optimize import minimize

class SeismicEngine:
    def __init__(self, stations=None):
        """
        Initialize the engine with a set of seismic stations.
        :param stations: List of coordinates [(x1, y1, z1), ...]
        """
        self.stations = np.array(stations) if stations is not None else np.array([])
        self.alpha = 0.05  # Noise factor

    def attenuation_model(self, R, A0):
        """
        Implements the model: A = A0 * exp(-R) / R
        """
        # Avoid division by zero
        R = np.maximum(R, 1e-9)
        return A0 * (np.exp(-R) / R)

    def generate_stations(self, count=5, x_range=(0, 100), y_range=(0, 100), z_range=(0, 10)):
        """
        Fase 1.1: Generación de Sensores
        """
        x = np.random.uniform(x_range[0], x_range[1], count)
        y = np.random.uniform(y_range[0], y_range[1], count)
        z = np.random.uniform(z_range[0], z_range[1], count)
        self.stations = np.column_stack((x, y, z))
        return self.stations

    def simulate_signal(self, source_pos, A0):
        """
        Fase 1.2: Inyección de Ruido
        source_pos: (x0, y0, z0)
        """
        source_pos = np.array(source_pos)
        distances = np.linalg.norm(self.stations - source_pos, axis=1)
        A_theoretical = self.attenuation_model(distances, A0)
        
        # Sigma = alpha * A_theoretical
        sigma = self.alpha * A_theoretical
        noise = np.random.normal(0, sigma)
        
        A_observed = A_theoretical + noise
        return A_observed

    def error_function(self, m, observed_amplitudes):
        """
        Fase 1.3: Función de Error (Suma de cuadrados de residuos)
        m: [x0, y0, z0, A0]
        """
        source_pos = m[:3]
        A0 = m[3]
        
        distances = np.linalg.norm(self.stations - source_pos, axis=1)
        A_predicted = self.attenuation_model(distances, A0)
        
        error = np.sum((observed_amplitudes - A_predicted)**2)
        return error

    def solve(self, observed_amplitudes, initial_guess=None):
        """
        Fase 1.4: Algoritmo de Optimización (Mínimos Cuadrados)
        """
        if initial_guess is None:
            # Default guess: center of stations and average amplitude-ish
            initial_guess = np.append(np.mean(self.stations, axis=0), 100.0)
            
        res = minimize(
            self.error_function, 
            initial_guess, 
            args=(observed_amplitudes,),
            method='L-BFGS-B',
            bounds=[(None, None), (None, None), (None, None), (0, None)]
        )
        return res

    def get_heatmap_data(self, z_plane, observed_amplitudes, A0_fixed, grid_size=50, x_range=(0, 100), y_range=(0, 100)):
        """
        Fase 2.2: Generador de Mapas de Calor
        Visualizar cortes en z=k para mostrar la intensidad de E(x, y, z)
        """
        x = np.linspace(x_range[0], x_range[1], grid_size)
        y = np.linspace(y_range[0], y_range[1], grid_size)
        X, Y = np.meshgrid(x, y)
        Z = np.zeros_like(X)

        for i in range(grid_size):
            for j in range(grid_size):
                m = [X[i, j], Y[i, j], z_plane, A0_fixed]
                Z[i, j] = self.error_function(m, observed_amplitudes)
        
        return X, Y, Z

    def get_global_error_curve(self, observed_amplitudes, A0_fixed, z_range=(0, 50), steps=50):
        """
        Fase 2.3: Gráfica de Error Global E_min(z)
        """
        z_values = np.linspace(z_range[0], z_range[1], steps)
        e_min_values = []

        for z in z_values:
            # For each z, find best (x, y)
            def temp_err(xy):
                m = [xy[0], xy[1], z, A0_fixed]
                return self.error_function(m, observed_amplitudes)
            
            res = minimize(temp_err, np.mean(self.stations[:, :2], axis=0), method='L-BFGS-B')
            e_min_values.append(res.fun)
            
        return z_values, np.array(e_min_values)
