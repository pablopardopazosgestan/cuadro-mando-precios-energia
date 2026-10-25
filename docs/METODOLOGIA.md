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

21 % en todo el periodo, con una excepción sin resolver: el RDL 7/2026 art. 42.c aplica el 10 % a los productos de
varios epígrafes del art. 50 de la Ley 38/1992 e incluye el 1.8 (GLP para usos distintos del carburante). No se ha
podido confirmar si Hacienda lo aplicó al butano envasado. Entre el 22/03/2026 y el 30/06/2026 el precio de la bombona
con impuestos se deja como **no disponible** con esa explicación, en vez de suponer un tipo.

### 3.6 Condiciones de IPC de 2026

Los tipos de junio, agosto, septiembre, noviembre y diciembre de 2026 dependen de si el IPC de una subclase
(04.5.1.0 Electricidad, 04.5.2.1 Gas natural, 04.5.2.2 Hidrocarburos licuados, carburantes) superó el 15 %
interanual en un mes de referencia, «de acuerdo con la información que publique el INE». El INE
(`www.ine.es`, `servicios.ine.es`) no es accesible desde el entorno de trabajo, así que esas condiciones están en
`datos/impuestos/condiciones_ipc_2026.json` con valor `null` y los precios con impuestos de esos meses salen como
**no disponibles**. En cuanto el dominio esté permitido se leerán del INE y se recalcularán todas las series (la
actualización vuelve a aplicar los impuestos a toda la serie en cada ejecución).

## 4. Factores de conversión (código: `precios/conversiones.py`)

| Factor | Valor | Procedencia | Estado |
|---|---|---|---|
| Pellet, PCI | 4,8 kWh/kg | Boletín de referencia (cita IDAE). Decisión 9. | AVEBIOM usa 4.100 kcal/kg = 4,76 kWh/kg; su c€/kWh se guarda en la nota de cada fila. |
| Gasóleo A y C, PCI | 10,28 kWh/l | Boletín de referencia (cita IDAE). Decisión 10 (mismo factor para ambos). | Verificación directa en el IDAE pendiente: `idae.es` no es accesible desde el entorno. |
| Butano, PCI | 12,73 kWh/kg | Boletín de referencia (cita IDAE). | Ídem. |
| Gas natural, PCI/PCS | 0,904 | Boletín de referencia (cita IDAE). | La TUR se factura en kWh PCS; el €/kWh PCI es mayor en un 10,6 %. |

## 5. Cómo ejecutar y probar

```bash
pip install -r requirements.txt
python -m precios actualizar -v              # todas las fuentes
python -m precios actualizar --solo omie,tur2
python -m pytest -q tests                    # conversiones, impuestos por fecha, lectores y series
```

La primera ejecución descarga todo el histórico (unos 1.800 ficheros diarios de OMIE y 2.500 sumarios del BOE) y
deja una caché en `.cache/` (ignorada por git). Las siguientes solo piden lo nuevo.
