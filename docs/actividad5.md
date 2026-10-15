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
| **POL-03** | **Integridad de cupos protegida.** (a) La restricción `ck_cupo` (`inscritos <= capacidad`) y el índice único de inscripciones activas existen siempre en el esquema. (b) Solo el componente Control de cupos modifica `inscritos`. (c) La prueba de concurrencia V-03.1 (300 solicitudes sobre 10 cupos) es obligatoria y bloqueante. | ADR-002, TAC-03, QAS-02, C04 | Script `verificar_reglas.py` (regla R5): falla si el ADR-002 deja de estar *Aceptado* sin haber sido reemplazado, si desaparece la restricción `CHECK (inscritos <= capacidad)` o si el modelo de componentes pierde el componente Control de cupos. | Prueba de integración que inspecciona el catálogo de PostgreSQL (`pg_constraint`) y falla si `ck_cupo` no existe; prueba ArchUnit sobre escrituras de `inscritos`; prueba V-03.1 en la integración continua. | Líder técnico y administrador de infraestructura (migraciones) |
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

---

## 5. Mecanismos de control automático integrados al repositorio

Los controles están implementados y se ejecutan con GitHub Actions en cada `push` y en cada solicitud de integración. Sus resultados se ven en la pestaña **Actions** del repositorio y como verificaciones dentro de cada solicitud.

| Control | Archivo | Qué verifica | Política |
|---|---|---|---|
| **Control 1. Verificación de reglas arquitectónicas** | [`.github/workflows/verificacion-arquitectura.yml`](../.github/workflows/verificacion-arquitectura.yml) → [`scripts/verificar_reglas.py`](../scripts/verificar_reglas.py) | R1: ningún elemento distinto del Sincronizador se relaciona con el legado en los modelos C4. R2: estructura y estado de los ADR. R3: nombre y documento en cada entregable. R4: cada `.puml` tiene sus versiones SVG y PNG. R5: siguen vigentes la decisión, la restricción de capacidad y el componente que protegen C04. | POL-01, POL-03, POL-04 |
| **Control 2. Pruebas automatizadas** | [`.github/workflows/pruebas-automatizadas.yml`](../.github/workflows/pruebas-automatizadas.yml) → [`tests/`](../tests/) | Pruebas unitarias del verificador, con casos positivos y negativos (por ejemplo, que detecte una relación `API → legado`). Pruebas de integridad de la documentación: enlaces e imágenes existentes, entregables mínimos y los tres niveles C4. Compilación de todos los diagramas PlantUML. | POL-01, POL-04 |

### 5.1 Control 1: la regla arquitectónica como función de aptitud

La regla R1 convierte la política POL-01 (que surge del Escenario A y del ADR-003) en una verificación ejecutable sobre el modelo de arquitectura:
1. El script lee las fuentes C4.
2. Identifica el elemento externo cuyo nombre contiene "legado".
3. Recorre todas las relaciones `Rel(origen, destino, ...)`.
4. Falla si alguna relación con el legado tiene un origen distinto del Sincronizador. La única excepción es el sistema PIA completo en el diagrama de contexto.

Por ejemplo, si un cambio agregara `Rel(api, legado, "Consulta prerrequisitos")` al diagrama de contenedores, la ejecución termina con código 1 y este mensaje:

```
Se encontraron 1 incumplimientos de reglas arquitectónicas:
  - R1 [c4-nivel2-contenedores.puml] 'api' se relaciona con el legado 'legado'; solo el Sincronizador puede hacerlo (POL-01).
```

La prueba `test_r1_rechaza_que_la_api_llame_al_legado` garantiza que el verificador sigue detectando ese caso.

### 5.2 Control 2: pruebas automatizadas

`pytest` ejecuta 27 pruebas en la versión actual:
- 13 sobre las reglas R1 a R5, con casos que deben pasar y casos que deben fallar;
- 14 sobre la documentación: una por cada documento Markdown, que comprueba sus enlaces e imágenes, más las de entregables mínimos y niveles C4.

El número crece automáticamente con cada documento nuevo.

Un trabajo paralelo compila los diagramas con PlantUML 1.2024.7 (`-checkonly -failfast2`), que termina con error si algún diagrama tiene un error de sintaxis o una inclusión inexistente.

### 5.3 Extensión de los controles cuando exista código

Cuando inicie la construcción, el mismo flujo de pruebas ejecutará `mvn verify`, que incluye las pruebas unitarias, las de integración con PostgreSQL real (Testcontainers) de la Actividad 4 (V-02.1 a V-03.4) y las pruebas de arquitectura con ArchUnit:

