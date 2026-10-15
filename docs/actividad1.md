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

---

## 3. Drivers arquitectónicos

### 3.1 Requisitos funcionales primarios

Cervantes y Kazman (2016) consideran primarios los requisitos funcionales que son críticos para los objetivos de negocio o que imponen mayores exigencias de calidad.

| ID | Requisito funcional | Por qué es primario |
|---|---|---|
| RFP-01 | Inscribir asignaturas verificando prerrequisitos, conflictos de horario y disponibilidad de cupos. | Concentra la concurrencia (C01, C04), depende de los prerrequisitos del legado (RES-03) y es el núcleo de OBN-01. |
| RFP-02 | Consultar asignaturas y grupos disponibles. | Es la operación de mayor volumen en la apertura de matrícula y la que mide C02. |
| RFP-03 | Sincronizar las inscripciones oficiales con el sistema legado. | Determina cuándo una inscripción es oficial y es el punto de falla del Escenario A. |
| RFP-04 | Cancelar inscripciones dentro de las fechas permitidas. | Libera cupos, así que afecta directamente la consistencia de C04. |
| RFP-05 | Consultar el estado de las solicitudes e inscripciones, y registrar la trazabilidad de las operaciones. | Es el canal que informa al estudiante durante la operación degradada y soporta OBN-04. |

### 3.2 Drivers de atributos de calidad

| ID | Atributo de calidad (ISO/IEC 25010:2023) | Descripción del driver | Origen |
|---|---|---|---|
| DQ-01 | Fiabilidad: disponibilidad y tolerancia a fallos | PIA debe seguir prestando servicio aunque el legado no responda hasta 40 minutos, sin consumir el presupuesto de indisponibilidad de C03. | C03, C05, RES-03, Escenario A, OBN-02 |
| DQ-02 | Adecuación funcional: corrección funcional (integridad de cupos) | Ningún grupo puede registrar más estudiantes que su capacidad, aunque haya muchas solicitudes simultáneas por el mismo cupo. | C04, C01, OBN-01 |
| DQ-03 | Fiabilidad e integridad de datos: no duplicación | Una solicitud repetida por reintentos del usuario o de la red debe producir una sola inscripción en PIA y una sola en el legado. | Problema de duplicados del caso; condición adicional; OBN-01 |
| DQ-04 | Eficiencia de desempeño: comportamiento temporal y capacidad | El 95 % de las consultas de asignaturas debe responder en 2 segundos o menos con 1.200 estudiantes conectados al tiempo. | C01, C02, OBN-02 |
| DQ-05 | Fiabilidad: recuperabilidad | Ante una falla de la infraestructura propia, PIA debe recuperarse en 30 minutos o menos, perdiendo como máximo 5 minutos de transacciones. | C06, C07, OBN-02 |
| DQ-06 | Seguridad: confidencialidad, integridad y responsabilidad (trazabilidad) | Solo los actores autorizados acceden a los datos y cada operación queda atribuida a un actor y registrada de forma inalterable. | C09, RES-04, OBN-04 |
| DQ-07 | Mantenibilidad: modificabilidad | Las reglas académicas deben poder agregarse o cambiarse sin modificar el control de cupos ni la integración con el legado. | Problema de esfuerzo técnico del caso; C10; OBN-03 |

---

## 4. Escenarios de atributos de calidad

Cada escenario sigue la estructura de seis partes de Bass et al. (2021). El *entorno* corresponde al contexto de operación que pide el enunciado.

### QAS-01 — Indisponibilidad del legado al iniciar la matrícula (Escenario A) — DQ-01

