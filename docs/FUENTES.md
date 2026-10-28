# Fase 1 · Disponibilidad real de las fuentes

Fecha del sondeo: **25 de octubre de 2026**. Todo lo que sigue se ha comprobado descargando los
datos desde esta sesión (script reproducible: `scripts/fase1_sondeo_fuentes.py`). Donde no se ha
podido comprobar algo, se dice expresamente.

## Resumen

| # | Indicador | Fuente | Formato | Frecuencia | Histórico desde 01/2022 | Impuestos | Automatizable |
|---|-----------|--------|---------|------------|-------------------------|-----------|---------------|
| 1 | Electricidad, mercado diario OMIE (España), €/MWh | OMIE, ficheros `marginalpdbc` | Texto `;` (zip anual hasta 2022, diario después) | Horaria hasta 09/2025, cuarto-horaria después; publicación diaria | Sí, completo (y desde 2018) | Sin impuestos (mayorista) | **Sí** |
| 2 | Gas natural, MIBGAS-ES Index, €/MWh | MIBGAS, `MIBGAS_Data_AAAA.xlsx` | Excel anual | Diaria (por día de gas) | Sí, completo (y desde 2015) | Sin impuestos (mayorista) | **Sí** (cambio de formato 2022→2023 ya resuelto) |
| 3 | Gasóleo de automoción, España, €/l | Comisión Europea, Weekly Oil Bulletin, fichero histórico | Excel (`Prices_History`) | Semanal (precio del lunes) | Sí, completo (y desde 2005) | **Con impuestos** (hay hoja sin impuestos) | **Sí** |
| 4 | Electricidad PVPC 2.0TD, término de energía, €/kWh | REE/ESIOS indicador 1001 | API JSON | Horaria (cuarto-horaria desde 10/2025, por confirmar) | Sí (2.0TD existe desde 01/06/2021) | Sin impuestos (por confirmar con la API) | **Pendiente**: falta `ESIOS_TOKEN` |
| 5 | Gas natural TUR 2, término variable, €/kWh | BOE, resoluciones DGPEM | API de sumarios (JSON) + XML de cada resolución | Trimestral (1 ene/abr/jul/oct) más revisiones extraordinarias | Sí, completo | Sin impuestos | **Sí** |
| 6 | Gasóleo de calefacción, España, €/kWh | Comisión Europea, Weekly Oil Bulletin | Igual que 3 | Semanal | Sí, completo | **Con impuestos** | **Sí** |
| 7 | Butano, bombona 12,5 kg, €/kWh | BOE, resoluciones DGPEM | Igual que 5 | Bimestral (tercer martes de ene/mar/may/jul/sep/nov) | Sí, completo | Sin impuestos (el precio con impuestos hay que calcularlo) | **Sí** |
| 8 | Pellet, saco 15 kg y granel en volquete, €/kWh | AVEBIOM, índice de precios (PDF trimestral) | PDF (texto extraíble) | Trimestral (unas 3 semanas tras el cierre) | **Parcial**: trimestral solo desde 4T2024; medias anuales 2022–2024 | **Con impuestos** (IVA 21 %, transporte incluido) | **Frágil** (PDF; la web rechaza al cliente genérico) |

Red: los seis dominios de las fuentes responden desde la sesión. Bloqueados por la política del
entorno (no imprescindibles): `energia.gob.es`, `www.miteco.gob.es`, `www.cnmc.es`,
`sedeaplicaciones.minetur.gob.es`, `web.archive.org`. El único que convendría abrir es
`web.archive.org`, por el motivo que se explica en el indicador 8.

---

## 1. Electricidad · mercado diario OMIE (España)

- **Dirección.** Listado: `https://www.omie.es/es/file-access-list?parents=/Mercado%20Diario/1.%20Precios&dir=Precios%20horarios%20del%20mercado%20diario%20en%20Espa%C3%B1a&realdir=marginalpdbc`.
  Descarga: `https://www.omie.es/file-download?parents=marginalpdbc&filename=marginalpdbc_AAAAMMDD.1`
  (fichero diario) y `…&filename=marginalpdbc_AAAA.zip` (zip anual, disponible de 2018 a 2022).
