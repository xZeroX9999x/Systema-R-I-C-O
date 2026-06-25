# R-I-C-O Bot v5.0

Sistema autónomo de análisis de portafolio con **lógica dual**: buy-and-hold para ETFs diversificados + tácticas técnicas para acciones individuales. Ejecuta semanalmente en GitHub Actions y envía un reporte HTML por correo.

## Filosofía

La versión anterior (v3.0) trataba a todos los activos con las mismas reglas: RSI alto → vender, RSI bajo → comprar. Esto destruye valor en ETFs globales porque:

- **Dalbar 2024**: el inversor promedio que intenta hacer market timing pierde ~8% anual vs buy-and-hold.
- **J.P. Morgan**: perderse los 30 mejores días del mercado en los últimos 20 años reduce el retorno un 84%.
- **Evidencia**: los índices con 9.000+ acciones tienen deriva alcista estructural; el RSI solo funciona bien como señal de reversión en activos individuales con comportamiento mean-reverting.

v5.0 separa la lógica y mejora con:

- ✅ **Gestión de estado transaccional** con SQLite para trailing stop real
- ✅ **Backtesting vectorizado** para validación empírica de señales
- ✅ **Asignación por volatilidad targeting** (risk budgeting)
- ✅ **Contexto cualitativo** con LLM (solo informativo, no decisivo)
- ✅ **Precios ajustados** para evitar problemas con splits y dividendos

## Estructura del proyecto
