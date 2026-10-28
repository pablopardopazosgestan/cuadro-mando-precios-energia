# Prompt: mejora de la visualización y la interactividad del cuadro de mando y de los informes

> Redactado por Claude el 27/10/2026 a petición de Pablo, para que él lo devuelva como encargo. Se aplica
> sobre el estado actual del repositorio (fases 1–5 terminadas, 74 pruebas, 8 fuentes en verde).

## Contexto que debes respetar

- El sistema es el de este repositorio: datos en `datos/` (series en frecuencia original, medias mensuales,
  metadatos, estado), panel estático en `sitio/` generado por `precios/panel.py` + `precios/plantilla_panel.html`
  (Plotly incluido en `sitio/plotly.min.js`, sin CDN), informes en `precios/informes.py` (`informe.pdf` y
  `historico.xlsx`), actualización semanal en `.github/workflows/actualizar.yml`. Nueve series: `omie`, `mibgas`,
  `gasoleo_a`, `pvpc`, `tur2`, `gasoleo_c`, `butano`, `pellet_saco`, `pellet_granel`.
- Reglas que no cambian: nada se inventa, interpola ni estima; cada dato conserva fuente, fecha de publicación,
  con/sin impuestos y original/calculado; «no disponible» cuando falta; OMIE y MIBGAS siempre etiquetados como
  mayoristas sin impuestos; todas las métricas exigidas por el encargo (precio actual en €/kWh, variación semanal e
  interanual, fecha, fuente, estado; comparativo; ocho gráficos individuales; filtro de periodo; comentario) siguen
  presentes en panel, PDF y Excel. Las pruebas de `tests/` deben seguir pasando y el workflow debe seguir publicando.
- Público: dirección. Tono serio y profesional, fácil de leer en diez segundos, pero sin perder densidad ni
  trazabilidad de los datos (el detalle sigue a un clic o al pasar el ratón).

## 1. Panel web (`precios/plantilla_panel.html`, `precios/panel.py`)

### 1.1 Selector de series del gráfico comparativo
- Sustituir el «solo leyenda» por un **selector explícito** encima del gráfico: una casilla por serie con su color y
  su nombre corto, más la etiqueta «sin impuestos» en OMIE y MIBGAS. Debe permitir cualquier combinación (p. ej.
  solo gasóleo C y pellet en saco).
- **Conjuntos predefinidos** (botones): Todas · Energía final con impuestos · Calefacción doméstica (TUR 2, gasóleo
  C, butano, pellet saco y granel) · Electricidad (OMIE, PVPC) · Gas natural (MIBGAS, TUR 2) · Carburantes (gasóleo
  A) · Ninguna.
- Al cambiar la selección, el **eje Y se reescala** a las series visibles y el gráfico se redibuja; la leyenda de
  Plotly queda sincronizada (si se oculta desde la leyenda, la casilla se desmarca).
- La selección, el periodo y la frecuencia se guardan en la **URL** (`#series=gasoleo_c,pellet_saco&desde=…&hasta=…`)
  para poder compartir o guardar una comparación concreta, y se restauran al abrir el enlace.

### 1.2 Legibilidad del comparativo
- La **leyenda nunca se superpone a las líneas**: va fuera del área de dibujo (arriba, en una o dos filas) y el área
  de dibujo tiene márgenes suficientes; en móvil la leyenda se oculta y manda el selector.
- **Etiquetas al final de cada línea** (nombre corto y último valor) a la derecha del área de dibujo, sin
  solaparse entre sí (desplazarlas verticalmente si chocan) y solo para las series visibles.
- Opción **«Base 100»** (índice = 100 en la primera fecha del periodo seleccionado) para comparar evoluciones de
  series con escalas muy distintas; se etiqueta claramente como índice derivado del dato, con el valor real en el
  detalle del ratón.
- Opción **«Media móvil de 7 días»** para las series diarias (OMIE, MIBGAS, PVPC), que reduce el ruido sin sustituir
  el dato: se dibuja la media móvil y el dato diario queda en el detalle; etiquetada como derivada.
- Detalle al pasar el ratón unificado por fecha, con números en formato español, la unidad original y el €/kWh, y la
  indicación «sin impuestos» donde proceda.
- Las series reguladas y el pellet se siguen dibujando en escalón; los huecos no se rellenan.

### 1.3 Resumen ejecutivo más visual, sin perder la tabla
- Añadir, encima de la tabla, **ocho tarjetas** (una por indicador; la del pellet con saco y granel) iguales a las de
  la página 1 del PDF: precio grande en €/kWh, variación semanal e interanual con flecha y color (rojo sube, verde
  baja), fuente, fecha, con/sin impuestos y una línea de tendencia de 24 meses.