- **Formato.** Texto plano con `;`: cabecera `MARGINALPDBC;`, filas `AAAA;MM;DD;periodo;precio_PT;precio_ES;`
  y una línea final `*`. La sexta columna es España (comprobado contra el informe mensual de OMIE, ver abajo).
  En 2022 hay 24 periodos (23/25 en los cambios de hora); en 2026 son cuartos de hora: 96 (92/100 en los
  cambios de hora; el fichero del 25/10/2026 tiene 100). El cambio a cuartos de hora fue el 01/10/2025 (fecha a
  confirmar con los ficheros en la fase 2).
- **Frecuencia y publicación.** Diaria; el fichero del día D+1 aparece a primera hora de la tarde del día D
  (el 25/10 a las 11:20 UTC existía el fichero del 25 y aún no el del 26).
- **Histórico.** El listado enlaza cada fichero tres veces: 1.095 enlaces de 2023 (365 días), 1.098 de 2024 (366), 1.095
  de 2025 (365) y 894 de 2026 (298 días, hasta el 25/10): años completos. 2020–2022 van en zips anuales.
- **Impuestos.** Precio mayorista, sin impuestos.
- **Descargas de comprobación.**
  - `marginalpdbc_2022.zip`: 365 ficheros. 01/01/2022: 24 horas, hora 1 = 145,86 €/MWh; media del día 122,63 €/MWh.
  - Media aritmética de enero de 2022 (744 horas): **201,72 €/MWh**. Coincide con el valor publicado por OMIE para enero de 2022.
  - Septiembre de 2026 (30 ficheros, 2.880 cuartos de hora): media España **143,25 €/MWh** y Portugal 143,90 €/MWh.
    El *Informe mensual septiembre 2026* de OMIE (`/sites/default/files/2026-10/informe-mensual-septiembre-2026_es.pdf`,
    página 3 del resumen) da España **143,25** y Portugal **143,90**: cuadra, y confirma que la columna 6 es España.
  - `marginalpdbc_20261024.1`: periodo 1 = 205,00 €/MWh.
- **Automatizable: sí.** URLs estables y sin autenticación. Riesgo: cambios de nombre o formato en OMIE
  (ya hubo uno, el paso a cuartos de hora); el lector detecta el número de periodos por fichero.

## 2. Gas natural · MIBGAS-ES Index

- **Dirección.** `https://www.mibgas.es/es/file-access/MIBGAS_Data_AAAA.xlsx?path=AGNO_AAAA/XLS`
  (hay ficheros de 2015 a 2026; la página `/es/file-access` los agrupa por año).
- **Formato.** Excel con varias hojas. El índice diario está en la hoja `Indices` (2022: columnas
  `Delivery day`, `Area`, `MIBGAS Index [EUR/MWh]`, una fila por área ES/PT) y, desde 2023, en la hoja
  `MIBGAS Indexes` (columna `MIBGAS-ES Index [EUR/MWh]`, una fila por día). La hoja `Definitions` define
  igual ambas series: «precio medio ponderado de todas las transacciones de todos los productos con entrega en
  el mismo día de gas en el PVB, en todas las sesiones ya concluidas».
- **Frecuencia y publicación.** Diaria, por día de gas; MIBGAS indica que se actualiza a las 21:30.
  El fichero de 2026 descargado el 25/10 llega al 24/10 (y tiene filas sin índice para el 25 y 26).
- **Histórico.** 2022: 365 días con índice ES. 2026: 297 días hasta el 24/10.
- **Impuestos.** Precio mayorista, sin impuestos.
- **Descargas de comprobación.**
  - 01/01/2022: 57,89 €/MWh; 03/01/2022: **66,53 €/MWh**; 31/12/2022: 57,91 €/MWh.
  - 24/10/2026: **92,87 €/MWh**. La gráfica «Índice de precio y volumen del día de gas» de la web de MIBGAS
    (`/es/market-results/gas-daily-price-index-and-volumes`) lleva incrustados los datos: 24/10/26 = 92,87;
    23/10/26 = 90,05; 22/10/26 = 87,38. Cuadran con el Excel.
