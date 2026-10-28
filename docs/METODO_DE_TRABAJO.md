# Método de trabajo, arquitectura y contexto del encargo

> Copia literal de las instrucciones de trabajo recibidas con el encargo (25/10/2026). El texto íntegro del encargo está en `ENCARGO.md`.

Vas a desarrollar y poner en funcionamiento, de principio a fin, el sistema que describe el
encargo de más abajo. Trabajas de forma autónoma dentro de cada fase y te paras al final de
cada una para que yo (Pablo) revise y decida. Escríbeme siempre en castellano, de forma directa.

## Cómo vas a trabajar

1. **El repositorio es tu única memoria.** Entre sesiones no recuerdas nada. Al empezar, crea y
   mantén al día:
   - `CLAUDE.md`: estado, decisiones tomadas, cómo ejecutar y probar, siguiente paso. Léelo al
     empezar cada sesión.
   - `docs/ENCARGO.md`: el texto íntegro del encargo de más abajo.
   - `docs/DECISIONES.md`: cada decisión mía, con fecha.
2. **Por fases.** Al terminar cada fase: haz commit y push, y escríbeme un informe breve con
   qué está hecho, qué has comprobado con datos reales, qué falla o es frágil, qué tengo que
   hacer yo y qué tengo que decidir. Después **para y espera** mi respuesta. No pases a la
   siguiente fase sin mi «sigue».
3. **Datos: nunca inventes, interpoles ni estimes** sin marcarlo expresamente. Cada dato lleva
   su fuente, su fecha de publicación, si es con o sin impuestos y si es original o calculado.
   Si una fuente no da un dato, el panel lo muestra como no disponible, no se rellena.
4. **Comprueba con datos reales** antes de dar algo por hecho: descarga, contrasta valores de
   control con la fuente original y escribe pruebas automáticas (pytest) para las conversiones,
   los impuestos por fecha y la lectura de cada fuente.
5. **Solo datos públicos.** No subas información confidencial. El boletín de APROPELLETS que
   sirve de referencia es de uso interno de los asociados y no se sube al repositorio: lo que
   necesitas de él está resumido más abajo.
6. **Secretos.** El token personal de ESIOS estará en la variable de entorno `ESIOS_TOKEN` de
   la sesión (si aún no está, dímelo y sigue con lo demás) y, para el sistema en producción, en
   el secreto de GitHub Actions `ESIOS_TOKEN`, que crearé yo. Nunca lo escribas en ningún fichero.
7. **Red.** Si una fuente no responde desde la sesión, dime el dominio exacto para que lo añada
   a la lista de dominios permitidos del entorno.
8. **Lo que no puedas hacer tú** (activar GitHub Pages, crear secretos, pedir permisos), dímelo
   con los pasos exactos, botón a botón, para que lo haga yo.

## Arquitectura (ya decidida)

La más sencilla y de menor mantenimiento que cumple el encargo:

- **Código en Python** en este repositorio de GitHub.
- **Datos versionados en el propio repositorio**: una serie por indicador con su frecuencia
  original, la media mensual, los valores originales y los convertidos a €/kWh, y sus metadatos.
- **GitHub Actions** para la actualización: programada **cada semana** y lanzable **a mano**
  (`workflow_dispatch`), que es la orden de «actualizar». La actualización ejecuta las pruebas
  antes de publicar; si fallan, no publica y deja el error registrado.
- **GitHub Pages** para el **enlace permanente**: sitio estático con gráficos interactivos, que
  lee los datos ya procesados. El panel muestra el estado de cada fuente, la fecha de la última
  actualización correcta y un enlace a la página de Actions para lanzar la actualización.
- **Informes PDF y Excel** generados en cada actualización y descargables desde el panel.
- Un fichero de estado (por ejemplo `estado.json`) con, por fuente: último dato, si hay dato
  nuevo, errores de descarga y fecha de la última actualización correcta.

Si al comprobar las fuentes ves que algo de esta arquitectura no funciona, dímelo en el informe
de la fase 1 con la alternativa, antes de construir.

## Lo que sale del boletín de referencia (APROPELLETS)

- **Fuentes que usa:** OMIE (ficheros de `omie.es/es/file-access-list`), MIBGAS (`mibgas.es/es/file-access`),
  REE/ESIOS indicador 1001 (PVPC 2.0TD, término de energía, Península; `api.esios.ree.es/indicators/1001`),
  Weekly Oil Bulletin de la Comisión Europea (gasóleo de automoción y de calefacción, con
  impuestos; `energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en`), BOE (resoluciones de
  la DGPEM para la TUR de gas natural y el butano envasado) y AVEBIOM (índice de precios de
  biocombustibles sólidos; `avebiom.org/actividades/indice-de-precios-biocombustibles-solidos/`).
- **Conversión a €/kWh sobre PCI** (según el boletín, fuente IDAE): pellet 4,8 kWh/kg; gasóleo de
  calefacción 10,28 kWh/l; butano 12,73 kWh/kg; gas natural, relación PCI/PCS 0,904. Verifica
  cada factor en su fuente y documenta su procedencia; si encuentras una razón técnica para otro,
  propónmelo, no lo cambies por tu cuenta.