```java
@AnalyzeClasses(packages = "co.edu.unisalle.pia")
class ReglasArquitectura {
  // POL-01: solo el Sincronizador conoce al legado
  @ArchTest static final ArchRule aislamientoLegado = noClasses()
      .that().resideOutsideOfPackage("..sincronizador..")
      .should().dependOnClassesThat().resideInAPackage("..integracion.legado..");

  // POL-02 (a): el dominio no depende de frameworks
  @ArchTest static final ArchRule dominioPuro = noClasses()
      .that().resideInAPackage("..dominio..")
      .should().dependOnClassesThat().resideInAnyPackage("org.springframework..", "jakarta.persistence..");

  // POL-02 (c): sin ciclos entre módulos
  @ArchTest static final ArchRule sinCiclos = slices()
      .matching("co.edu.unisalle.pia.(*)..").should().beFreeOfCycles();

  // POL-03 (b): solo Control de cupos escribe el contador de inscritos
  @ArchTest static final ArchRule cuposCentralizados = noClasses()
      .that().resideOutsideOfPackage("..inscripciones.cupos..")
      .should().callMethod(GrupoRepositorio.class, "incrementarInscritos", Long.class);
}
```

### 5.4 Configuración de la rama protegida

Para que los controles **impidan** integrar un cambio, y no solo lo informen, la rama principal se configura en GitHub, en *Settings → Branches → Branch protection rules*:
- verificaciones obligatorias `Reglas R1-R5`, `Pruebas de reglas y de documentación` y `Compilación de los diagramas PlantUML`;
- al menos 1 aprobación;
- revisión de los propietarios de código ([`CODEOWNERS`](../.github/CODEOWNERS)) en las rutas protegidas;
- prohibición de `push` directo.

---

## 6. Excepciones, incumplimientos y deuda técnica

### 6.1 Procedimiento de excepción

Una excepción es una autorización temporal y explícita para no cumplir una política.

1. **Solicitud.** El desarrollador abre un *issue* con la etiqueta `excepcion-arquitectura` que indique: política afectada, alcance exacto (archivos o componentes), justificación, riesgo, medida compensatoria y fecha de vencimiento propuesta.
2. **Aprobación.**
   - Para POL-02 y POL-04, la aprueba el líder técnico en ≤ 2 días hábiles.
   - Para POL-01 y POL-03, que protegen los dos drivers de mayor prioridad, la aprueba el comité.
   - **No se aprueban excepciones a POL-03 (a)**, es decir, eliminar `ck_cupo` o el índice único, porque protegen la condición C04, que no admite excepciones.
3. **Registro.** La excepción aprobada se agrega al [registro de excepciones](gobernanza/registro-excepciones.md) con su identificador `EXC-NNN`. Cualquier supresión de una regla en el código (por ejemplo, `@ArchIgnore` o un archivo de congelamiento de ArchUnit) debe citar ese identificador en un comentario.
4. **Vencimiento.** Máximo un período académico. Al vencer, la excepción se corrige o se convierte en deuda técnica registrada; no se renueva automáticamente.

### 6.2 Manejo de incumplimientos

| Momento de detección | Qué ocurre | Responsable | Plazo |
|---|---|---|---|
| En la integración continua (antes de integrar) | La verificación falla y la rama protegida impide integrar. El autor corrige o solicita una excepción (6.1). | Autor | Antes de integrar |
| En revisión o auditoría posterior (por ejemplo, un cambio integrado sin pasar por los controles) | Se abre un *issue* con la etiqueta `incumplimiento` y se clasifica según la severidad (filas siguientes). | Líder técnico | — |
| Severidad crítica: afecta C04, la integridad de datos o POL-01 en producción | Corrección inmediata, análisis del incidente sin culpables en ≤ 5 días hábiles y nueva regla automática que lo habría detectado. | Comité | Inmediato |
| Severidad mayor | Corrección antes del siguiente período de matrícula. | Líder técnico | Antes de la próxima matrícula |
| Severidad menor | Se registra como deuda técnica (6.3). | Autor | Según priorización |

### 6.3 Deuda técnica

La deuda técnica es el costo futuro de un atajo tomado hoy (Cunningham, 1992); se gestiona de forma explícita (Kruchten, Nord y Ozkaya, 2019).

- **Registro:** [docs/gobernanza/deuda-tecnica.md](gobernanza/deuda-tecnica.md), con identificador, descripción, origen, driver afectado, severidad, responsable y fecha objetivo. Hoy contiene tres partidas conocidas (DT-001 a DT-003).
- **Capacidad reservada:** el 15 % de la capacidad de cada iteración se dedica a reducir deuda, priorizada por el líder técnico según el driver afectado.
- **Regla de corte antes de cada matrícula:** no puede quedar abierta ninguna deuda de severidad *alta* que afecte QAS-01, QAS-02 o QAS-03. Si queda alguna, el comité decide entre corregirla o aceptar el riesgo de forma documentada.
- **Revisión:** mensual, y en la revisión posterior a cada matrícula (sección 4.3).

---