- **Automatizable: sí.** El cambio de estructura entre 2022 y 2023 está contemplado. Riesgo: nuevos cambios
  de nombre de hoja o columna (el lector buscará por nombre y fallará con aviso, nunca con un valor erróneo).

## 3 y 6. Gasóleo de automoción y gasóleo de calefacción (Weekly Oil Bulletin)

- **Dirección.** Página `https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en`. Enlaza el
  fichero histórico completo `Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx` (4,5 MB; la URL es del tipo
  `/document/download/<uuid>_en?filename=…`, así que el descargador la localizará en la página por el nombre,
  no por el uuid). También hay un Excel semanal por fecha, pero el histórico lo contiene todo.
- **Formato.** Hojas `Prices with taxes` y `Prices wo taxes` (y `VAT`, `Excise duties`…). Una fila por semana
  (fecha = lunes). España: columnas `ES_price_with_tax_diesel` (gasóleo de automoción) y
  `ES_price_with_tax_heating_oil` (gasóleo de calefacción), en **€/1.000 l**; las mismas en la hoja sin impuestos.
- **Frecuencia y publicación.** Semanal. El histórico descargado el 25/10/2026 llega al **19/10/2026**.
- **Histórico.** 1.089 semanas, del 03/01/2005 al 19/10/2026. Única falta desde 2022: el 18/04/2022
  (Lunes de Pascua), no hay dato esa semana. No se rellenará.
- **Impuestos.** Con impuestos (IVA, hidrocarburos y resto). Ratio comprobado con impuestos / (sin impuestos +
  impuesto especial) = 1,21 en todas las semanas revisadas de 2022 y 2023.
- **Aviso importante (2022).** Entre el 1/4/2022 y el 31/12/2022 el precio pagado en surtidor llevaba una
  bonificación de 20 c€/l (RDL 6/2022) que **el Boletín no descuenta**: la serie española de abril a diciembre de
  2022 es el precio antes de la bonificación (gasóleo A 04/04/2022: 1.847,03 €/1.000 l con impuestos). Propuesta
  en el apartado de decisiones (n.º 11).
- **Descargas de comprobación.**
  - 03/01/2022: gasóleo A **1.347,15** €/1.000 l con impuestos (734,35 sin); gasóleo C **830,03** (589,27 sin).
  - 19/10/2026: gasóleo A **1.889,22** con impuestos (1.382,34 sin); gasóleo C **1.521,33** (1.236,30 sin).
- **Automatizable: sí.** Riesgo: la Comisión cambia de vez en cuando el nombre o la ubicación del fichero;
  el descargador lo busca en la página y avisa si no lo encuentra.

## 4. Electricidad PVPC 2.0TD · término de energía (REE/ESIOS 1001)

- **Dirección.** `https://api.esios.ree.es/indicators/1001?start_date=…&end_date=…&geo_ids[]=8741` (Península),
  con cabecera `x-api-key: <token>`.
- **Estado (actualizado el 27/10/2026, ya con token).** Comprobado: el indicador se llama «Término de facturación de
  energía activa del PVPC 2.0TD», magnitud «Precio €/MWh», paso horario, geos Península (8741), Canarias, Baleares,
  Ceuta y Melilla. 01/01/2022 00h Península = 204,51 €/MWh (igual que la API pública de REE); media del día 178,27 €/MWh.
  El cortafuegos de ESIOS (Incapsula) devuelve 403 si se encadenan peticiones seguidas: el descargador espacia las
  peticiones y, ante un 403, espera varios minutos antes de reintentar.
- **Alternativa pública sin token, probada.** `https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real`
  (REE) devuelve la serie «PVPC» horaria en €/MWh: 01/01/2022 00h = 204,51 €/MWh; 01/06/2023 00h = 125,71;
  24/10/2026 00h = 228,20; 25/10/2026 23h = 314,04. Pero rechaza con 403 (mismo cortafuegos) los rangos de más
  de un día y, a ratos, cualquier petición. Sirve como contraste y como respaldo, no como fuente principal:
  reconstruir el histórico exigiría unas 1.750 peticiones de un día.
