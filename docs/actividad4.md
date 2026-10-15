**Estudiante:** Camilo Andrés López Hernández — **Documento:** 1233691138

# Actividad 4. Selección y validación de tácticas arquitectónicas

Una táctica es una decisión de diseño que influye en la respuesta del sistema ante un estímulo de un atributo de calidad (Bass, Clements y Kazman, 2021). Las tácticas de este documento se seleccionaron a partir de los escenarios priorizados en la [Actividad 1](actividad1.md), se ubican en los componentes de la [Actividad 2](actividad2.md) y concretan las decisiones de los [ADR](actividad3/).

Para cada táctica se documentan:
- el atributo de calidad que mejora;
- el problema específico que resuelve;
- los componentes donde se implementa;
- su funcionamiento técnico;
- sus beneficios y costos;
- su **alcance**: qué cubre y qué no;
- el **mecanismo de verificación**: una prueba ejecutable con un criterio numérico de aprobación, tomado de la medida del escenario de calidad correspondiente.

| ID | Táctica (catálogo de Bass et al., 2021) | Atributo | Escenario |
|---|---|---|---|
| TAC-01 | Detección por tiempo de espera, interruptor de circuito y degradación controlada | Disponibilidad | QAS-01 (Escenario A) |
| TAC-02 | Comunicación asíncrona persistente con reintento idempotente (bandeja de salida) | Disponibilidad, integridad | QAS-01, QAS-03 |
| TAC-03 | Transacciones locales con restricciones declarativas sobre el recurso compartido | Integridad de cupos | QAS-02, QAS-03 |
| TAC-04 | Control de la demanda: limitación de tasa y colas acotadas | Rendimiento | QAS-04 |
| TAC-05 | Redundancia activa, redundancia pasiva y respaldo con archivado continuo | Disponibilidad, recuperabilidad | QAS-05 |

---

## TAC-01. Detección por tiempo de espera, interruptor de circuito y degradación controlada

**Atributo de calidad:** disponibilidad. Combina tácticas de detección de fallas (tiempo de espera), de recuperación (degradación) y de prevención (sacar de servicio al componente que falla) (Bass et al., 2021; Nygard, 2018).

**Problema específico (Escenario A):** cuando el legado deja de responder, cada intento de comunicación espera hasta agotar su tiempo máximo. Sin control, los hilos y conexiones del Sincronizador quedan bloqueados en esas esperas, los reintentos se acumulan, y el legado, al recuperarse, recibe de golpe todo lo represado. Además, el estudiante no sabría si su inscripción es válida.

**Componentes donde se implementa:**
- *Sincronizador*: adaptador anticorrupción del legado, con Resilience4j.
- *Base de datos*: tabla `integracion.estado_legado`.
- *API*: componente Consulta de estado y banner de la aplicación web.

**Funcionamiento técnico:**
1. **Tiempo de espera.** Toda llamada al legado tiene un límite de 5 s, para que ninguna operación espere indefinidamente.
2. **Interruptor de circuito** con tres estados:
   - *Cerrado*: las llamadas pasan.
   - *Abierto*: se activa tras 5 fallas seguidas o un 50 % de fallas en una ventana de 20 llamadas. Las llamadas se rechazan de inmediato sin tocar al legado.
   - *Semiabierto*: después de 30 s abierto, se permite una llamada de prueba; si tiene éxito el circuito se cierra, y si falla vuelve a abrirse.
3. **Publicación del estado.** Cada cambio de estado del circuito se escribe en `estado_legado`, con hora de inicio, y genera una alerta al administrador y a registro académico.
4. **Degradación controlada.** La API lee `estado_legado` y, sin cambiar su lógica de inscripción (ADR-003), activa el banner informativo. Restringe solo las inscripciones de estudiantes con copia del historial no vigente (ADR-004).
5. **Reanudación con ritmo limitado.** Al cerrarse el circuito, la bandeja de salida se vacía a un máximo de 10 eventos por segundo, para no saturar al legado recién recuperado.

```yaml
# Configuración propuesta del adaptador (Resilience4j)
resilience4j.circuitbreaker.instances.legado:
  slidingWindowType: COUNT_BASED
  slidingWindowSize: 20
  failureRateThreshold: 50
  slowCallDurationThreshold: 5s
  waitDurationInOpenState: 30s
  permittedNumberOfCallsInHalfOpenState: 1
resilience4j.timelimiter.instances.legado:
  timeoutDuration: 5s
```

