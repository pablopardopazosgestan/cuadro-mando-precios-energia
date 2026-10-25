# Cuadro de mando de precios energéticos en España

Este repositorio es la única memoria del proyecto entre sesiones. Léelo entero al empezar.
Escribe a Pablo siempre en castellano, de forma directa.

## Documentos de referencia

- `docs/ENCARGO.md`: texto íntegro del encargo (no se modifica).
- `docs/METODO_DE_TRABAJO.md`: cómo trabajar (fases, reglas sobre datos, secretos, red), arquitectura decidida,
  resumen del boletín de referencia y contradicciones a resolver. Léelo también.
- `docs/DECISIONES.md`: decisiones de Pablo con fecha y lista de propuestas pendientes.
- `docs/FUENTES.md`: resultado de la fase 1 (disponibilidad real de cada fuente, valores de control, propuestas).

## Reglas que no se negocian

- Nunca inventar, interpolar ni estimar datos sin marcarlo. Cada dato lleva fuente, fecha de publicación,
  con/sin impuestos y original/calculado. Si la fuente no da el dato, se muestra «no disponible».
- Solo datos públicos. El boletín de APROPELLETS es interno y no se sube.
- El token de ESIOS va en la variable de entorno `ESIOS_TOKEN` (sesión) y en el secreto `ESIOS_TOKEN` de GitHub
  Actions. Nunca en un fichero.
- Trabajar por fases; al terminar cada una: commit, push, informe breve a Pablo y **parar** hasta su «sigue».
- Comprobar con datos reales y escribir pruebas (pytest) para conversiones, impuestos por fecha y lectores.
- No hacerse pasar por un navegador. Si una web rechaza al cliente genérico, identificarse con el User-Agent
  del proyecto (`cuadro-mando-precios-energia/<versión> (…github…)`), como hace `scripts/fase1_sondeo_fuentes.py`.

## Estado

- **Fase 1 (disponibilidad de fuentes): terminada el 25/10/2026, pendiente de revisión de Pablo.**
  Resultado en `docs/FUENTES.md`. Siete de las ocho fuentes se han descargado y contrastado; el PVPC (ESIOS 1001)
  queda pendiente porque no había `ESIOS_TOKEN` en la sesión.
- Fase 2 (histórico y base de datos): no empezada. No empezar sin el «sigue» de Pablo.

## Siguiente paso

Al recibir el «sigue» de la fase 1: anotar en `docs/DECISIONES.md` las decisiones sobre los 11 puntos de
`docs/FUENTES.md`, comprobar si ya existe `ESIOS_TOKEN`, y empezar la fase 2 (descargadores por fuente,
normalización, tabla de impuestos por fecha con referencia al BOE, conversiones a €/kWh, media mensual,
metadatos, pytest y tabla de comprobaciones).

## Cómo ejecutar y probar (por ahora)

```bash
pip install -r requirements.txt
python scripts/fase1_sondeo_fuentes.py   # sondeo de fuentes; descarga en ./descargas/ (ignorado por git)
```

Red necesaria: `www.omie.es`, `www.mibgas.es`, `api.esios.ree.es`, `energy.ec.europa.eu`, `www.boe.es`,
`avebiom.org`. Bloqueados en el entorno actual y no imprescindibles: `energia.gob.es`, `www.miteco.gob.es`,
`www.cnmc.es`, `sedeaplicaciones.minetur.gob.es`, `web.archive.org`.

## Hechos técnicos ya comprobados (resumen; detalle en `docs/FUENTES.md`)

- OMIE: zips anuales `marginalpdbc_AAAA.zip` (2018–2022) y ficheros diarios `marginalpdbc_AAAAMMDD.1`; columna 6 =
  España; cuartos de hora desde 01/10/2025. Media enero 2022 = 201,72 €/MWh; septiembre 2026 = 143,25 (= informe OMIE).
- MIBGAS: `MIBGAS_Data_AAAA.xlsx?path=AGNO_AAAA/XLS`; hoja `Indices` (2022, columna Area) / `MIBGAS Indexes`
  (2023+, columna `MIBGAS-ES Index`). 24/10/2026 = 92,87 €/MWh (= web).
- Boletín Petrolero: fichero histórico `Weekly_Oil_Bulletin_Prices_History…xlsx`, hojas con/sin impuestos, columnas
  `ES_price_with_tax_diesel` / `_heating_oil` en €/1.000 l, semanal desde 2005. No descuenta la bonificación de 2022.
- BOE: API `datosabiertos/api/boe/sumario/AAAAMMDD` + `diario_boe/xml.php?id=`; TUR trimestral (tablas en el XML);
  butano bimestral (precio antes de impuestos en c€/kg; el título cambió en 2026 a «butano comercial envasado»).
  Reintentar ante `Connection reset`; 404 = día sin BOE.
- AVEBIOM: PDF trimestral `IPB-indice-precios-PELLET-nTAAAA.pdf` (página 5: últimos 5 trimestres; página 2: medias
  anuales). Solo hay PDF desde 4T2025 en la mediateca (`/wp-json/wp/v2/media`): trimestral desde 4T2024, anual antes.
  La página HTML devuelve 403 al User-Agent por defecto de python-requests.
