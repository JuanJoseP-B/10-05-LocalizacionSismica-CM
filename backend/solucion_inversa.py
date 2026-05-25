import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

from backend.engine import SeismicEngine
from backend.stations_grid import GRID_STATIONS, STATION_NAMES

# ====================================================================
# PROYECTO: Localización de una Fuente Sísmica (Problema Inverso)
# ====================================================================

FUENTE_REAL = [10.0, -15.0, 30.0, 5000.0]
ALPHA_RUIDO = 0.05

DIAG_EPS = 1e-10
MAX_PASO_ESPACIAL = 15.0
Z0_SEMILLA = 5.0
A0_MAX_ESTIMADO = 1e7
A0_MIN_SEMILLA = 1000.0
MAX_ITER_DEFAULT = 500


def calcular_Ri(x_i, y_i, z_i, x0, y0, z0):
    return np.sqrt((x_i - x0) ** 2 + (y_i - y0) ** 2 + (z_i - z0) ** 2)


def modelo_atenuacion(x_i, y_i, z_i, m):
    x0, y0, z0, A0 = m
    R_i = calcular_Ri(x_i, y_i, z_i, x0, y0, z0)
    R_i = np.where(R_i == 0, 1e-5, R_i)
    return A0 * (np.exp(-R_i) / R_i)


def generar_datos_simulados(fuente=None, alpha=ALPHA_RUIDO):
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
    A_obs = df['Amplitud_Azi'].values
    A_pred = modelo_atenuacion(df['X'].values, df['Y'].values, df['Z'].values, m)
    return np.sum((A_obs - A_pred) ** 2)


def calcular_jacobiano_analitico(df, m):
    x0, y0, z0, A0 = m
    x_i = df['X'].values
    y_i = df['Y'].values
    z_i = df['Z'].values

    R = calcular_Ri(x_i, y_i, z_i, x0, y0, z0)
    R = np.where(R == 0, 1e-5, R)

    exp_R = np.exp(-R)
    A_pred = A0 * exp_R / R

    G = np.zeros((len(df), 4))
    spatial_factor = A0 * exp_R * (R + 1) / (R ** 3)

    G[:, 0] = spatial_factor * (x_i - x0)
    G[:, 1] = spatial_factor * (y_i - y0)
    G[:, 2] = spatial_factor * (z_i - z0)
    G[:, 3] = exp_R / R

    return G, A_pred


def limites_grid_estaciones(df, margin_frac=0.2):
    min_x, max_x = df['X'].min(), df['X'].max()
    min_y, max_y = df['Y'].min(), df['Y'].max()
    mx = (max_x - min_x) * margin_frac
    my = (max_y - min_y) * margin_frac
    return min_x - mx, max_x + mx, min_y - my, max_y + my


def calcular_semilla_inteligente(df):
    A_obs = df['Amplitud_Azi'].values
    idx = int(np.argmax(A_obs))
    row = df.iloc[idx]
    x0, y0 = float(row['X']), float(row['Y'])
    z0 = Z0_SEMILLA
    max_obs = A_obs[idx]

    A0 = 0.0
    for i in range(len(df)):
        r = df.iloc[i]
        R = max(calcular_Ri(r['X'], r['Y'], r['Z'], x0, y0, z0), 1e-9)
        est = A_obs[i] * R * np.exp(R)
        if np.isfinite(est) and est > A0:
            A0 = est
    if not np.isfinite(A0) or A0 <= 0 or A0 > A0_MAX_ESTIMADO:
        A0 = max_obs * 100
    if A0 < A0_MIN_SEMILLA:
        A0 = A0_MIN_SEMILLA

    bounds = limites_grid_estaciones(df)
    return aplicar_dominio_fisico(np.array([x0, y0, z0, A0], dtype=float), bounds)


def recortar_paso_espacial(delta_m):
    delta_m = np.asarray(delta_m, dtype=float).copy()
    delta_m[0:3] = np.clip(delta_m[0:3], -MAX_PASO_ESPACIAL, MAX_PASO_ESPACIAL)
    return delta_m


