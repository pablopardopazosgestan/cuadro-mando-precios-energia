# Cuadro de mando de precios energéticos en España

Este repositorio es la única memoria del proyecto entre sesiones. Léelo entero al empezar.
Escribe a Pablo siempre en castellano, de forma directa.

## Documentos de referencia

- `docs/ENCARGO.md`: texto íntegro del encargo (no se modifica).
- `docs/METODO_DE_TRABAJO.md`: cómo trabajar (fases, reglas sobre datos, secretos, red), arquitectura decidida,
  resumen del boletín de referencia y contradicciones a resolver. Léelo también.
- `docs/DECISIONES.md`: decisiones de Pablo con fecha y lista de propuestas pendientes.
- `docs/FUENTES.md`: resultado de la fase 1 (disponibilidad real de cada fuente, valores de control, propuestas).
- `docs/METODOLOGIA.md`: fase 2: ficheros de datos, cómo se construye cada serie, tabla de impuestos por fecha con
  referencia al BOE, factores de conversión y cómo ejecutar/probar.
- `docs/COMPROBACIONES.md`: tabla de valores de control contrastados con la fuente.

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

- Fase 1 (disponibilidad de fuentes): terminada el 25/10/2026 y aceptada por Pablo (las 11 propuestas).
- Fase 2 (histórico y base de datos): terminada el 25/10/2026 y aceptada el 27/10/2026. El 27/10 se completó:
  impuestos de 2026 con el IPC del INE (`precios/fuentes/ine.py`), IVA del butano de 2026 resuelto, factores IDAE
  verificados. **PVPC: el cortafuegos de ESIOS (Incapsula) bloqueó la IP del entorno tras las primeras peticiones**
  (403 también con curl); el descargador espacia peticiones y reintenta con esperas largas. Si sigue bloqueado,
  la descarga se hará desde el ejecutor de GitHub Actions (fase 4).
- Fase 3 (cuadro de mando): terminada y publicada el 27/10/2026. Pablo activó Pages (Settings → Pages → Source:
  GitHub Actions) y permitió la rama `claude/new-session-dqbsty` en el entorno `github-pages`. Enlace:
  https://pablopardopazosgestan.github.io/cuadro-mando-precios-energia/
- **Fase 4 (actualización automática): terminada el 27/10/2026, pendiente de revisión de Pablo.** Workflow
  `.github/workflows/actualizar.yml` (lunes 05:17 UTC + manual + al cambiar el propio fichero en la rama de trabajo):
  pytest → actualizar → verificar histórico → comprobaciones → panel → commit de datos/ y sitio/ → Pages. Ejecución
  real el 27/10/2026 (run 40486363420): todo correcto en 56 s, commit «Actualización automática» y publicación;
  terminó en rojo solo por el PVPC (falta el secreto `ESIOS_TOKEN`, que debe crear Pablo). Mientras el workflow no
  esté en `main`, GitHub no muestra «Run workflow»: se relanza con «Re-run all jobs» o cambiando el fichero.
  Las ejecuciones automáticas hacen commits en la rama: hacer `git pull --rebase` antes de trabajar.
- Fase 4 aceptada el 27/10/2026: Pablo creó el secreto `ESIOS_TOKEN` y relanzó; la ejecución desde GitHub descargó
  el PVPC completo (1.975 días desde 01/06/2021) sin bloqueo: **las 8 fuentes están en ok.**
- **Fase 5 (exportación PDF y Excel): terminada el 27/10/2026, pendiente de revisión de Pablo.** `python -m precios
  informes` genera `sitio/informes/informe.pdf` y `historico.xlsx` (ver `docs/METODOLOGIA.md` §8); el workflow los
  regenera antes del panel y el panel los enlaza en «Descargas».
- **Mejora de visualización (27/10/2026, versión 0.3.0), pendiente de revisión de Pablo.** Encargo en
  `docs/PROMPT_MEJORA_VISUALIZACION.md`. Panel: selector de series con conjuntos, estado en la URL, leyenda fuera,
  etiquetas finales sin solapes, Base 100, media móvil 7 d, tarjetas + ranking + tabla ordenable, gráficos
  individuales con unidad, «Ver datos», CSV y marcas de cambios de impuestos (`impuestos.cambios_impuestos`), nav
  fija, impresión, claro/oscuro. PDF: etiquetas finales, segundo comparativo de energía final, periodo sombreado,
  mini tendencias en la tabla. Excel: tarjetas y ranking ordenado en «Cuadro de mando», hoja «Comparador» con
  desplegables, INDEX/MATCH y gráfico vinculado (fórmulas comprobadas con LibreOffice). Detalle en
  `docs/METODOLOGIA.md` §6 y §8; pruebas JS con Node en `tests/test_panel_js.py`.
