# Metodología: base de datos, impuestos y conversiones

Fase 2 (25/10/2026). Describe cómo se construye cada serie, qué impuestos se aplican en cada fecha
(con su referencia al BOE) y qué factores de conversión se usan. Las decisiones que lo sustentan
están en `DECISIONES.md`; la disponibilidad de cada fuente, en `FUENTES.md`.

## 1. Ficheros de datos (`datos/`)

| Fichero | Contenido |
|---|---|
| `series/<id>.csv` | Una fila por dato en su frecuencia original (día, semana, resolución, trimestre o año). Columnas: `fecha`, `periodo`, `valor_original`, `unidad_original`, `eur_kwh_sin_impuestos`, `eur_kwh_con_impuestos`, `con_impuestos_origen` (original / calculado / no disponible / no aplica), `impuestos_detalle`, `impuestos_pendiente`, `fecha_publicacion`, `referencia` (fichero, identificador BOE o PDF de origen), `nota`. |
| `mensual/<id>.csv` | Media mensual: `media_original`, `media_eur_kwh_sin_impuestos`, `media_eur_kwh_con_impuestos`, `n_datos` y `metodo` (cómo se ha calculado). |
| `metadatos.json` | Descripción de cada indicador (fuente, unidad, frecuencia, impuestos, conversión, primer y último dato) y los factores de conversión. |
| `estado.json` | Resultado de la última ejecución por fuente: ok/error, mensaje, última actualización correcta, último dato y si hay dato nuevo. |
| `fuentes_originales/` | Copia de los documentos fuente que podrían desaparecer: XML del BOE de cada resolución y PDF de AVEBIOM. |
| `impuestos/condiciones_ipc_2026.json` | Condiciones de IPC de las que dependen los impuestos de 2026 (ver §3.6). |

Identificadores de serie: `omie`, `mibgas`, `gasoleo_a`, `pvpc`, `tur2`, `gasoleo_c`, `butano`, `pellet_saco`, `pellet_granel`
(el indicador 8 del encargo tiene dos formatos).

Reglas generales:
- **Nada se rellena.** Si la fuente no da un dato, no hay fila; si no se puede calcular el precio con impuestos, la
  columna queda vacía y `impuestos_pendiente` explica por qué.
- **El histórico se conserva.** Cada actualización carga el CSV existente, añade o sustituye las filas descargadas
  (misma `fecha` + `periodo`) y nunca borra las antiguas. Si una fuente falla, su serie queda como estaba y el
  fallo se registra en `estado.json`.
- **Original frente a calculado.** `valor_original` es siempre el dato de la fuente. Los precios con impuestos de
  PVPC, TUR 2 y butano son calculados (la fuente los publica sin impuestos); los del Boletín Petrolero y AVEBIOM
  son originales.
- Histórico desde el 01/01/2020 donde la fuente lo da (decisión 4); PVPC 2.0TD desde el 01/06/2021; pellet con
  medias anuales hasta 2024 y trimestral desde 4T2024.

## 2. Cómo se construye cada serie

| Serie | Dato original por fila | Frecuencia | €/kWh sin impuestos | €/kWh con impuestos |
|---|---|---|---|---|
| `omie` | Media aritmética de los precios marginales (horarios o cuarto-horarios) del día, España | diaria | €/MWh ÷ 1.000 | no aplica (mayorista) |
| `mibgas` | MIBGAS-ES Index del día de gas | diaria | €/MWh ÷ 1.000 | no aplica (mayorista) |
| `gasoleo_a`, `gasoleo_c` | Precio del lunes en España (Boletín Petrolero), con impuestos; se guarda también el sin impuestos | semanal | €/1.000 l sin imp. ÷ 1.000 ÷ 10,28 | €/1.000 l con imp. ÷ 1.000 ÷ 10,28 |
| `pvpc` | Media aritmética de los valores del indicador 1001 (Península) del día | diaria | €/MWh ÷ 1.000 | (precio + cuota IEE) × (1 + IVA) ÷ 1.000 |
| `tur2` | Término variable TUR.2 de cada resolución (vigente desde su fecha de efectos) | trimestral | c€/kWh ÷ 100 ÷ 0,904 | (precio + IH gas) × (1 + IVA), ÷ 100 ÷ 0,904 |
| `butano` | Precio máximo antes de impuestos (c€/kg) de cada resolución (vigente desde su fecha de efectos) | bimestral | c€/kg × 12,5 kg ÷ 100 → € bombona ÷ 12,5 ÷ 12,73 | (precio × 12,5 kg + IH GLP × 0,0125 t) × (1 + IVA) → € bombona ÷ 12,5 ÷ 12,73 |
| `pellet_saco` | Precio medio del saco de 15 kg (AVEBIOM, IVA incluido) | trimestral (anual hasta 2024) | no publicado | €/saco ÷ 15 ÷ 4,8 |
| `pellet_granel` | Precio medio del granel en volquete (AVEBIOM, IVA y transporte incluidos) | trimestral (anual hasta 2024) | no publicado | €/t ÷ 1.000 ÷ 4,8 |

