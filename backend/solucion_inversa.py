import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import os

# ====================================================================
# PROYECTO: Localización de una Fuente Sísmica (Problema Inverso)
# Este script importa el CSV generado por el simulador frontend y 
# utiliza herramientas de cálculo multivariado para encontrar el origen.
# ====================================================================

# 1. CARGA DE DATOS
# ====================================================================
def cargar_datos(filepath):
    """Carga el archivo CSV con las observaciones Az."""
    if not os.path.exists(filepath):
        print(f"❌ Error: No se encontró el archivo '{filepath}'.")
        print("Por favor, ve al simulador web, haz clic en 'Descargar CSV' y pega el archivo en esta misma carpeta.")
        return None
    
    df = pd.read_csv(filepath)
    print("✅ Datos cargados exitosamente:\n", df.head())
    return df

# 2. MODELO MATEMÁTICO Y FUNCIÓN DE ERROR
# ====================================================================
def calcular_Ri(x_i, y_i, z_i, x0, y0, z0):
    """Ecuación 2: Calcula la distancia euclidiana entre fuente y estación."""
    return np.sqrt((x_i - x0)**2 + (y_i - y0)**2 + (z_i - z0)**2)

def modelo_atenuacion(x_i, y_i, z_i, m):
    """
    Ecuación 1 (Sin ruido): Calcula la Amplitud teórica predicha.
    m = [x0, y0, z0, A0]
    NOTA: Se divide R_i por 100 en el exponente para igualar el modelo del simulador.
    """
    x0, y0, z0, A0 = m
    R_i = calcular_Ri(x_i, y_i, z_i, x0, y0, z0)
    R_i = np.where(R_i == 0, 1e-5, R_i) # Evitar división por cero
    return A0 * (np.exp(-R_i / 100) / R_i)

def calcular_error_global(df, m):
    """Ecuación 7: Calcula Err = Sum(A_obs_i - A_pred_i)^2"""
    x_est = df['X'].values
    y_est = df['Y'].values
    z_est = df['Z'].values
    A_obs = df['Amplitud_Azi'].values
    A_pred = modelo_atenuacion(x_est, y_est, z_est, m)
    return np.sum((A_obs - A_pred)**2)

# 3. JACOBIANO Y MÉTODO DE GAUSS-NEWTON (Inversión)
# ====================================================================
def calcular_jacobiano_numerico(df, m, delta=1e-4):
    """Calcula la matriz Jacobiana (G) usando diferencias finitas."""
    x_est, y_est, z_est = df['X'].values, df['Y'].values, df['Z'].values
    num_estaciones = len(df)
    num_params = len(m)
    
    G = np.zeros((num_estaciones, num_params))
    A_pred_base = modelo_atenuacion(x_est, y_est, z_est, m)
    
    for j in range(num_params):
        m_perturbado = np.copy(m)
        m_perturbado[j] += delta
        A_pred_pert = modelo_atenuacion(x_est, y_est, z_est, m_perturbado)
        G[:, j] = (A_pred_pert - A_pred_base) / delta # Ecuación 8
        
    return G, A_pred_base

def inversion_gauss_newton(df, m_inicial, max_iter=50, tol=1e-4):
    """Ecuación 10 y 11: Minimiza el error resolviendo el sistema iterativamente."""
    A_obs = df['Amplitud_Azi'].values
    m = np.array(m_inicial, dtype=float)
    historial_errores = []
    
    print("\n--- INICIANDO INVERSIÓN (Gauss-Newton) ---")
    for k in range(max_iter):
        G, A_pred = calcular_jacobiano_numerico(df, m)
        delta_Az = A_obs - A_pred
        
        error_actual = np.sum(delta_Az**2)
        historial_errores.append(error_actual)
        
        # Ec 10: delta_m = (G^T G)^-1 G^T delta_Az
        GTG = G.T @ G
        GTG += np.eye(len(m)) * 1e-6 # Regularización de Tikhonov (Evita matrices singulares)
        
        delta_m = np.linalg.inv(GTG) @ G.T @ delta_Az
        m = m + delta_m # Ec 11
        
        print(f"Iteración {k+1:02d} | Error: {error_actual:.4f} | Solución temporal: x0={m[0]:.1f}, y0={m[1]:.1f}, z0={m[2]:.1f}, A0={m[3]:.1f}")
        
        if np.linalg.norm(delta_m) < tol:
            print("✅ Convergencia alcanzada.")
            break
            
    return m, historial_errores