**Beneficios:**
- La falla del legado se detecta en segundos y no consume recursos de PIA.
- El estudiante recibe información veraz sobre el estado de su inscripción.
- El legado no recibe una avalancha de solicitudes al recuperarse.

**Costos:**
- Hay que calibrar umbrales. Si son muy sensibles, el circuito se abre ante fallas momentáneas; si son muy laxos, la detección tarda más.
- Agrega estados que se deben monitorear y probar.
- Durante el estado abierto, las inscripciones no se oficializan.

**Alcance:**
- **Cubre** las fallas del legado de cualquier duración: lentitud, rechazo de conexiones o ausencia de respuesta.
- **No cubre** las fallas de los componentes de PIA (las cubre TAC-05).
- **No elimina** la consistencia eventual: durante la falla las inscripciones son provisionales por diseño.
- **No resuelve** los rechazos que el legado haga al sincronizar; esos los maneja la compensación de TAC-02.

**Mecanismo de verificación:**

| Prueba | Cómo se ejecuta | Criterio de aprobación |
|---|---|---|
| V-01.1 Prueba de componente del adaptador | En la integración continua de cada Pull Request: el adaptador se prueba contra un simulador del legado (WireMock) programado para no responder. | El circuito se abre tras el umbral configurado. Ninguna llamada dura más de 5 s. En estado abierto, el adaptador no envía llamadas al simulador. |
| V-01.2 Inyección de fallas con carga (Escenario A completo) | En el ambiente de preproducción, antes de cada matrícula: se lanza la prueba de carga de 1.200 usuarios virtuales (k6) y, a los 5 minutos, Toxiproxy corta la conexión con el simulador del legado durante 40 minutos. | Apertura del circuito y alerta en ≤ 30 s. Percentil 95 de las consultas ≤ 2 s y errores < 1 % durante el corte. 0 minutos de indisponibilidad de la API. |
| V-01.3 Verificación de no confirmación indebida | Al terminar V-01.2: consulta SQL `SELECT count(*) FROM inscripcion WHERE estado = 'CONFIRMADA' AND id NOT IN (registros del simulador)`. | Resultado = 0. |
| V-01.4 Indicador en producción | Métrica del estado del circuito y del tiempo en estado abierto, expuesta con Micrometer y recolectada por Prometheus. | Tiempo de detección ≤ 30 s en cada incidente real; se revisa en el informe posterior a la matrícula. |

---

## TAC-02. Comunicación asíncrona persistente con reintento idempotente (bandeja de salida transaccional)

**Atributo de calidad:** disponibilidad, mediante las tácticas de recuperación *reintento* y *mensajería persistente*, e integridad (no duplicación) (Bass et al., 2021; Richardson, 2018).

**Problema específico:**
1. **Escritura dual.** Si la API guardara la inscripción en PostgreSQL y después la enviara al legado, una falla entre ambos pasos dejaría inscripciones nunca sincronizadas, o eventos de inscripciones que no existen.
2. **Duplicados.** Cuando el Sincronizador envía un registro y no recibe respuesta (tiempo agotado), no puede saber si el legado lo guardó. Si reintenta a ciegas, puede duplicarlo. No existe una entrega garantizada exactamente una vez (Gray, 1978).

**Componentes donde se implementa:**
- *API*: componente Publicador de eventos de integración y tabla `integracion.outbox`.
- *Sincronizador*: despachador de la outbox y adaptador anticorrupción.
- *API, módulo Inscripciones*: caso de uso Aplicar resultado de sincronización.

**Funcionamiento técnico:**
1. **Escritura del evento.** En la transacción T1 (o T2), junto con la inscripción, se inserta un evento en `outbox` con `id`, `inscripcion_id`, `tipo`, `creado_en`, `intentos` y `estado`. Ambos se confirman o se anulan juntos.
2. **Reclamo de eventos.** El Sincronizador toma eventos pendientes con `SELECT ... FOR UPDATE SKIP LOCKED LIMIT 50`. Así, si se ejecutan varios hilos, ninguno toma el evento de otro, y los eventos de una misma inscripción se procesan en orden de creación.
3. **Envío idempotente.** Por cada evento:
   - Se consulta en el legado si ya existe la inscripción por clave natural (estudiante, grupo, período).
   - Si no existe, se registra enviando el `inscripcion_id` de PIA como referencia.
   - Si la consulta indica que ya existe, se trata como éxito.