- Añadir un **ranking horizontal** del coste por kWh de la energía final con impuestos (barras ordenadas) con los
  mayoristas aparte y etiquetados.
- La tabla completa se mantiene (es la exigida por el encargo), con columnas ordenables, formato español de números,
  colores en las variaciones y el detalle (base del cálculo, valor original, nota) al pasar el ratón.

### 1.4 Gráficos individuales
- Cada uno con el **último valor anotado** y con un conmutador «unidad original / €/kWh».
- Opción **«Mostrar cambios de impuestos»**: marcas verticales con etiqueta en PVPC, TUR 2, butano y pellet en las
  fechas en que cambió el IVA, el impuesto eléctrico o el de hidrocarburos (datos de `precios/impuestos.py`, con la
  referencia al BOE en el detalle). Es información verificable, no interpretación.
- Vista de **tabla** por gráfico (botón «Ver datos»), con el periodo filtrado, y **descarga en CSV** de esos datos.

### 1.5 Navegación y presentación
- Barra de navegación fija con las secciones (Resumen · Comparativo · Indicadores · Estado · Fuentes · Descargas).
- Cabecera con fecha de referencia, última actualización correcta, enlaces al PDF y al Excel y botón «Actualizar»
  (enlace al workflow).
- Modo claro y oscuro coherentes (ya existe) y hoja de estilos de impresión (el panel debe imprimirse limpio en A4).
- Todo el texto en castellano, fechas dd/mm/aaaa, decimales con coma.

## 2. Informe PDF (`precios/informes.py`)

- Mantener la estructura actual (cuadro de mando de una página, tabla y comparativo, gráficos individuales y medias
  anuales, estado de fuentes y metodología).
- En el comparativo, **sin solapes**: leyenda fuera del área de dibujo y etiquetas al final de cada línea con nombre
  y último valor, separadas verticalmente si chocan. Añadir un **segundo comparativo solo de energía final con
  impuestos** (sin OMIE ni MIBGAS), que es el que dirección compara, con la misma regla de etiquetas.
- En los gráficos individuales, sombrear suavemente el **periodo analizado** (los 7 días) y anotar el último valor
  sin tapar la línea.
- En la tabla de precios, añadir una mini tendencia (sparkline) por fila.

## 3. Excel (`precios/informes.py`, hoja nueva «Comparador»)

- Hoja **«Comparador»**: hasta cuatro desplegables (validación de datos) para elegir series y un desplegable de
  frecuencia (mensual/anual); las columnas de datos se obtienen con fórmulas (ÍNDICE/COINCIDIR) desde «Mensual» o
  «Anual», y un gráfico de líneas está vinculado a esas columnas, de modo que el usuario compara lo que quiera sin
  tocar los datos. Opción «Base 100» mediante una celda de selección y fórmulas.
- En «Cuadro de mando», mantener el formato condicional y añadir las tarjetas en celdas (precio grande, variaciones
  con color) y el ranking como gráfico de barras ordenado.
- Todas las hojas de datos siguen siendo tablas filtrables con trazabilidad completa.

## 4. Criterios de diseño (comunes)

- Paleta categórica fija y validada (una tonalidad por indicador, la actual); el pellet a granel comparte tono con
  el saco y se distingue por trazo discontinuo. Nunca color solo: leyenda o etiqueta siempre presentes.
- Un solo eje Y por gráfico (nunca doble eje). Para comparar escalas distintas: Base 100 o gráficos separados.
- Rejilla y ejes discretos; líneas finas; texto en los colores de texto, no en el color de la serie.
- Números en formato español; unidades siempre visibles; «n. d.» para no disponible.

## 5. Entregables y comprobación

1. Código con pruebas nuevas (selector y estado en URL, Base 100, media móvil, etiquetas sin solape, CSV) y las 74
   existentes en verde.
2. Capturas del panel (claro, oscuro, móvil) y del PDF revisadas antes de publicar; comprobar que el Excel abre.
3. `docs/METODOLOGIA.md` §6 y §8 actualizados; `CLAUDE.md` con el estado.
4. Commit, push, ejecución real del workflow y enlace publicado. Parar e informar.

## 6. Lo que no se debe hacer

- No eliminar ni resumir ninguna métrica exigida; no sustituir datos por derivados (media móvil y Base 100 son capas
  opcionales, no reemplazos); no añadir fuentes ni datos que no estén ya en `datos/`; no depender de CDN ni de
  servicios externos; no cambiar las decisiones registradas en `docs/DECISIONES.md` sin consultarlo.