- Mejora de visualización aceptada el 27/10/2026 («sigue»). Pablo delegó la decisión sobre AVEBIOM (ver abajo).
- **Fase 6: Pablo aceptó la fusión el 28/10/2026 («fusiona en main»).** La rama `claude/new-session-dqbsty` se fusionó en
  `main` (merge sin reescribir historia); los dos workflows disparan ahora solo en `main` (y «Run workflow» ya aparece).
  A partir de aquí se trabaja en `main`; las ejecuciones automáticas hacen commits en `main`: `git pull --rebase` antes.

- **28/10/2026, a petición de Pablo:** botón «Actualizar» del panel lanza el workflow por la API de GitHub con token
  personal guardado en el navegador (`panel.json` → `github`; diálogo en la plantilla). PDF reducido a 2 páginas: cuadro
  de mando + gráfico de sobrecoste de las alternativas frente al pellet + «lectura para dirección» con texto fijo por
  indicador (`precios/lectura.py`, decisión en DECISIONES) y frases calculadas. Pruebas: `tests/test_lectura.py`.
- Guía de usuario en PDF (27/10/2026, a petición de Pablo antes de fusionar): `docs/GUIA_DE_USUARIO.pdf`, generada por
  `scripts/generar_guia.py` a partir de las capturas de `docs/guia/` (`scripts/capturas_guia.js`, Playwright) y de las
  páginas del informe. Regenerar si cambia el panel o los informes.

## Siguiente paso

Entrega hecha (enlace, PDF, Excel, `docs/USO.md`, `docs/GUIA_DE_USUARIO.pdf`, actualización semanal en `main`). Sin
tareas abiertas salvo las que pida Pablo. Pendiente de observar: primera ejecución programada del lunes y la búsqueda del
PDF 4T2026 de AVEBIOM a partir del 15/01/2027.

## Cómo ejecutar y probar

```bash
pip install -r requirements.txt
python -m precios actualizar -v            # descarga lo nuevo y reconstruye datos/ (primera vez: ~30 min)
python -m precios actualizar --solo omie   # una sola serie
python -m precios informes                 # genera sitio/informes/informe.pdf y historico.xlsx
python -m precios panel                    # genera el cuadro de mando en sitio/
python -m pytest -q tests                  # pruebas
python scripts/comprobaciones.py           # valores de control contra la fuente
python scripts/fase1_sondeo_fuentes.py     # sondeo de fuentes de la fase 1
```

Caché de descargas en `.cache/` (ignorada). Documentos originales (XML del BOE, PDF de AVEBIOM) en
`datos/fuentes_originales/` (versionados).

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
- Impuestos: tabla completa 2020–2026 en `docs/METODOLOGIA.md` §3 y `precios/impuestos.py`. Los meses de 2026 cuyos
  tipos dependen del IPC (junio, agosto, septiembre, noviembre, diciembre) están «no disponibles» hasta poder leer el
  INE; el IVA del butano entre 22/03 y 30/06/2026 queda sin resolver (RDL 7/2026 art. 42.c).
- Accesibles desde el 27/10/2026: `www.ine.es` (incluido su servicio Tempus `/wstempus/js/ES/DATOS_TABLA/<id>`;
  `servicios.ine.es` sigue bloqueado), `www.idae.es`, `www.miteco.gob.es`. Siguen bloqueados `web.archive.org`,
  `sede.agenciatributaria.gob.es`. Las CDN de JavaScript no son accesibles desde el entorno: Plotly va dentro del repo
  (`precios/plotly.min.js`, extraído del paquete `plotly` de PyPI).
- ESIOS: la API bloquea por IP (Incapsula, 403) tras varias peticiones seguidas; `precios/fuentes/esios.py` espacia
  las peticiones 4 s y espera 2–15 min ante un 403.
- AVEBIOM: el 27/10/2026 su servidor (SiteGround) respondió al ejecutor de GitHub con un desafío captcha
  (`/.well-known/sgcaptcha/`) en dos ejecuciones (40498936289, 40499351715); desde el entorno de sesión responde bien.
  Decisión (Pablo delegó): el pellet se reconstruye desde los PDF versionados (`datos/fuentes_originales/avebiom/` +
  `indice.json`) y la web solo se consulta cuando puede haber trimestre nuevo (`avebiom.toca_consultar`: 14 días tras
  el cierre del trimestre siguiente al último guardado), con dos reintentos espaciados; `--solo pellet_saco` fuerza.
