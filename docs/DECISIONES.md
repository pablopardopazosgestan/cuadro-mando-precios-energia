# Registro de decisiones

Cada decisión de Pablo, con fecha. Las propuestas pendientes de decidir se listan al final;
cuando se decidan pasan a la tabla con su fecha.

| Fecha | Decisión | Contexto / alternativa descartada |
|-------|----------|-----------------------------------|
| 2026-10-25 | Arquitectura: Python + datos versionados en el repositorio + GitHub Actions (semanal y manual) + GitHub Pages + PDF/Excel generados en cada actualización. | Fijada en el encargo. En la fase 1 no se ha encontrado nada que la invalide. |

## Pendientes de decisión (propuestas de la fase 1)

Las propuestas detalladas, con los datos que las sustentan, están en `FUENTES.md`, apartado
«Contradicciones del encargo y propuestas». Resumen:

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
