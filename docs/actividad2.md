**Estudiante:** Camilo Andrés López Hernández — **Documento:** 1233691138

# Actividad 2. Diseño de la estructura arquitectónica

La estructura que se propone responde a los drivers priorizados en la [Actividad 1](actividad1.md), en este orden:

1. QAS-02, integridad de cupos.
2. QAS-01, disponibilidad ante la falla del legado (Escenario A).
3. QAS-03, no duplicación.
4. QAS-04, rendimiento de consultas.
5. QAS-05, recuperabilidad.
6. QAS-06, seguridad y trazabilidad.
7. QAS-07, modificabilidad.

También responde a las restricciones RES-01 a RES-04.

Los diagramas siguen el modelo C4 (Brown, 2018). Sus fuentes están en texto PlantUML (`.puml`), versionadas en [docs/diagramas/](diagramas/), y cada una se exporta en SVG (vectorial) y en PNG.

---

## 1. Selección del estilo arquitectónico

### 1.1 Alternativas consideradas

| Alternativa | Descripción |
|---|---|
| A1. Monolito en capas | Una sola aplicación organizada en capas horizontales: presentación, negocio y datos. Cada capa solo usa a la inferior (Buschmann et al., 1996). |
| A2. Monolito modular con arquitectura hexagonal | Una sola base de código dividida en módulos verticales por subdominio (oferta, inscripciones, reglas, historial, auditoría, integración). Dentro de cada módulo, el dominio queda en el centro y se comunica con el exterior solo mediante puertos (interfaces) y adaptadores (Cockburn, 2005). Los módulos solo se comunican a través de sus interfaces públicas (Parnas, 1972). |
| A3. Microservicios | Servicios desplegables por separado, cada uno con su propia base de datos, comunicados por red (Lewis y Fowler, 2014). |

La arquitectura limpia (Martin, 2017) se consideró una variante de A2: comparte la regla de que las dependencias apuntan hacia el dominio. Se prefirió la formulación hexagonal porque el problema central de PIA es aislar al dominio de sistemas externos que fallan, como el legado y el proveedor de identidad, y el concepto de puerto y adaptador modela eso directamente con menos capas que mantener.

### 1.2 Comparación según los drivers

Escala: ++ favorece claramente, + favorece, 0 neutro, − perjudica, −− perjudica claramente.

| Criterio (driver) | A1. Capas | A2. Modular + hexagonal | A3. Microservicios |
|---|---|---|---|
| QAS-02 Integridad de cupos: transacción local sobre cupo, inscripción y auditoría | ++ Una base de datos y una transacción. | ++ Una base de datos y una transacción. | −− El cupo y la inscripción quedan en servicios distintos; hace falta coordinación distribuida (sagas o dos fases). |
| QAS-01 Aislamiento de la falla del legado | − La integración queda mezclada con la lógica de negocio. | ++ El legado queda detrás de un puerto; se puede sacar a un proceso aparte sin cambiar el dominio. | + Se aísla en un servicio, pero sumando otros puntos de falla de red. |
| QAS-04 Rendimiento | + Llamadas en memoria. | + Llamadas en memoria entre módulos. | − Cada consulta atraviesa varios saltos de red (Deutsch, 1994). |
| QAS-07 Modificabilidad de reglas | − Las reglas se dispersan en la capa de negocio. | ++ Las reglas son un módulo con un puerto propio. | + Aisladas, pero cada cambio puede afectar contratos entre servicios. |
| RES-02 Operable por 4 desarrolladores y 1 administrador | ++ Un despliegue. | + Dos procesos de la misma base de código. | −− Muchos despliegues, bases de datos, monitoreo distribuido y probablemente un orquestador. |
| RES-01 Linux, PostgreSQL y sin servicios comerciales | ++ | ++ | − En la práctica requiere broker, descubrimiento de servicios y orquestación que habría que operar en infraestructura propia. |
| Gobernanza: reglas de dependencia verificables automáticamente | − Solo se controla la dirección entre capas. | ++ Reglas de módulo y de hexágono verificables con pruebas de arquitectura (ver Actividad 5). | + Los límites los fija la red, pero el contrato entre servicios exige otra gobernanza. |

### 1.3 Decisión

**Se selecciona A2: un monolito modular con arquitectura hexagonal en cada módulo, desplegado en dos procesos de la misma base de código.**
- Un proceso **API**, en dos instancias, atiende a los usuarios.
- Un proceso **Sincronizador** ejecuta la integración con el legado.

