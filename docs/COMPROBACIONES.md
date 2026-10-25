# Comprobaciones con valores de control

Fase 2 (25/10/2026). Cada fila compara un valor de la base de datos (`datos/`) con un valor de control leído
directamente en la fuente original. La tabla la genera `python scripts/comprobaciones.py` (los valores de
control están escritos a mano en ese script, con su origen). Se vuelve a pasar en cada fase.

## Tabla automática (última ejecución: 25/10/2026)

| Serie | Clave | Columna | Base de datos | Control | Origen del control | Resultado |
|---|---|---|---|---|---|---|
| omie | 2022-01-01 | valor_original | 122.629200 | 122.630000 | fichero marginalpdbc_20220101.1 (media de 24 horas, col. España) | OK |
| omie | 2022-01 | media_original | 201.717623 | 201.720000 | OMIE: precio medio del mercado diario, España, enero 2022 | OK |
| omie | 2026-09 | media_original | 143.254043 | 143.250000 | OMIE, Informe mensual septiembre 2026, España | OK |
| omie | 2026-10-24 | valor_original | 137.192500 | 137.190000 | fichero marginalpdbc_20261024.1 (media de 96 cuartos de hora) | OK |
| mibgas | 2022-01-03 | valor_original | 66.530000 | 66.530000 | MIBGAS_Data_2022.xlsx, hoja Indices, ES | OK |
| mibgas | 2026-10-24 | valor_original | 92.870000 | 92.870000 | web de MIBGAS, gráfica «Índice de precio y volumen del día de gas» | OK |
| gasoleo_a | 2022-01-03 | valor_original | 1.347150 | 1.347150 | Weekly Oil Bulletin, ES_price_with_tax_diesel = 1.347,15 €/1.000 l | OK |
| gasoleo_a | 2022-01-03 | eur_kwh_sin_impuestos | 0.071435 | 0.071435 | 734,35 €/1.000 l sin impuestos ÷ 10,28 kWh/l | OK |
| gasoleo_c | 2022-01-03 | valor_original | 0.830030 | 0.830030 | Weekly Oil Bulletin, ES_price_with_tax_heating_oil = 830,03 €/1.000 l | OK |
| gasoleo_c | 2026-10-19 | valor_original | 1.521330 | 1.521330 | Weekly Oil Bulletin (histórico descargado el 25/10/2026) | OK |
| tur2 | 2022-01-01 | valor_original | 4.520114 | 4.520114 | BOE-A-2021-21356, tabla TUR.2, variable cent/kWh | OK |
| tur2 | 2022-01-01 | eur_kwh_con_impuestos | 0.063634 | 0.063634 | (4,520114 + 0,234) × 1,21 c€/kWh PCS → €/kWh PCI | OK |
| tur2 | 2026-10-01 | valor_original | 5.042762 | 5.042762 | BOE-A-2026-20389, tabla TUR.2 | OK |
| butano | 2022-01-18 | valor_original | 115.903700 | 115.903700 | BOE-A-2022-665: 115,9037 c€/kg | OK |
| butano | 2022-01-18 | eur_kwh_con_impuestos | 0.111593 | 0.111593 | bombona 17,76 € con impuestos (calculado) ÷ 12,5 kg ÷ 12,73 kWh/kg | OK |
| pellet_saco | 2026-07-01 | valor_original | 5.920000 | 5.920000 | AVEBIOM IPB pellet 3T2026, saco 15 kg | OK |
| pellet_granel | 2026-07-01 | valor_original | 370.240000 | 370.240000 | AVEBIOM IPB pellet 3T2026, granel en volquete | OK |
| pellet_saco | 2022-01-01 | valor_original | 6.530000 | 6.530000 | AVEBIOM IPB pellet (media anual 2022) | OK |

18 de 18 comprobaciones correctas

## Contrastes adicionales (a mano)