Medias mensuales (`mensual/<id>.csv`):
- Series diarias y semanales: media aritmética de los datos del mes (la media con impuestos solo se da si está
  disponible para todos los datos del mes).
- TUR 2 y butano: valor vigente cada día del mes, media ponderada por días.
- Pellet: el valor del trimestre se asigna a sus tres meses y la media anual a los meses del año sin dato trimestral
  (en 2024 solo hay el 4T trimestral: enero–septiembre llevan la media anual); `metodo` lo dice expresamente. No es un
  dato mensual, es el dato del periodo que lo cubre.

## 3. Impuestos vigentes en cada fecha (código: `precios/impuestos.py`)

Todas las normas se han leído en el BOE (XML en `datos/fuentes_originales/boe/` cuando se descargan). Los
reales decretos-ley entran en vigor el día siguiente al de su publicación salvo que el artículo fije otra fecha.

### 3.1 IVA de la electricidad (consumidor doméstico, potencia ≤ 10 kW)

| Desde | Hasta | Tipo | Condición | Norma |
|---|---|---|---|---|
| — | 25/06/2021 | 21 % | — | Ley 37/1992, art. 90 |
| 26/06/2021 | 30/06/2022 | 10 % | precio medio del mercado diario del mes anterior > 45 €/MWh (si no, 21 %) | RDL 12/2021 art. 1 (BOE-A-2021-10584); prórrogas RDL 29/2021 (BOE-A-2021-21096) y RDL 6/2022 DF 36ª (BOE-A-2022-4972) |
| 01/07/2022 | 31/12/2023 | 5 % | misma condición | RDL 11/2022 art. 18 (BOE-A-2022-10557); prórroga RDL 20/2022 (BOE-A-2022-22685) |
| 01/01/2024 | 31/12/2024 | 10 % | misma condición | RDL 8/2023 art. 21.1 (BOE-A-2023-26452) |
| 01/01/2025 | 21/03/2026 | 21 % | — | Ley 37/1992, art. 90 |
| 22/03/2026 | 31/05/2026 | 10 % | sin condición de precio | RDL 7/2026 art. 42.a (BOE-A-2026-6544) |
| 01/06/2026 | 30/06/2026 | 10 % o 21 % | solo si el IPC de electricidad de abril de 2026 superó el +15 % interanual | RDL 7/2026 art. 42.a |
| 01/07/2026 | 31/07/2026 | 21 % | — | RDL 18/2026 no reduce el IVA en julio |
| 01/08/2026 | 31/08/2026 | 10 % o 21 % | IPC de electricidad de junio > +15 % | RDL 18/2026 art. 10 (BOE-A-2026-14112) |
| 01/09/2026 | 30/09/2026 | 10 % o 21 % | IPC de electricidad de julio > +15 % | RDL 18/2026 art. 11 |
| 01/10/2026 | 31/10/2026 | 21 % | — | RDL 25/2026 no reduce el IVA en octubre |
| 01/11/2026 | 30/11/2026 | 10 % o 21 % | IPC de electricidad de septiembre > +15 % | RDL 25/2026 art. 18 (BOE-A-2026-20265) |
| 01/12/2026 | 31/12/2026 | 10 % o 21 % | IPC de electricidad de octubre > +15 % | RDL 25/2026 art. 19 |

La condición de los 45 €/MWh se evalúa con la media mensual de la propia serie `omie` del mes natural anterior.
Meses de 2021–2024 en los que no se cumplió (y se aplicó el 21 %): se obtienen del dato, no de una lista fija
(p. ej. marzo–junio de 2024, por los precios de febrero–mayo de 2024).

