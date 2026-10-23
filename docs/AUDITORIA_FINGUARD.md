# Auditoría de FinGuard antes de publicación

**Estado posterior:** la revisión local adicional y sus límites están en [QA_PREPUBLICACION.md](QA_PREPUBLICACION.md). Se ejecutaron navegador real, instalación nueva y escaneos, y se cambió la caché a alcance de sesión. El detalle original de esta auditoría se conserva como historial.

Fecha: 23 de octubre de 2026. Alcance: implementación local actual, sin publicación en GitHub ni despliegue en Streamlit Cloud. No se modificaron fórmulas, comportamiento, interfaz ni dependencias de producción. Se añadieron pruebas y archivos de evidencia.

## Actualización tras aprobación de las dos correcciones

El informe original que sigue documenta la versión auditada antes de corregirla. Posteriormente el usuario autorizó corregir únicamente F-01 y F-02. Ambos están ahora resueltos:

- **F-01:** el donut y el texto de progreso muestran **69.77%** en ambos idiomas, sin alterar la fracción calculada.
- **F-02:** la evaluación patrimonial usa el pago adicional factible del primer mes base sin emergencia, obtenido del motor ya validado. Respeta efectivo disponible, intereses y deuda pendiente tras el pago mínimo. Conserva la definición de disponible después del ahorro previsto.
- Verificación posterior ejecutada: **170 pruebas aprobadas, ninguna fallida**, registrada en `audit_pytest_corrections.xml`. Incluye las dos regresiones originales y tres casos nuevos de límite de deuda, intereses y capacidad de aportación, en ambos idiomas.

No se modificaron los supuestos de pagos mínimos, el alcance de las cachés ni las observaciones O-01 a O-04. Las verificaciones externas y visuales pendientes del informe original siguen pendientes; esta corrección no constituye aprobación de despliegue.

## Dictamen

**Validación financiera aprobada para los casos y supuestos probados; publicación pendiente de correcciones y verificaciones adicionales.** La última ejecución completa produjo **165 pruebas aprobadas y 2 fallidas, sobre 167 ejecutadas**. Las dos fallidas documentan defectos reproducibles y no se ocultaron con `skip` o `xfail`. No se considera aprobada la versión completa para publicar.

No se identificó un error en las fórmulas financieras centrales dentro del alcance ejecutado. Esto no equivale a certificar todos los datos posibles, reproducir contratos bancarios o garantizar resultados financieros. Hay un error funcional de severidad media en el aviso de capacidad patrimonial y una discrepancia de precisión visual de severidad baja. También hay observaciones sobre privacidad, supuestos de pagos mínimos y documentación.

## Evidencia y método

- Suite previa, ejecutada antes de añadir pruebas: **79 aprobadas**; evidencia `audit_pytest_baseline.xml`.
- Auditoría adicional: **86 pruebas de validación independiente** y **2 pruebas de requisitos actualmente incumplidos**. La ejecución completa final incluye ambas y los casos previos; evidencia `audit_pytest_final.xml`.
- `audit_pytest_independent.xml` corresponde a una ejecución intermedia con 85 pruebas aprobadas. El caso adicional de endeudamiento desde deuda inicial cero se ejecutó después y está incluido en el XML final. No deben sumarse los XML de ejecuciones distintas.
- Entorno ejecutado: Windows; Python 3.14.7; Streamlit 1.66.1; Pandas 3.1.0; Plotly 6.9.0; Pytest 9.1.1.
- Se usaron aritmética `Decimal`, fórmulas cerradas de amortización, suma independiente de flujos capitalizados y ejemplos calculados explícitamente. Una segunda hoja mensual independiente usa prioridades de asignación y saldos `Decimal`.
- Se contrastaron 24 trayectorias completas de 120 meses: cuatro políticas —base y tres estrategias— por seis escenarios. Se compararon ahorro, deuda, intereses, pagos obligatorios/adicionales, aportaciones, endeudamiento nuevo e intereses pagados.
- Otros 12 perfiles deterministas generados con semillas fijas comprueban 48 trayectorias de 24 meses, con conservación mensual de fuentes/usos y saldos. Estas identidades complementan los oráculos; por sí solas no prueban que una política financiera sea apropiada.
- Las proyecciones se compararon con sumas independientes de flujos bajo seis tasas, tres pausas, dos horizontes y dos aportaciones mensuales: 72 configuraciones.
- AppTest verificó interacción, estado, contenido emitido y especificaciones de gráficos. No representa una comprobación visual del navegador.
- `audit_evidence.json` registra versiones, saldos observados, escenarios, resultados de estrategias, disponibilidad de herramientas y hashes de archivos productivos. Los importes de ese archivo son datos ficticios.

