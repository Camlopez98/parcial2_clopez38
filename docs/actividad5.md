**Estudiante:** Camilo Andrés López Hernández — **Documento:** 1233691138

# Actividad 5. Gobernanza de arquitectura

## 1. Propósito y enfoque

La gobernanza de arquitectura busca que las decisiones tomadas (Actividades 1 a 4) se mantengan mientras el software evoluciona. Las leyes de evolución del software indican que un sistema en uso cambia continuamente y que su complejidad crece salvo que se trabaje activamente para reducirla (Lehman, 1980). Sin mecanismos de control, el monolito modular del ADR-001 tendería a degradarse en un sistema sin estructura (Foote y Yoder, 1997).

El modelo que se propone es **liviano y automatizado**, proporcional al equipo institucional de cuatro desarrolladores y un administrador de infraestructura (C10):

- **Pocas reglas, todas verificables.** Una regla es verificable si existe una prueba que puede declararla incumplida (criterio de falsabilidad; Popper, 1959). Cada política de este documento tiene un mecanismo de verificación y un responsable.
- **Verificación automática antes que revisión manual.** Las reglas se expresan como *funciones de aptitud arquitectónica*: pruebas automáticas y objetivas de una característica de la arquitectura, que se ejecutan en cada cambio (Ford, Parsons y Kua, 2017).
- **Documentación como código.** Los ADR, los diagramas (fuentes PlantUML) y las reglas viven en el mismo repositorio que el software y se revisan en las mismas solicitudes de integración (Pull Requests).
- **Responsables con nombre de rol** y procedimientos para proponer, decidir, exceptuar y corregir, siguiendo el marco de partes interesadas y responsabilidades de ISO/IEC/IEEE 42010:2022.

---

## 2. Políticas arquitectónicas verificables

| ID | Política | Origen | Cómo se verifica (hoy, sobre los modelos) | Cómo se verifica (cuando exista código) | Responsable de la regla |
|---|---|---|---|---|---|
| **POL-01** | **Aislamiento del legado.** Solo el Sincronizador y su adaptador anticorrupción se comunican con el sistema legado. Ningún componente que atienda solicitudes de usuario puede depender del legado. | ADR-003, DEP-03, QAS-01 (Escenario A) | El script `scripts/verificar_reglas.py` (regla R1) analiza los modelos C4 (`docs/diagramas/c4-*.puml`) y falla si existe una relación con el legado cuyo origen no sea el Sincronizador o, en el diagrama de contexto, el sistema PIA completo. | Prueba ArchUnit: ninguna clase de los paquetes `..api..`, `..inscripciones..`, `..oferta..` o `..reglas..` puede depender de `..integracion.legado..` (sección 5.3). | Líder técnico |
| **POL-02** | **Fronteras de módulo.** (a) El paquete `dominio` de cada módulo no depende de Spring, JPA ni de otros módulos. (b) Un módulo solo usa el paquete `api` de otro módulo. (c) No hay ciclos entre módulos. | ADR-001, DEP-01, DEP-02, DEP-04, QAS-07 | Revisión del diagrama de componentes en la solicitud de integración. | Pruebas ArchUnit de capas, de acceso entre paquetes y `slices().beFreeOfCycles()` (sección 5.3). | Líder técnico |
| **POL-03** | **Integridad de cupos protegida.** (a) La restricción `ck_cupo` (`inscritos <= capacidad`) y el índice único de inscripciones activas existen siempre en el esquema. (b) Solo el componente Control de cupos modifica `inscritos`. (c) La prueba de concurrencia V-03.1 (300 solicitudes sobre 10 cupos) es obligatoria y bloqueante. | ADR-002, TAC-03, QAS-02, C04 | Regla de documentación: el ADR-002 debe permanecer en estado *Aceptado* mientras no exista un ADR que lo reemplace (regla R2). | Prueba de integración que inspecciona el catálogo de PostgreSQL (`pg_constraint`) y falla si `ck_cupo` no existe; prueba ArchUnit sobre escrituras de `inscritos`; prueba V-03.1 en la integración continua. | Líder técnico y administrador de infraestructura (migraciones) |
| **POL-04** | **Decisiones y diagramas versionados.** Toda decisión significativa (sección 3.2) tiene un ADR con la estructura de la plantilla. Todo diagrama tiene su fuente `.puml` y sus versiones SVG y PNG. Todo documento de actividad empieza con el nombre y documento del autor. | Actividad 3, Actividad 2, enunciado | Script `verificar_reglas.py` (reglas R2, R3 y R4) y prueba de compilación de los diagramas en la integración continua. | Igual. | Autor del cambio y líder técnico |

