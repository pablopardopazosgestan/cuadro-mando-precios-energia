# Instrucciones de uso

Cuadro de mando de precios energéticos en España: ocho indicadores en €/kWh (OMIE, MIBGAS, gasóleo A, PVPC 2.0TD,
TUR 2, gasóleo C, butano y pellet en saco y a granel), histórico desde 2020 donde la fuente lo da (obligatorio desde
2022), actualización automática semanal e informes PDF y Excel. Nada se estima: cuando una fuente no da un dato,
aparece «no disponible» (n. d.).

## 1. Consultar

- **Enlace:** https://pablopardopazosgestan.github.io/cuadro-mando-precios-energia/ (público para quien tenga el enlace).
- **Resumen ejecutivo:** ocho tarjetas con el precio actual, la variación semanal e interanual (rojo sube, verde
  baja), la fuente, la fecha del dato y la tendencia de 24 meses; ranking del coste por kWh de la energía final con
  impuestos; tabla ordenable (pulsar una cabecera) y «Claves de la semana», generadas solo a partir de los números.
- **Precio actual:** media de los últimos 7 días (OMIE, MIBGAS, PVPC), última semana publicada (gasóleos) o valor
  vigente hoy (TUR 2, butano, pellet). OMIE y MIBGAS son precios mayoristas sin impuestos; el resto, con impuestos.
- **Comparativo:** marque las series que quiera comparar o use un conjunto (todas, energía final con impuestos,
  calefacción doméstica, electricidad, gas natural, carburantes). Elija el periodo (fechas o atajos), la frecuencia
  (original o media mensual), **Base 100** (para comparar evoluciones de series con precios muy distintos) y la
  **media móvil de 7 días** (suaviza OMIE, MIBGAS y PVPC). Cada línea lleva su nombre y último valor al final.
  Pase el ratón por una línea para ver el valor exacto y el dato original. La selección queda en la dirección de la
  página: «Copiar enlace» da una URL que reproduce esa misma comparación.
- **Evolución de cada indicador:** un gráfico por indicador en su unidad original o en €/kWh, «Ver datos» (tabla del
  periodo con el dato original y el €/kWh sin y con impuestos) y «CSV» (descarga de esos datos). La casilla
  «Mostrar cambios de impuestos» marca las fechas en que cambió el IVA, el impuesto eléctrico o el de hidrocarburos,
  con la referencia al BOE.
- **Estado de las fuentes:** última descarga correcta, último dato y resultado de cada fuente, con enlace a la última
  ejecución.
- **Fuentes y criterios:** de dónde sale cada indicador, unidad, frecuencia, impuestos y conversión a €/kWh.
- La página se adapta al móvil, sigue el modo claro u oscuro del dispositivo y se imprime limpia (Ctrl+P).

## 2. Actualizar

- **Automática:** cada lunes a las 05:17 UTC (06:17 u 07:17 hora peninsular) GitHub Actions descarga lo nuevo de
  cada fuente, comprueba que el histórico no se reduce, regenera los informes y el panel, guarda los datos en el
  repositorio y publica la web. No hay que hacer nada.
- **A mano, desde el panel:** botón «Actualizar» de la cabecera. La primera vez pide un token personal de GitHub
  (*fine-grained*, solo este repositorio, permiso *Actions: Read and write*; empieza por `github_pat_`), que se guarda
  únicamente en ese navegador. **No es el token de ESIOS**: ese ya está como secreto en GitHub y lo usa el workflow.
  Lanza la actualización por la API de GitHub, muestra el progreso y recarga la página al terminar (1–2 minutos).
  «Olvidar token» lo borra del navegador.
- **A mano, desde GitHub:** pestaña *Actions* → «Actualizar datos y publicar» → *Run workflow*.
- **En un ordenador propio** (Python 3.12 o superior):
  ```bash
  pip install -r requirements.txt
  export ESIOS_TOKEN=...            # token personal de ESIOS (REE), necesario solo para el PVPC
  python -m precios actualizar -v   # descarga lo nuevo y reconstruye datos/
  python -m precios informes        # PDF y Excel en sitio/informes/
  python -m precios panel           # cuadro de mando en sitio/
  python -m pytest -q tests         # pruebas
  ```
- **Resultado de cada actualización:** `datos/estado.json` (por fuente: resultado, error, última descarga correcta,
  último dato y si hubo dato nuevo) y el resumen de la ejecución en GitHub Actions. Si una fuente falla, la ejecución
  termina en rojo y GitHub avisa por correo, pero la web se publica igualmente con el último dato correcto.