Justificación:
1. **El driver de mayor prioridad, QAS-02, exige atomicidad local.** El cupo, la inscripción, el registro de idempotencia, el evento de sincronización y la auditoría se confirman o anulan juntos en una sola transacción de PostgreSQL (Haerder y Reuter, 1983). Ninguna alternativa distribuida da esa garantía con menor costo.
2. **El segundo driver, QAS-01, exige que ninguna operación de usuario dependa de forma síncrona del legado** (Actividad 1, sección 4.1). Con los puertos y adaptadores, el legado solo se toca desde el adaptador del Sincronizador. Ejecutarlo en un proceso aparte impide que sus esperas, reintentos o caídas consuman hilos o conexiones de la API.
3. **Es lo que el equipo puede operar (RES-02).** Se despliegan dos procesos de una misma base de código más PostgreSQL, sin brokers ni orquestadores. Esto también respeta la ley de Conway (Conway, 1968): un solo equipo pequeño mantiene un solo producto.
4. **Las fronteras de módulo dan la modificabilidad de QAS-07 sin pagar el costo de la red.** Esas fronteras se hacen cumplir con pruebas automáticas de arquitectura (Actividad 5).

La decisión se documenta formalmente en el ADR-001 ([Actividad 3](actividad3/)).

### 1.4 Tecnologías propuestas

Todas son de código abierto y se ejecutan sobre Linux (RES-01).

| Elemento | Tecnología | Justificación |
|---|---|---|
| API y Sincronizador | Java 21 (LTS) con Spring Boot 3 | Soporte de largo plazo, gestión transaccional declarativa sobre PostgreSQL y bibliotecas maduras para los mecanismos que exigen los drivers: Resilience4j (interruptor de circuito, tiempos de espera), Flyway (migraciones) y ArchUnit (pruebas de arquitectura). Habría que revisarla si la experiencia del equipo institucional está en otro ecosistema. |
| Interfaz web | Aplicación de una sola página (React) servida como archivos estáticos | No necesita servidor de aplicaciones propio y se puede almacenar en caché. |
| Proxy inverso y balanceo de carga | Nginx | Terminación TLS, balanceo entre las instancias de la API, limitación de tasa y servicio de archivos estáticos con un solo componente. |
| Base de datos | PostgreSQL 16 con réplica en espera (replicación en flujo) y archivado del registro de transacciones con pgBackRest | Ya es parte de la infraestructura (C08). La réplica y el archivado continuo cubren el RTO de 30 minutos y el RPO de 5 minutos (QAS-05). |
| Autenticación | Proveedor de identidad institucional mediante OpenID Connect | Reutiliza la cuenta institucional y evita almacenar credenciales en PIA (QAS-06). |

---

## 2. Nivel 1: diagrama de contexto

![Diagrama de contexto C4](diagramas/c4-nivel1-contexto.svg)

Fuente: [c4-nivel1-contexto.puml](diagramas/c4-nivel1-contexto.puml) · [PNG](diagramas/c4-nivel1-contexto.png)

### 2.1 Actores

| Actor | Interés en PIA | Driver relacionado |
|---|---|---|
| Estudiante | Consultar la oferta, inscribir y cancelar asignaturas, y conocer el estado real de sus solicitudes, incluso durante una falla del legado. | QAS-01, QAS-02, QAS-03, QAS-04 |
| Funcionario de registro académico | Configurar el período, las fechas de inscripción y la capacidad autorizada de los grupos; atender reclamaciones. | QAS-02, QAS-06 |
| Auditor o control interno | Reconstruir quién hizo qué operación y cuándo. | QAS-06 |

### 2.2 Sistemas externos

| Sistema | Relación con PIA | Por qué queda fuera del límite de PIA |
|---|---|---|
| Sistema académico legado | Le entrega a PIA la oferta del período y el historial académico, y recibe de PIA las inscripciones y cancelaciones para su registro oficial. | La restricción RES-03 lo mantiene como fuente oficial; PIA no lo reemplaza ni es dueño de sus datos. Su disponibilidad no depende de PIA (C05). |
| Proveedor de identidad institucional | Autentica a los usuarios. | Ya existe en la universidad; reutilizarlo cumple RES-01 y QAS-06 sin gestionar credenciales propias. |
| Servidor de correo institucional | Entrega notificaciones de confirmación o rechazo. | Servicio institucional existente. |

### 2.3 Decisión de frontera más relevante

El legado queda **fuera** del sistema y la relación con él es **asíncrona**. Las operaciones de usuario nunca esperan una respuesta del legado. El Sincronizador intercambia datos con él en segundo plano, que es la condición necesaria para cumplir QAS-01.