4. **Reintento con espera exponencial y variación aleatoria.** Si el envío falla, se reintenta con una espera de `min(60 s, 1 s × 2^intentos)` multiplicada por un factor aleatorio entre 0 y 1 (Brooker, 2015). Así se evita que todos los reintentos lleguen al legado al mismo tiempo.
5. **Registro del resultado.** El resultado se aplica en la transacción local T3: *confirmada*, o *rechazada* con liberación del cupo como compensación (García-Molina y Salem, 1987). El evento queda marcado como procesado.
6. **Fallas del propio Sincronizador.** Si cae entre el envío al legado y T3, el evento sigue pendiente y se reintenta. El paso 3 evita el duplicado.

**Beneficios:**
- Ninguna inscripción queda sin sincronizar y ninguna se registra dos veces en el legado.
- El trabajo pendiente sobrevive a reinicios y caídas, porque está en PostgreSQL y no en memoria.
- No requiere un broker de mensajería (RES-01, RES-02).

**Costos:**
- Consistencia eventual: hay una demora entre la inscripción en PIA y su oficialización.
- La tabla `outbox` exige mantenimiento: se depuran los eventos procesados con más de 30 días.
- Cada envío hace una consulta adicional al legado (la consulta de existencia).
- Depende de que el legado permita consultar por clave natural (SUP-03).

**Alcance:**
- **Cubre** la entrega de inscripciones y cancelaciones de PIA hacia el legado, con al menos un intento efectivo y sin duplicados.
- **No cubre** la dirección contraria: la importación del historial del legado hacia PIA es responsabilidad del ADR-004.
- **No garantiza** que el legado acepte la inscripción; garantiza que el resultado, sea aceptación o rechazo, quede reflejado de forma consistente en PIA.

**Mecanismo de verificación:**

| Prueba | Cómo se ejecuta | Criterio de aprobación |
|---|---|---|
| V-02.1 Atomicidad de la outbox | Prueba de integración en la integración continua, con PostgreSQL real (Testcontainers): se fuerza una excepción después de insertar la inscripción y antes del `COMMIT`. | No queda ni la inscripción ni el evento. |
| V-02.2 Caída del Sincronizador entre el envío y T3 | Prueba de integración: el simulador del legado registra la inscripción y el Sincronizador se detiene antes de T3. Luego se reinicia. | El simulador tiene exactamente 1 registro de esa inscripción, y en PIA la inscripción queda *confirmada*. |
| V-02.3 Respuestas perdidas | Prueba con el simulador configurado para registrar pero no responder (tiempo agotado) en el 30 % de las llamadas, con 1.000 eventos. | 0 duplicados en el simulador (conteo agrupado por clave natural). El 100 % de los eventos queda procesado. |
| V-02.4 Vaciado después de 40 minutos de falla | Continuación de V-01.2: se acumulan unos 6.000 eventos y se restablece el simulador. | Bandeja de salida vacía en ≤ 15 min y conciliación PIA–simulador con 0 diferencias. |
| V-02.5 Indicador en producción | Métricas de cantidad de eventos pendientes y antigüedad del evento más viejo. | Alerta si la antigüedad supera 45 min. Conciliación diaria con 0 diferencias. |

---

## TAC-03. Transacciones locales con restricciones declarativas sobre el recurso compartido

**Atributo de calidad:** integridad de datos y corrección funcional. Corresponde a la táctica *transacciones* para prevenir fallas (Bass et al., 2021), reforzada con restricciones de integridad del modelo relacional (Codd, 1970).

**Problema específico:**
- Cientos de transacciones compiten por la misma fila (el contador de inscritos del grupo). Sin control, dos transacciones leen el mismo cupo libre y ambas inscriben: es una actualización perdida (Berenson et al., 1995) que viola C04.
- Las repeticiones de una misma solicitud producen inscripciones duplicadas.
- Dos solicitudes simultáneas del mismo estudiante pueden pasar la validación de conflicto de horario al mismo tiempo.

**Componentes donde se implementa:**
- *API, módulo Inscripciones*: caso de uso Inscribir asignatura (límite de T1), Control de cupos, Guardia de idempotencia y Repositorio de inscripciones.
- *Base de datos*: restricciones de las tablas.

