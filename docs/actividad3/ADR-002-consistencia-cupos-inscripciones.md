**Estudiante:** Camilo Andrés López Hernández — **Documento:** 1233691138

# ADR-002. Consistencia de cupos e inscripciones: actualización condicional atómica, restricciones declarativas e idempotencia

| Campo | Valor |
|---|---|
| Identificador | ADR-002 |
| Título | Estrategia para mantener la consistencia de las inscripciones y los cupos |
| Fecha | 2026-10-14 |
| Estado | Aceptado |
| Autor | Camilo Andrés López Hernández |
| Relacionado con | [ADR-001](ADR-001-estilo-arquitectonico.md), [Actividad 2, sección 5.1](../actividad2.md) (límites transaccionales) |

## 1. Contexto y problema

Al abrir la matrícula, cientos de estudiantes compiten al mismo tiempo por los mismos grupos. El caso reporta dos problemas del sistema actual:
- **Inconsistencias en los cupos.** Si dos transacciones leen "queda 1 cupo" y ambas inscriben, se produce una *actualización perdida* (Berenson et al., 1995) y el grupo supera su capacidad, lo que viola C04.
- **Inscripciones duplicadas.** Las causan los reintentos: el doble clic, la recarga de la página o el reintento automático tras un tiempo de espera.

Además, la verificación de conflicto de horario lee las otras inscripciones del mismo estudiante. Dos solicitudes simultáneas del mismo estudiante podrían pasar esa validación a la vez.

**Problema:** ¿qué mecanismo garantiza que ningún grupo supere su capacidad y que ninguna solicitud repetida genere una segunda inscripción, sin degradar el rendimiento en el pico de matrícula?

## 2. Drivers arquitectónicos relacionados

| Driver | Prioridad | Medida |
|---|---|---|
| QAS-02 Integridad de cupos (C04) | 1 (A, A) | Inscritos ≤ capacidad en el 100 % de las pruebas; 300 solicitudes sobre 10 cupos producen exactamente 10 inscripciones. |
| QAS-03 No duplicación | 3 (A, M) | 0 duplicados; un solo cupo consumido por estudiante, asignatura y período. |
| QAS-04 Rendimiento | 4 (A, M) | Respuesta a cada inscripción en ≤ 3 s en el pico. |
| RES-01 PostgreSQL | Obligatoria | Usar las capacidades del motor existente. |

## 3. Alternativas consideradas

### A1. Bloqueo pesimista explícito del grupo
`SELECT ... FROM grupo WHERE id = ? FOR UPDATE`, seguido de la verificación del cupo en la aplicación y la actualización (bloqueo en dos fases; Eswaran et al., 1976). El bloqueo se mantiene desde la lectura hasta el final de la transacción.

### A2. Control de concurrencia optimista con versión
Se lee el grupo con su número de versión y se actualiza con `WHERE version = ?`. Si otra transacción cambió la fila, la actualización afecta 0 filas y la aplicación reintenta todo el proceso (Kung y Robinson, 1981).

### A3. Aislamiento serializable (SSI de PostgreSQL)
Todas las transacciones de inscripción se ejecutan en `SERIALIZABLE`. El motor detecta las combinaciones peligrosas y aborta una de las transacciones con un error de serialización que la aplicación debe reintentar (Cahill et al., 2008; Ports y Grittner, 2012).

### A4. Actualización condicional atómica, con restricciones declarativas e idempotencia (seleccionada)
- **Cupo:** una sola sentencia `UPDATE grupo SET inscritos = inscritos + 1 WHERE id = ? AND inscritos < capacidad`, en *read committed*. Si afecta 0 filas, no hay cupo. Como defensa adicional, la tabla declara `CHECK (inscritos <= capacidad)`.
- **Duplicados de negocio:** un índice único parcial sobre `(estudiante_id, asignatura_id, periodo_id)` para las inscripciones en estado activo.
- **Reintentos:** una clave de idempotencia (UUID generado por la aplicación web por cada intento), registrada con clave primaria en la misma transacción. La respuesta se almacena y se devuelve ante las repeticiones (Helland, 2012).
- **Concurrencia del mismo estudiante:** `SELECT ... FOR UPDATE` sobre la fila `estudiante_periodo` al inicio de la transacción.
- **Orden dentro de la transacción:** primero las validaciones de lectura (reglas, horario) y al final el `UPDATE` del cupo, para que el bloqueo sobre la fila del grupo dure lo mínimo.

### A5 (descartada de entrada). Contador de cupos en un almacén en memoria externo
Por ejemplo, un contador atómico en Redis o Valkey. Se descarta porque agrega un componente que el equipo debe operar (RES-02) y crea un segundo lugar donde vive el cupo, que habría que mantener consistente con PostgreSQL.

## 4. Criterios de comparación

| Criterio | A1. Pesimista | A2. Optimista | A3. Serializable | A4. Condicional + declarativa |
|---|---|---|---|---|
| Corrección de C04 bajo concurrencia | Correcta. | Correcta si todos los caminos respetan la versión. | Correcta. | Correcta. Además, la base de datos lo garantiza con `CHECK` aunque falle el código. |
| Comportamiento con alta contención sobre un mismo grupo | El bloqueo dura toda la transacción, incluidas las validaciones; las esperas crecen. | Muchas actualizaciones fallan y se reintentan; los reintentos multiplican la carga justo en el pico. Kung y Robinson (1981) recomiendan este enfoque para conflictos poco frecuentes. | Los abortos por serialización crecen con la contención; cada uno exige reintentar la transacción completa. | Una sola sentencia que espera y vuelve a evaluar la condición; no hay abortos ni reintentos de la aplicación; el bloqueo dura solo el final de la transacción. |
| Complejidad en la aplicación | Media: hay que respetar el orden de bloqueo. | Alta: lógica de reintentos en cada caso de uso. | Alta: todos los caminos deben manejar los errores de serialización. | Baja: una sentencia más tres restricciones declarativas. |
| Protección ante duplicados por reintentos | No la resuelve por sí sola. | No la resuelve. | No la resuelve. | La resuelve: clave de idempotencia más índice único. |
| Verificabilidad | Media. | Media. | Media. | Alta: las restricciones se pueden consultar en el esquema y comprobar con una prueba de concurrencia. |

