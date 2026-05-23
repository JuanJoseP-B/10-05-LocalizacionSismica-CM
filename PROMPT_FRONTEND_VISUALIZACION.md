# Fase 2: Frontend - Interfaz de Análisis Multivariable

**Repositorio:** `https://github.com/JuanJoseP-B/10-05-LocalizacionSismica-CM.git`
**Estándar:** GitFlow (Ramas: `feature/frontend-ui`)
**Estética:** Minimalista, Glassmorphism, tipografía refinada.

## 1. Requerimientos de Visualización
1. [cite_start]**Mapa de Estaciones:** Renderizar un plano 3D o 2D que muestre la ubicación de los sensores y la fuente real estimada[cite: 107].
2. [cite_start]**Generador de Mapas de Calor:** Visualizar cortes en $z=k$ para mostrar la intensidad de la función de error $E(x, y, z)$[cite: 114].
3. [cite_start]**Gráfica de Error Global:** Implementar una gráfica de $E_{min}(z)$ para identificar visualmente la profundidad del sismo[cite: 118].
4. **Exportación de Datos:** Botón para generar los resultados que se incluirán en el documento LaTeX final.

## 2. Criterios de Evaluación a Cumplir
- [cite_start]**Calidad de Gráficos (20%):** Los mapas deben ser interpretables y claros[cite: 9].
- [cite_start]**Presentación (15%):** Diseño limpio y comunicación visual efectiva del problema[cite: 9].

## 3. Flujo de GitFlow
- Crear rama `feature/frontend-ui` desde `develop`.
- Implementar componentes de visualización (sugerencia: Plotly o Chart.js para los mapas de calor).
- [cite_start]Asegurar que la lógica de la "Función reducida" se represente correctamente en la interfaz[cite: 116].