## 7. Criterios para aceptar o rechazar una solicitud de integración (Pull Request)

### 7.1 Una solicitud de integración se **acepta** solo si cumple **todos** estos criterios

| # | Criterio | Cómo se comprueba |
|---|---|---|
| A1 | Las tres verificaciones automáticas están en verde: reglas R1-R5, pruebas automatizadas y compilación de los diagramas. Cuando exista código, también `mvn verify` con ArchUnit y las pruebas de integración. | Automático (rama protegida) |
| A2 | Tiene al menos 1 aprobación de un desarrollador distinto del autor. | Automático (rama protegida) |
| A3 | Si modifica rutas protegidas (`CODEOWNERS`), tiene la aprobación del líder técnico; si afecta infraestructura, también la del administrador. | Automático (`CODEOWNERS`) |
| A4 | Si es un cambio significativo (sección 3.2), incluye o referencia un ADR en estado `Aceptado`. | Revisión con la plantilla de la solicitud |
| A5 | Si cambia contenedores, componentes, comunicación o transacciones, incluye los `.puml` actualizados con sus SVG y PNG. | R4 automática más revisión |
| A6 | Incluye pruebas del comportamiento nuevo. Si toca cupos o inscripciones, la prueba V-03.1 pasa. | Revisión más integración continua |
| A7 | Toda supresión de una regla cita una excepción `EXC-NNN` vigente. | Revisión |
| A8 | Las dependencias nuevas tienen licencia libre (RES-01). | Revisión |
| A9 | Su tamaño permite revisarla: ≤ 400 líneas cambiadas, sin contar archivos generados como SVG o PNG, o con una justificación. | Revisión |

### 7.2 Una solicitud de integración se **rechaza** si ocurre **cualquiera** de estos casos

| # | Causa de rechazo | Política |
|---|---|---|
| X1 | Alguna verificación automática falla. | Todas |
| X2 | Introduce una comunicación con el legado desde un componente distinto del Sincronizador, o una llamada síncrona al legado en una operación de usuario. | POL-01 |
| X3 | Crea un ciclo entre módulos o accede a clases internas o a tablas de otro módulo. | POL-02 |
| X4 | Elimina o debilita `ck_cupo` o el índice único, o modifica `inscritos` fuera de Control de cupos. | POL-03 |
| X5 | Modifica la decisión de un ADR aceptado en lugar de reemplazarlo con uno nuevo. | POL-04 |
| X6 | Cambia la estructura sin actualizar diagramas ni ADR. | POL-04 |
| X7 | Agrega un servicio o dependencia comercial, o un componente que el equipo no puede operar, sin un ADR aprobado. | RES-01, RES-02 |

---

## 8. Estrategia para que la documentación y los diagramas evolucionen con la solución

1. **Un solo repositorio.** Documentación, ADR, fuentes de los diagramas, reglas y, más adelante, el código viven juntos y se versionan con las mismas solicitudes de integración. No existe una "versión de la documentación" aparte del software.
2. **Diagramas como código.** Las fuentes `.puml` son texto, así que sus cambios se revisan línea a línea. La integración continua comprueba que compilen y que tengan sus versiones SVG y PNG (R4).
3. **El modelo es verificable.** La regla R1 analiza el modelo C4 y, cuando exista código, ArchUnit verificará las mismas reglas sobre el código. Si el código y el diagrama divergen, una de las dos verificaciones falla.
4. **La lista de verificación de la solicitud obliga a la pregunta:** "¿Este cambio altera contenedores, componentes, comunicación o transacciones?". Si la respuesta es sí, el criterio A5 exige actualizar los diagramas en la misma solicitud.
5. **Definición de terminado:** una historia no está terminada si su cambio arquitectónico no se refleja en los diagramas y ADR correspondientes.
6. **Evidencias versionadas.** Los resultados de las pruebas de preproducción de la Actividad 4 (k6, simulacros, conciliaciones) se guardan en `docs/evidencias/<período>/`. Las medidas de los escenarios de calidad se actualizan con datos reales en la revisión posterior a cada matrícula.
7. **Versiones etiquetadas.** Al cerrar cada período de matrícula se crea una etiqueta de Git (por ejemplo, `arquitectura-2027-1`) que fija el estado de la documentación vigente durante ese período.

---

## Referencias (secciones 5 a 8)

- Cunningham, W. (1992). The WyCash portfolio management system. *OOPSLA '92 Experience Report*.
- Ford, N., Parsons, R. y Kua, P. (2017). *Building Evolutionary Architectures*. O'Reilly.
- Kruchten, P., Nord, R. y Ozkaya, I. (2019). *Managing Technical Debt: Reducing Friction in Software Development*. Addison-Wesley.
- Nygard, M. (2011). *Documenting Architecture Decisions*.
- TNG Technology Consulting (2024). *ArchUnit User Guide*. archunit.org.