- **Presentación:** el boletín muestra OMIE como media de 7 días y la TUR 2 sin impuestos.
- **Estructura del boletín:** número y periodo cubierto; resumen ejecutivo; indicadores
  destacados con su variación y su estado («actualizado respecto al boletín anterior», «sin
  actualización en el periodo», «fuente no disponible o dato pendiente»); cuadro de mandos;
  fuentes. Cada dato remite a su fuente original.

## Cómo se hacía hasta ahora (lo cuenta quien hace el encargo)

Hasta ahora el informe se montaba a mano, copiando gráficas y datos de tres sitios:

- **Electricidad:** gráficas copiadas de la página de resultados mensuales del mercado diario de
  OMIE: `https://www.omie.es/es/market-results/monthly/daily-market/daily-market-price?scope=monthly&year=2026&month=10`
- **Gas:** gráficas de los resultados de mercado de MIBGAS: `https://www.mibgas.es/es/market-results`
- **Gasóleo:** datos descargados del Weekly Oil Bulletin
  (`https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en`), con las gráficas
  actualizadas en un Excel.

Lo que pide, en sus palabras: que quede «un poco más profesional» y que «se actualice más o menos
rápido». Tenlo en cuenta en las decisiones de diseño: el objetivo es sustituir ese trabajo manual
por algo fiable y presentable, no un sistema más complicado de lo necesario. Estas páginas sirven
para contrastar los datos, pero descarga de los ficheros o la API de cada fuente, no de las
gráficas de la web. Si en el repositorio hay una carpeta `referencia/` con el Excel que se usaba,
mírala para reproducir lo útil de su formato y para contrastar valores.

## Contradicciones del encargo: preséntamelas en la fase 1 con tu propuesta

Yo decido; no las resuelvas por tu cuenta. Mi propuesta inicial, para que la confirmes o la
discutas con datos:

1. **OMIE y MIBGAS son precios mayoristas, sin impuestos.** Propuesta: mostrarlos sin impuestos,
   indicándolo claramente.
2. **TUR 2:** el encargo pide con impuestos y el boletín la da sin ellos. Propuesta: con impuestos
   (IVA e impuesto sobre hidrocarburos vigentes en cada fecha), guardando también el valor sin
   impuestos.
3. **PVPC con impuestos:** confirmar qué incluye el indicador 1001 y aplicar el impuesto
   eléctrico y el IVA vigentes en cada fecha (cambiaron varias veces entre 2022 y 2024), con su
   referencia al BOE.
4. **Gráfico desde 2020 y histórico desde 2022.** Propuesta: el histórico desde enero de 2022 es
   obligatorio; si las fuentes dan 2020 y 2021 sin esfuerzo, se incluyen.
5. **Variación semanal en indicadores que no son semanales** (TUR, butano, pellet). Propuesta:
   comparar el valor vigente hoy con el vigente hace 7 días (0 % si no ha cambiado), con nota.
6. **Pellet:** si el índice de AVEBIOM no se puede descargar de forma automática y fiable,
   explícalo antes de construir. No se introducen datos a mano.
7. **Acceso:** GitHub Pages publica una web visible para cualquiera con el enlace. Confírmame que
   lo sabes antes de publicar.

## Fases

**Fase 1. Disponibilidad real de las fuentes.** Para cada uno de los ocho indicadores: dirección
o API, formato, frecuencia, si hay histórico desde enero de 2022 y cómo se obtiene, si es con o
sin impuestos, si se puede automatizar (sí, frágil o no) y por qué. Descarga de verdad un dato
reciente y uno de enero de 2022 de cada uno. Resultado: `docs/FUENTES.md` y las propuestas sobre
las contradicciones. **Para.**

**Fase 2. Histórico y base de datos.** Descargadores por fuente, normalización, impuestos por
fecha (tabla documentada con su referencia), conversiones a €/kWh, frecuencia original más media
mensual y metadatos. Pruebas automáticas y una tabla de comprobaciones con valores de control
contrastados con la fuente. **Para.**

**Fase 3. Cuadro de mando.** Resumen ejecutivo (precio actual en €/kWh, variación semanal e
interanual, fecha, fuente, estado), gráfico comparativo con series seleccionables, ocho gráficos
individuales, filtro de periodo personalizado y comentario semanal generado a partir de los datos
(solo lo verificable). Publicación en GitHub Pages y pasos exactos para lo que tenga que hacer
yo. **Para.**

**Fase 4. Actualización automática.** Workflow semanal y manual, pruebas antes de publicar,
detección de fuentes sin dato nuevo, errores visibles en el panel y en la ejecución fallida,
registro de la última actualización correcta y conservación del histórico. Haz una ejecución real
completa. **Para.**

**Fase 5. Exportación.** PDF con presentación parecida al boletín, limitada a los ocho
indicadores, y Excel con el histórico, datos originales y convertidos, tabla resumen, gráficos
vinculados, fuentes y criterios y filtros. Generados en cada actualización y descargables desde
el panel. **Para.**

**Fase 6. Verificación y entrega.** Comprueba todo lo del apartado 7 del encargo y entrega lo del
apartado 8: enlace, PDF, Excel, `docs/USO.md` con instrucciones breves y confirmación de cómo
funciona la actualización semanal. No lo des por terminado mientras algo dependa de introducir
datos a mano.

Empieza por la fase 1.
