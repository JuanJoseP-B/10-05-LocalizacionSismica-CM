import numpy as np
from backend.engine import SeismicEngine

def run_simulation():
    print("--- Iniciando Fase 1: Simulación y Optimización ---")
    engine = SeismicEngine()
    
    # 1. Generación de Sensores
    stations = engine.generate_stations(count=6, x_range=(0, 100), y_range=(0, 100), z_range=(0, 5))
    print(f"Estaciones generadas:\n{stations}")
    
    # Fuente Real (Sismo hipotético)
    real_source = [45.0, 60.0, 15.0]
    real_A0 = 500.0
    print(f"Fuente Real: Pos={real_source}, A0={real_A0}")
    
    # 2. Simulación de señales con ruido
    observed_amplitudes = engine.simulate_signal(real_source, real_A0)
    print(f"Amplitudes observadas (con ruido):\n{observed_amplitudes}")
    
    # 4. Optimización
    print("Minimizando función de error...")
    result = engine.solve(observed_amplitudes)
    
    if result.success:
        estimated_m = result.x
        print("\nResultados de la Optimización:")
        print(f"Posición Estimada: x={estimated_m[0]:.2f}, y={estimated_m[1]:.2f}, z={estimated_m[2]:.2f}")
        print(f"Amplitud A0 Estimada: {estimated_m[3]:.2f}")
        print(f"Error Final (SSR): {result.fun:.4f}")
        
        # Comparación
        error_dist = np.linalg.norm(estimated_m[:3] - real_source)
        print(f"Distancia de error a la fuente real: {error_dist:.2f} unidades")
    else:
        print("La optimización falló.")

    print("\n--- Fase 2: Preparación de Datos de Visualización ---")
    # Ejemplo de generación de datos para mapa de calor en z=15
    print("Generando datos para mapa de calor en z=15...")
    X, Y, Z = engine.get_heatmap_data(15.0, observed_amplitudes, real_A0, grid_size=10)
    print(f"Matriz de error generada (muestra 2x2):\n{Z[:2, :2]}")
    
    # Ejemplo de curva de error global
    print("Generando curva E_min(z)...")
    z_vals, e_vals = engine.get_global_error_curve(observed_amplitudes, real_A0, z_range=(0, 30), steps=10)
    print(f"Profundidad más probable (E_min): {z_vals[np.argmin(e_vals)]:.2f}")

if __name__ == "__main__":
    run_simulation()
