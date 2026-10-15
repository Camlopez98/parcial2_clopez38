**Estudiante:** Camilo Andrés López Hernández — **Documento:** 1233691138

# ADR-003. Integración con el sistema legado y manejo de sus fallas: bandeja de salida transaccional, sincronizador aislado y operación degradada controlada

| Campo | Valor |
|---|---|
| Identificador | ADR-003 |
| Título | Estrategia de integración y manejo de fallas del sistema legado |
| Fecha | 2026-10-14 |
| Estado | Aceptado |
| Autor | Camilo Andrés López Hernández |
| Relacionado con | [ADR-001](ADR-001-estilo-arquitectonico.md), [ADR-002](ADR-002-consistencia-cupos-inscripciones.md), [ADR-004](ADR-004-validacion-prerrequisitos-copia-local.md), [Actividad 2, secciones 3.3 y 5](../actividad2.md) |

## 1. Contexto y problema

El sistema legado sigue siendo la fuente oficial del historial académico y de los prerrequisitos, y el lugar donde una inscripción se vuelve oficial (RES-03). PIA administra las inscripciones del período y debe sincronizarlas con él. El legado puede quedar sin responder hasta 40 minutos (C05).

**Escenario A asignado:** al iniciar la matrícula, el legado deja de responder durante 40 minutos.

La Actividad 1 (sección 4.1) mostró que, con una dependencia síncrona, esa sola falla consume el 92,6 % del presupuesto mensual de indisponibilidad de C03 (43,2 minutos).

**Problema:** ¿cómo se integra PIA con el legado para que:
- una falla del legado no detenga la matrícula;
- no se generen confirmaciones incorrectas, es decir, inscripciones presentadas como oficiales que el legado no registró o que no cumplen prerrequisitos;
- no se generen registros duplicados en el legado cuando la sincronización se reintenta?

## 2. Drivers arquitectónicos relacionados

| Driver | Prioridad | Medida |
|---|---|---|
| QAS-01 Disponibilidad ante falla del legado | 2 (A, A) | 0 min de indisponibilidad de PIA por la falla del legado; detección ≤ 30 s; sincronización del 100 % de lo pendiente ≤ 15 min tras la recuperación; 0 inscripciones mostradas como confirmadas sin registro en el legado. |
| QAS-03 No duplicación | 3 (A, M) | 0 duplicados en el legado. |
| RES-03 El legado es la fuente oficial | Obligatoria | Solo es oficial lo que el legado registró. |
| C05 Interrupciones de hasta 40 min | Supuesto (SUP-01) | — |

## 3. Alternativas consideradas

### A1. Integración síncrona en cada operación
La API consulta prerrequisitos y registra la inscripción en el legado durante la solicitud del estudiante, con tiempo máximo de espera y reintentos.

### A2. Integración síncrona con interruptor de circuito y rechazo rápido
Igual que A1, pero con un interruptor de circuito (Nygard, 2018). Mientras el legado está caído, la API rechaza de inmediato las inscripciones con el mensaje "servicio no disponible", sin esperar.

### A3. Integración asíncrona: bandeja de salida transaccional y Sincronizador aislado (seleccionada)
- La API nunca llama al legado. Cada inscripción o cancelación escribe un evento en `integracion.outbox` dentro de su misma transacción local (Richardson, 2018).
- Un proceso separado, el **Sincronizador**, lee la bandeja de salida y registra los eventos en el legado mediante un **adaptador anticorrupción** (Evans, 2003) que encapsula su protocolo y su modelo.
- El Sincronizador aplica un tiempo máximo de espera de 5 s, un interruptor de circuito, reintentos con espera exponencial y variación aleatoria (Brooker, 2015), y una **consulta de existencia antes de registrar**.
- La inscripción queda en estado *pendiente de sincronización* y solo pasa a *confirmada* cuando el legado la registra.

### A4. Escritura directa en la base de datos del legado
PIA escribe directamente en las tablas del legado, con una transacción distribuida o con escrituras independientes.

## 4. Criterios de comparación