Para reproducir desde la raíz:

```powershell
.venv\Scripts\python.exe -m pytest -q --junitxml=docs/audit_pytest_final.xml
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m compileall -q finguard streamlit_app.py
```

Pytest devuelve actualmente código 1 debido a los dos hallazgos pendientes. `pip check` terminó con «No broken requirements found». `compileall` terminó sin errores. No se debe describir la suite completa como verde.

## 1. Diagnóstico inicial: esperado frente a real

Se conservaron los datos solicitados: ingreso 4,000; esenciales 2,000; discrecionales 500; pago mínimo 150; ahorro 4,500; aportación 400; meta tres meses. Deuda 3,000 y APR 24% completan el perfil para simulaciones.

| Indicador | Cálculo independiente | Resultado real | Estado |
|---|---|---|---|
| Flujo antes de ahorrar | 4,000 − 2,000 − 500 − 150 | $1,350.00 | Aprobado |
| Disponible después de ahorrar | 1,350 − 400 | $950.00 | Aprobado |
| Cobertura | 4,500 / 2,150 = 2.093023… | 2.09 meses | Aprobado |
| Meta | 3 × 2,150 | $6,450.00 | Aprobado |
| Faltante | max(0, 6,450 − 4,500) | $1,950.00 | Aprobado |
| Pagos / ingreso neto | 150 / 4,000 × 100 | 3.75% | Aprobado |
| Fracción de meta cubierta | 4,500 / 6,450 × 100 | 69.76744186046511% internamente | Aprobado en cálculo |
| Porcentaje visible solicitado | Redondeado a dos decimales: 69.77% | Donut y texto de avance: 70% | Fallido: precisión visual |

La cobertura incluye gastos esenciales y pagos obligatorios; excluye discrecionales. La razón se etiqueta sobre ingreso neto, no como DTI convencional de un prestamista. Los pagos adicionales opcionales no forman parte de los seis indicadores originales y se explican por separado.

## 2. Emergencias: resultados comprobados

Política base, perfil inicial, 24 meses, APR 24%, aportación prevista de 400 y pago adicional cero. La factura aparece una vez en el mes 1; las alteraciones de ingresos/costos duran tres meses en los escenarios correspondientes.

### Primer mes: esperado y observado coinciden

| Escenario | Flujo antes de asignaciones | Ahorro al cierre | Deuda al cierre | Préstamo nuevo | Aportación real al ahorro |
|---|---:|---:|---:|---:|---:|
| Factura médica $2,500 | -$1,150.00 | $3,350.00 | $2,910.00 | $0.00 | $0.00 |
| Reparación $10,000 | -$8,650.00 | $0.00 | $7,060.00 | $4,150.00 | $0.00 |
| Pérdida total de ingreso | -$2,650.00 | $1,850.00 | $2,910.00 | $0.00 | $0.00 |
| Ingreso reducido 30% | $150.00 | $4,650.00 | $2,910.00 | $0.00 | $150.00 |
| Esenciales aumentan $300 | $1,050.00 | $4,900.00 | $2,910.00 | $0.00 | $400.00 |

El gasto médico no resta simplemente 2,500 al ahorro inicial: el modelo usa primero el excedente de ingreso del mismo mes. Por eso quedan 3,350, no 2,000. Es una decisión de orden de operaciones documentada, no un error aritmético.

### Cierre a 24 meses

Estos saldos e intereses coinciden con la hoja independiente `Decimal`. Los meses de logro/recuperación también se verifican mediante las pruebas de definiciones y los casos de recuperación de la suite.

| Escenario | Ahorro final | Deuda final | Interés acumulado | Nuevo crédito total | Mes de meta / recuperación |
|---|---:|---:|---:|---:|---|
| Médico $2,500 | $6,450.00 | $262.03 | $862.03 | $0.00 | 9 / 9 |
| Reparación $10,000 | $6,450.00 | $6,806.16 | $3,256.16 | $4,150.00 | 18 / no alcanzada |
| Desempleo tres meses | $6,450.00 | $5,515.33 | $2,665.33 | $3,450.00 | 20 / no alcanzada |
| Reducción 30%, tres meses | $6,450.00 | $262.03 | $862.03 | $0.00 | 7 / 7 |
| Esenciales +$300, tres meses | $6,450.00 | $262.03 | $862.03 | $0.00 | 5 / 5 |

