# Registro de decisiones

Cada decisión de Pablo, con fecha. Las propuestas pendientes de decidir se listan al final;
cuando se decidan pasan a la tabla con su fecha.

| Fecha | Decisión | Contexto / alternativa descartada |
|-------|----------|-----------------------------------|
| 2026-10-25 | Arquitectura: Python + datos versionados en el repositorio + GitHub Actions (semanal y manual) + GitHub Pages + PDF/Excel generados en cada actualización. | Fijada en el encargo. En la fase 1 no se ha encontrado nada que la invalide. |
| 2026-10-25 | Pablo acepta las 11 propuestas de la fase 1 («acepto tus propuestas, sigue»). | Ver detalle de cada una en `FUENTES.md`, apartado «Contradicciones del encargo y propuestas». Resumen: 1) OMIE y MIBGAS sin impuestos, etiquetados como mayoristas; 2) TUR 2 con impuestos vigentes en cada fecha, guardando el valor sin impuestos; 3) PVPC con impuesto eléctrico e IVA vigentes en cada fecha; 4) histórico desde 2022 y 2020–2021 donde la fuente lo dé; 5) variación semanal de regulados = vigente hoy frente a hace 7 días; 6) pellet trimestral desde 4T2024 y anual antes, salvo recuperación de PDF antiguos; 7) GitHub Pages será público con el enlace; 8) «precio actual» de OMIE, MIBGAS y PVPC = media de 7 días; 9) pellet a 4,8 kWh/kg, guardando el c€/kWh de AVEBIOM; 10) gasóleo A a €/kWh con 10,28 kWh/l; 11) gasóleos de 2022 sin descontar la bonificación, con nota. |

## Pendientes de decisión (propuestas de la fase 1)

Todas las propuestas de la fase 1 quedaron aceptadas el 25/10/2026 (fila anterior). Se conserva la lista para referencia:

1. OMIE y MIBGAS: mostrar sin impuestos, indicándolo.
2. TUR 2: con impuestos (IVA e hidrocarburos vigentes en cada fecha), guardando el valor sin impuestos.
3. PVPC: el indicador 1001 de ESIOS es sin impuestos; aplicar impuesto eléctrico e IVA vigentes en cada fecha.
4. Histórico: obligatorio desde 01/01/2022; 2020 y 2021 se incluyen donde la fuente los da sin esfuerzo (OMIE, MIBGAS, Boletín Petrolero, BOE). PVPC 2.0TD solo existe desde 01/06/2021; AVEBIOM solo da medias anuales antes de 4T2024.
5. Variación semanal en indicadores no semanales: valor vigente hoy frente al vigente hace 7 días, con nota.
6. Pellet: histórico trimestral automático solo desde 4T2024; antes, medias anuales oficiales de AVEBIOM. Se proponen vías para recuperar los trimestres 2022–2024 sin introducir datos a mano.
7. Acceso: GitHub Pages publica una web visible para cualquiera que tenga el enlace.
8. (Nueva) «Precio actual» de los indicadores diarios (OMIE, MIBGAS, PVPC): media de los últimos 7 días, como hace el boletín con OMIE.
9. (Nueva) Factor del pellet: 4,8 kWh/kg (boletín, IDAE) frente a 4,76 kWh/kg (AVEBIOM, 4.100 kcal/kg).
10. (Nueva) Gasóleo de automoción: el encargo lo pide en €/l; para la tabla resumen en €/kWh se propone el mismo factor que el de calefacción (10,28 kWh/l, IDAE), marcándolo como calculado.
11. (Nueva) Gasóleos 2022: el Boletín Petrolero no descuenta la bonificación de 20 c€/l de abril–diciembre de 2022; se propone mostrar el precio del Boletín con una nota.

| 2026-10-27 | Pablo acepta la fase 2 y aporta el token de ESIOS y el acceso al INE, idae.es y miteco.gob.es. Pide completar los datos pendientes y pasar a la fase 3. | `web.archive.org` sigue bloqueado en el entorno. |
| 2026-10-27 | Criterio (propuesto por Claude, sin objeción): el «IPC de carburantes» del RDL 7/2026 se lee como la clase 07.2.2 del INE (Combustibles y lubricantes para vehículos personales). | La norma no da código. El resultado (+15,5 % en abril) coincide con que la bombona mantuvo en junio el IVA del 10 % y el IH a 0. |
| 2026-10-27 | El IVA del butano del 22/03 al 30/06/2026 se toma al 10 % (RDL 7/2026 art. 42.c), confirmado por el precio oficial de la bombona de mayo (15,39 €). | Antes figuraba como «no disponible». |