- **Histórico.** La tarifa 2.0TD (y con ella el indicador 1001) existe desde el 01/06/2021: no hay 2020 ni
  primer semestre de 2021 comparables.
- **Impuestos.** Sin impuestos (por confirmar). Con impuestos = término de energía × (1 + impuesto eléctrico) ×
  (1 + IVA) vigentes en cada hora/fecha: será un valor **calculado**, marcado como tal.
- **Automatizable: sí, con token.** El token es personal; irá en el secreto `ESIOS_TOKEN` de GitHub Actions.

## 5. Gas natural TUR 2 · término variable (BOE)

- **Dirección.** Sumario diario del BOE en datos abiertos: `https://www.boe.es/datosabiertos/api/boe/sumario/AAAAMMDD`
  (JSON). Cada resolución, en XML: `https://www.boe.es/diario_boe/xml.php?id=BOE-A-AAAA-NNNNN`. El buscador web
  del BOE no admite consultas por URL simples, así que el método es recorrer los sumarios día a día y filtrar por
  título «…por la que se publica la tarifa de último recurso de gas natural». Para el histórico son unos 1.760
  sumarios (una sola vez); la actualización semanal solo lee los días nuevos.
- **Formato.** El XML contiene las tablas: `Tarifa | Fijo (€/cliente)/mes | Variable cent/kWh` para TUR.1, TUR.2,
  TUR.3 (y desde 2026 hasta TUR.11), más la fecha de efectos («surtirá efectos el 1 de …»).
- **Frecuencia.** Trimestral, con efectos el 1 de enero, abril, julio y octubre; publicación los últimos días del
  trimestre anterior o el día 1. Puede haber revisiones extraordinarias (p. ej. en 2022 con el RDL 18/2022), por
  eso se leen todos los días y se toma el valor vigente en cada fecha.
- **Impuestos.** Sin impuestos («Los precios sin impuestos de la tarifa de último recurso…»).
- **Descargas de comprobación.**
  - `BOE-A-2021-21356` (publicado 25/12/2021, efectos 01/01/2022): **TUR.2 variable 4,520114 c€/kWh**, fijo 10,24 €/mes.
  - `BOE-A-2026-20389` (publicado 01/10/2026, efectos 01/10/2026): **TUR.2 variable 5,042762 c€/kWh**, fijo 8,17 €/mes.
    El texto cita el RDL 7/2026 y el RDL 25/2026 («Plan Integral de Respuesta a la Crisis en Oriente Medio»), que
    limitan la subida del coste de la materia prima y pueden afectar también a los impuestos: en la fase 2 leeré
    esos textos en el BOE antes de fijar la tabla de impuestos de 2026.
  - Entre el 20/12/2021 y el 20/01/2022 solo hay una resolución de TUR (la del 25/12), lo esperado.
- **Fragilidad.** La API del BOE corta la conexión de vez en cuando (`Connection reset`); con reintentos funciona.
  Algunos días no hay BOE (404 en domingos y festivos): se trata como «sin publicación», no como error.
- **Automatizable: sí.**

## 7. Butano · bombona de 12,5 kg (BOE)

- **Dirección y formato.** Igual que TUR. Título hasta 2025: «…nuevos precios máximos de venta, antes de impuestos,
  de los gases licuados del petróleo envasados, en envases de carga igual o superior a 8 kg e inferior a 20 kg…».
  **En 2026 el título cambió** a «…del butano comercial envasado en envases de carga…» (comprobado en
  `BOE-A-2026-10669`, `BOE-A-2026-15740`, `BOE-A-2026-19115`): el filtro contempla ambos.
