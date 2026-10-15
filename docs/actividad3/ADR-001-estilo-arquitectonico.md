**Estudiante:** Camilo Andrés López Hernández — **Documento:** 1233691138

# ADR-001. Estilo arquitectónico: monolito modular hexagonal desplegado en dos procesos

| Campo | Valor |
|---|---|
| Identificador | ADR-001 |
| Título | Selección del estilo arquitectónico de PIA |
| Fecha | 2026-10-14 |
| Estado | Aceptado |
| Autor | Camilo Andrés López Hernández |
| Relacionado con | [Actividad 1](../actividad1.md) (drivers), [Actividad 2](../actividad2.md) (estructura), [ADR-002](ADR-002-consistencia-cupos-inscripciones.md), [ADR-003](ADR-003-integracion-sistema-legado.md) |

## 1. Contexto y problema

La universidad necesita una plataforma de inscripción que:

- atienda hasta 1.200 estudiantes al tiempo (C01);
- no permita sobrecupos (C04);
- mantenga una disponibilidad del 99,9 % durante la matrícula (C03), aunque el sistema legado no responda hasta 40 minutos (C05, Escenario A);
- permita incorporar reglas académicas con bajo esfuerzo.

La solución debe ejecutarse sobre Linux y PostgreSQL, sin servicios comerciales (C08), y la mantendrá un equipo de cuatro desarrolladores y un administrador de infraestructura (C10).

**Problema:** ¿qué estilo arquitectónico organiza la solución para satisfacer los drivers de mayor prioridad sin exceder la capacidad operativa del equipo?

## 2. Drivers arquitectónicos relacionados

| Driver | Prioridad (Actividad 1) | Exigencia sobre el estilo |
|---|---|---|
| QAS-02 Integridad de cupos | 1 (A, A) | El cupo y la inscripción deben confirmarse de forma atómica. |
| QAS-01 Disponibilidad ante falla del legado | 2 (A, A) | La falla del legado no puede propagarse a las operaciones de usuario. |
| QAS-07 Modificabilidad de reglas | 7 (M, M) | Las reglas deben poder cambiarse sin tocar cupos ni integración. |
| RES-01 Linux, PostgreSQL y sin servicios comerciales | Obligatoria | Todo componente debe ser libre y operable en la infraestructura propia. |
| RES-02 4 desarrolladores y 1 administrador | Obligatoria | La operación debe ser sostenible por ese equipo. |

## 3. Alternativas consideradas

### A1. Monolito en capas
Una aplicación con capas de presentación, negocio y datos, donde cada capa usa solo a la inferior (Buschmann et al., 1996). La integración con el legado se hace desde la capa de negocio.

### A2. Monolito modular con arquitectura hexagonal, desplegado en dos procesos
- Una base de código dividida en módulos verticales: oferta, inscripciones, reglas, historial, auditoría e integración. Cada módulo tiene interfaces públicas explícitas (Parnas, 1972).
- Dentro de cada módulo, el dominio solo se comunica con el exterior mediante puertos y adaptadores (Cockburn, 2005).
- Se despliega como dos procesos de la misma base de código: la **API**, con dos instancias, y el **Sincronizador**, único proceso que se comunica con el legado.
- Comparten una base de datos PostgreSQL con un esquema por módulo.

### A3. Microservicios
Servicios independientes (oferta, inscripciones, cupos, reglas, integración), cada uno con su propia base de datos, comunicados por HTTP y un broker de mensajería (Lewis y Fowler, 2014).

## 4. Criterios de comparación

Los pesos se derivan de la prioridad de los drivers de la Actividad 1. Escala: 1 (muy desfavorable) a 5 (muy favorable).

| Criterio | Peso | A1. Capas | A2. Modular hexagonal | A3. Microservicios |
|---|---|---|---|---|
| C-1 Atomicidad de cupo e inscripción (QAS-02) | 30 % | 5: una base de datos, una transacción. | 5: una base de datos, una transacción. | 1: el cupo y la inscripción quedan en servicios distintos; exige sagas o compromiso en dos fases. |
| C-2 Aislamiento de la falla del legado (QAS-01) | 25 % | 2: la integración comparte hilos y conexiones con las operaciones de usuario. | 5: el legado está detrás de un puerto y en otro proceso. | 4: aislado en un servicio, pero se agregan otros puntos de falla de red. |
| C-3 Operabilidad por el equipo (RES-01, RES-02) | 20 % | 5: un despliegue. | 4: dos procesos de una misma base de código. | 1: muchos despliegues, bases de datos, broker y monitoreo distribuido. |
| C-4 Modificabilidad de reglas (QAS-07) | 15 % | 2: las reglas se dispersan en la capa de negocio. | 5: módulo de reglas con un puerto propio. | 4: aislado, pero con contratos entre servicios que versionar. |
| C-5 Rendimiento de consultas (QAS-04) | 10 % | 4: llamadas en memoria. | 4: llamadas en memoria. | 2: saltos de red por consulta (Deutsch, 1994). |
| **Total ponderado** | 100 % | **3,70** | **4,70** | **2,30** |

