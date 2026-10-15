**Estudiante:** Camilo Andrés López Hernández — **Documento:** 1233691138

# Actividad 1. Identificación y priorización de drivers arquitectónicos

**Caso:** Plataforma de Inscripción Académica (PIA) — Universidad de La Salle.
**Situación extraordinaria asignada:** Escenario A — Indisponibilidad del sistema académico legado (último dígito del documento: 8, par).

## Marco de referencia

- Se consideran drivers arquitectónicos el propósito del diseño, los requisitos funcionales primarios, los escenarios de atributos de calidad, las restricciones y las preocupaciones arquitectónicas (Cervantes y Kazman, 2016).
- Los atributos de calidad se expresan como escenarios de seis partes: fuente, estímulo, artefacto, entorno, respuesta y medida de la respuesta (Bass, Clements y Kazman, 2021).
- Los atributos se clasifican según el modelo de calidad de producto ISO/IEC 25010:2023.
- La priorización usa el árbol de utilidad del método ATAM, que califica cada escenario con un par (importancia para el negocio, dificultad técnica) (Kazman, Klein y Clements, 2000).

---

## 1. Objetivos de negocio

Los objetivos de negocio expresan el resultado que la universidad espera y son el origen de los drivers de calidad (Bass et al., 2021). Se formulan a partir de los problemas identificados en el caso, sin referirse a tecnología.

| ID | Objetivo de negocio | Problema del caso que lo origina | Indicador de logro |
|---|---|---|---|
| OBN-01 | Asegurar la integridad del proceso de matrícula: cada estudiante queda inscrito una sola vez por grupo y ningún grupo supera su capacidad autorizada. | Inscripciones duplicadas por reintentos; inconsistencias en la disponibilidad de cupos. | 0 sobrecupos y 0 inscripciones duplicadas por período académico; reducción de las solicitudes de corrección manual posteriores a la matrícula. |
| OBN-02 | Dar continuidad al servicio de matrícula durante los períodos críticos, incluso cuando fallen sistemas de los que depende. | Lentitud y fallas de disponibilidad con accesos simultáneos; dependencia del legado. | Disponibilidad de PIA ≥ 99,9 % mensual durante la matrícula (C03), sin que una falla del legado se convierta en una falla de PIA. |
| OBN-03 | Reducir el costo y el tiempo de incorporar nuevas reglas académicas con el equipo institucional existente. | Alto esfuerzo técnico para implementar nuevas reglas académicas. | Una regla académica nueva se implementa, prueba y despliega sin modificar los módulos de cupos ni de integración con el legado. |
| OBN-04 | Garantizar la trazabilidad de las operaciones académicas para resolver reclamaciones y demostrar cumplimiento de la normativa de protección de datos. | Dificultad para identificar y auditar modificaciones en las inscripciones; C09. | El 100 % de las operaciones de inscripción, cancelación y sincronización queda registrado con actor, fecha y hora, operación y resultado. |

**Daño institucional que se evita con cada objetivo:**
- **OBN-01.** Grupos con sobrecupo, reclamos de estudiantes, ajustes manuales posteriores y pérdida de confianza en el proceso.
- **OBN-02.** Estudiantes sin poder inscribirse en su ventana asignada, desborde de la mesa de ayuda, retraso en el inicio de clases y afectación reputacional.
- **OBN-03.** Decisiones académicas que no se pueden aplicar a tiempo por limitaciones técnicas.
- **OBN-04.** Imposibilidad de resolver disputas con evidencia y riesgo de incumplir la Ley 1581 de 2012 (Colombia), de protección de datos personales.

---

## 2. Restricciones arquitectónicas

Una restricción es una decisión de diseño que el arquitecto recibe ya tomada y que no puede modificar (Bass et al., 2021).

| ID | Restricción | Origen | Por qué no deja margen de decisión | Implicación arquitectónica |
|---|---|---|---|---|
| RES-01 | La solución debe ejecutarse sobre infraestructura Linux y PostgreSQL, sin contratar servicios comerciales adicionales. | C08 | La universidad ya fijó la plataforma y prohibió nuevos costos de licenciamiento o servicios. | Se descartan nubes administradas, bases de datos comerciales y brokers de mensajería de pago. Todo componente debe ser software libre y desplegable en la infraestructura existente. |
| RES-02 | El mantenimiento estará a cargo de cuatro desarrolladores y un administrador de infraestructura. | C10 | Es la capacidad institucional disponible; no depende del diseño. | La arquitectura no puede exigir operar muchas unidades desplegables independientes, orquestadores complejos ni especialistas que la universidad no tiene. |
| RES-03 | El sistema legado sigue siendo la fuente oficial del historial académico y de los prerrequisitos; PIA administra las inscripciones del período y debe sincronizarlas con el legado. | Condición adicional del caso | La universidad decidió no reemplazar el legado. | PIA no puede ser dueña del historial ni de los prerrequisitos: solo puede consultarlos o mantener copias de lectura. La inscripción solo es oficial cuando queda registrada en el legado. |
| RES-04 | Los datos académicos y personales deben tener controles de acceso, trazabilidad y protección. | C09; Ley 1581 de 2012 | Es una obligación legal e institucional. | Autenticación y autorización obligatorias, registro de auditoría de las operaciones y protección de los datos en tránsito y en reposo. |

### 2.1 Supuestos de diseño

Los supuestos son condiciones que se asumen ciertas y que la universidad debe validar, porque las decisiones posteriores dependen de ellos.

| ID | Supuesto | Origen | Consecuencia si resulta falso |
|---|---|---|---|
| SUP-01 | El legado puede quedar sin responder hasta 40 minutos seguidos, incluso al inicio de la matrícula. | C05; Escenario A | Es una condición del entorno, no una restricción: PIA no puede cambiarla, solo tolerarla. Si las interrupciones fueran más largas, habría que revisar la estrategia de operación degradada. |
| SUP-02 | El historial académico y los prerrequisitos aprobados no cambian durante la matrícula, porque las notas del período anterior ya están cerradas. Las excepciones (homologaciones, correcciones de notas) son puntuales e identificables. | Calendario académico | Si el historial cambiara con frecuencia durante la matrícula, una copia cargada antes de la apertura no serviría para validar prerrequisitos sin el legado. |
| SUP-03 | El legado ofrece algún mecanismo de integración para consultar el historial y registrar inscripciones (servicio, acceso a base de datos o intercambio de archivos). | Condición adicional del caso | Si no existiera, la sincronización exigiría desarrollar ese mecanismo en el legado, con costo y riesgo adicionales. |

Las condiciones C01, C02, C03, C04, C06 y C07 no son restricciones: son requisitos de atributos de calidad, porque fijan un resultado medible pero dejan libertad sobre cómo alcanzarlo. Se desarrollan en la sección 3.