En el desempleo se comprueban explícitamente las deudas de los primeros tres meses: 2,910; 3,618.20; 6,190.564. El ahorro se agota en el mes 2; el ingreso vuelve a 4,000 en el mes 4.

### Supuestos que condicionan los resultados

1. Una emergencia activa; comienza en el mes 1. Sin incertidumbre, inflación, cambios fiscales ni prestaciones por desempleo.
2. El desempleo no reduce automáticamente los gastos discrecionales de 500; se mantiene el presupuesto introducido.
3. Interés del mes = deuda al inicio × APR / 100 / 12. Se acumula antes de pagos; el crédito nuevo genera intereses desde el siguiente mes.
4. Pago obligatorio = mínimo entre el importe fijo configurado y deuda más intereses. No se recalcula mediante una fórmula del emisor.
5. Primero ingreso, luego gastos y pago obligatorio. El déficit consume ahorro y después se financia con crédito hipotético ilimitado, al mismo APR. No se modelan aprobación, límites, mora, comisiones ni período de gracia.
6. Los excedentes financian ahorro y pagos adicionales según política; no se descuentan dos veces. Nunca se permiten saldos negativos de ahorro o deuda.
7. Meta de ahorro fija según el perfil previo; no disminuye al amortizar deuda ni aumenta durante el incremento temporal de gastos. Las aportaciones se detienen al alcanzar la meta.
8. El efectivo sin asignar se muestra por mes; no se acumula automáticamente en otra cuenta ni se invierte.
9. «Recuperación» exige ahorro en la meta y deuda no superior a la inicial después del último mes del impacto. No exige deuda cero, ni promete mantener esa condición en meses posteriores. Los meses se cuentan desde el inicio, no desde el fin del desempleo.
10. Se usa precisión de coma flotante durante la simulación y redondeo al presentar; no redondeo bancario de cada transacción. Las comparaciones independientes usan tolerancias de hasta 0.0000001 USD en trayectorias ordinarias.

