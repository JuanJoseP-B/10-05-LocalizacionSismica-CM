# Fase 1: Backend - Motor de Simulación y Optimización Sismológica

**Repositorio:** `https://github.com/JuanJoseP-B/10-05-LocalizacionSismica-CM.git`
**Estándar:** GitFlow (Ramas: `main`, `develop`, `feature/backend-core`)

## 1. Contexto Técnico
[cite_start]Desarrollar el motor matemático para resolver el problema inverso de localización de una fuente sísmica[cite: 12]. Se debe implementar el modelo de atenuación:
[cite_start]$$A_{zi} = A_0 \frac{e^{-R_i}}{R_i} + \epsilon_i$$ [cite: 26]

## 2. Requerimientos de Implementación (Fase de Simulación)
1. [cite_start]**Generación de Sensores:** Crear un módulo que defina $M$ estaciones con coordenadas $(x_i, y_i, z_i)$[cite: 70].
2. [cite_start]**Inyección de Ruido:** Implementar una función para generar ruido gaussiano $\epsilon$ con $\mu=0$ y $\sigma = \alpha A_0 \frac{e^{-R_i}}{R_i}$, donde $\alpha=0.05$[cite: 35, 37].
3. [cite_start]**Función de Error:** Programar la función objetivo $E_{rr} = \sum_{i=1}^{M} (A_{zi} - A_{zi}')^2$[cite: 50].
4. [cite_start]**Algoritmo de Optimización:** Implementar un método iterativo (Mínimos Cuadrados Linealizados o Búsqueda por Malla) para minimizar $E_{rr}$ y hallar $m = [x_0, y_0, z_0, A_0]^T$[cite: 41, 60].

## 3. Flujo de GitFlow
- Inicializar repositorio local y conectar con el remoto.
- Crear rama `develop`.
- Crear rama `feature/simulation-engine` para el desarrollo de las fórmulas.
- Realizar commits modulares (ej: "feat: implement gauss noise function").
- Finalizar feature con un merge a `develop`.