# 4. VISUALIZACIÓN: MAPAS DE CALOR Y CORTES Z
# ====================================================================
def graficar_mapa_calor_z(df, z_fijo, A0_fijo, resolucion=60):
    """Cumple el objetivo 4.2: Graficar curvas de nivel para el plano z=k."""
    x_rango = np.linspace(-100, 100, resolucion)
    y_rango = np.linspace(-100, 100, resolucion)
    X, Y = np.meshgrid(x_rango, y_rango)
    Z_err = np.zeros_like(X)
    
    print(f"\nCalculando mapa de calor para el plano de profundidad z = {z_fijo:.2f}...")
    for i in range(resolucion):
        for j in range(resolucion):
            Z_err[i, j] = calcular_error_global(df, [X[i, j], Y[i, j], z_fijo, A0_fijo])
            
    plt.figure(figsize=(9, 7))
    # Usamos log(Error) para resaltar el mínimo visualmente
    cp = plt.contourf(X, Y, np.log10(Z_err + 1e-5), levels=40, cmap='viridis_r')
    plt.colorbar(cp, label='Log10(Error Residual)')
    
    # Marcadores de estaciones
    plt.scatter(df['X'], df['Y'], c='black', marker='^', s=100, label='Estaciones Receptoras')
    
    # Encontrar y marcar el mínimo epicentro en la grilla
    min_idx = np.unravel_index(np.argmin(Z_err), Z_err.shape)
    plt.scatter(X[min_idx], Y[min_idx], c='red', marker='X', s=150, label=f'Epicentro Calculado (x={X[min_idx]:.1f}, y={Y[min_idx]:.1f})')
    
    plt.title(f'Mapa de Calor del Error en Profundidad z = {z_fijo:.2f}m')
    plt.xlabel('Coordenada X (m)')
    plt.ylabel('Coordenada Y (m)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

# ====================================================================
# EJECUCIÓN PRINCIPAL
# ====================================================================
if __name__ == "__main__":
    # Nombre exacto con el que el frontend descarga el archivo
    archivo_csv = "Vector_Az_Observaciones.csv" 
    
    df = cargar_datos(archivo_csv)
    
    if df is not None:
        # Suposición inicial m0 = [x, y, z, A0]
        # (El algoritmo empezará a buscar desde aquí)
        m0 = [0.0, 0.0, 10.0, 1000.0] 
        
        # Resolver el Problema Inverso
        m_estimado, errores = inversion_gauss_newton(df, m0)
        
        print("\n🏆================ RESULTADOS FINALES ================🏆")
        print(f"Coordenada X (x0) estimada:   {m_estimado[0]:.2f} m")
        print(f"Coordenada Y (y0) estimada:   {m_estimado[1]:.2f} m")
        print(f"Profundidad (z0)  estimada:   {m_estimado[2]:.2f} m")
        print(f"Amplitud base (A0) estimada:  {m_estimado[3]:.2f}")
        print("========================================================\n")
        
        # Gráfica 1: Convergencia
        plt.figure(figsize=(7, 4))
        plt.plot(errores, marker='o', linestyle='-', color='b')
        plt.title('Convergencia del Algoritmo de Gauss-Newton')
        plt.xlabel('Número de Iteración')
        plt.ylabel('Error Cuadrático Total (Err)')
        plt.grid(True)
        plt.tight_layout()
        plt.show()
        
        # Gráfica 2: Mapa de Calor en el plano Z óptimo
        graficar_mapa_calor_z(df, z_fijo=m_estimado[2], A0_fijo=m_estimado[3])
