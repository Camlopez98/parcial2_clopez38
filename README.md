# Parcial 2 — Propuesta de Arquitectura: Plataforma de Inscripción Académica (PIA)

**Estudiante:** Camilo Andrés López Hernández — **Documento:** 1233691138

[![Verificación de reglas arquitectónicas](https://github.com/Camlopez98/parcial2_clopez38/actions/workflows/verificacion-arquitectura.yml/badge.svg?branch=dev_clopez38)](https://github.com/Camlopez98/parcial2_clopez38/actions/workflows/verificacion-arquitectura.yml)
[![Pruebas automatizadas](https://github.com/Camlopez98/parcial2_clopez38/actions/workflows/pruebas-automatizadas.yml/badge.svg?branch=dev_clopez38)](https://github.com/Camlopez98/parcial2_clopez38/actions/workflows/pruebas-automatizadas.yml)

## Resumen ejecutivo

La Universidad de La Salle (24.000 estudiantes) necesita reemplazar el proceso de inscripción de asignaturas de su sistema académico legado. Ese proceso falla con accesos simultáneos, genera inscripciones duplicadas y sobrecupos, y depende en línea del legado para consultar prerrequisitos. Esta propuesta define la arquitectura de la nueva **Plataforma de Inscripción Académica (PIA)** y se centra en la situación extraordinaria asignada: el **Escenario A**, en el que el legado deja de responder durante 40 minutos al iniciar la matrícula.

**Hallazgo central.** El 99,9 % de disponibilidad exigido (C03) permite solo **43,2 minutos** de indisponibilidad al mes. Una sola caída de 40 minutos del legado (C05) consumiría el 92,6 % de ese margen si PIA dependiera de él de forma síncrona. Por eso la arquitectura **desacopla por completo la disponibilidad de PIA de la del legado**, sin generar confirmaciones incorrectas ni registros duplicados.

**Decisiones principales:**

| Decisión | Resumen | ADR |
|---|---|---|
| Estilo | Monolito modular con arquitectura hexagonal, desplegado en dos procesos: una API con dos instancias y un Sincronizador, sobre PostgreSQL. Se descartan los microservicios por la atomicidad que exige C04 y por la capacidad del equipo (C10). | [ADR-001](docs/actividad3/ADR-001-estilo-arquitectonico.md) |
| Consistencia de cupos | Actualización condicional atómica (`UPDATE … WHERE inscritos < capacidad`) con `CHECK` en la base de datos, índice único parcial y claves de idempotencia, todo en una transacción local. | [ADR-002](docs/actividad3/ADR-002-consistencia-cupos-inscripciones.md) |
| Integración con el legado | Bandeja de salida transaccional y un Sincronizador aislado con interruptor de circuito, reintentos con espera exponencial y consulta de existencia antes de registrar. La inscripción solo es *confirmada* cuando el legado la registra. | [ADR-003](docs/actividad3/ADR-003-integracion-sistema-legado.md) |
| Prerrequisitos sin el legado | Copia local del historial, cargada antes de abrir la matrícula y refrescada cada 15 minutos, con marca de vigencia por estudiante. | [ADR-004](docs/actividad3/ADR-004-validacion-prerrequisitos-copia-local.md) |

**Durante los 40 minutos sin legado:**
- Continúan la consulta, la inscripción (con cupo reservado en estado *pendiente de sincronización*), la cancelación y la consulta de estado.
- Se restringen solo las inscripciones de estudiantes cuya copia del historial no está vigente.
- El estudiante ve un aviso explícito de que su inscripción aún no es oficial.
- Al recuperarse el legado, lo pendiente se sincroniza en unos 10 minutos, sin duplicados, y se ejecuta una conciliación.

## Navegación de la documentación

| Actividad | Entregable | Contenido |
|---|---|---|
| 1. Drivers arquitectónicos | [docs/actividad1.md](docs/actividad1.md) | Objetivos de negocio, restricciones y supuestos, 7 escenarios de calidad con medidas, árbol de utilidad, 4 conflictos entre drivers y matriz consolidada. |
| 2. Estructura arquitectónica (C4) | [docs/actividad2.md](docs/actividad2.md) y [docs/diagramas/](docs/diagramas/) | Selección del estilo; diagramas de contexto, contenedores y componentes; límites transaccionales; reglas de dependencia; máquina de estados y diagrama dinámico del Escenario A. |
| 3. Registros de decisiones (ADR) | [docs/actividad3/](docs/actividad3/) | ADR-001 a ADR-004. |
| 4. Tácticas arquitectónicas | [docs/actividad4.md](docs/actividad4.md) | 5 tácticas con alcance y verificación numérica, y plan de verificación por ambiente. |
| 5. Gobernanza de arquitectura | [docs/actividad5.md](docs/actividad5.md) y [docs/gobernanza/](docs/gobernanza/) | Políticas verificables, responsables, procedimiento de ADR, controles automáticos, excepciones, deuda técnica y criterios de aceptación de solicitudes de integración. |

**Diagramas** (fuente PlantUML, SVG y PNG):
- [Contexto](docs/diagramas/c4-nivel1-contexto.svg)
- [Contenedores](docs/diagramas/c4-nivel2-contenedores.svg)
- [Componentes](docs/diagramas/c4-nivel3-componentes-inscripciones.svg)
- [Estados de la inscripción](docs/diagramas/estados-inscripcion.svg)
- [Secuencia del Escenario A](docs/diagramas/secuencia-escenario-a.svg)

**Orden de lectura sugerido:** este resumen → Actividad 1 → Actividad 2 → ADR → Actividad 4 → Actividad 5.

## Tecnologías

| Ámbito | Tecnología | Por qué |
|---|---|---|
| Plataforma propuesta | Java 21 y Spring Boot 3, React, Nginx, PostgreSQL 16 con réplica en espera, pgBackRest, Resilience4j, Flyway | Software libre sobre Linux y PostgreSQL (C08), operable por el equipo institucional (C10). |
| Verificación propuesta | ArchUnit, JUnit con Testcontainers, k6, Toxiproxy, WireMock, Micrometer con Prometheus | Validación de reglas y tácticas (Actividades 4 y 5). |
| Documentación | Markdown, modelo C4 con PlantUML (C4-PlantUML) | Diagramas como código, versionados con la solución. |
| Controles del repositorio | GitHub Actions, Python 3.12 y pytest, PlantUML 1.2024.7 | Verificación automática de reglas arquitectónicas y pruebas (Actividad 5). |

## Verificación local

```bash
python scripts/verificar_reglas.py   # reglas arquitectónicas R1-R4
pip install pytest && python -m pytest -v   # pruebas automatizadas
```

## Estructura del repositorio

```
├── README.md
├── docs/
│   ├── actividad1.md … actividad5.md
│   ├── actividad3/        ADR-001 … ADR-004
│   ├── diagramas/         fuentes .puml y exportaciones .svg / .png
│   └── gobernanza/        plantilla de ADR, registro de excepciones y de deuda técnica
├── scripts/verificar_reglas.py
├── tests/                 pruebas automatizadas (pytest)
└── .github/               workflows, CODEOWNERS y plantilla de Pull Request
```