---

## 3. Responsables y aprobación de cambios significativos

### 3.1 Roles

| Rol | Quién lo ejerce en el equipo institucional | Responsabilidades de gobernanza |
|---|---|---|
| **Líder técnico (arquitecto de referencia)** | Uno de los cuatro desarrolladores, designado por la coordinación de sistemas por un año, con posibilidad de renovación. | Custodia las políticas POL-01 a POL-04. Aprueba los cambios en rutas protegidas (archivo `CODEOWNERS`). Convoca y preside el comité de arquitectura. Mantiene el registro de excepciones y de deuda técnica. |
| **Administrador de infraestructura** | El administrador del equipo (C10). | Aprueba los cambios que afectan despliegue, base de datos, réplica, respaldos o seguridad de la infraestructura. Ejecuta las pruebas de preproducción de la Actividad 4. |
| **Desarrolladores** | Los otros tres desarrolladores. | Proponen ADR. Revisan solicitudes de integración entre pares. Corrigen los incumplimientos que detecta la integración continua. Uno de ellos integra el comité por rotación semestral. |
| **Representante de registro académico** | Funcionario designado por la oficina de registro. | Participa con voz y voto cuando la decisión cambia reglas académicas, la experiencia del estudiante durante la matrícula o los escenarios de calidad. |
| **Comité de arquitectura (CA)** | Líder técnico, administrador de infraestructura y el desarrollador rotativo. El representante de registro académico se suma cuando aplica. | Decide los ADR de cambios significativos. Revisa las excepciones a POL-01 y POL-03. Hace la revisión de arquitectura posterior a cada matrícula. Sesiona cada dos semanas (30 minutos) y de forma extraordinaria ante un incidente. |

### 3.2 Qué es un cambio significativo

Requiere un ADR aprobado por el comité cualquier cambio que:
1. modifique el estilo arquitectónico, agregue o elimine un contenedor, o cambie la forma en que se comunican (ADR-001);
2. cambie los límites transaccionales T1 a T4 o el mecanismo de control de cupos (ADR-002);
3. cambie la integración con el legado, los estados de la inscripción o la copia del historial (ADR-003, ADR-004);
4. incorpore una tecnología, biblioteca de infraestructura o servicio nuevo, que debe ser libre y operable por el equipo (RES-01, RES-02);
5. modifique una política POL-01 a POL-04 o una medida de los escenarios de calidad de la Actividad 1.

Los demás cambios, como funcionalidades dentro de un módulo, reglas académicas nuevas en el módulo de reglas o correcciones, siguen el flujo normal de solicitud de integración (sección 7).

### 3.3 Matriz de responsabilidades (RACI)

R = responsable de ejecutar, A = aprueba, C = consultado, I = informado.

| Actividad | Líder técnico | Admin. infraestructura | Desarrolladores | Registro académico | Comité |
|---|---|---|---|---|---|
| Proponer un ADR | C | C | R | C | I |
| Aprobar un ADR de cambio significativo | R | C (A si afecta infraestructura) | C | C (A si afecta reglas académicas) | **A** |
| Aprobar una solicitud de integración en rutas protegidas | **A** | A (infraestructura) | R | I | I |
| Aprobar una excepción a POL-01 o POL-03 | R | C | C | I | **A** |
| Aprobar una excepción a POL-02 o POL-04 | **A** | I | R | I | I |
| Priorizar la deuda técnica | **A** | C | R | C | I |
| Revisión de arquitectura posterior a la matrícula | R | R | C | C | **A** |