| Qué | Base de datos | Fuente / referencia externa | Resultado |
|---|---|---|---|
| OMIE, media mensual de septiembre de 2026 (España y Portugal) | 143,25 (ES) y 143,90 (PT) €/MWh | Informe mensual de OMIE, septiembre 2026: España 143,25, Portugal 143,90 | Coincide; confirma que la columna 6 de los ficheros es España |
| OMIE, media de enero de 2022 | 201,72 €/MWh | Valor publicado por OMIE para enero de 2022 | Coincide |
| MIBGAS-ES Index 22–24/10/2026 | 87,38 / 90,05 / 92,87 | Gráfica «Índice de precio y volumen del día de gas» de mibgas.es | Coincide |
| Boletín Petrolero, ratio con impuestos / (sin impuestos + impuesto especial) | 1,21 en todas las semanas de 2022–2023 revisadas | IVA 21 % sobre carburantes | Coherente; confirma que el precio español de 2022 no descuenta la bonificación de 20 c€/l |
| Butano, bombona con impuestos (calculado) 17/05/2022 | 19,55 € | Precio máximo de la bombona congelado en 19,55 € desde mayo de 2022 (RDL 6/2022 y prórrogas), ampliamente publicado | Coincide al céntimo; valida el cálculo (IH 15 €/t + IVA 21 %) |
| Butano, bombona 16/11/2021 y 18/01/2022 | 16,92 € y 17,76 € | Subidas del 5 % publicadas en esas revisiones | Coincide (17,76 / 16,92 = 1,0496) |
| TUR 2 en vigor el 01/07/2024 | Sin fila nueva: sigue el valor del 01/04/2024 (4,095293 c€/kWh) | BOE-A-2024-13105 dice literalmente que TUR.1–3 «serán los mismos publicados en la Resolución de 26 de marzo de 2024» | Correcto: la serie mantiene el valor vigente |
| TUR 2, corrección de errores de junio de 2023 | TUR.2 desde 01/07/2023 = 4,020647 c€/kWh | BOE-A-2023-15235 (corrige la resolución de 27/06/2023) | La serie toma el valor corregido |
| TUR 2, serie 2020–2026 | 25 revisiones (trimestrales, sin 2T2020 ni 3T2024) | Sumarios del BOE recorridos día a día desde 01/11/2019 | Ver nota 1 |
| Pellet, trimestres solapados entre PDF (4T2025–2T2026) | Idénticos en los cuatro PDF | PDF 4T2025, 1T2026, 2T2026, 3T2026 de AVEBIOM | Coherente |
| Pellet, c€/kWh | 8,28 (AVEBIOM, 4,76 kWh/kg) frente a 8,22 (4,8 kWh/kg) para 5,92 €/saco | Aritmética | Diferencia del 0,8 % por el factor (decisión 9) |

Nota 1. En el 2T2020 no hay resolución de TUR en el BOE con el título habitual; se mantiene el valor de enero de
2020 hasta el 01/07/2020. En el 3T2024 la resolución de junio solo revisa las TUR.4 a TUR.11 y dice que TUR.1–3 no
cambian.

## Lo que no se ha podido comprobar

- **PVPC (ESIOS 1001):** sin `ESIOS_TOKEN` no hay datos. Los dos únicos contrastes posibles han sido con la API pública
  de REE para días sueltos (01/01/2022 00h = 204,51 €/MWh; 24/10/2026 00h = 228,20 €/MWh), que no admite rangos.
- **Impuestos de 2026 condicionados al IPC:** junio, agosto, septiembre, noviembre y diciembre de 2026 (IVA e IEE de
  la electricidad; IVA e hidrocarburos del gas y los pellets; hidrocarburos del butano). Sin acceso al INE quedan
  como «no disponible». Afecta hoy a 2 de 40 filas del butano (mayo y septiembre de 2026: vigentes en junio/agosto y
  septiembre/noviembre) y afectará al PVPC cuando haya datos. No afecta al Boletín Petrolero ni a AVEBIOM (precios ya
  con impuestos).
- **IVA del butano entre el 22/03 y el 30/06/2026** (RDL 7/2026 art. 42.c): sin resolver; ver `METODOLOGIA.md` §3.5.
- **Factores de conversión del IDAE:** no se ha podido abrir idae.es; se usan los del boletín de referencia.
