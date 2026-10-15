**Estudiante:** Camilo Andrés López Hernández — **Documento:** 1233691138

# ADR-004. Validación de prerrequisitos con una copia local y vigente del historial académico

| Campo | Valor |
|---|---|
| Identificador | ADR-004 |
| Título | Fuente de datos para validar prerrequisitos durante la matrícula (decisión adicional ligada a un driver de alta prioridad) |
| Fecha | 2026-10-14 |
| Estado | Aceptado |
| Autor | Camilo Andrés López Hernández |
| Relacionado con | [ADR-003](ADR-003-integracion-sistema-legado.md), [Actividad 1, SUP-02](../actividad1.md) |

## 1. Contexto y problema

Para inscribir una asignatura hay que verificar que el estudiante aprobó sus prerrequisitos (RFP-01). El historial académico y los prerrequisitos pertenecen al legado (RES-03). El ADR-003 desacopla el *registro* de inscripciones, pero la *validación* también necesita datos del legado. Si se consultara en línea, el Escenario A volvería a detener las inscripciones.

**Problema:** ¿de dónde obtiene PIA el historial académico para validar prerrequisitos sin depender en línea del legado y sin generar inscripciones inválidas?

## 2. Drivers arquitectónicos relacionados

| Driver | Prioridad | Relación |
|---|---|---|
| QAS-01 Disponibilidad ante falla del legado | 2 (A, A) | La validación no puede depender del legado en línea. |
| QAS-02 / OBN-01 Integridad de la matrícula | 1 (A, A) | Una inscripción sin prerrequisitos ocupa un cupo que otro estudiante habilitado necesita. |
| QAS-04 Rendimiento | 4 (A, M) | Validar debe tomar milisegundos dentro de la transacción T1. |
| RES-03 El legado es la fuente oficial | Obligatoria | PIA solo puede tener copias de lectura, nunca la versión oficial. |
| RES-04 Protección de datos | Obligatoria | La copia contiene datos académicos personales. |

## 3. Alternativas consideradas

### A1. Consulta en línea al legado por cada inscripción
La API pregunta al legado el historial del estudiante en el momento de inscribir.

### A2. Validación diferida
Se inscribe sin validar prerrequisitos y el legado valida al sincronizar. Si rechaza, se revierte la inscripción.

### A3. Caché bajo demanda con vencimiento
La primera vez que el estudiante entra se consulta el legado y el resultado se guarda durante un tiempo.

### A4. Copia local precargada con refresco incremental y marca de vigencia (seleccionada)
- Antes de abrir la matrícula, cuando ya están cerradas las notas del período anterior (SUP-02), el Sincronizador carga en el esquema `historial` la copia de **todas las asignaturas aprobadas** de cada estudiante habilitado, junto con el catálogo de prerrequisitos del período.
- Mientras el legado está disponible, el Sincronizador refresca de forma incremental cada 15 minutos las novedades: homologaciones, correcciones de notas y reintegros.
- Cada estudiante tiene una **marca de vigencia**. Si el legado reporta una novedad que todavía no se ha cargado, o el estudiante no estaba en la carga inicial, su copia queda *no vigente* y sus inscripciones se restringen hasta el siguiente refresco.
- El legado sigue siendo la validación final: si al sincronizar rechaza una inscripción, esta pasa a *rechazada* (ADR-003).

## 4. Criterios de comparación

| Criterio | A1. En línea | A2. Diferida | A3. Caché bajo demanda | A4. Copia precargada |
|---|---|---|---|---|
| Disponibilidad durante el Escenario A | Nula. | Total. | Nula para quien entra por primera vez. Justo en la apertura nadie tiene caché. | Total para estudiantes con copia vigente. |
| Riesgo de inscripciones inválidas | Nulo. | Alto: cualquier estudiante puede ocupar cupos sin cumplir prerrequisitos durante 40 min. | Bajo. | Bajo y acotado: solo cambios ocurridos después del último refresco. |
| Carga sobre el legado en el pico | Muy alta: una consulta por inscripción. | Nula en el pico. | Alta al inicio de la matrícula. | Nula en el pico: la carga masiva se hace antes de abrir. |
| Rendimiento de la validación | Depende del legado. | No aplica. | Variable. | Lectura local en milisegundos. |
| Frescura de los datos | Máxima. | No aplica. | Hasta el vencimiento de la caché. | Hasta 15 min en operación normal, o la duración de la falla. |

