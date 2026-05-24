import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

from backend.engine import SeismicEngine
from backend.stations_grid import GRID_STATIONS, STATION_NAMES

# ====================================================================
# PROYECTO: Localización de una Fuente Sísmica (Problema Inverso)
# Simula observaciones con la misma cuadrícula 3x3 del frontend React
# y resuelve el problema inverso con Gauss-Newton.
# ====================================================================

# Parámetros por defecto (equivalentes al simulador web)
FUENTE_REAL = [10.0, -15.0, 30.0, 5000.0]  # x0, y0, z0, A0
ALPHA_RUIDO = 0.05  # 5 %


def calcular_Ri(x_i, y_i, z_i, x0, y0, z0):
    """Ecuación 2: distancia euclidiana fuente-estación."""
    return np.sqrt((x_i - x0) ** 2 + (y_i - y0) ** 2 + (z_i - z0) ** 2)


def modelo_atenuacion(x_i, y_i, z_i, m):
    """Ecuación 1: A_zi = A0 * exp(-R_i) / R_i"""
    x0, y0, z0, A0 = m
    R_i = calcular_Ri(x_i, y_i, z_i, x0, y0, z0)
    R_i = np.where(R_i == 0, 1e-5, R_i)
    return A0 * (np.exp(-R_i) / R_i)


def generar_datos_simulados(fuente=None, alpha=ALPHA_RUIDO):
    """Genera el vector Az con el motor sísmico (sin CSV externo)."""
    if fuente is None:
        fuente = FUENTE_REAL

    x0, y0, z0, A0 = fuente
    engine = SeismicEngine(stations=GRID_STATIONS)
    engine.alpha = alpha
    amplitudes = engine.simulate_signal([x0, y0, z0], A0)

    df = pd.DataFrame({
        'ID': np.arange(1, len(GRID_STATIONS) + 1),
        'Estacion': STATION_NAMES,
        'X': GRID_STATIONS[:, 0],
        'Y': GRID_STATIONS[:, 1],
        'Z': GRID_STATIONS[:, 2],
        'Amplitud_Azi': amplitudes,
    })
    print("Datos simulados (cuadricula 3x3 del frontend):\n", df.to_string(index=False))
    return df, [x0, y0, z0, A0]


def calcular_error_global(df, m):
    """Ecuación 7: Err = sum(A_obs_i - A_pred_i)^2"""
    A_obs = df['Amplitud_Azi'].values
    A_pred = modelo_atenuacion(df['X'].values, df['Y'].values, df['Z'].values, m)
    return np.sum((A_obs - A_pred) ** 2)


def calcular_jacobiano_numerico(df, m, delta=1e-4):
    """Jacobiano G por diferencias finitas (Ecuación 8)."""
    num_estaciones = len(df)
    num_params = len(m)
    G = np.zeros((num_estaciones, num_params))
    A_pred_base = modelo_atenuacion(df['X'].values, df['Y'].values, df['Z'].values, m)

    for j in range(num_params):
        m_pert = np.copy(m)
        m_pert[j] += delta
        A_pred_pert = modelo_atenuacion(df['X'].values, df['Y'].values, df['Z'].values, m_pert)
        G[:, j] = (A_pred_pert - A_pred_base) / delta

    return G, A_pred_base


def inversion_gauss_newton(df, m_inicial, max_iter=50, tol=1e-4):
    """Gauss-Newton (Ecuaciones 10 y 11)."""
    A_obs = df['Amplitud_Azi'].values
    m = np.array(m_inicial, dtype=float)
    historial_errores = []

    print("\n--- INICIANDO INVERSIÓN (Gauss-Newton) ---")
    for k in range(max_iter):
        G, A_pred = calcular_jacobiano_numerico(df, m)
        delta_Az = A_obs - A_pred
        error_actual = np.sum(delta_Az ** 2)
        historial_errores.append(error_actual)

        GTG = G.T @ G + np.eye(len(m)) * 1e-6
        delta_m = np.linalg.inv(GTG) @ G.T @ delta_Az
        m = m + delta_m

        print(
            f"Iteración {k + 1:02d} | Error: {error_actual:.4f} | "
            f"x0={m[0]:.1f}, y0={m[1]:.1f}, z0={m[2]:.1f}, A0={m[3]:.1f}"
        )

        if np.linalg.norm(delta_m) < tol:
            print("Convergencia alcanzada.")
            break

    return m, historial_errores


