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
   - *Abierto*: se activa cuando, con al menos 5 llamadas evaluadas, el 50 % o más de las últimas 20 fallan o tardan más de 5 s. Por eso 5 fallas seguidas, unos 25 s, abren el circuito dentro del límite de 30 s de QAS-01. Las llamadas se rechazan de inmediato sin tocar al legado.
   - *Semiabierto*: después de 30 s abierto, se permite una llamada de prueba; si tiene éxito el circuito se cierra, y si falla vuelve a abrirse.
3. **Publicación del estado.** Cada cambio de estado del circuito se escribe en `estado_legado`, con hora de inicio, y genera una alerta al administrador y a registro académico.
4. **Degradación controlada.** La API lee `estado_legado` y, sin cambiar su lógica de inscripción (ADR-003), activa el banner informativo. Restringe solo las inscripciones de estudiantes con copia del historial no vigente (ADR-004).
5. **Reanudación con ritmo limitado.** Al cerrarse el circuito, la bandeja de salida se vacía a un máximo de 10 eventos por segundo, para no saturar al legado recién recuperado.

```yaml
# Configuración propuesta del adaptador (Resilience4j)
resilience4j.circuitbreaker.instances.legado:
  slidingWindowType: COUNT_BASED
  slidingWindowSize: 20
  minimumNumberOfCalls: 5
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

---

## TAC-04. Control de la demanda: limitación de tasa, colas acotadas y caché de lectura

**Atributo de calidad:** eficiencia de desempeño. Combina tácticas para controlar la demanda (gestionar las solicitudes de trabajo y limitar la respuesta a eventos) con tácticas para gestionar recursos (acotar el tamaño de las colas y mantener múltiples copias de los datos) (Bass et al., 2021).

**Problema específico:**
- En la apertura de la matrícula, 1.200 estudiantes generan una ráfaga de consultas y escrituras.
- Los reintentos multiplican esa carga: un estudiante impaciente repite el clic o recarga la página.
- Sin límites, la base de datos recibe más trabajo del que puede atender, las colas internas crecen sin control y el tiempo de respuesta se degrada para **todos**, incumpliendo C02.

**Componentes donde se implementa:**
- *Proxy inverso (Nginx)*: límite por dirección IP y balanceo.
- *API*: límite por estudiante para escrituras (Bucket4j), pool de conexiones acotado (HikariCP), límite de hilos del servidor web y caché de la oferta (Caffeine).
- *Aplicación web*: respeta el encabezado `Retry-After` y reutiliza la clave de idempotencia.

**Funcionamiento técnico:**

1. **Dimensionamiento con la ley de Little** (L = λW; Little, 1961). Supuesto de diseño: cada estudiante conectado hace en promedio una solicitud cada 10 s.
   - Tasa de llegada: λ ≈ 1.200 / 10 = **120 solicitudes por segundo**.
   - Con un tiempo de servicio objetivo W ≈ 0,2 s, el número medio de solicitudes en curso es L = 120 × 0,2 ≈ **24**, es decir, unas 12 por instancia de la API.
   - Un pool de **30 conexiones por instancia** (60 en total, con PostgreSQL configurado para 100) da un margen de 2,5 veces para picos sin saturar el motor.
   - Ese supuesto se debe validar en la prueba de carga.
2. **Límite de tasa en dos niveles** (algoritmo de cubeta de *tokens*; Tanenbaum y Wetherall, 2011):
   - **Nginx**, por dirección IP: `limit_req` de 30 solicitudes/s con ráfaga de 60. El valor es holgado porque muchos estudiantes del campus comparten IP a través de la red inalámbrica. Su función es frenar abusos, no a los estudiantes.
   - **API**, por estudiante (identificado por el token): 5 solicitudes de inscripción o cancelación cada 10 s. Lo que exceda ese límite recibe `429 Too Many Requests` con `Retry-After`.
3. **Colas acotadas y rechazo rápido:**
   - El servidor web de la API admite un máximo de 200 hilos y una cola de 100 conexiones.
   - HikariCP espera como máximo 2 s por una conexión. Si no la obtiene, responde `503` con `Retry-After: 5` en lugar de dejar la solicitud esperando indefinidamente.
   - Así, una sobrecarga produce rechazos rápidos y explícitos, no tiempos de espera generalizados.
4. **Caché de lectura de la oferta.** El listado de asignaturas y grupos, que cambia poco, se guarda en la memoria de cada instancia durante 5 s (Caffeine). El número de cupos que se muestra puede tener hasta 5 s de antigüedad; la validación definitiva ocurre en T1 (CF-02, ADR-002).
5. **Cliente disciplinado.** La aplicación web deshabilita el botón de inscribir mientras hay una solicitud en curso. Ante `429` o `503`, espera lo que indica `Retry-After` y reintenta con la **misma** clave de idempotencia.

**Beneficios:**
- Bajo sobrecarga, el sistema se degrada de forma controlada y predecible: las solicitudes admitidas cumplen C02 y las rechazadas reciben una respuesta inmediata.
- La caché reduce la mayor parte de las lecturas de oferta a la base de datos durante el pico.
- Los reintentos del cliente quedan regulados.

**Costos:**
- Un estudiante puede recibir ocasionalmente "intente en unos segundos".
- Los límites deben calibrarse con datos reales de cada matrícula.
- La caché muestra cupos con hasta 5 s de antigüedad.
- Cada instancia lleva su propio contador de límite por estudiante. Con dos instancias, el límite efectivo puede llegar al doble, lo que se considera aceptable frente al costo de un almacén compartido (RES-02).

**Alcance:**
- **Cubre** la protección de la API y de PostgreSQL ante picos y ráfagas de reintentos, y el cumplimiento de C02 para las solicitudes admitidas.
- **No cubre** un aumento sostenido de la demanda muy por encima de la capacidad dimensionada: en ese caso hay que agregar capacidad, y aplica la condición de revisión del ADR-001.
- **No reemplaza** la idempotencia (TAC-03): limitar la tasa reduce los reintentos, pero no impide que uno llegue dos veces.

**Mecanismo de verificación:**

| Prueba | Cómo se ejecuta | Criterio de aprobación |
|---|---|---|
| V-04.1 Carga nominal (QAS-04) | Prueba de carga con k6 en preproducción, antes de cada matrícula: 1.200 usuarios virtuales durante 15 min, con mezcla de 80 % consultas, 15 % inscripciones y 5 % cancelaciones, y 10 s de pausa entre acciones. | Percentil 95 de consultas ≤ 2 s; percentil 95 de inscripciones ≤ 3 s; errores (5xx) < 1 %; conexiones activas a PostgreSQL ≤ 60. |
| V-04.2 Pico por encima de lo nominal | La misma prueba, escalando a 1.800 usuarios (+50 %) durante 5 min. | Las solicitudes admitidas mantienen el percentil 95 ≤ 2 s. El exceso se rechaza con `429` o `503` en < 100 ms, sin tiempos de espera agotados. Al bajar la carga, el sistema vuelve a 0 rechazos en ≤ 1 min. |
| V-04.3 Ráfaga de reintentos | Un grupo de usuarios virtuales repite cada inscripción 5 veces en 2 s. | Respuestas `429` o idénticas a la original, 0 inscripciones duplicadas (verificado con V-03.2) y sin impacto en el percentil 95 de los demás usuarios. |
| V-04.4 Indicador en producción | Métricas de latencia por percentil, tasa de 429 y 503, y uso del pool de conexiones (Micrometer y Prometheus). | Alerta si el percentil 95 de consultas supera 2 s durante 5 minutos seguidos. |

---

## TAC-05. Redundancia activa, redundancia pasiva y respaldo con archivado continuo

**Atributo de calidad:** disponibilidad y recuperabilidad. Combina tácticas de recuperación: redundancia activa, redundancia pasiva y respaldo con recuperación (Bass et al., 2021).

**Problema específico:**
- Una falla de hardware, del sistema operativo o de PostgreSQL en el servidor principal detendría la matrícula y podría perder inscripciones.
- C06 exige recuperar el servicio en ≤ 30 min y C07, perder como máximo 5 min de datos.
- También existen las fallas *lógicas*, como un borrado accidental, que una réplica copiaría de inmediato.

**Componentes donde se implementa:**
- *API*: dos instancias activas detrás de Nginx.
- *Base de datos*: primaria y réplica en espera con replicación en flujo.
- *Repositorio de respaldos*: pgBackRest.
- *Infraestructura*: servicios systemd con reinicio automático.

**Funcionamiento técnico:**
1. **Redundancia activa de la API.**
   - Dos instancias atienden al mismo tiempo. Nginx verifica su salud: tras 3 fallas en 10 s, retira la instancia del balanceo.
   - Como la API no guarda estado en memoria, la otra instancia atiende sin pérdida de sesión.
   - Los despliegues se hacen de una instancia a la vez, de modo que una actualización no produce indisponibilidad.
2. **Redundancia pasiva de la base de datos.**
   - La réplica recibe continuamente el registro de transacciones de la primaria (replicación en flujo asíncrona) y queda lista para promoverse.
   - Se elige la replicación asíncrona porque la síncrona agregaría latencia a cada `COMMIT`, y el RPO de 5 min no la exige.
   - Hay una alerta si el retraso de replicación supera 60 s.
3. **Conmutación por procedimiento documentado.** La ejecuta el administrador de infraestructura:

   | Paso | Tiempo estimado |
   |---|---|
   | (1) Confirmar la caída de la primaria | 5 min |
   | (2) Promover la réplica con `SELECT pg_promote()` | 1 min |
   | (3) Apuntar la API al nuevo servidor (dirección virtual o configuración) y reiniciar las instancias | 5 min |
   | (4) Ejecutar la conciliación de cupos V-03.5 | 5 min |
   | (5) Reabrir las inscripciones | — |
   | **Total** | **≈ 16–21 min, dentro de los 30 min de C06** |

   Se descarta la conmutación automática (por ejemplo, Patroni con etcd) en esta etapa: agrega un clúster de consenso que el equipo de RES-02 tendría que operar, y el RTO de 30 minutos se alcanza de forma manual.
4. **Respaldo con archivado continuo.**
   - pgBackRest hace un respaldo completo semanal y uno diferencial diario.
   - El registro de transacciones se archiva de forma continua, con `archive_timeout = 60 s`.
   - Esto permite recuperar la base de datos a cualquier instante (*point-in-time recovery*), con una pérdida máxima de 1 minuto aunque se pierdan la primaria y la réplica. También protege contra borrados accidentales.

**Beneficios:**
- La falla de una instancia de la API es transparente para los usuarios.
- La falla de la base de datos se recupera dentro del RTO.
- Existe protección contra fallas lógicas.
- Todo con software libre sobre la infraestructura existente (RES-01).

**Costos:**
- Se necesita un segundo servidor de base de datos y almacenamiento para respaldos.
- La conmutación depende de que el administrador esté disponible. Durante la matrícula se requiere un turno de disponibilidad.
- Hay que realizar simulacros periódicos.

**Alcance:**
- **Cubre** la falla de una instancia de la API, la falla del servidor de base de datos y la pérdida o corrupción de datos.
- **No cubre** la caída del único proxy Nginx. Se mitiga con reinicio automático por systemd, y se puede agregar un segundo Nginx con dirección virtual (keepalived) si los indicadores de disponibilidad lo justifican.
- **No cubre** la caída completa del centro de datos, que excede el alcance del caso.
- **No cubre** las fallas del legado; esas las cubren TAC-01 y TAC-02.

**Mecanismo de verificación:**

| Prueba | Cómo se ejecuta | Criterio de aprobación |
|---|---|---|
| V-05.1 Falla de una instancia de la API | Durante V-04.1, se detiene una instancia de la API. | Errores < 1 % y percentil 95 ≤ 2 s; Nginx retira la instancia en ≤ 10 s. |
| V-05.2 Simulacro de conmutación (RTO) | En preproducción, antes de cada matrícula, con carga activa: se apaga la primaria y se ejecuta el procedimiento. | Tiempo entre la falla y la primera inscripción exitosa ≤ 30 min (C06). |
| V-05.3 Medición de la pérdida de datos (RPO) | Durante V-05.2, un proceso inserta un registro "latido" con marca de tiempo cada 10 s. Después de la conmutación se consulta el último latido presente. | Diferencia entre la hora de la falla y el último latido recuperado ≤ 5 min (C07). |
| V-05.4 Restauración desde respaldo | Una vez al mes: se restaura con pgBackRest a un instante dado en un servidor de prueba. | Restauración exitosa al instante pedido, con un tiempo total registrado y conciliación de cupos (V-03.5) en 0 filas. |
| V-05.5 Indicador en producción | Retraso de replicación y antigüedad del último registro de transacciones archivado. | Alerta si el retraso supera 60 s o si el último archivado tiene más de 5 min. |

---

## Matriz resumen de tácticas

| Táctica | Escenario y medida | Componentes | Verificación principal | Momento |
|---|---|---|---|---|
| TAC-01 Interruptor de circuito y degradación | QAS-01: detección ≤ 30 s; 0 min de indisponibilidad por el legado | Sincronizador (adaptador), `estado_legado`, API (consulta de estado) | V-01.2 inyección de fallas de 40 min con carga | Antes de cada matrícula |
| TAC-02 Outbox y reintento idempotente | QAS-01 / QAS-03: vaciado ≤ 15 min; 0 duplicados en el legado | Publicador de eventos, outbox, Sincronizador, Aplicar resultado | V-02.2 y V-02.3 (en cada Pull Request), V-02.4 | Integración continua y antes de cada matrícula |
| TAC-03 Transacciones y restricciones declarativas | QAS-02 / QAS-03: inscritos ≤ capacidad; 0 duplicados | Inscribir asignatura, Control de cupos, Guardia de idempotencia, esquema | V-03.1 300 sobre 10 cupos | Cada Pull Request |
| TAC-04 Control de la demanda | QAS-04: percentil 95 ≤ 2 s con 1.200 usuarios | Nginx, límite por estudiante, pool acotado, caché | V-04.1 y V-04.2 prueba de carga | Antes de cada matrícula |
| TAC-05 Redundancia y respaldo | QAS-05: RTO ≤ 30 min, RPO ≤ 5 min | API ×2, réplica, pgBackRest | V-05.2 y V-05.3 simulacro con latidos | Antes de cada matrícula y mensual |

## Plan de verificación por ambiente

| Ambiente | Pruebas | Frecuencia | Responsable | Evidencia que se conserva |
|---|---|---|---|---|
| Integración continua (cada Pull Request) | V-01.1, V-02.1, V-02.2, V-02.3, V-03.1 a V-03.4 | En cada Pull Request; bloquean la integración si fallan (Actividad 5) | Desarrollador autor | Informe de la ejecución en el Pull Request |
| Preproducción, con datos sintéticos de volumen real | V-01.2, V-01.3, V-02.4, V-04.1 a V-04.3, V-05.1 a V-05.3 | Antes de cada período de matrícula | Administrador de infraestructura y líder técnico | Informe de k6, registros del simulacro y resultados SQL, guardados en `docs/evidencias/<período>/` |
| Producción | V-01.4, V-02.5, V-03.5, V-04.4, V-05.4, V-05.5 | Continuo, diario y mensual | Administrador de infraestructura | Alertas e informe posterior a la matrícula |

Una táctica se considera **validada** solo cuando su verificación se ejecutó y cumplió el criterio numérico. Si un criterio falla, se registra como incumplimiento y se trata con el procedimiento de la Actividad 5.

---

## Referencias

- Bass, L., Clements, P. y Kazman, R. (2021). *Software Architecture in Practice* (4.ª ed.). Addison-Wesley. Catálogos de tácticas de disponibilidad, rendimiento e integridad.
- Berenson, H. et al. (1995). A critique of ANSI SQL isolation levels. *Proceedings of the ACM SIGMOD*.
- Brooker, M. (2015). *Exponential Backoff and Jitter*. AWS Architecture Blog.
- Codd, E. F. (1970). A relational model of data for large shared data banks. *CACM, 13*(6).
- García-Molina, H. y Salem, K. (1987). Sagas. *Proceedings of the ACM SIGMOD*.
- Gray, J. (1978). Notes on data base operating systems. En *Operating Systems: An Advanced Course*, LNCS 60. Springer.
- Little, J. D. C. (1961). A proof for the queuing formula L = λW. *Operations Research, 9*(3), 383–387.
- Nygard, M. (2018). *Release It!* (2.ª ed.). Pragmatic Bookshelf.
- PostgreSQL Global Development Group (2024). *PostgreSQL 16 Documentation*, cap. 13 "Concurrency Control", cap. 26 "Backup and Restore" y cap. 27 "High Availability, Load Balancing, and Replication".
- Richardson, C. (2018). *Microservices Patterns*. Manning.
- Tanenbaum, A. y Wetherall, D. (2011). *Computer Networks* (5.ª ed.). Pearson. Algoritmo de cubeta de *tokens*.