| Parte | Contenido |
|---|---|
| Fuente | Sistema académico legado (falla interna, ajena a PIA). |
| Estímulo | El legado deja de responder (tiempos de espera agotados o conexiones rechazadas) durante 40 minutos seguidos. |
| Artefacto | Adaptador de integración con el legado y módulo de inscripciones de PIA. |
| Entorno | Apertura de la matrícula, con 1.200 estudiantes conectados al tiempo (C01). |
| Respuesta | (1) PIA detecta la falla y deja de invocar al legado (interruptor de circuito abierto). (2) Siguen operando la consulta de oferta y grupos, la consulta de estado, las cancelaciones y las inscripciones; las inscripciones validan prerrequisitos contra la copia del historial cargada desde el legado antes de la apertura (SUP-02). (3) Toda inscripción hecha durante la falla queda en estado *pendiente de sincronización*, con su cupo reservado, y el estudiante ve en pantalla que aún no es oficial. (4) Se restringen, con un mensaje explícito, las inscripciones de estudiantes sin copia válida del historial (por homologaciones o notas corregidas después de la carga). (5) Cuando el legado vuelve, PIA sincroniza las operaciones pendientes de forma idempotente y solo entonces las marca como *confirmadas*. |
| Medida | Falla detectada en ≤ 30 s. 0 minutos de indisponibilidad de PIA atribuibles a la falla del legado. 95 % de las consultas en ≤ 2 s durante la falla. 0 inscripciones mostradas como *confirmadas* sin registro en el legado. 100 % de las operaciones pendientes sincronizadas en ≤ 15 min tras la recuperación del legado, con 0 duplicados. ≥ 99 % de las inscripciones provisionales aceptadas por el legado; las rechazadas se notifican al estudiante y su cupo se libera en ≤ 1 min. |

#### 4.1 Cálculo que sustenta QAS-01

- Un mes de 30 días tiene 30 × 24 × 60 = 43.200 minutos.
- El 99,9 % de C03 permite 0,001 × 43.200 = **43,2 minutos** de indisponibilidad al mes. Se usa la relación indisponibilidad = (1 − A) × período (Bass et al., 2021).
- Una sola caída del legado de 40 minutos (C05) consumiría el **92,6 %** de ese presupuesto y dejaría solo **3,2 minutos** para todas las demás fallas del mes.
- Una falla propia de PIA con el RTO máximo de C06 (30 minutos), sumada a una caída del legado, daría 70 minutos, que superan los 43,2 permitidos.
- Si la disponibilidad se mide solo en la ventana de matrícula, el presupuesto es menor: en 14 días, 0,001 × 20.160 = 20,16 minutos, que los 40 minutos de C05 exceden por sí solos.

**Conclusión:** una dependencia síncrona de PIA respecto del legado hace imposible cumplir C03. La disponibilidad de PIA debe quedar desacoplada de la del legado.

### QAS-02 — Competencia simultánea por los últimos cupos de un grupo — DQ-02

| Parte | Contenido |
|---|---|
| Fuente | Estudiantes habilitados para inscribir. |
| Estímulo | 300 solicitudes de inscripción llegan al mismo tiempo sobre un grupo al que le quedan 10 cupos. |
| Artefacto | Módulo de inscripciones y control de cupos, y base de datos de PIA. |
| Entorno | Pico de matrícula con 1.200 estudiantes conectados (C01), con el legado disponible o no. |
| Respuesta | Exactamente 10 solicitudes quedan inscritas. Las otras 290 se rechazan con el mensaje "sin cupo disponible" y la opción de consultar otros grupos. No queda ninguna solicitud en estado indeterminado. |
| Medida | Inscripciones activas del grupo ≤ capacidad autorizada en el 100 % de las ejecuciones de la prueba de carga. 0 sobrecupos por período, verificados por una consulta de conciliación al final de cada jornada. Respuesta a cada solicitud en ≤ 3 s. |

### QAS-03 — Solicitud de inscripción repetida por reintentos — DQ-03

| Parte | Contenido |
|---|---|
| Fuente | Estudiante (doble clic o recarga de página) o el cliente HTTP (reintento automático tras un tiempo de espera). |
| Estímulo | La misma solicitud de inscripción llega hasta 5 veces en menos de 10 segundos. |
| Artefacto | Interfaz de inscripción (API), módulo de inscripciones y proceso de sincronización con el legado. |
| Entorno | Operación normal o pico de matrícula; incluye la retransmisión de la sincronización después de una falla del legado. |
| Respuesta | La primera solicitud se procesa. Las repeticiones devuelven el mismo resultado de la primera sin crear registros nuevos ni consumir cupos adicionales. La sincronización con el legado, aunque se reenvíe, produce un solo registro oficial. |
| Medida | 0 inscripciones duplicadas en PIA y 0 en el legado por período, verificadas por conciliación. 1 solo cupo consumido por cada combinación estudiante–grupo–período. |