- **Frecuencia.** Bimestral; efectos el tercer martes de enero, marzo, mayo, julio, septiembre y noviembre.
- **Impuestos.** El BOE publica solo el **precio máximo antes de impuestos, en c€/kg**. El precio de la bombona con
  impuestos no está en el BOE: se **calculará** (precio/kg × 12,5 kg + impuesto de hidrocarburos del GLP para usos
  distintos de carburante + IVA) y se marcará como calculado, contrastándolo con el precio de la bombona que
  publican el Ministerio y la prensa en cada revisión. Hay que confirmar en la fase 2 el tratamiento de los
  periodos de congelación del precio (2022–2023), que las resoluciones deberían reflejar.
- **Descargas de comprobación.**
  - `BOE-A-2022-665` (publicado 17/01/2022): «Desde las cero horas del día 18 de enero de 2022, el precio máximo de
    venta, antes de impuestos … será de **115,9037 c€/Kg**». La tabla del XML da el desglose (coste de materia prima,
    comercialización, desajuste).
  - Última resolución localizada: `BOE-A-2026-19115` (publicada 14/09/2026). La siguiente se espera hacia el 16/11/2026.
- **Automatizable: sí.**

## 8. Pellet · saco de 15 kg y granel en volquete (AVEBIOM)

- **Dirección.** Página `https://avebiom.org/actividades/indice-de-precios-biocombustibles-solidos/`, con el enlace
  «Descargar Índice Pellet» al PDF trimestral `IPB-indice-precios-PELLET-<n>T<AAAA>.pdf` (el 25/10/2026 apunta al
  3T2026, subido el 20/10/2026). La mediateca de WordPress (`/wp-json/wp/v2/media?mime_type=application/pdf`)
  lista todos los PDF publicados y es el método más fiable para encontrarlos.
- **Formato.** PDF de 11 páginas con texto extraíble. Página 2: medias anuales 2012–2025 y trimestres del año en
  curso, por formato (saco 15 kg en €/saco; palet, granel en volquete y granel en cisterna en €/t), con c€/kWh
  e IPB. Página 5: **tabla de los últimos 5 trimestres**. Páginas 4 y 7–11: gráficos sin valores extraíbles.
  Metodología declarada: precios a consumidor final **con IVA (21 %) y transporte medio de 200 km** en granel,
  clases A1/A2, PCI **4.100 kcal/kg = 4,76 kWh/kg**, encuesta en la primera quincena del mes siguiente al trimestre.
- **Frecuencia.** Trimestral. Publicación unas 3 semanas tras cerrar el trimestre (3T2026 → 20/10/2026;
  2T2026 → 31/07/2026; 1T2026 → 04/05/2026; 4T2025 → 04/02/2026).
- **Histórico: parcial.** La mediateca actual solo conserva los PDF de 4T2025, 1T2026, 2T2026 y 3T2026. Como cada
  uno trae 5 trimestres, se cubren **4T2024–3T2026** con dato trimestral original. Los PDF anteriores vivían en
  la web antigua (`www.avebiom.org/sites/default/files/ipb/…`) y hoy devuelven 404; las noticias de 2022–2025 de la
  propia web no enlazan PDF. Para **2022, 2023 y 2024** la única cifra original descargable es la **media anual**
  (saco: 6,53 / 6,21 / 5,25 €/saco; granel volquete: 407,88 / 361,35 / 324,73 €/t), que está en todos los PDF.
  Coherencia comprobada: los trimestres que se solapan entre PDF (4T2025, 1T2026…) coinciden exactamente.
- **Impuestos.** Con impuestos (IVA 21 %). Ojo: la nota del 3T2026 dice que aplica el 21 % «vigente durante el
  tercer trimestre de 2026, manteniendo el mismo criterio del trimestre anterior», y en la mediateca hay una imagen
  «pellet-iva-21-desde-1-jun2026». Es decir, en 2026 el IVA del pellet estuvo reducido hasta el 31/05/2026 y AVEBIOM
  pudo aplicar el tipo vigente en cada trimestre. En la fase 2 se verificará en el BOE qué tipo rigió cada
  trimestre y qué tipo aplicó AVEBIOM, para no mezclar criterios.