def calcular_mapa_error_z(df, z_fijo, A0_fijo, resolucion=60,
                          x_range=(-100, 100), y_range=(-100, 100)):
    x_rango = np.linspace(x_range[0], x_range[1], resolucion)
    y_rango = np.linspace(y_range[0], y_range[1], resolucion)
    X, Y = np.meshgrid(x_rango, y_rango)
    Z_err = np.zeros_like(X)

    for i in range(resolucion):
        for j in range(resolucion):
            Z_err[i, j] = calcular_error_global(df, [X[i, j], Y[i, j], z_fijo, A0_fijo])

    return X, Y, Z_err


def graficar_mapa_calor_z(df, z_fijo, A0_fijo, resolucion=60, save_path=None, show=True):
    X, Y, Z_err = calcular_mapa_error_z(df, z_fijo, A0_fijo, resolucion)

    fig, ax = plt.subplots(figsize=(9, 7))
    cp = ax.contourf(X, Y, np.log10(Z_err + 1e-5), levels=40, cmap='viridis_r')
    plt.colorbar(cp, ax=ax, label='Log10(Error Residual)')
    ax.scatter(df['X'], df['Y'], c='black', marker='^', s=100, label='Estaciones')
    min_idx = np.unravel_index(np.argmin(Z_err), Z_err.shape)
    ax.scatter(
        X[min_idx], Y[min_idx], c='red', marker='X', s=150,
        label=f'Mínimo (x={X[min_idx]:.1f}, y={Y[min_idx]:.1f})'
    )
    ax.set_title(f'Mapa de Calor del Error en z = {z_fijo:.2f} m')
    ax.set_xlabel('Coordenada X (m)')
    ax.set_ylabel('Coordenada Y (m)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=100)
    if show:
        plt.show()
    else:
        plt.close(fig)

    return X, Y, Z_err


def generar_video_cortes_z(df, A0_fijo, z_min=1, z_max=200, num_cortes=100,
                           output_video='video_cortes_z.mp4', frames_dir='frames_z_cortes',
                           resolucion=40, fps=10, cleanup_frames=True):
    import imageio.v2 as imageio

    os.makedirs(frames_dir, exist_ok=True)
    z_values = np.linspace(z_min, z_max, num_cortes)
    frame_paths = []

    print(f"\nGenerando {num_cortes} cortes en z ∈ [{z_min}, {z_max}]...")
    for idx, z_fijo in enumerate(z_values):
        frame_path = os.path.join(frames_dir, f'frame_{idx:04d}.png')
        graficar_mapa_calor_z(
            df, z_fijo, A0_fijo,
            resolucion=resolucion,
            save_path=frame_path,
            show=False
        )
        frame_paths.append(frame_path)
        if (idx + 1) % 10 == 0 or idx == num_cortes - 1:
            print(f"  Progreso: {idx + 1}/{num_cortes} (z = {z_fijo:.2f} m)")

    print(f"Uniendo frames → {output_video}")
    with imageio.get_writer(output_video, fps=fps) as writer:
        for frame_path in frame_paths:
            writer.append_data(imageio.imread(frame_path))

    if cleanup_frames:
        for frame_path in frame_paths:
            os.remove(frame_path)
        if os.path.isdir(frames_dir) and not os.listdir(frames_dir):
            os.rmdir(frames_dir)

    print(f"Video generado: {output_video}")
    return output_video


if __name__ == "__main__":
    df, fuente_real = generar_datos_simulados()
    m0 = [0.0, 0.0, 10.0, 1000.0]

    m_estimado, errores = inversion_gauss_newton(df, m0)

    print("\n================ RESULTADOS FINALES ================")
    print(f"Fuente real:     x={fuente_real[0]:.2f}, y={fuente_real[1]:.2f}, z={fuente_real[2]:.2f}, A0={fuente_real[3]:.2f}")
    print(f"Fuente estimada: x={m_estimado[0]:.2f}, y={m_estimado[1]:.2f}, z={m_estimado[2]:.2f}, A0={m_estimado[3]:.2f}")
    print("========================================================\n")

    plt.figure(figsize=(7, 4))
    plt.plot(errores, marker='o', linestyle='-', color='b')
    plt.title('Convergencia del Algoritmo de Gauss-Newton')
    plt.xlabel('Iteración')
    plt.ylabel('Error Cuadrático Total')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    graficar_mapa_calor_z(df, z_fijo=m_estimado[2], A0_fijo=m_estimado[3])

    generar_video_cortes_z(
        df,
        A0_fijo=m_estimado[3],
        z_min=1,
        z_max=200,
        num_cortes=100,
        resolucion=40,
        fps=10
    )