| Criterio | A1. Síncrona | A2. Síncrona con interruptor | A3. Asíncrona con outbox | A4. Escritura directa |
|---|---|---|---|---|
| Disponibilidad de PIA durante 40 min sin legado (QAS-01) | Nula: las inscripciones fallan y además retienen hilos durante las esperas. | Nula para inscribir, aunque falla rápido. Consume 40 de los 43,2 min de C03. | Total: inscripción, cancelación y consulta siguen operando. | Nula si la base del legado también está caída. |
| Riesgo de confirmaciones incorrectas | Bajo. | Bajo. | Bajo: nada se presenta como oficial antes de la respuesta del legado. | Alto si una de las escrituras falla (escritura dual). |
| Riesgo de duplicados en el legado | Alto: un tiempo de espera agotado seguido de un reintento puede registrar dos veces. | Igual que A1. | Controlado: consulta de existencia por clave natural y una clave única por evento. | Alto. |
| Dependencia de capacidades del legado (SUP-03) | Necesita un servicio en línea rápido. | Igual que A1. | Le basta cualquier mecanismo de consulta y registro, aunque sea lento. | Acopla PIA al esquema interno del legado. |
| Complejidad | Baja. | Baja a media. | Media: Sincronizador, outbox, estados intermedios. | Media, con riesgo alto. |
| Compatibilidad con RES-01 y RES-02 | Sí. | Sí. | Sí: la outbox es una tabla de PostgreSQL, sin broker. | Sí, pero rompe el encapsulamiento del legado. |

## 5. Decisión

**Se adopta A3.** La integración con el legado es asíncrona, mediante una bandeja de salida transaccional en PostgreSQL y un proceso Sincronizador aislado con adaptador anticorrupción, interruptor de circuito, reintentos con espera exponencial y consulta de existencia antes de registrar. La inscripción solo se presenta como oficial (*confirmada*) cuando el legado la registra. Los prerrequisitos se validan contra una copia local del historial, según el ADR-004.

## 6. Justificación

1. **Es la única alternativa compatible con C03 bajo C05.** A1 y A2 hacen que la disponibilidad de PIA sea, como máximo, la del legado. A3 las desacopla: la operación del estudiante termina con el `COMMIT` local en PostgreSQL.
2. **Evita la escritura dual sin un broker.** Como el evento se escribe en la misma transacción que la inscripción, no puede existir una inscripción sin evento ni un evento sin inscripción. Esto se logra con PostgreSQL, que ya existe (RES-01), sin agregar un componente que el equipo deba operar (RES-02).
3. **Hace imposible el duplicado aunque la entrega se repita.** No se puede garantizar una entrega exactamente una vez sobre un canal que falla (Gray, 1978), así que el diseño asume entrega *al menos una vez* y hace idempotente el registro: antes de registrar, el adaptador consulta si ya existe la inscripción del estudiante en ese grupo y período, y envía el identificador de la inscripción de PIA como referencia única.
4. **Respeta RES-03 sin bloquear al estudiante.** El estado *pendiente de sincronización* comunica con honestidad que la inscripción está registrada en PIA y tiene cupo reservado, pero todavía no es oficial. Ninguna inscripción se presenta como oficial antes de tiempo.

## 7. Comportamiento durante el Escenario A

### 7.1 Detección
- El interruptor de circuito del Sincronizador se abre tras 5 fallas seguidas (unos 25 s, dado el tiempo máximo de espera de 5 s por llamada).
- El Sincronizador registra `estado_legado = NO_DISPONIBLE` y la hora de inicio.
- Se envía una alerta al administrador de infraestructura y al área de registro académico.

### 7.2 Qué operaciones continúan y cuáles se restringen

| Operación | Durante la falla | Fundamento |
|---|---|---|
| Consultar asignaturas y grupos | **Continúa** sin cambios. | La oferta del período ya está en PIA. |
| Inscribir (estudiante con copia del historial vigente) | **Continúa.** Queda en *pendiente de sincronización* con cupo reservado. | Prerrequisitos validados con la copia local (ADR-004); cupo garantizado por PostgreSQL (ADR-002). |
| Inscribir (estudiante con copia del historial no vigente, por una novedad no cargada) | **Se restringe.** Se rechaza sin consumir cupo. | No es posible validar prerrequisitos sin riesgo de inscripción inválida. |
| Cancelar | **Continúa.** El cupo se libera de inmediato en PIA; la cancelación oficial queda pendiente. | El cupo es un dato de PIA; la cancelación oficial se sincroniza después. |
| Consultar estado | **Continúa**, mostrando el estado del legado. | — |
| Cambios de capacidad de grupos (funcionario de registro) | **Continúa**, con auditoría. | Dato administrado por PIA. |
| Refrescar el historial desde el legado | **Se suspende.** | Requiere al legado. |