- **Descargas de comprobación.**
  - 3T2026: saco **5,92 €/saco** (8,28 c€/kWh), granel volquete **370,24 €/t** (7,77 c€/kWh). Comprobación aritmética:
    5,92 / 15 kg / 4,76 kWh/kg = 8,29 c€/kWh (redondeo).
  - 4T2024 (del PDF 4T2025): saco 5,17 €/saco; granel volquete 316,99 €/t.
- **Fragilidades.** (a) Es un PDF: el texto se extrae bien hoy, pero un cambio de maqueta rompe el lector (fallará
  con aviso, no con datos malos). (b) El formato de los números varía (p. ej. «329,9» frente a «335,66»). (c) La
  página HTML devuelve 403 al cliente genérico de Python; funciona identificándose con un *User-Agent* propio
  del proyecto (sin hacerse pasar por un navegador) y la mediateca y los PDF se descargan sin problema.
- **Automatizable: frágil pero sí.** El dato nuevo de cada trimestre se obtiene sin intervención manual.

### Opciones para completar el histórico trimestral 2022–2024 del pellet (sin introducir datos a mano)

1. **Internet Archive.** Es probable que `web.archive.org` conserve los PDF antiguos de AVEBIOM. Hoy ese dominio
   está bloqueado en el entorno. Si lo permites, intento recuperarlos; serían documentos originales de AVEBIOM,
   guardados en el repositorio con su procedencia y leídos por el mismo lector.
2. **PDF antiguos que tengáis en APROPELLETS.** Si conserváis los informes trimestrales de AVEBIOM de 2022–2024,
   puedes dejarlos en `referencia/avebiom/` y el sistema los leerá igual que los actuales. No es teclear datos:
   es aportar el documento fuente.
3. **Pedir la serie a AVEBIOM** (el índice es público y gratuito por declaración suya).
4. **Quedarse con las medias anuales** de 2022–2024 (original, AVEBIOM) y el trimestral desde 4T2024.

Mi propuesta: intentar 1 y, en paralelo, 2; si ninguna da fruto, aplicar 4 y marcarlo con claridad en el panel.

---

## Contradicciones del encargo y propuestas

Las decides tú. Aquí van con los datos de la fase 1.

1. **OMIE y MIBGAS son mayoristas y sin impuestos.** Propuesta: mostrarlos sin impuestos y etiquetarlos
   «mayorista, sin impuestos» en tabla, gráficos y exportaciones. Convertirlos a «con impuestos» exigiría decidir un
   consumidor tipo; no hay forma homogénea y verificable de hacerlo.
2. **TUR 2 con impuestos.** Propuesta: con impuestos (IVA e impuesto sobre hidrocarburos vigentes en cada fecha),
   guardando también el valor sin impuestos, que es el que publica el BOE y el que usa el boletín. Impuestos a
   verificar en el BOE en la fase 2 (lo que sé hoy, pendiente de confirmar texto a texto): IVA 21 % hasta
   30/09/2022; 5 % del 01/10/2022 al 31/12/2023 (RDL 17/2022); 10 % del 01/01 al 31/03/2024 (RDL 8/2023); 21 % desde
   el 01/04/2024, salvo medidas de 2026 (RDL 7/2026 y 25/2026) que leeré. Hidrocarburos gas natural uso doméstico:
   0,65 €/GJ = 0,00234 €/kWh (Ley 38/1992, epígrafe 1.10). Además la TUR se factura en kWh PCS; el boletín usa la
   relación PCI/PCS 0,904 para pasarla a PCI, como el resto de combustibles.
3. **PVPC con impuestos.** Propuesta: confirmar con la API (cuando haya token) que el 1001 es sin impuestos y aplicar
   el impuesto especial sobre la electricidad y el IVA vigentes en cada fecha. Lo que sé hoy, a confirmar en el BOE:
   IVA 10 % desde 26/06/2021 (RDL 12/2021); 5 % del 01/07/2022 al 31/12/2023 (RDL 11/2022); en 2024, 10 % o 21 %
   según el precio medio del mercado del mes anterior superara o no 45 €/MWh (RDL 8/2023), lo que da meses al 21 %
   (de marzo a junio de 2024) y meses al 10 %; 21 % desde 01/01/2025. Impuesto eléctrico: 0,5 % del 16/09/2021 al
   31/12/2023 (RDL 17/2021 y prórrogas); 2,5 % de enero a marzo de 2024; 3,8 % de abril a junio de 2024; 5,11269632 %
   desde 01/07/2024. Con referencia al BOE de cada tramo en la tabla de la fase 2.