### 3.2 Impuesto especial sobre la electricidad (IEE)

| Desde | Hasta | Tipo | Norma |
|---|---|---|---|
| — | 15/09/2021 | 5,11269632 % | Ley 38/1992, art. 99 |
| 16/09/2021 | 31/12/2023 | 0,5 % | RDL 17/2021 DA 6ª (BOE-A-2021-14974); prórrogas RDL 29/2021, 6/2022, 11/2022 art. 17, 20/2022 |
| 01/01/2024 | 31/03/2024 | 2,5 % | RDL 8/2023 art. 22 |
| 01/04/2024 | 30/06/2024 | 3,8 % | RDL 8/2023 art. 22 |
| 01/07/2024 | 21/03/2026 | 5,11269632 % | Ley 38/1992, art. 99 |
| 22/03/2026 | 31/05/2026 | 0,5 % | RDL 7/2026 art. 40.Uno |
| 06/2026, 08/2026, 09/2026, 11/2026, 12/2026 | | 0,5 % o 5,11269632 % | según el IPC de electricidad de abril, junio, julio, septiembre y octubre (RDL 7/2026 art. 40.Dos; RDL 18/2026 arts. 12–13; RDL 25/2026 arts. 20–21) |
| 07/2026 y 10/2026 | | 5,11269632 % | sin reducción |

Cuota mínima: 1 €/MWh en usos no industriales (Ley 38/1992 art. 99.2); con el 0,5 % y precios por debajo de
200 €/MWh es la que se aplica. **Aproximación documentada:** la base real del IEE incluye el término de potencia;
aquí se aplica solo al término de energía, que es lo que mide el indicador.

### 3.3 IVA del gas natural (TUR) y de los pellets

| Desde | Hasta | Gas natural | Pellets, briquetas y leña | Norma |
|---|---|---|---|---|
| — | 30/09/2022 | 21 % | 21 % | Ley 37/1992, art. 90 |
| 01/10/2022 | 31/12/2023 | 5 % | 5 % | RDL 17/2022 arts. 5 y 6 (BOE-A-2022-15354); prórroga RDL 20/2022 art. 1 |
| 01/01/2024 | 31/03/2024 | 10 % | 10 % | RDL 8/2023 art. 21.2 y 21.3 |
| 01/04/2024 | 30/06/2024 | 21 % | 10 % | RDL 8/2023 art. 21.3 |
| 01/07/2024 | 21/03/2026 | 21 % | 21 % | Ley 37/1992, art. 90 |
| 22/03/2026 | 31/05/2026 | 10 % | 10 % | RDL 7/2026 art. 42.b |
| 06, 08, 09, 11 y 12/2026 | | 10 % o 21 % | 10 % o 21 % | según el IPC de gas natural (04.5.2.1) de abril, junio, julio, septiembre y octubre |
| 07 y 10/2026 | | 21 % | 21 % | sin reducción |

### 3.4 Impuesto sobre hidrocarburos

- **Gas natural, epígrafe 1.10.1** (usos distintos del carburante): 0,65 €/GJ = 0,00234 €/kWh (sobre PCS, que es como
  factura la TUR). 2026: 0,30 €/GJ del 22/03 al 31/05 (RDL 7/2026 art. 38); junio según IPC de carburantes de abril;
  0,39 en julio; 0,48 en agosto (0,30 si IPC gas junio > 15 %); 0,56 en septiembre (0,30 si IPC julio; 0,39 si solo
  junio) (RDL 18/2026 arts. 5–7); 0,65 en octubre; noviembre 0,65 (0,30 si IPC septiembre); diciembre 0,65 (0,30 si IPC
  octubre; 0,42 si solo septiembre) (RDL 25/2026 arts. 13–15).
- **GLP, epígrafe 1.8** (usos distintos del carburante; butano envasado): 15 €/t = 0,1875 € por bombona de 12,5 kg.
  2026: 0 €/t del 22/03 al 31/05; junio según IPC de carburantes de abril; 3,75 en julio; 7,5 en agosto (0 si IPC
  hidrocarburos licuados junio); 11,25 en septiembre (0 si IPC julio; 3,75 si solo junio); 15 en octubre; noviembre 15
  (0 si IPC septiembre); diciembre 15 (0 si IPC octubre; 5,25 si solo septiembre).

