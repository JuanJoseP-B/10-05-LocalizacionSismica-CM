import numpy as np
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import minimize

LOG_ERR_EPS = 1e-15
NUM_CONTOUR_LEVELS = 10
DEFAULT_LOG_RANGE = (-2.0, 4.0)


def _to_log_visual(Z, log_eps=LOG_ERR_EPS):
    """Z_visual = log10(Z_error + ε) — comprime el rango dinámico."""
    Z = np.asarray(Z, dtype=float)
    return np.log10(np.maximum(Z, 0.0) + log_eps)


def _validar_niveles_contorno(levels, z_lo, z_hi, n=NUM_CONTOUR_LEVELS):
    """Garantiza niveles estrictamente crecientes para contourf."""
    levels = np.asarray(levels, dtype=float)
    levels = levels[np.isfinite(levels)]
    invalid = (
        levels.size < 2
        or np.any(np.diff(levels) <= 0)
    )
    if invalid:
        lo = z_lo if np.isfinite(z_lo) else DEFAULT_LOG_RANGE[0]
        hi = z_hi if np.isfinite(z_hi) and z_hi > lo else DEFAULT_LOG_RANGE[1]
        if hi <= lo:
            lo, hi = DEFAULT_LOG_RANGE
        return np.linspace(lo, hi, n)
    return levels


def _niveles_equiespaciados(z_lo, z_hi, n=NUM_CONTOUR_LEVELS):
    lo = float(z_lo) if np.isfinite(z_lo) else DEFAULT_LOG_RANGE[0]
    hi = float(z_hi) if np.isfinite(z_hi) else DEFAULT_LOG_RANGE[1]
    if hi <= lo:
        lo, hi = DEFAULT_LOG_RANGE
    return _validar_niveles_contorno(np.linspace(lo, hi, n), lo, hi, n)