4. **Gráfico desde 2020 e histórico desde 2022.** Propuesta: histórico obligatorio desde 01/01/2022; y además 2020 y
   2021 para OMIE, MIBGAS, Boletín Petrolero, TUR y butano, que lo dan sin esfuerzo. PVPC 2.0TD solo desde
   01/06/2021 (antes la tarifa era otra); pellet, lo que se logre con el punto 8. El gráfico comparativo mostrará
   cada serie desde donde exista, sin rellenar.
5. **Variación semanal en indicadores no semanales.** Propuesta: comparar el valor vigente hoy con el vigente hace
   7 días (0 % si no cambió), con una nota «precio regulado/trimestral: sin cambio en la semana». Para OMIE, MIBGAS y
   PVPC, ver la propuesta 8.
6. **Pellet.** El índice se puede descargar y leer automáticamente (frágil). El histórico trimestral automático
   empieza en 4T2024. Ver las cuatro opciones de arriba.
7. **Acceso.** Sé que GitHub Pages publica una web visible para cualquiera que tenga el enlace (no se puede
   restringir en repositorios gratuitos). No publicaré nada hasta que me lo confirmes. Alternativa si no quieres
   que sea público: repositorio privado con Pages solo para la organización (requiere plan de pago de GitHub).
8. **(Nueva) «Precio actual» de los indicadores diarios.** El boletín presenta OMIE como media de 7 días. Propuesta:
   para OMIE, MIBGAS y PVPC, el «precio actual» de la tabla resumen es la media de los últimos 7 días con dato, la
   variación semanal compara con los 7 días anteriores y la interanual con los mismos 7 días del año anterior. Los
   gráficos muestran la serie diaria.
9. **(Nueva) Poder calorífico del pellet.** El boletín usa 4,8 kWh/kg (IDAE); AVEBIOM calcula sus c€/kWh con
   4,76 kWh/kg (4.100 kcal/kg). Propuesta: usar 4,8 kWh/kg para la conversión homogénea de todos los indicadores,
   guardar también el c€/kWh que publica AVEBIOM y documentar la diferencia (0,8 %). Verificaré los cuatro factores
   del boletín (pellet 4,8 kWh/kg; gasóleo C 10,28 kWh/l; butano 12,73 kWh/kg; gas natural PCI/PCS 0,904) en las
   publicaciones del IDAE en la fase 2 y te diré si alguna no coincide.
10. **(Nueva) Gasóleo de automoción en €/kWh.** El encargo lo define en €/l y la tabla resumen pide €/kWh. Propuesta:
    mostrar €/l como dato original y convertir con el mismo factor que el gasóleo de calefacción (10,28 kWh/l), marcado
    como calculado.
11. **(Nueva) Bonificación de 2022 en los gasóleos.** El Boletín no descuenta los 20 c€/l de abril–diciembre de 2022.
    Propuesta: mostrar el precio del Boletín tal cual (precio con impuestos antes de la bonificación), con una nota en
    ese tramo; no se recalcula un precio «neto» porque no lo publica la fuente.

## Qué necesito de ti para la fase 2

- **`ESIOS_TOKEN`** en la sesión (y, más adelante, como secreto de GitHub Actions). Hasta entonces el PVPC queda sin comprobar.
- Permitir **`web.archive.org`** en el entorno si quieres que intente recuperar los PDF antiguos de AVEBIOM (opcional).
- Si tenéis los PDF trimestrales de AVEBIOM de 2022–2024, dejarlos en `referencia/avebiom/` (opcional).
- Tus decisiones sobre los 11 puntos anteriores (basta un «de acuerdo» o el cambio que quieras).