### 3.5 IVA del butano

21 % en todo el periodo salvo del 22/03/2026 al 30/06/2026, en que el RDL 7/2026 art. 42.c aplicó el 10 % a los
productos del epígrafe 1.8 (GLP para usos distintos del carburante), es decir, al butano envasado. Que se aplicó lo
confirma el precio oficial de la bombona del 19/05/2026: 15,39 € = 111,9680 c€/kg × 12,5 kg × 1,10 (con IH a 0 €/t),
y la subida del 21/07/2026 a 17,83 € «por el fin de la rebaja del IVA» (prensa, La Moncloa). En junio la rebaja
siguió vigente porque el IPC de carburantes de abril (+15,5 %) superó el 15 %.

### 3.6 Condiciones de IPC de 2026

Los tipos de junio, agosto, septiembre, noviembre y diciembre de 2026 dependen de si el IPC de una subclase superó
el 15 % interanual en un mes de referencia, «de acuerdo con la información que publique el INE». El módulo
`precios/fuentes/ine.py` lee en cada actualización las tablas del IPC del INE (servicio Tempus en `www.ine.es`:
tabla 79184 de subclases y 76127 de clases) y rellena `datos/impuestos/condiciones_ipc_2026.json` con el valor y el
resultado de cada condición. Series usadas: 04.5.1.0 Electricidad, 04.5.2.1 Gas natural, 04.5.2.2 Hidrocarburos
licuados y, para el «IPC de carburantes» del RDL 7/2026, la clase 07.2.2 Combustibles y lubricantes para vehículos
personales (criterio documentado: la norma no da código; el resultado coincide con lo que ocurrió con la bombona).

Valores leídos el 27/10/2026 (variación anual, %): abril: electricidad −4,3; gas natural −9,6; hidrocarburos
licuados −16,4; carburantes +15,5. Junio: 6,0 / 0,8 / −14,4 / 7,8. Julio: 8,4 / 4,1 / −1,4 / 11,6. Septiembre:
11,4 / 4,3 / 10,2 / 30,8. Consecuencias: en junio solo siguieron las rebajas ligadas a carburantes (hidrocarburos del
gas a 0,30 €/GJ, del GLP a 0 €/t, IVA del butano al 10 %); electricidad, gas natural y pellets volvieron al tipo
general el 01/06/2026; en agosto, septiembre y noviembre no se activó ninguna rebaja. El IPC de octubre (que decide
diciembre) se publica a mediados de noviembre; hasta entonces diciembre figura como pendiente.

## 4. Factores de conversión (código: `precios/conversiones.py`)

| Factor | Valor | Procedencia | Estado |
|---|---|---|---|
| Pellet, PCI | 4,8 kWh/kg | Boletín de referencia (cita IDAE). Decisión 9. | No aparece en la guía del IDAE consultada; AVEBIOM usa 4.100 kcal/kg = 4,76 kWh/kg y su c€/kWh se guarda en la nota de cada fila. |
| Gasóleo A y C, PCI | 10,28 kWh/l | IDAE, *Guía técnica de diseño de centrales de calor eficientes*, tabla CBL-01 (gasóleo: PCI 10,28 kWh/l, PCS 10,89). Decisión 10 (mismo factor para ambos). | Verificado el 27/10/2026. |
| Butano, PCI | 12,73 kWh/kg | IDAE, misma guía, tabla CBL-01 (gas butano: PCI 12,73 kWh/kg, PCS 13,79). | Verificado el 27/10/2026. |
| Gas natural, PCI/PCS | 0,904 | IDAE, misma guía, tabla CBL-05 (gas natural: PCI/PCS 0,904). | Verificado el 27/10/2026. La TUR se factura en kWh PCS; el €/kWh PCI es mayor en un 10,6 %. |

## 5. Cómo ejecutar y probar

```bash
pip install -r requirements.txt
python -m precios actualizar -v              # todas las fuentes
python -m precios actualizar --solo omie,tur2
python -m pytest -q tests                    # conversiones, impuestos por fecha, lectores y series
```

La primera ejecución descarga todo el histórico (unos 1.800 ficheros diarios de OMIE y 2.500 sumarios del BOE) y
deja una caché en `.cache/` (ignorada por git). Las siguientes solo piden lo nuevo.