## 3. Exportar

- **Informe PDF** (2 páginas, para dirección: cuadro de mando con tarjetas, ranking, sobrecoste de las alternativas
  frente al pellet y claves; y ocho gráficos grandes de evolución a 24 meses con la lectura de qué mide cada indicador y cómo repercute en el pellet) y **Excel** (histórico completo con datos originales y convertidos,
  medias mensuales y anuales, gráficos vinculados, hoja «Comparador» con desplegables, fuentes y criterios): botones
  «Informe PDF» e «Histórico Excel» en la cabecera del panel, o la sección «Descargas». Se regeneran en cada
  actualización; solo se conserva la última versión (el histórico completo está en `datos/`, versionado en git).
- **CSV de un indicador:** botón «CSV» en su gráfico (datos del periodo elegido; separador «;», abre en Excel).
- **Datos brutos:** `datos/series/<indicador>.csv` (frecuencia original) y `datos/mensual/<indicador>.csv`.
- En el Excel, la hoja «Comparador» permite elegir hasta cuatro series, frecuencia mensual o anual y Base 100 sin
  tocar fórmulas; los periodos sin dato aparecen como #N/A y no se dibujan.

## 4. Si una fuente falla

Dónde se ve: aviso en la cabecera del panel, tabla «Estado de las fuentes», correo de GitHub y `datos/estado.json`
(campo `error` y traza). Mientras tanto se muestra el último dato correcto con su fecha. Casos previstos:

| Fuente | Qué suele pasar | Qué hacer |
|---|---|---|
| REE/ESIOS (PVPC) | Falta o caducó el secreto `ESIOS_TOKEN`; bloqueo temporal por IP (403). | Crear o renovar el secreto en *Settings → Secrets and variables → Actions* (token gratuito pidiéndolo a consultasios@ree.es). Si es un 403, el descargador ya espera y reintenta; relanzar más tarde. |
| AVEBIOM (pellet) | El servidor responde con un desafío captcha al ejecutor de GitHub (no se sortea). | La web solo se consulta cuando puede haber trimestre nuevo (desde 14 días después del cierre del trimestre siguiente al último guardado) y se reintenta con esperas. Si persiste, lanzar `python -m precios actualizar --solo pellet_saco` desde otro equipo: el PDF queda guardado en el repositorio y las ejecuciones siguientes ya no lo necesitan. |
| BOE (TUR 2, butano) | Caída pasajera o cambio de título de la resolución. | Relanzar. Si una resolución nueva no se detecta, revisar las expresiones de `precios/fuentes/boe.py` (las resoluciones se buscan por título en el sumario). |
| OMIE, MIBGAS | Fichero del día aún no publicado o cambio de formato. | Relanzar al día siguiente; si persiste, comparar el fichero con `docs/FUENTES.md`. |
| Comisión Europea (gasóleos) | El Boletín Petrolero se publica con 1–2 semanas de retraso; a veces la descarga se corta. | Relanzar. «Sin actualización en el periodo» con dato de hace una o dos semanas es normal. |
| INE (IPC de 2026) | Caída pasajera. | Relanzar. Solo afecta a los impuestos de 2026 que dependen del IPC; mientras tanto esos meses quedan «no disponibles», nunca estimados. |

Comprobaciones útiles: `python scripts/comprobaciones.py` (22 valores de control contra la fuente) y
`python scripts/verificar_historico.py` (ninguna serie pierde filas).

## 5. Dónde está cada cosa

- Código: `precios/` (lectores en `precios/fuentes/`, impuestos en `precios/impuestos.py`, conversiones en
  `precios/conversiones.py`, panel en `precios/panel.py` y `precios/plantilla_panel.html`, informes en
  `precios/informes.py`). Pruebas en `tests/`. Flujos de GitHub en `.github/workflows/`.
- Datos: `datos/` (series, medias mensuales, estado, metadatos, condiciones de IPC y documentos originales).
- Web publicada: `sitio/` (generada; no editar a mano).
- Documentación: `docs/METODOLOGIA.md` (cómo se construye cada serie, tabla de impuestos por fecha con referencia al
  BOE, factores), `docs/FUENTES.md`, `docs/COMPROBACIONES.md`, `docs/DECISIONES.md`.