def aplicar_dominio_fisico(m, bounds, m_actual=None):
    x_min, x_max, y_min, y_max = bounds
    m = np.asarray(m, dtype=float)
    A = m[3]
    if A <= 0:
        A = m_actual[3] * 0.1 if m_actual is not None else A0_MIN_SEMILLA
    return np.array([
        np.clip(m[0], x_min, x_max),
        np.clip(m[1], y_min, y_max),
        max(0.1, m[2]),
        A,
    ])


def _escalar_sistema_relativo(G, delta_Az, A_obs):
    w = 1.0 / A_obs
    return G * w[:, np.newaxis], delta_Az * w


def _aplicar_amortiguamiento_diagonal(GTG, lam):
    GTG_damped = GTG.copy()
    for i in range(GTG.shape[0]):
        d = max(GTG_damped[i, i], DIAG_EPS)
        GTG_damped[i, i] = d + lam * d
    return GTG_damped


def inversion_gauss_newton(df, m_inicial=None, max_iter=MAX_ITER_DEFAULT, tol=1e-4, lambda_init=1e-3):
    A_obs = df['Amplitud_Azi'].values
    bounds = limites_grid_estaciones(df)
    if m_inicial is None:
        m_inicial = calcular_semilla_inteligente(df)
    else:
        m_inicial = aplicar_dominio_fisico(np.array(m_inicial, dtype=float), bounds)

    m = np.array(m_inicial, dtype=float)
    historial_errores = []
    lam = lambda_init

    idx_pico = int(np.argmax(A_obs))
    print("\n--- INICIANDO INVERSIÓN (Gauss-Newton + LM) ---")
    print(f"Estación pico: {df.iloc[idx_pico]['Estacion']} | Semilla: {m}")

    for k in range(max_iter):
        G, A_pred = calcular_jacobiano_analitico(df, m)
        delta_Az = A_obs - A_pred
        error_actual = np.sum((delta_Az / A_obs) ** 2)
        historial_errores.append(error_actual)

        G_rel, delta_rel = _escalar_sistema_relativo(G, delta_Az, A_obs)
        GTG = G_rel.T @ G_rel
        GTG_damped = _aplicar_amortiguamiento_diagonal(GTG, lam)
        delta_m = recortar_paso_espacial(
            np.linalg.inv(GTG_damped) @ G_rel.T @ delta_rel
        )

        m_candidato = aplicar_dominio_fisico(m + delta_m, bounds, m)

        A_pred_cand = modelo_atenuacion(
            df['X'].values, df['Y'].values, df['Z'].values, m_candidato
        )
        error_candidato = np.sum(((A_obs - A_pred_cand) / A_obs) ** 2)

        if error_candidato < error_actual:
            m = m_candidato
            lam = max(lam / 10, 1e-10)
        else:
            lam *= 10

        if (k + 1) % 50 == 0 or k == 0 or error_actual < tol:
            print(
                f"Iteracion {k + 1:03d} | Error: {error_actual:.6e} | lambda={lam:.1e} | "
                f"x0={m[0]:.2f}, y0={m[1]:.2f}, z0={m[2]:.2f}, A0={m[3]:.2f}"
            )

        if np.linalg.norm(delta_m) < tol:
            print(f"Convergencia alcanzada en iteración {k + 1}.")
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

    print(f"\nGenerando {num_cortes} cortes en z in [{z_min}, {z_max}]...")
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

    print(f"Uniendo frames -> {output_video}")
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
    m_estimado, errores = inversion_gauss_newton(df)

    print("\n================ RESULTADOS FINALES ================")
    print(f"Fuente real:     x={fuente_real[0]:.2f}, y={fuente_real[1]:.2f}, z={fuente_real[2]:.2f}, A0={fuente_real[3]:.2f}")
    print(f"Fuente estimada: x={m_estimado[0]:.2f}, y={m_estimado[1]:.2f}, z={m_estimado[2]:.2f}, A0={m_estimado[3]:.2f}")
    print("========================================================\n")