| 2026-10-27 | Fase 3 construida como sitio estático con Plotly incluido en el repositorio (sin CDN) y publicación por GitHub Actions (`pages.yml`). | GitHub Pages solo admite raíz o `/docs` de una rama, o despliegue por Actions; `docs/` ya es la documentación. |

| 2026-10-27 | Pablo activa GitHub Pages (origen «GitHub Actions») y permite la rama de trabajo en el entorno `github-pages`; el cuadro de mando queda publicado. Pide avanzar a la fase 4. | Enlace: https://pablopardopazosgestan.github.io/cuadro-mando-precios-energia/ |
| 2026-10-27 | Fase 4: la actualización semanal se programa los lunes a las 05:17 UTC; si falla una fuente se publica con el último dato correcto y la ejecución termina en rojo. | Decisión de Claude dentro de lo que fija el encargo; cambiable en `actualizar.yml`. |

| 2026-10-27 | Pablo crea el secreto `ESIOS_TOKEN` y relanza el workflow; acepta la fase 4 y pide la fase 5. | PVPC completo desde el ejecutor de GitHub. |
| 2026-10-27 | Fase 5: los informes se regeneran en cada actualización y solo se conserva la última versión (`informe.pdf`, `historico.xlsx`). El Excel incluye también 2020–2021 donde la fuente lo da (el encargo pide desde 2022). | Decisión de Claude; cambiable. |
| 2026-10-27 | Pablo pide, antes de la fase 6, mejorar la presentación de los informes (más visual y manejable para dirección, sin perder métricas) y después la visualización e interactividad del panel (selector de series, sin solapes, Base 100, media móvil, cambios de impuestos, Excel «Comparador»…), con el encargo detallado en `docs/PROMPT_MEJORA_VISUALIZACION.md`. | Aplicado el 27/10/2026 (versión 0.3.0). Sin cambios en fuentes, datos ni criterios de cálculo. |
| 2026-10-27 | AVEBIOM devolvió un desafío captcha al ejecutor de GitHub en dos ejecuciones. Pablo delega la solución en Claude: la web se consulta solo cuando puede haber trimestre nuevo (14 días tras el cierre del trimestre siguiente al último guardado) y, al consultar, se reintenta con esperas; el resto de semanas el pellet se reconstruye desde los PDF versionados. El plazo «fuente no disponible» del pellet pasa de 125 a 230 días. | `docs/METODOLOGIA.md` §7. Nada se estima: si la consulta falla, error visible. |
| 2026-10-28 | Pablo pide que el botón «Actualizar» actualice directamente desde el panel. Se hace por la API de GitHub con un token personal del usuario guardado solo en su navegador (sin servidor intermedio ni secretos en el repositorio). | El sitio es estático; no hay otra forma de lanzar el workflow sin exponer credenciales. |
| 2026-10-28 | Pablo pide un PDF más corto y visual, con texto que explique qué significa cada métrica y cómo repercute en los costes de producción y el precio del pellet. Se relaja el criterio «sin interpretación» del informe: se añade una lectura fija por indicador (texto redactado, revisable) separada de las frases calculadas con datos; el gráfico de sobrecoste frente al pellet es un dato derivado marcado como calculado. El panel web sigue sin interpretación. | `precios/lectura.py`; `docs/METODOLOGIA.md` §8. El impacto en €/t no se cuantifica (requiere consumos de planta, no públicos). |
| 2026-10-29 | Pablo pide un PDF aún más visual: en la página 2 se quita la columna de frases calculadas y se ponen ocho gráficos grandes de evolución (24 meses) con la lectura fija debajo. | Los datos y tablas quedan en el panel y el Excel. |
| 2026-10-28 | Pablo acepta fusionar la rama de desarrollo en `main`. Los workflows pasan a disparar solo en `main`. | Entrega de la fase 6. |

## Pendientes que dependen de Pablo (fase 2, 25/10/2026; revisado el 27/10/2026)

1. ~~Token de ESIOS~~ Resuelto el 27/10/2026 (en la sesión). Falta crearlo como secreto `ESIOS_TOKEN` de GitHub Actions en la fase 4.
2. ~~Acceso al INE~~ Resuelto el 27/10/2026 (`www.ine.es`; `servicios.ine.es` sigue bloqueado pero no hace falta).
3. **Acceso a `web.archive.org`:** sigue bloqueado el 27/10/2026 (la petición CONNECT recibe 403 del proxy). Serviría para
   intentar recuperar los PDF antiguos de AVEBIOM (2022–2024).
4. ~~Acceso a miteco.gob.es~~ Abierto, aunque la duda del IVA del butano se resolvió con los precios publicados por La Moncloa y la prensa.
5. ~~Secreto `ESIOS_TOKEN` en GitHub Actions~~ Creado el 27/10/2026.