Cálculo de A2: 0,30 × 5 + 0,25 × 5 + 0,20 × 4 + 0,15 × 5 + 0,10 × 4 = 4,70.

## 5. Decisión

**Se adopta A2: monolito modular con arquitectura hexagonal en cada módulo, desplegado en dos procesos (API y Sincronizador) sobre una base de datos PostgreSQL con un esquema por módulo.**

## 6. Justificación

La elección no se basa en la popularidad del estilo, sino en su ajuste a las condiciones de la universidad:

1. **C04 se garantiza con una transacción local.** Con A2, el descuento del cupo, la inscripción, el evento de sincronización y la auditoría se confirman juntos en PostgreSQL (atomicidad; Haerder y Reuter, 1983). A3 obligaría a repartir el invariante entre servicios y a coordinar transacciones distribuidas, con un costo y un riesgo que el driver de mayor prioridad no tolera.
2. **El Escenario A exige aislar al legado, no distribuir todo el sistema.** El único componente con un perfil de fallo distinto es la integración con el legado. A2 lo aísla en un proceso aparte (Sincronizador) y con una regla de dependencia (DEP-03): la API no tiene forma de llamar al legado. Se obtiene el beneficio de aislamiento de A3 en el único punto donde hace falta.
3. **El equipo puede operarlo.** Cuatro desarrolladores y un administrador pueden mantener dos procesos de una misma base de código, Nginx y PostgreSQL con réplica. No pueden operar con garantías un conjunto de microservicios, un broker y un orquestador, que además tendrían que instalar y mantener en infraestructura propia por C08. La ley de Conway (Conway, 1968) indica que un solo equipo produce, de forma natural, un solo sistema cohesionado.
4. **La modificabilidad se consigue con fronteras de módulo verificables.** Las reglas de dependencia (DEP-01 a DEP-04) se comprueban automáticamente en la integración continua (Actividad 5), lo que reduce el riesgo de que el monolito se degrade en un "gran barro" sin estructura (Foote y Yoder, 1997).

## 7. Consecuencias

### Positivas
- Consistencia fuerte de cupos sin coordinación distribuida.
- Una sola base de código, un solo flujo de integración continua y un solo modelo de despliegue.
- La falla o lentitud del legado no consume recursos de la API.
- Las pruebas de los casos de uso pueden ejecutarse con adaptadores en memoria, sin infraestructura.

### Negativas
- Los módulos de la API escalan juntos: no es posible asignar más recursos solo al módulo de inscripciones.
- La base de datos es compartida, por lo que una consulta costosa de un módulo puede afectar a los demás.
- Un error grave en un módulo puede afectar a todo el proceso de la API, aunque las dos instancias atenúan el efecto.

### Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Erosión de las fronteras entre módulos con el tiempo. | Pruebas de arquitectura automáticas y bloqueantes en cada Pull Request (Actividad 5). |
| La base de datos se convierte en cuello de botella en el pico. | Pool de conexiones acotado, limitación de tasa en Nginx, consultas de oferta separadas de la escritura y prueba de carga antes de cada matrícula. |
| La base de datos es un único punto de falla. | Réplica en espera y archivado continuo (QAS-05). |

## 8. Condiciones para revisar la decisión

- La concurrencia sostenida supera 3 veces la de C01 (más de 3.600 usuarios) y la prueba de carga muestra que la API o PostgreSQL ya no cumplen C02 con escalamiento vertical.
- El equipo crece a más de un equipo independiente, o se asignan equipos distintos a módulos distintos.
- La universidad autoriza servicios administrados o una plataforma de orquestación, eliminando la restricción RES-01.
- Se retira el sistema legado y PIA pasa a ser la fuente oficial del historial, lo que cambia el perfil de integración.

## 9. Referencias

- Buschmann, F. et al. (1996). *Pattern-Oriented Software Architecture, Vol. 1*. Wiley.
- Cockburn, A. (2005). *Hexagonal architecture (Ports and Adapters)*.
- Conway, M. (1968). How do committees invent? *Datamation, 14*(4).
- Deutsch, P. (1994). *The Eight Fallacies of Distributed Computing*. Sun Microsystems.
- Foote, B. y Yoder, J. (1997). Big Ball of Mud. *Pattern Languages of Program Design 4 (PLoP)*.
- Haerder, T. y Reuter, A. (1983). Principles of transaction-oriented database recovery. *ACM Computing Surveys, 15*(4).
- Lewis, J. y Fowler, M. (2014). *Microservices*. martinfowler.com.
- Parnas, D. (1972). On the criteria to be used in decomposing systems into modules. *CACM, 15*(12).