## 5. Decisión

**Se adopta A4.** El cupo se descuenta con una actualización condicional atómica en *read committed*, protegida por `CHECK (inscritos <= capacidad)`. La no duplicación se garantiza con un índice único parcial y con claves de idempotencia registradas en la misma transacción. Las solicitudes concurrentes del mismo estudiante se ordenan con un bloqueo sobre su fila `estudiante_periodo`. Todo ocurre en la transacción local T1 de la Actividad 2.

## 6. Justificación

1. **Corrección demostrable con las capacidades de PostgreSQL (RES-01).** En *read committed*, un `UPDATE` que encuentra una fila modificada por otra transacción en curso espera a que esta termine y vuelve a evaluar el `WHERE` sobre la versión confirmada (PostgreSQL Global Development Group, 2024, sección 13.2.1). Por eso la verificación "queda cupo" y el descuento son indivisibles, sin bloquear la tabla ni elevar el nivel de aislamiento.
2. **Es el mejor comportamiento ante contención alta,** que es exactamente lo que ocurre en la apertura de matrícula sobre los grupos más solicitados. A2 y A3 responden a la contención con abortos y reintentos, que aumentan la carga en el peor momento. A4 la absorbe con esperas cortas y acotadas.
3. **Las garantías son del motor, no del código.** `CHECK` y el índice único hacen imposibles el sobrecupo y la inscripción duplicada aunque un desarrollador futuro cometa un error, lo que resulta adecuado para un equipo pequeño que rotará con el tiempo (C10). Codd (1970) fundamenta la integridad declarativa en el modelo relacional.
4. **La idempotencia resuelve un problema que ningún control de concurrencia resuelve.** Un reintento no es una solicitud concurrente, sino la misma solicitud repetida. Solo una clave de idempotencia permite reconocerla y devolver el mismo resultado (Helland, 2012).
5. **Es coherente con el Escenario A.** La consistencia de cupos depende solo de PostgreSQL, no del legado, y se mantiene íntegra durante sus 40 minutos de indisponibilidad (CF-01, Actividad 1).

## 7. Consecuencias

### Positivas
- C04 y la no duplicación quedan garantizadas por el motor y son verificables directamente en el esquema.
- No hay lógica de reintentos por conflictos en la aplicación.
- El bloqueo sobre el grupo dura solo desde el `UPDATE` hasta el `COMMIT`.

### Negativas
- Las solicitudes sobre un mismo grupo se procesan una tras otra en el tramo final de la transacción; en un grupo muy solicitado aparecen esperas.
- La tabla de claves de idempotencia crece y debe depurarse; se conservan las claves del período en curso.
- El cupo que muestra la consulta de oferta puede tener unos segundos de antigüedad (CF-02). El estudiante puede ver "1 cupo" y recibir "sin cupo" al inscribir.

### Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Esperas de bloqueo prolongadas en el pico. | `lock_timeout` de 2 s y `statement_timeout` de 5 s en la sesión de la API. Limitación de tasa en Nginx. Transacción T1 sin llamadas de red externas. Prueba de carga con un grupo muy solicitado (Actividad 4). |
| Un camino de código modifica `inscritos` sin pasar por el componente Control de cupos. | `CHECK` en la base de datos. Prueba de arquitectura que prohíbe escribir `inscritos` fuera de ese componente. |
| La aplicación web genera una clave nueva en cada reintento. | Contrato documentado: la clave se genera por intento de usuario y se reutiliza en los reintentos. El índice único parcial actúa como segunda barrera. |

## 8. Condiciones para revisar la decisión

- El tiempo de respuesta de la inscripción supera 3 s en el percentil 95 por esperas de bloqueo, medido en la prueba de carga o en producción.
- La universidad incorpora listas de espera o reservas temporales con vencimiento, que cambian el modelo del cupo.
- Los datos de inscripción se distribuyen en varias bases de datos (por ejemplo, si se revisa ADR-001), lo que impediría la transacción local.

## 9. Referencias

- Berenson, H. et al. (1995). A critique of ANSI SQL isolation levels. *Proceedings of the ACM SIGMOD*.
- Cahill, M., Röhm, U. y Fekete, A. (2008). Serializable isolation for snapshot databases. *Proceedings of the ACM SIGMOD*.
- Codd, E. F. (1970). A relational model of data for large shared data banks. *CACM, 13*(6).
- Eswaran, K. et al. (1976). The notions of consistency and predicate locks in a database system. *CACM, 19*(11).
- Helland, P. (2012). Idempotence is not a medical condition. *ACM Queue, 10*(4).
- Kung, H. T. y Robinson, J. (1981). On optimistic methods for concurrency control. *ACM Transactions on Database Systems, 6*(2).
- Ports, D. y Grittner, K. (2012). Serializable snapshot isolation in PostgreSQL. *Proceedings of the VLDB Endowment, 5*(12).
- PostgreSQL Global Development Group (2024). *PostgreSQL 16 Documentation*, cap. 13 "Concurrency Control".