## 6. Cuadro de mando (fase 3, código: `precios/panel.py` y `precios/plantilla_panel.html`)

`python -m precios panel` genera `sitio/` (HTML estático + `datos/panel.json` + Plotly servido desde el propio
sitio, sin CDN). GitHub Pages publica esa carpeta mediante `.github/workflows/pages.yml`.

Criterios del resumen ejecutivo:
- **Precio actual (€/kWh):** OMIE, MIBGAS y PVPC: media de los últimos 7 días con dato (decisión 8). Gasóleos:
  última semana publicada. TUR 2, butano y pellet: valor vigente en la fecha de referencia (decisión 5).
  Con impuestos siempre que la fuente o el cálculo lo den; OMIE y MIBGAS sin impuestos y etiquetados como
  mayoristas (decisión 1). Si el precio con impuestos no está disponible (p. ej. condición de IPC pendiente), la
  celda dice «no disponible» y el detalle explica por qué.
- **Variación semanal:** frente a los 7 días anteriores (diarios), la semana anterior (semanales) o el valor vigente
  7 días antes (regulados y pellet: 0 % si no ha cambiado). **Interanual:** lo mismo 364/365 días atrás.
- **Estado:** «actualizado» (dato nuevo en la última ejecución o publicado en los últimos 7 días), «sin actualización
  en el periodo» (la fuente no ha publicado nada nuevo, dentro de su periodicidad) o «fuente no disponible o dato
  pendiente» (sin datos, o más días sin dato de los que admite su periodicidad: 4 diarios, 14 semanales, 70 butano,
  100 TUR, 230 pellet: inicio del trimestre, el trimestre siguiente completo y las 3–5 semanas que tarda el PDF). Si
  una descarga falla pero hay dato reciente, se muestra ese dato y se anota el fallo.
- **Comentario semanal:** frases generadas solo con los números de la tabla (variaciones ≥ 1 %, interanuales,
  orden de precios de la energía final y datos no disponibles). No contiene interpretación.
- **Comparativo en €/kWh** (mejora de visualización del 27/10/2026, `docs/PROMPT_MEJORA_VISUALIZACION.md`):
  selector explícito de series (casillas con el color de cada serie; OMIE y MIBGAS marcados «sin impuestos») y
  conjuntos predefinidos (todas, energía final con impuestos, calefacción doméstica, electricidad, gas natural,
  carburantes, ninguna); periodo con fechas libres y atajos (3 meses, 1 año, 3 años, desde 2022, todo); frecuencia
  original (diaria, semanal, trimestral…) o media mensual; opción **Base 100** en la primera fecha del periodo
  (cada serie dividida por su primer valor disponible; el €/kWh real sigue en el hover) y **media móvil de 7 días**
  solo para OMIE, MIBGAS y PVPC (el dato diario sigue en los gráficos individuales y en el Excel). Las series
  reguladas y el pellet se dibujan en escalón y se arrastra el valor vigente al inicio del periodo. La leyenda va
  fuera del área de datos (arriba) y cada línea lleva al final su nombre y último valor, separados en vertical si
  chocan (mínimo 13 px). La selección, el periodo y las opciones se guardan en la URL (`#series=…&desde=…&hasta=…
  &frecuencia=…&base100=1&mm7=1&impuestos=1`) y el botón «Copiar enlace» la comparte. Los huecos no se rellenan.
- **Resumen ejecutivo:** ocho tarjetas (precio, variaciones con color, fuente y fecha, mini tendencia de 24 meses),
  ranking de barras del coste por kWh de la energía final con impuestos (sin mayoristas) y tabla ordenable por
  columna; cada fila muestra al pasar el ratón la base del cálculo, el valor original y las notas.
- **Gráficos individuales:** uno por indicador con alternancia entre unidad original y €/kWh, botón «Ver datos»
  (tabla del periodo con fecha, periodo, valor original y €/kWh sin/con impuestos) y descarga en CSV (separador «;»,
  con BOM, columnas `fecha;periodo;valor_original;unidad;eur_kwh_sin_impuestos;eur_kwh_con_impuestos;fuente`;
  los datos no disponibles quedan vacíos). Opción «Mostrar cambios de impuestos»: líneas verticales en las fechas
  en que cambia algún tipo (IVA, IEE, hidrocarburos) con el texto «antes → después» y la referencia al BOE
  (`precios.impuestos.cambios_impuestos`). El periodo seleccionado en el comparativo se aplica a todos.
