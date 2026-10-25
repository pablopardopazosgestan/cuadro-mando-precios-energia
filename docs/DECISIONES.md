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

## Pendientes que dependen de Pablo (fase 2, 25/10/2026)

1. **Token de ESIOS.** Se solicita gratis a REE escribiendo a consultasios@ree.es (asunto «Solicitud de token personal
   API e·sios»); llega por correo. Hay que definirlo como variable de entorno `ESIOS_TOKEN` de la sesión y, en la fase 4,
   como secreto de GitHub Actions con el mismo nombre. Sin él, el PVPC no tiene datos.
2. **Acceso al INE** (`www.ine.es` y `servicios.ine.es`): necesario para resolver los impuestos de junio, agosto,
   septiembre, noviembre y diciembre de 2026 (condiciones de IPC de los RDL 7/2026, 18/2026 y 25/2026).
3. **Acceso a `web.archive.org`:** permitido por Pablo el 25/10/2026, pero el entorno seguía bloqueándolo en esa sesión
   (puede requerir una sesión nueva). Serviría para recuperar los PDF antiguos de AVEBIOM (2022–2024).
4. **Acceso a `www.miteco.gob.es`** (opcional): para contrastar el precio de la bombona con impuestos que publica el
   Ministerio en cada revisión y resolver la duda del IVA del butano en primavera de 2026.