---

## 4. Procedimiento para proponer, revisar, aprobar y actualizar un ADR

### 4.1 Estados de un ADR

`Propuesto` → `En revisión` → `Aceptado` o `Rechazado`. Un ADR aceptado puede pasar después a `Reemplazado por ADR-XXX` u `Obsoleto`.

Un ADR aceptado **no se edita en su decisión**: se reemplaza por uno nuevo, de modo que el historial de razonamiento se conserva (Nygard, 2011). Solo se permiten correcciones de forma, como erratas o enlaces.

### 4.2 Procedimiento

| Paso | Qué se hace | Quién | Plazo |
|---|---|---|---|
| 1. Proponer | Se crea una rama `adr/NNN-titulo-corto` y un archivo `docs/actividad3/ADR-NNN-titulo.md` a partir de la [plantilla](gobernanza/plantilla-adr.md), en estado `Propuesto`. Debe incluir el driver relacionado, al menos dos alternativas, criterios, consecuencias y condiciones de revisión. | Cualquier desarrollador | — |
| 2. Abrir la solicitud de integración | Se abre la solicitud hacia la rama principal con la etiqueta `adr`. La integración continua verifica la estructura del ADR (regla R2) y, si el ADR cambia la estructura, que los diagramas se hayan actualizado (regla R4). El estado cambia a `En revisión`. | Autor | — |
| 3. Revisar | Los miembros del comité y los consultados comentan en la solicitud. Se puede pedir evidencia, por ejemplo un prototipo o una prueba de carga. | Comité y consultados | 3 días hábiles |
| 4. Decidir | El comité decide en su sesión. Se requiere el voto del líder técnico y de al menos otro miembro. Es obligatorio el voto del administrador si afecta infraestructura, y del representante de registro si afecta reglas o la experiencia del estudiante. La decisión y sus motivos se registran como comentario en la solicitud. | Comité | Siguiente sesión (≤ 2 semanas) |
| 5. Integrar | Si se acepta, el estado cambia a `Aceptado` con la fecha, y se integra junto con los diagramas y documentos afectados. Si se rechaza, se integra igualmente en estado `Rechazado`, para dejar constancia de por qué no se eligió esa opción. | Autor y líder técnico | — |
| 6. Actualizar o reemplazar | Cuando se cumple una de las *condiciones para revisar la decisión* del ADR, o en la revisión posterior a cada matrícula, se crea un ADR nuevo que referencia al anterior. El anterior pasa a `Reemplazado por ADR-NNN`. | Líder técnico | Revisión posterior a cada matrícula |

### 4.3 Revisión periódica

Después de cada período de matrícula, el comité revisa en una sesión de 1 hora:
- los indicadores de producción de la Actividad 4 (V-01.4, V-02.5, V-03.5, V-04.4, V-05.5);
- las condiciones de revisión de cada ADR;
- las excepciones vencidas;
- la deuda técnica.

El resultado es un acta en `docs/gobernanza/revisiones/<período>.md` con las decisiones de mantener o reemplazar cada ADR.

---

## Referencias (secciones 1 a 4)

- Foote, B. y Yoder, J. (1997). Big Ball of Mud. *Pattern Languages of Program Design 4*.
- Ford, N., Parsons, R. y Kua, P. (2017). *Building Evolutionary Architectures: Support Constant Change*. O'Reilly.
- ISO/IEC/IEEE 42010:2022. *Software, systems and enterprise — Architecture description*.
- Lehman, M. M. (1980). Programs, life cycles, and laws of software evolution. *Proceedings of the IEEE, 68*(9), 1060–1076.
- Nygard, M. (2011). *Documenting Architecture Decisions*. cognitect.com.
- Popper, K. (1959). *The Logic of Scientific Discovery*. Hutchinson.