def escribir_video_mp4(frame_paths, output_path, fps=10):
    """
    Une PNGs en MP4 con códec compatible (mp4v / libx264).
    Cierra el escritor siempre en finally.
    """
    if not frame_paths:
        raise ValueError('No hay fotogramas para el video')

    try:
        import cv2
        first = cv2.imread(frame_paths[0])
        if first is None:
            raise RuntimeError(f'No se pudo leer el frame: {frame_paths[0]}')
        h, w = first.shape[:2]
        for codec in ('mp4v', 'avc1'):
            fourcc = cv2.VideoWriter_fourcc(*codec)
            writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
            if not writer.isOpened():
                continue
            try:
                for fp in frame_paths:
                    frame = cv2.imread(fp)
                    if frame is None:
                        continue
                    if frame.shape[0] != h or frame.shape[1] != w:
                        frame = cv2.resize(frame, (w, h))
                    writer.write(frame)
            finally:
                writer.release()
            if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
                return output_path
    except ImportError:
        pass

    import imageio.v2 as imageio
    writer = None
    try:
        try:
            writer = imageio.get_writer(
                output_path,
                fps=fps,
                codec='libx264',
                format='FFMPEG',
                output_params=['-pix_fmt', 'yuv420p'],
            )
        except Exception:
            writer = imageio.get_writer(output_path, fps=fps, codec='libx264')
        for fp in frame_paths:
            writer.append_data(imageio.imread(fp))
    finally:
        if writer is not None:
            writer.close()
    return output_path


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

    def relative_error_function(self, m, observed_amplitudes):
        """
        Error relativo (misma métrica que la inversión LM):
        E_rr = Σ ((A_obs_i - A_calc_i) / A_obs_i)²
        """
        source_pos = np.asarray(m[:3], dtype=float)
        A0 = float(m[3])
        distances = np.linalg.norm(self.stations - source_pos, axis=1)
        A_predicted = self.attenuation_model(distances, A0)
        obs = np.asarray(observed_amplitudes, dtype=float)
        denom = np.maximum(np.abs(obs), 1e-30)
        with np.errstate(divide='ignore', invalid='ignore'):
            rel = (obs - A_predicted) / denom
        rel = np.nan_to_num(rel, nan=0.0, posinf=0.0, neginf=0.0)
        # Evita explosión en bordes lejanos del grid (obs ~ 1e-50)
        rel = np.clip(rel, -50.0, 50.0)
        return float(np.sum(rel ** 2))

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
                Z[i, j] = self.relative_error_function(m, observed_amplitudes)

        return X, Y, Z

    def precalcular_rango_log_global(
        self,
        observed_amplitudes,
        A0_fixed,
        z_range,
        num_cuts,
        grid_size=40,
        x_range=(-70, 70),
        y_range=(-70, 70),
        log_eps=LOG_ERR_EPS,
    ):
        """Recorre todos los cortes Z y devuelve (z_lo, z_hi, levels) fijos para el video."""
        z_values = np.linspace(z_range[0], z_range[1], num_cuts)
        z_lo, z_hi = np.inf, -np.inf

        for z_plane in z_values:
            _, _, Z = self.get_heatmap_data(
                z_plane, observed_amplitudes, A0_fixed,
                grid_size=grid_size, x_range=x_range, y_range=y_range,
            )
            Z_log = _to_log_visual(Z, log_eps)
            finite = Z_log[np.isfinite(Z_log)]
            if finite.size == 0:
                continue
            z_lo = min(z_lo, float(np.min(finite)))
            z_hi = max(z_hi, float(np.max(finite)))

        if not np.isfinite(z_lo) or not np.isfinite(z_hi) or z_hi <= z_lo:
            z_lo, z_hi = DEFAULT_LOG_RANGE
        else:
            margin = max((z_hi - z_lo) * 0.02, 0.05)
            z_lo -= margin
            z_hi += margin

        levels = _niveles_equiespaciados(z_lo, z_hi, NUM_CONTOUR_LEVELS)
        return float(z_lo), float(z_hi), levels

    @staticmethod
    def _minimo_grid(X, Y, Z):
        """Índice del mínimo real; si el relieve colapsa, centrar la marca."""
        Z = np.asarray(Z, dtype=float)
        if Z.size == 0:
            return 0, 0
        z_min = np.nanmin(Z)
        z_max = np.nanmax(Z)
        if not np.isfinite(z_min) or np.allclose(Z, z_min, rtol=0, atol=1e-15 * max(abs(z_min), 1.0)):
            ci, cj = Z.shape[0] // 2, Z.shape[1] // 2
        else:
            ci, cj = np.unravel_index(np.nanargmin(Z), Z.shape)
        return int(ci), int(cj)

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

    def save_heatmap_frame(
        self,
        z_plane,
        observed_amplitudes,
        A0_fixed,
        output_path,
        grid_size=40,
        x_range=(-70, 70),
        y_range=(-70, 70),
        contour_levels=None,
        log_vmin=None,
        log_vmax=None,
    ):
        """Renderiza y guarda un mapa de calor para un corte z=k como PNG."""
        X, Y, Z = self.get_heatmap_data(
            z_plane, observed_amplitudes, A0_fixed,
            grid_size=grid_size, x_range=x_range, y_range=y_range,
        )

        Z_log = _to_log_visual(Z)
        z_lo = log_vmin if log_vmin is not None else float(np.nanmin(Z_log))
        z_hi = log_vmax if log_vmax is not None else float(np.nanmax(Z_log))
        if contour_levels is None:
            levels = _niveles_equiespaciados(z_lo, z_hi)
        else:
            levels = _validar_niveles_contorno(contour_levels, z_lo, z_hi)

        fig, ax = plt.subplots(figsize=(9, 7))
        cp = ax.contourf(
            X, Y, Z_log,
            levels=levels,
            cmap='viridis_r',
            vmin=levels[0],
            vmax=levels[-1],
            extend='both',
        )
        cbar = plt.colorbar(cp, ax=ax, ticks=levels)
        cbar.set_label(f'log10(E_rr relativo + {LOG_ERR_EPS:g})')

        if len(self.stations) > 0:
            ax.scatter(
                self.stations[:, 0], self.stations[:, 1],
                c='black', marker='^', s=100, label='Estaciones Receptoras'
            )

        mi, mj = self._minimo_grid(X, Y, Z)
        ax.scatter(
            X[mi, mj], Y[mi, mj], c='red', marker='X', s=150,
            label=f'Mínimo (x={X[mi, mj]:.1f}, y={Y[mi, mj]:.1f})'
        )

        ax.set_title(f'Mapa de Calor del Error en Profundidad z = {z_plane:.2f} m')
        ax.set_xlabel('Coordenada X (m)')
        ax.set_ylabel('Coordenada Y (m)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(output_path, dpi=100)
        plt.close(fig)

    def generate_z_cuts_video(self, observed_amplitudes, A0_fixed, output_path,
                              z_range=(1, 200), num_cuts=100, frames_dir=None,
                              grid_size=40, fps=10, cleanup_frames=True,
                              x_range=(-70, 70), y_range=(-70, 70)):
        """Genera MP4 con cortes en Z; niveles de contorno globales fijos."""
        if frames_dir is None:
            frames_dir = os.path.join(os.path.dirname(output_path), 'frames_z_cortes')

        os.makedirs(frames_dir, exist_ok=True)
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        z_lo, z_hi, levels = self.precalcular_rango_log_global(
            observed_amplitudes, A0_fixed, z_range, num_cuts,
            grid_size=grid_size, x_range=x_range, y_range=y_range,
        )

        z_values = np.linspace(z_range[0], z_range[1], num_cuts)
        frame_paths = []

        for idx, z_plane in enumerate(z_values):
            frame_path = os.path.join(frames_dir, f'frame_{idx:04d}.png')
            self.save_heatmap_frame(
                z_plane, observed_amplitudes, A0_fixed, frame_path,
                grid_size=grid_size, x_range=x_range, y_range=y_range,
                contour_levels=levels, log_vmin=z_lo, log_vmax=z_hi,
            )
            frame_paths.append(frame_path)

        escribir_video_mp4(frame_paths, output_path, fps=fps)

        if cleanup_frames:
            for frame_path in frame_paths:
                if os.path.isfile(frame_path):
                    os.remove(frame_path)
            if os.path.isdir(frames_dir) and not os.listdir(frames_dir):
                os.rmdir(frames_dir)

        return output_path