- **Botón «Actualizar» (28/10/2026):** lanza el workflow `actualizar.yml` desde el propio panel mediante la API de GitHub
  (`POST /repos/{owner}/{repo}/actions/workflows/actualizar.yml/dispatches`, `ref` = rama que figura en `panel.json` →
  `github.rama`, la del ejecutor o la del repositorio local). Requiere un token personal *fine-grained* del usuario con
  permiso *Actions: Read and write* sobre el repositorio; se pide una vez y se guarda solo en `localStorage` del
  navegador (nunca en el repositorio ni en el servidor). El panel sigue la ejecución por la API (`runs?event=
  workflow_dispatch`) y recarga la página al terminar, avisando si alguna fuente falló. Sin token, el cuadro enlaza la
  página de ejecuciones.
- **Presentación:** navegación fija por secciones, modo claro/oscuro automático, hoja de estilos de impresión y
  diseño adaptable a móvil. Paleta categórica fija y validada (una tonalidad por indicador; el pellet a granel
  comparte tono con el saco y usa trazo discontinuo); un solo eje Y; números en formato español.
- **Pruebas:** `tests/test_panel_js.py` ejecuta con Node las funciones puras de la plantilla (estado en la URL,
  Base 100, media móvil, etiquetas finales sin solapes, CSV); `tests/test_panel.py` comprueba el JSON del panel.

## 7. Actualización automática (fase 4, `.github/workflows/actualizar.yml`)

- **Cuándo:** cada lunes a las 05:17 UTC (06:17/07:17 hora peninsular) y a mano desde la pestaña Actions del
  repositorio («Actualizar datos y publicar» → «Run workflow»). El cuadro de mando enlaza esa página.
- **Qué hace, en orden:** instala dependencias; ejecuta las pruebas (`pytest`); descarga solo lo nuevo de cada fuente
  (`python -m precios actualizar`); comprueba que ninguna serie pierde filas ni retrocede su primer dato respecto a la
  versión guardada (`scripts/verificar_historico.py`); pasa las comprobaciones de control (aviso si alguna no cuadra);
  genera el cuadro de mando (`python -m precios panel`); guarda `datos/` y `sitio/` con un commit «Actualización
  automática»; publica `sitio/` en GitHub Pages.
- **Si fallan las pruebas o se perdería histórico:** la ejecución se detiene antes del commit y no se publica nada.
- **Si falla la descarga de una fuente:** se publica igualmente con el último dato correcto de esa fuente, el panel
  muestra un aviso y la tabla «Estado de las fuentes» recoge el error, y la ejecución termina en rojo (GitHub avisa
  por correo). `datos/estado.json` guarda por fuente la última actualización correcta, el último dato, si hubo dato
  nuevo y el error, además del enlace a la ejecución.
- **Fuentes sin dato nuevo:** `dato_nuevo` en `estado.json` y el estado «sin actualización en el periodo» del panel.
- **Secretos:** `ESIOS_TOKEN` como secreto del repositorio (Settings → Secrets and variables → Actions). Sin él, el
  PVPC queda en error y el resto se actualiza.
- **Caché:** en Actions no hay caché local; cada ejecución pide solo los días/ficheros posteriores al último dato
  guardado (OMIE: desde 7 días antes del último dato; MIBGAS: el fichero del año en curso; Boletín Petrolero: el
  histórico completo, 4,5 MB; BOE: sumarios desde la última publicación; ESIOS: desde 3 días antes del último dato;
  INE: dos tablas).
- **AVEBIOM (decisión del 27/10/2026):** su servidor (SiteGround) respondió dos veces al ejecutor de GitHub con un
  desafío captcha, que no se sortea. Por eso el pellet se reconstruye siempre desde los PDF guardados en
  `datos/fuentes_originales/avebiom/` (con `indice.json`: url y fecha de subida de cada uno) y la web solo se consulta
  cuando puede haber trimestre nuevo: desde 14 días después del cierre del trimestre siguiente al último guardado
  (`avebiom.toca_consultar`; p. ej. el 4T2026 se busca a partir del 15/01/2027, cada lunes hasta que aparezca). Al
  consultar, se piden la mediateca y la página con el User-Agent del proyecto y, si fallan, se reintenta dos veces
  con esperas de 4 y 8 minutos; si sigue fallando, la fuente queda en error (publicación con el último dato y
  ejecución en rojo). `python -m precios actualizar --solo pellet_saco` fuerza la consulta.