**Funcionamiento técnico** (ADR-002):

```sql
-- Restricción de capacidad: el motor rechaza cualquier violación de C04
ALTER TABLE oferta.grupo
  ADD CONSTRAINT ck_cupo CHECK (inscritos >= 0 AND inscritos <= capacidad);

-- Una sola inscripción activa por estudiante, asignatura y período
CREATE UNIQUE INDEX ux_inscripcion_activa
  ON inscripcion.inscripcion (estudiante_id, asignatura_id, periodo_id)
  WHERE estado IN ('PENDIENTE_SINCRONIZACION', 'CONFIRMADA', 'CANCELACION_PENDIENTE');

-- Registro de idempotencia
CREATE TABLE integracion.idempotencia (
  clave UUID, estudiante_id BIGINT, respuesta JSONB, creado_en TIMESTAMPTZ,
  PRIMARY KEY (clave, estudiante_id));

-- Descuento atómico del cupo, ejecutado al final de T1
UPDATE oferta.grupo SET inscritos = inscritos + 1
 WHERE id = :grupo AND inscritos < capacidad;   -- 0 filas = sin cupo
```

Orden de T1:
1. Insertar la clave de idempotencia. Si ya existe, se devuelve la respuesta almacenada.
2. `SELECT ... FOR UPDATE` sobre `estudiante_periodo`.
3. Validar reglas con la copia del historial.
4. Ejecutar el `UPDATE` condicional del cupo.
5. Insertar la inscripción, el evento de outbox y la auditoría.
6. `COMMIT`.

El bloqueo sobre la fila del grupo se toma en el paso 4 y se libera en el `COMMIT`. Como T1 no contiene llamadas de red externas, ese tramo dura milisegundos. La sesión de la API usa `lock_timeout = 2s` para que una espera excepcional falle de forma controlada en lugar de acumularse.

**Beneficios:**
- C04 y la no duplicación quedan garantizadas por el motor de base de datos, aunque exista un error en el código.
- No hay reintentos por conflictos de concurrencia en la aplicación.
- Las garantías se pueden verificar con solo inspeccionar el esquema.

**Costos:**
- En un grupo muy solicitado, las solicitudes se procesan de a una en el tramo final de T1, lo que genera esperas cortas.
- La tabla de idempotencia crece durante el período y debe depurarse al cerrarlo.
- El cupo mostrado en las consultas puede tener segundos de antigüedad (CF-02).

**Alcance:**
- **Cubre** la consistencia del cupo y la unicidad de inscripciones dentro de PIA, con o sin legado.
- **No cubre** la unicidad en el legado (la cubre TAC-02).
- **No garantiza** que el cupo que el estudiante vio en la consulta siga disponible al inscribir; garantiza que la respuesta de la inscripción sea correcta.

**Mecanismo de verificación:**

| Prueba | Cómo se ejecuta | Criterio de aprobación |
|---|---|---|
| V-03.1 Concurrencia sobre los últimos cupos (QAS-02) | Prueba de integración automática en cada Pull Request, con PostgreSQL real (Testcontainers): 300 hilos inscriben al mismo tiempo, en un grupo con 10 cupos libres, a 300 estudiantes distintos. | Exactamente 10 inscripciones creadas, `inscritos = capacidad`, 290 respuestas "sin cupo" y 0 errores no controlados. Se repite 20 veces sin una sola falla. |
| V-03.2 Repeticiones (QAS-03) | Prueba automática: la misma solicitud con la misma clave se envía 5 veces en paralelo. Una variante envía claves distintas para el mismo estudiante y grupo. | 1 inscripción, 1 cupo consumido y las 5 respuestas idénticas. En la variante, 1 inscripción y 4 respuestas "ya inscrito". |
| V-03.3 Conflicto de horario concurrente | Prueba automática: el mismo estudiante inscribe al mismo tiempo dos grupos con horario cruzado. | Exactamente 1 inscripción aceptada. |
| V-03.4 Restricción declarativa | Prueba automática: un `UPDATE` directo que intenta `inscritos = capacidad + 1`. | El motor lo rechaza con violación de `ck_cupo`. |
| V-03.5 Conciliación en producción | Consulta programada al cierre de cada jornada de matrícula: grupos con inscripciones activas mayores que la capacidad, o con `inscritos` distinto del número real de inscripciones activas. | 0 filas. Cualquier fila genera un incidente. |