La aproximación APR/12 es válida para el modelo mensual elegido, pero no debe anunciarse como reproducción exacta de una tarjeta real: el CFPB describe emisores que calculan y capitalizan intereses diarios. [CFPB: tasa periódica diaria](https://www.consumerfinance.gov/ask-cfpb/what-is-a-daily-periodic-rate-on-a-credit-card-en-46/).

## 3. Deuda e intereses

Se aprobaron pruebas ejecutadas de APR cero, APR 12/24/36%, pago cero, pago inferior al interés, deuda cero, amortización final y liberación del pago mínimo después de liquidar deuda. La fórmula cerrada usada para contrastar el saldo de una deuda con pago fijo P es:

```text
B(n) = max(0, B(0)*(1+r)^n - P*((1+r)^n-1)/r), r = APR/1200
```

Para tasa cero se usa `max(0, B(0)-P*n)`. El pago final se comprueba por separado y se limita a la deuda con su interés. El interés acumulado se reconcilia con deuda final − deuda inicial + pagos totales − nuevos préstamos.

Los intereses pagados se atribuyen primero a intereses acumulados pendientes, sin descontar el mismo pago dos veces. El principal inicial incluye toda deuda anterior a la simulación. Si el mínimo no cubre el interés, aumenta la deuda; esto es amortización negativa coherente con los supuestos, no un fallo de la fórmula.

**Limitación confirmada importante:** si se parte con deuda cero y mínimo cero, una factura de 10,000 produce un préstamo nuevo de 4,000; el mes siguiente suma 80 de interés, paga cero como mínimo y cierra en 4,080. La prueba confirma el contrato actual del modelo, no que una tarjeta real permita pagos mínimos cero. Antes de publicar conviene hacer este supuesto más explícito en la interfaz. Cambiar a mínimos dinámicos sería una decisión de modelo que requiere aprobación.

## 4. Recuperación

Las tres políticas emplean el mismo perfil, mismo shock y mismo límite de asignación. No se suman otra vez las aportaciones previstas del perfil. Se limita la asignación al excedente real. La política deuda primero cubre la reserva elegida antes del pago adicional; esa reserva puede consumirse ante déficits.

Ejemplo independiente sin shock y límite mensual 400: ahorro primero aporta 400 y paga cero adicional; deuda primero aporta cero y paga 400 adicional; equilibrada aporta 200 y paga 200 adicional. Todas dejan 950 sin asignar en el primer mes.

Con factura médica de 2,500 y reserva cero:

| Estrategia | Ahorro al mes 24 | Deuda al mes 24 | Interés acumulado/pagado | Mes de meta |
|---|---:|---:|---:|---:|
| Ahorro primero | $6,450.00 | $0.00 | $571.88 | 9 |
| Deuda primero | $6,450.00 | $0.00 | $257.67 | 15 |
| Equilibrada | $6,450.00 | $0.00 | $364.87 | 14 |

Los saldos de las trayectorias fueron contrastados con la hoja independiente. Que una política reduzca más el interés de este ejemplo no la convierte en recomendación universal: también cambia cuándo se dispone de liquidez. Se verificaron el límite común de presupuesto, la reserva, la redistribución al liquidar deuda o llenar el fondo y las tablas a 12/24 meses.

## 5. Proyecciones patrimoniales

Tasa mensual efectiva = `(1 + tasa_anual/100)^(1/12) − 1`. Se aplica el rendimiento al saldo inicial del mes y se deposita la aportación al final. El contraste independiente suma cada flujo capitalizado durante los meses restantes, en vez de reutilizar el bucle de producción.

| Configuración | Esperado independiente | Real |
|---|---:|---:|
| Inicial 1,000; aporte 100; 12 meses; 0% | $2,200.00 | $2,200.00 |
| Misma configuración, pausa inicial tres meses | $1,900.00 | $1,900.00 |
| Inicial 1,000; sin aportaciones; 12 meses; 12% efectivo | $1,120.00 | $1,120.00 |
| Inicial 1,000; sin aportaciones; 12 meses; −10% efectivo | $900.00 | $900.00 |
| Inicial 1,000; aporte 200; diez años; 5% efectivo | $32,501.53 | $32,501.53 |
| Misma configuración, pausa inicial tres meses | $31,532.10 | $31,532.10 |

Se verificaron tasas negativas, tasa cero, pausa que omite aportaciones sin recuperarlas después, capital aportado y casos inválidos. No se confundió APR de tarjeta con tasa efectiva anual de proyección.

Las proyecciones son independientes del fondo de emergencia y de las trayectorias de deuda. El saldo inicial no se retira automáticamente del fondo y los intereses de deuda no se descuentan otra vez. No hay comisiones, impuestos, inflación, volatilidad, probabilidades ni selección de inversiones. El tipo de meta es una etiqueta de planificación, no un modelo específico de hipoteca o jubilación. La línea de 0% tampoco garantiza que las aportaciones puedan financiarse. Como referencia educativa de parámetros, se consultó [Investor.gov: calculadora de interés compuesto](https://www.investor.gov/financial-tools-calculators/calculators/compound-interest-calculator); no se ejecutó ni se afirmó equivalencia numérica con esa calculadora externa.

## 6. Hallazgos y correcciones propuestas

| ID | Gravedad | Hallazgo | Evidencia / corrección propuesta |
|---|---|---|---|
| F-01 | Baja | La meta cubierta se presenta como 70% y no 69.77% | Cálculo correcto; formato entero en `ui_assessment.py:90` y texto de progreso. Ajustar solo precisión visible, en ambos idiomas. Prueba de requisito ejecutada y fallida. |
| F-02 | Media | Falso aviso de aportación patrimonial sin financiación cuando el pago extra no es ejecutable | Con deuda/mínimo cero, extra previsto 1,500 y aporte patrimonial 200, hay 1,100 tras ahorro previsto; el motor paga extra cero, pero `ui_wealth.py:45` resta 1,500 sin limitarlo. Alinear la evaluación con un pago extra factible, preservando la definición de los indicadores base. Prueba ejecutada y fallida. |
| O-01 | Media, privacidad/documentación | La descripción puede sugerir que todos los resultados financieros duran únicamente la sesión, pero las cachés tienen alcance global por defecto | `ui_simulation.py:13–14` y `ui_wealth.py` usan `st.cache_data` sin alcance de sesión ni TTL. No se demostró una filtración entre usuarios. Acordar caché de sesión, eliminación del caché para estos cálculos pequeños, o una descripción exacta de retención. |
| O-02 | Media, comunicación del modelo | Un mínimo fijo cero no cambia cuando aparece deuda nueva; un mínimo inferior al interés causa deuda creciente | Comportamiento reproducido y compatible con `docs/model.md`. Hacer visible el supuesto en el contexto de resultados; cualquier fórmula dinámica necesita aprobación y validación propia. |
| O-03 | Baja, documentación | README conserva «Hi, Carlos / Hola, Carlos» aunque la aplicación muestra «Welcome, Carlos / Bienvenido, Carlos» | Corregir descripción antes de publicar; no afecta números ni ejecución. |
| O-04 | Baja, presentación | Los gráficos forman valores negativos como `$-650.00`, mientras las tarjetas usan `-$650.00` | Detectado por inspección de plantillas de tooltip y helper monetario; normalizar formato tras aprobación. El importe y signo no cambian. Apariencia final en navegador pendiente. |

O-01 se apoya en la [documentación oficial de `st.cache_data`](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data): el alcance global comparte caché entre sesiones y devuelve copias por llamada. En el código actual los argumentos financieros forman parte de la clave y se probó que dos sesiones con ingresos distintos reciben resultados distintos. Esto no prueba aislamiento, borrado ni seguridad integral. No se observó envío a servicios financieros externos ni persistencia de esos datos en archivos desde el código de la aplicación.

## 7. Casos extremos, estado y experiencia bilingüe

**Ejecutados y aprobados:** ingreso cero, ahorro cero, deuda cero con pago obligatorio cero, flujo negativo, factura superior al ahorro, obligaciones cero y razones indefinidas, meta cero, aportaciones sin presupuesto, APR cero, deuda con interés superior al pago, horizonte inválido y pausas inválidas. Se comprueban rechazo de NaN/infinito/negativos, rechazo de desbordamiento en los casos existentes y que las divisiones indefinidas se presenten como «No definido / Not defined».

Se comprobaron los cinco escenarios en ambos idiomas, igualdad de importes y continuidad de selecciones, perfil compartido entre cinco pestañas, conservación del nombre de demostración, navegación y reinicio de importes. Los textos traducidos de «no alcanzado» se normalizaron al contrastar resultados; una traducción correcta no se consideró un cambio financiero.

Se inspeccionaron las ocho especificaciones Plotly emitidas para el caso inicial: datos del waterfall, segmentos 4,500/1,950 del donut, y ausencia de NaN/infinito en esas especificaciones. Esto no certifica todos los gráficos bajo todas las entradas. Los títulos de tarjetas usan Markdown fuera de la etiqueta oculta de `st.metric` para permitir ajuste de línea; la moneda del texto enriquecido se escapa para evitar interpretación como LaTeX.

## 8. Seguridad y comprobaciones técnicas

**Ejecutado:** Pytest; compilación de todos los módulos; `pip check`; revisión de código de entradas, cachés y E/S; comprobación limitada de patrones de claves AWS/OpenAI y claves privadas en archivos productivos/configuración, sin coincidencias; prueba de dos sesiones con perfiles diferentes. No se detectaron en el código productivo revisado ejecución dinámica con `eval/exec`, SQL, conexiones bancarias, cargas de archivos, HTML inseguro habilitado ni escritura externa de datos financieros. Estas revisiones son limitadas y no equivalen a un análisis de amenazas completo ni a una garantía de ausencia de secretos.

**No ejecutado:** escaneo de vulnerabilidades de dependencias (`pip-audit` no está instalado), análisis automatizado Bandit/Ruff, cobertura de líneas, prueba de penetración, infraestructura HTTPS o logs del host. `pip check` solo confirma compatibilidad declarada entre paquetes instalados: no certifica que estén libres de CVE. Los límites de versiones de `pyproject.toml` no son un lockfile reproducible. No se cambiaron ni instalaron herramientas como parte de esta auditoría.

## 9. Aún sin verificar y condiciones antes de publicar

1. Resolver F-02 y F-01, y repetir la suite completa sin omitir las regresiones.
2. Aclarar O-01 y O-02 antes de invitar a introducir datos financieros reales. La aplicación sigue siendo una demostración sin autenticación; un nombre visible no ofrece protección de cuenta.
3. Actualizar documentación y revisar formato monetario negativo.
4. Revisar en navegador real escritorio y móvil: textos recortados, saltos de línea, scroll de pestañas, tooltips, contraste, teclado y lector de pantalla. No hay evidencia visual para marcarlos aprobados.
5. Probar instalación limpia y ejecución en el Python/OS elegidos para Streamlit Cloud. Solo se verificó el entorno local existente; no se hizo despliegue, prueba de arranque remoto ni validación de permisos/logs del proveedor.
6. Ejecutar un escaneo actualizado de dependencias y revisar el contenido exacto que se enviará a GitHub. La revisión local de patrones no sustituye el examen del historial del repositorio ni de la configuración del hosting.

**Las correcciones siguen pendientes de aprobación.** Los únicos cambios realizados para esta auditoría son pruebas y evidencia documental. No se modificó la experiencia de usuario ni la lógica financiera para obtener resultados verdes.