## 8. Informes PDF y Excel (fase 5, `precios/informes.py`)

`python -m precios informes` genera, con los mismos datos que el panel (`panel.construir`), dos ficheros pensados
para dirección (rediseñados el 27/10/2026 a petición de Pablo):
- **`sitio/informes/informe.pdf`** (A4, 2 páginas desde el 28/10/2026 a petición de Pablo: más corto, visual y con
  lectura para dirección; tipografía DejaVu Sans incluida con matplotlib):
  1. *Cuadro de mando*: ocho tarjetas (precio en €/kWh, variación semanal e interanual con flecha y color, mini tendencia
     de 24 meses, fuente, fecha, con/sin impuestos; la del pellet incluye el granel); ranking del coste por kWh de la
     energía final con impuestos; «Claves de la semana»; y el gráfico «Pellet frente a las alternativas de calefacción»
     (`informes.grafico_competitividad`): sobrecoste del kWh de gasóleo C, butano, TUR 2 y PVPC frente al pellet en saco
     hoy y hace un año (barras) y su evolución en 24 meses con medias mensuales (líneas). Sobrecoste = precio
     alternativa ÷ precio pellet saco − 1, ambos en €/kWh con impuestos; el de hace un año se deduce de las variaciones
     interanuales (precio ÷ (1 + variación)). Es un dato derivado y se marca como calculado.
  2. *Evolución y lectura* (29/10/2026, a petición de Pablo: más gráfico, sin texto redundante): cuadrícula 2×4 con un
     gráfico grande por indicador (`informes.grafico_evolucion`): últimos 24 meses en €/kWh en la frecuencia original
     (series diarias con el dato en claro y la media de 7 días en trazo grueso; pellet granel en discontinuo), último
     valor anotado a la derecha; encima, precio y variaciones; debajo, el **texto fijo** de `precios/lectura.py` sobre qué
     mide y por qué importa para el coste de producción o el precio del pellet (redactado el 28/10/2026, revisable a
     mano). Las frases calculadas de `lectura.frase_dinamica` se mantienen en el código y probadas, pero ya no van en
     el PDF. Cierra con el estado de las fuentes en una línea; el resumen de cómo se calcula va al pie de la página 1.
  Los gráficos comparativos desde 2022 y los nueve individuales dejan de ir en el PDF (están en el panel y en el Excel);
  las funciones `grafico_comparativo` y `grafico_individual` se conservan y prueban.
- **`sitio/informes/historico.xlsx`**: «Cuadro de mando» (ocho tarjetas en celdas combinadas con precio, variaciones
  con color, fuente y fecha; tabla resumen con formato condicional: color y flechas en las variaciones; claves de la
  semana; ranking de la energía final ordenado de menor a mayor con gráfico de barras vinculado); «Anual» (medias
  anuales en €/kWh); «Mensual» (media mensual de cada serie en €/kWh y en su unidad original, desde 2020, como tabla
  filtrable); «Gráficos» (comparativo mensual, barras anuales y nueve individuales, *vinculados* a las hojas Anual y
  Mensual); **«Comparador»** (hasta cuatro series elegidas con desplegables, frecuencia mensual o anual y opción
  Base 100; la tabla se calcula con fórmulas INDEX/MATCH sobre «Mensual» y «Anual», los periodos sin dato dan #N/A
  y no se dibujan, y el gráfico de líneas está vinculado a esa tabla; el libro se recalcula al abrirse); una hoja
  «Datos n nombre» por serie con el histórico completo en su frecuencia original (fecha, periodo, valor original,
  €/kWh sin y con impuestos, origen, impuestos aplicados, fecha de publicación, referencia y nota) en formato tabla
  de Excel con filtros y paneles inmovilizados; «Fuentes y criterios». Las fórmulas del «Comparador» se han
  comprobado recalculando el libro con LibreOffice (modos mensual/anual y Base 100).
Ambos se regeneran en cada actualización (paso previo al panel en `actualizar.yml`) y se descargan desde el panel.
Solo se conserva la última versión de cada uno (el histórico está en `datos/`, versionado en git).