### QAS-04 — Consulta de oferta académica en el pico de matrícula — DQ-04

| Parte | Contenido |
|---|---|
| Fuente | Estudiantes. |
| Estímulo | Consultas de asignaturas y grupos disponibles generadas por 1.200 estudiantes conectados al tiempo. |
| Artefacto | Interfaz web, API de consulta y base de datos de PIA. |
| Entorno | Primeras horas de la matrícula, con el legado disponible o no disponible. |
| Respuesta | El sistema responde las consultas con datos del período. La información de cupos que se muestra puede tener unos segundos de antigüedad, pero la validación definitiva del cupo ocurre al inscribir (QAS-02). |
| Medida | Percentil 95 del tiempo de respuesta ≤ 2 s y tasa de errores < 1 %, medidos durante una prueba de carga sostenida de 15 minutos con 1.200 usuarios virtuales concurrentes. |

### QAS-05 — Falla del servidor de base de datos de PIA — DQ-05

| Parte | Contenido |
|---|---|
| Fuente | Infraestructura propia (falla de hardware, sistema operativo o PostgreSQL). |
| Estímulo | El servidor principal de PostgreSQL queda inutilizable. |
| Artefacto | Base de datos de PIA y sus mecanismos de respaldo y réplica. |
| Entorno | Durante la matrícula, con escrituras en curso. |
| Respuesta | El administrador de infraestructura ejecuta el procedimiento de recuperación documentado: promueve la réplica o restaura el respaldo con el registro de transacciones archivado. Las aplicaciones se reconectan y se verifica la integridad de los cupos antes de reabrir las inscripciones. |
| Medida | Servicio restablecido en ≤ 30 min (RTO, C06). Pérdida de transacciones confirmadas ≤ 5 min (RPO, C07). Ambos valores medidos en un simulacro antes de cada período de matrícula. |

### QAS-06 — Auditoría de una modificación de inscripción — DQ-06

| Parte | Contenido |
|---|---|
| Fuente | Auditor o funcionario de registro académico que atiende una reclamación; también un usuario no autorizado. |
| Estímulo | (a) Se solicita saber quién inscribió, canceló o modificó una inscripción y cuándo. (b) Un usuario intenta consultar o modificar inscripciones de otro estudiante. |
| Artefacto | Registro de auditoría, módulo de seguridad y módulo de inscripciones. |
| Entorno | Durante o después del período de matrícula. |
| Respuesta | (a) El sistema entrega la historia completa de la inscripción: actor, fecha y hora, operación, estado anterior y nuevo, y origen de la solicitud. (b) El sistema niega el acceso y registra el intento. |
| Medida | 100 % de las operaciones de inscripción, cancelación y sincronización con registro de auditoría. 100 % de los accesos no autorizados negados y registrados. Registro de auditoría sin operaciones de modificación ni borrado permitidas a la aplicación. Consulta de la historia de una inscripción en ≤ 5 s. |

### QAS-07 — Incorporación de una nueva regla académica — DQ-07

| Parte | Contenido |
|---|---|
| Fuente | Consejo académico o dirección de programa. |
| Estímulo | Se solicita una regla nueva, por ejemplo un límite de créditos por período según el promedio acumulado. |
| Artefacto | Módulo de reglas académicas de PIA. |
| Entorno | En desarrollo, entre períodos de matrícula, con el equipo de C10. |
| Respuesta | La regla se implementa como una unidad nueva dentro del módulo de reglas, con sus pruebas automatizadas, sin modificar el control de cupos ni la integración con el legado. |
| Medida | Implementada, probada y desplegada en ≤ 5 días-persona. 0 archivos modificados fuera del módulo de reglas, verificado en la revisión de la solicitud de integración (Pull Request). 0 regresiones en la suite de pruebas automatizadas. |
