# Texto íntegro del encargo

> Copia literal del encargo recibido (fase 1, 25/10/2026). No se modifica; las decisiones posteriores van en `DECISIONES.md`.


ENCARGO: CUADRO DE MANDO DE PRECIOS ENERGÉTICOS

Quiero que desarrolles y pongas en funcionamiento un cuadro de mando de precios energéticos en España, tomando como referencia el boletín de APROPELLETS que te he facilitado.

No quiero una plantilla, un prototipo ni un archivo con datos pendientes de introducir. Quiero un cuadro de mando operativo, alimentado con datos reales, históricos y actualizados, que pueda consultar en cualquier momento y desde el que pueda generar informes en PDF y Excel.

1. Indicadores

El cuadro de mando incluirá exclusivamente estos ocho indicadores:

1. Electricidad: precio del mercado diario OMIE, España, en €/MWh
2. Gas natural: MIBGAS-ES Index, en €/MWh
3. Gasóleo de automoción: precio medio en España, en €/l
4. Electricidad PVPC: término de energía, tarifa 2.0TD, en €/kWh
5. Gas natural TUR 2: término variable, en €/kWh
6. Gasóleo de calefacción: precio medio en España, en €/kWh
7. Butano: bombona regulada de 12,5 kg, en €/kWh
8. Pellet: precio medio en España del saco de pellet de 15 kg, en €/kWh y precio medio en España de pellet a granel en volquete en €/kWh

Todos los precios deben expresarse con impuestos, aplicando criterios homogéneos y técnicamente justificados.

Utiliza prioritariamente las fuentes oficiales y sectoriales que aparecen en el boletín de APROPELLETS: OMIE, MIBGAS, REE/ESIOS, Comisión Europea, BOE y AVEBIOM.

Indica si el precio es con o sin impuestos.

2. Histórico desde enero de 2022

Recupera los datos históricos reales de los ocho indicadores desde el 1 de enero de 2022 hasta la fecha actual.

- Descarga o consulta las series históricas de sus fuentes originales.
- Construye una base de datos histórica de cada indicador, precio medio mensual original, unidad, precio medio mensual convertido a €/kWh, fuente, si es con o sin impuestos y fecha de publicación.
- Utiliza los poderes caloríficos y factores de conversión apropiados, indicando su procedencia.
- Conserva la frecuencia original de publicación de cada indicador: diaria, semanal, bimestral o trimestral.
- Para tarifas y precios regulados, utiliza el valor vigente en cada fecha.
- No inventes, interpoles ni estimes precios históricos sin identificarlo expresamente.

La recuperación del histórico es un requisito esencial, no una mejora opcional.

3. Visualización del cuadro de mando

Quiero un panel visual, sencillo y profesional, que contenga:

A. Resumen ejecutivo. Una tabla con los ocho indicadores y las siguientes columnas:
- Precio actual en €/kWh.
- Variación respecto a la semana anterior, en %.
- Variación respecto al mismo periodo del año anterior, en %.
- Fecha del dato.
- Fuente.
- Estado de actualización.

B. Gráfico comparativo. Un gráfico de líneas con la evolución de los ocho indicadores desde enero de 2020, con posibilidad de seleccionar y ocultar series para facilitar su comparación.

C. Gráficos individuales. Ocho gráficos, uno por indicador, mostrando la evolución histórica.

D. Filtros temporales. Permite visualizar Periodo personalizado.

E. Comentario semanal. Incluye un breve análisis de las principales variaciones, tendencias y diferencias de precios entre las distintas fuentes energéticas. Limítalo a información relevante y verificable.

4. Actualización automática

El cuadro de mando debe actualizarse en el momento en el que usuario lo solicite, utilizando los últimos datos publicados en cada fuente.

La actualización debe:
- Consultar automáticamente las fuentes originales.
- Incorporar los nuevos datos a la base histórica.
- Actualizar los indicadores y gráficos.
- Mantener el histórico anterior.
- Identificar las fuentes que no hayan publicado nuevos datos.
- Detectar y comunicar errores de descarga o actualización.
- Registrar la fecha de la última actualización correcta.

No quiero tener que descargar datos manualmente, introducir precios ni modificar archivos para mantener el cuadro de mando actualizado, más allá de dar la orden de "actualizar".

5. Acceso permanente

Necesito poder consultar el cuadro de mando en cualquier momento, preferentemente mediante un enlace permanente.

Quiero poder acceder a los indicadores y gráficos sin tener que solicitarte cada vez que vuelvas a elaborar el informe.

Si para ello es necesario utilizar una plataforma externa, base de datos, aplicación web o servicio de alojamiento, proponme la solución más sencilla, fiable y de menor mantenimiento.

No confundas un archivo HTML descargable con un cuadro de mando conectado a fuentes de datos y actualizado automáticamente.

Si no puedes realizar directamente alguna operación técnica, indícame exactamente qué herramienta, acceso o autorización necesitas para completarla.

6. Exportación de informes

Desde el cuadro de mando quiero poder generar y descargar:

Informe PDF, con una presentación similar al boletín de APROPELLETS, pero limitado a mis ocho indicadores, incluyendo:
- Fecha y periodo analizado.
- Resumen ejecutivo.
- Tabla de precios y variaciones.
- Gráfico comparativo.
- Gráficos individuales.
- Breve comentario de evolución.
- Fuentes y metodología.

Archivo Excel, con:
- Histórico completo desde enero de 2022.
- Datos originales y convertidos a €/kWh.
- Tabla resumen de indicadores.
- Gráficos vinculados a los datos.
- Fuentes y criterios de conversión.
- Posibilidad de analizar y filtrar los datos.

Los informes deben generarse utilizando los datos actualizados del cuadro de mando.

7. Implantación y verificación

Quiero que ejecutes el trabajo completo, no que te limites a explicar cómo podría hacerse.

Trabaja en este orden:
1. Comprueba la disponibilidad real de las fuentes de datos y sus históricos.
2. Recupera y valida las series históricas.
3. Construye la base de datos.
4. Desarrolla el cuadro de mando y sus gráficos.
5. Configura la actualización semanal.
6. Implementa la exportación a PDF y Excel.
7. Comprueba que el sistema funciona con datos reales.
8. Facilítame el acceso y unas instrucciones breves de utilización.

Antes de dar el trabajo por terminado, verifica que los ocho indicadores muestran datos reales, que los gráficos históricos funcionan, que los informes pueden descargarse y que el mecanismo de actualización está configurado y probado.

No consideres terminado el trabajo mientras no se cumplan estos requisitos.

Si existen limitaciones técnicas que impiden completar alguna funcionalidad, explícalas antes de entregar una solución parcial. No presentes como operativo un sistema que todavía dependa de introducir o actualizar datos manualmente.

8. Resultado esperado

Quiero recibir:
1. Un enlace de acceso al cuadro de mando operativo.
2. Un informe PDF generado con datos reales.
3. Un Excel con el histórico disponible desde enero de 2022.
4. Una explicación sencilla de cómo consultar, actualizar y exportar la información.
5. Confirmación de cómo funciona la actualización automática semanal.

Puedes realizar búsquedas externas en las fuentes públicas necesarias para obtener los precios energéticos. No utilices ni transmitas información confidencial de mi empresa.