## 5. Decisión

**Se adopta A4.** PIA valida prerrequisitos contra una copia local del historial cargada antes de la apertura de la matrícula y refrescada cada 15 minutos, con una marca de vigencia por estudiante. El legado conserva la validación final al momento de sincronizar.

## 6. Justificación

1. **Es la única alternativa que mantiene a la vez disponibilidad e integridad en el Escenario A.** A1 y A3 fallan justo en la apertura, cuando el legado no responde. A2 sacrifica la integridad, porque deja que estudiantes no habilitados ocupen cupos.
2. **Se apoya en una propiedad del dominio:** durante la matrícula, el historial aprobado prácticamente no cambia, porque las notas ya están cerradas (SUP-02). Por eso una copia cargada antes de abrir es casi exacta, y las pocas novedades se identifican y se manejan con la marca de vigencia en lugar de invalidar toda la copia.
3. **No contradice RES-03.** La copia es de lectura, no es oficial y no se modifica en PIA. La decisión final sigue siendo del legado al sincronizar.
4. **Traslada la carga sobre el legado fuera del pico.** La consulta masiva ocurre antes de abrir la matrícula, cuando el legado no está sometido a la demanda de 1.200 usuarios.

## 7. Consecuencias

### Positivas
- La validación de prerrequisitos es local, rápida y está disponible aunque el legado no responda.
- El legado deja de recibir consultas de historial durante el pico.

### Negativas
- Hay una ventana de desactualización de hasta 15 minutos en operación normal, y de la duración de la falla en el Escenario A.
- Algunos estudiantes con novedades recientes no podrán inscribir mientras el legado no esté disponible.
- Hay que mantener un proceso de carga, refresco y verificación de la copia.

### Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| La carga inicial queda incompleta. | Verificación antes de abrir: el número de estudiantes y de registros copiados debe coincidir con el del legado. Si no coincide, registro académico decide si abrir la matrícula. |
| SUP-02 resulta falso: el historial cambia con frecuencia durante la matrícula. | El indicador de tasa de rechazos al sincronizar lo revela (alerta si supera el 1 %). En ese caso se revisa esta decisión. |
| La copia expone datos personales. | **Minimización de datos** (principio de finalidad, Ley 1581 de 2012): se copian solo los códigos de asignaturas aprobadas, sin notas ni otros datos. El acceso es solo para el módulo de reglas, y la copia se elimina al cierre del período. |

## 8. Condiciones para revisar la decisión

- La tasa de rechazos al sincronizar por prerrequisitos supera el 1 % de forma sostenida.
- La universidad permite modificar el historial durante la matrícula, por ejemplo con notas tardías o habilitaciones.
- El legado ofrece un servicio de consulta en línea con disponibilidad comprobada igual o superior a la de PIA.
- Se retira el legado y PIA pasa a ser la fuente oficial del historial.

## 9. Referencias

- Bass, L., Clements, P. y Kazman, R. (2021). *Software Architecture in Practice* (4.ª ed.). Addison-Wesley. Táctica "mantener múltiples copias de los datos".
- Congreso de Colombia (2012). Ley Estatutaria 1581 de 2012, art. 4 (principios de finalidad y de acceso y circulación restringida).
- Evans, E. (2003). *Domain-Driven Design*. Addison-Wesley.
- Abadi, D. (2012). Consistency tradeoffs in modern distributed database system design. *IEEE Computer, 45*(2).