### 7.3 Cómo se informa al estudiante
- **Banner global** mientras `estado_legado = NO_DISPONIBLE`: "El sistema académico está temporalmente no disponible. Puedes seguir inscribiendo: tus inscripciones quedan registradas y con cupo reservado, y serán oficiales cuando se restablezca la conexión."
- **Inscripción exitosa:** estado *Registrada, pendiente de confirmación oficial*.
- **Inscripción restringida:** "No es posible validar tus prerrequisitos en este momento por una novedad reciente en tu historial. Intenta de nuevo más tarde; no se ha consumido ningún cupo."
- **Al sincronizar:** correo de confirmación o, en caso de rechazo, correo con el motivo, y el cupo se libera.

### 7.4 Cómo se recupera la operación normal
1. Mientras el interruptor está abierto, el Sincronizador hace una prueba cada 30 s. Cuando el legado responde, el interruptor pasa a semiabierto y luego a cerrado, y se registra `estado_legado = DISPONIBLE`.
2. Se vacía la bandeja de salida **en orden de creación por inscripción**, con un ritmo limitado de 10 eventos por segundo para no saturar al legado recién recuperado.
   - Estimación: si en 40 minutos 1.200 estudiantes inscriben en promedio 5 asignaturas, se acumulan unos 6.000 eventos. A 10 por segundo se procesan en unos 10 minutos, dentro de los 15 minutos de QAS-01.
   - El ritmo de 10 por segundo es un supuesto que se debe validar con el área responsable del legado.
3. Por cada evento: consulta de existencia → registro si no existe → transacción T3 (*confirmada* o *rechazada*, con liberación del cupo si hay rechazo) → notificación.
4. Al terminar, el Sincronizador ejecuta una **conciliación**: compara las inscripciones *confirmadas* de PIA con las registradas en el legado para el período y genera un informe de diferencias para registro académico. El resultado esperado es 0 diferencias.
5. Se reanuda el refresco incremental del historial (ADR-004).

## 8. Consecuencias

### Positivas
- La disponibilidad de PIA deja de depender de la del legado.
- No hay escritura dual ni duplicados, aunque se reintente.
- El legado queda encapsulado detrás del adaptador anticorrupción: un cambio en su protocolo solo afecta a ese adaptador.

### Negativas
- **Consistencia eventual** con el legado: durante la falla y unos segundos en operación normal, la inscripción no es oficial.
- Una inscripción provisional puede ser rechazada al sincronizar, por ejemplo si el legado detecta una novedad que la copia local no tenía. El estudiante pierde el cupo después de haberlo visto reservado, y se le notifica.
- Hay más piezas que operar y monitorear: el Sincronizador, la bandeja de salida y la conciliación.

### Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| El legado no admite consultas por clave natural, lo que impide la consulta de existencia (SUP-03). | Validar con el área del legado antes de construir. Como alternativa, una tabla de referencias PIA–legado en el adaptador. |
| La bandeja de salida crece sin control si el legado está caído mucho más de 40 minutos. | Alerta por antigüedad del evento más viejo (> 45 min) y procedimiento manual de contingencia con registro académico. |
| La tasa de rechazos al sincronizar es alta, lo que indica una copia desactualizada. | Indicador de tasa de rechazo con alerta si supera el 1 %; revisión del refresco del ADR-004. |
| El Sincronizador cae. | Se reinicia automáticamente como servicio del sistema operativo. Como el progreso está en la outbox, no se pierde trabajo. |

## 9. Condiciones para revisar la decisión

- Las interrupciones del legado superan con frecuencia los 40 minutos, o se producen varias veces por período.
- La tasa de rechazos al sincronizar supera el 1 % de forma sostenida.
- El legado ofrece un servicio de registro idempotente o una publicación de eventos, lo que simplificaría el adaptador.
- La universidad decide que PIA sea la fuente oficial de las inscripciones, lo que elimina RES-03.

## 10. Referencias

- Brooker, M. (2015). *Exponential Backoff and Jitter*. AWS Architecture Blog.
- Evans, E. (2003). *Domain-Driven Design*. Addison-Wesley. Patrón *Anticorruption Layer*.
- García-Molina, H. y Salem, K. (1987). Sagas. *Proceedings of the ACM SIGMOD*.
- Gray, J. (1978). Notes on data base operating systems. En *Operating Systems: An Advanced Course*, LNCS 60. Springer.
- Helland, P. (2012). Idempotence is not a medical condition. *ACM Queue, 10*(4).
- Nygard, M. (2018). *Release It! Design and Deploy Production-Ready Software* (2.ª ed.). Pragmatic Bookshelf. Patrones *Circuit Breaker* y *Timeouts*.
- Richardson, C. (2018). *Microservices Patterns*. Manning. Patrón *Transactional Outbox*.
