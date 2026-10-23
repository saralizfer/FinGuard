# Revisión local antes de publicar FinGuard

Fecha: 23 de octubre de 2026. Se completaron las comprobaciones locales pendientes. No se creó ningún repositorio remoto ni se publicó o desplegó la aplicación.

## Resultado ejecutado

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Instalación nueva con `pip install -r requirements.txt` | Aprobada en `.qa-venv`, Python 3.14.7/Windows | Instalación y construcción de wheel finalizadas sin errores |
| Suite completa en el entorno nuevo | **170 aprobadas, 0 fallidas** | `qa/pytest_fresh_environment.xml` |
| Compatibilidad de dependencias | Sin dependencias rotas | `pip check`, ejecutado tras instalar herramientas QA |
| Dependencias con vulnerabilidades conocidas | **0 reportadas en 42 distribuciones consultadas** | `qa/dependencies.json`, pip-audit 2.10.1; se excluyó el proyecto editable `finguard` |
| Análisis estático de la aplicación | **0 hallazgos y 0 errores reportados** | `qa/bandit.json`, Bandit 1.9.4 |
| Arranque local en entorno nuevo | HTTP 200 en salud del servidor | `qa/browser.json`, `qa/server.log` |
| Cinco pestañas × dos idiomas × dos tamaños | **20 recorridos de vista aprobados** | `qa/browser.json`, Chromium 156.0.8078.4 |
| JavaScript durante el último recorrido | Sin errores de página ni de consola registrados | `qa/browser.json` |
| Capturas de pantalla | 52 capturas guardadas | `qa/*.png` |

Los escaneos corresponden a las versiones instaladas y a las bases de datos consultadas en esta ejecución. No demuestran ausencia de vulnerabilidades desconocidas, ni cubren automáticamente versiones que se instalen en el futuro. `pip-audit` consultó las dependencias del entorno de desarrollo de la aplicación; las herramientas QA están aisladas en `.qa-venv` y no se añaden a las dependencias productivas.

## Cambios realizados

- Las tres cachés financieras usan `scope="session"`: simulación, comparación de recuperación y proyección. Se mantienen los límites de entradas y no se habilita persistencia en disco. Esto no convierte la demostración en una cuenta autenticada.
- El simulador y la comparación explican en ambos idiomas que el pago mínimo es fijo, no se recalcula al endeudarse y puede resultar inferior al interés mensual. Se conserva el modelo validado.
- Las leyendas de las series temporales se trasladaron debajo de los gráficos para reducir el solapamiento observado en móvil. Se conservaron datos e interactividad.
- Se actualizó el saludo descrito en README para que coincida con la aplicación.
- Se excluyeron de Git los entornos, navegadores descargados, cachés de auditoría y directorio de construcción.

Las correcciones anteriores del 69.77% y del pago adicional factible siguen verificadas por la suite. No se cambiaron fórmulas de ingreso, cobertura, deuda, asignación de estrategias ni capitalización patrimonial.

## Revisión de navegador

Se ejecutó Chromium real, sin interfaz visible, con escritorio de 1440 × 1000 y emulación móvil de 390 × 844. Cada combinación de idioma/pestaña comprobó selección de pestaña, presencia de gráficos cuando corresponde, ausencia de excepciones Streamlit, conservación de los importes iniciales y ausencia de desbordamiento horizontal de toda la página. El porcentaje 69.77% se comprobó también en el DOM. La navegación de pestañas puede desplazarse horizontalmente en móvil; no se exige que cinco etiquetas largas quepan simultáneamente en 390 píxeles.

Se inspeccionaron visualmente capturas del diagnóstico de escritorio y móvil, distribución del presupuesto, emergencias y proyecciones patrimoniales. Los importes, encabezados y explicaciones revisados se leen; los gráficos se apilan en móvil. Las leyendas patrimoniales resultaban apretadas y se ajustó su posición antes del último recorrido aprobado. Las capturas son vistas de página y regiones de gráficos, no una certificación de cada píxel ni de cada entrada posible.

El primer recorrido automático, que no esperaba el fin de las actualizaciones del servidor, encontró una discrepancia durante el cambio de idioma móvil. La herramienta se corrigió para esperar el estado `notRunning` y comprobar seis importes del perfil después de cada navegación. Los dos recorridos completos posteriores aprobaron esas comprobaciones. No se modificaron los cálculos para resolver esa discrepancia. No se certifica comportamiento ante interrupciones deliberadas o navegación más rápida que las actualizaciones.

Para reproducir, instalar las herramientas QA en un entorno separado y Chromium de Playwright, definir `PLAYWRIGHT_BROWSERS_PATH` apuntando al directorio de navegadores, y ejecutar `scripts/check_browser.py`. El script inicia un servidor propio únicamente en `127.0.0.1:8599` y lo detiene al finalizar; no modifica servidores del usuario. En este equipo, las restricciones del entorno requirieron ejecución autorizada del navegador fuera del sandbox.

## Alcance pendiente

- **Despliegue remoto real:** no ejecutado. La instalación y el servidor local no sustituyen una prueba de Streamlit Cloud, sus logs, TLS, permisos o versión de Python. La preparación está en `running.md`.
- **Navegadores y dispositivos:** no se probaron Safari, Firefox, iPhone/Android físicos ni todos los tamaños de pantalla. La vista móvil usada es emulación de Chromium.
- **Accesibilidad completa:** no se realizó auditoría WCAG, lector de pantalla ni recorrido integral de teclado. Los controles y gráficos nativos conservan sus etiquetas accesibles, pero eso no es una certificación.
- **Seguridad integral:** no hubo prueba de penetración, carga concurrente, revisión de infraestructura o garantía de borrado físico de memoria. La caché está limitada por sesión a nivel de API; no existe autenticación ni se invita a tratar el sitio como banca privada.
- **Reproducibilidad futura:** los rangos de `pyproject.toml` siguen sin ser un lockfile. Las versiones del siguiente despliegue deben volver a comprobarse.

La aplicación queda preparada para una publicación de demostración con estos límites conocidos y una comprobación posterior del hosting. No se afirma que ya esté desplegada ni que toda posible condición esté certificada.
