**Estudiante:** Camilo Andrés López Hernández — **Documento:** 1233691138

# Registro de deuda técnica

Procedimiento: [Actividad 5, sección 6.3](../actividad5.md).

| ID | Descripción | Origen | Impacto (driver afectado) | Severidad | Responsable | Fecha objetivo | Estado |
|---|---|---|---|---|---|---|---|
| DT-001 | La conmutación de PostgreSQL es manual. | Decisión consciente (TAC-05) por la capacidad del equipo (RES-02). | QAS-05: el RTO depende de la disponibilidad del administrador. | Media | Administrador de infraestructura | Revisión posterior a la primera matrícula | Abierta |
| DT-002 | Un solo proxy Nginx sin dirección virtual redundante. | Alcance de TAC-05. | QAS-01 / C03: punto único de falla mitigado solo con reinicio automático. | Media | Administrador de infraestructura | Revisión posterior a la primera matrícula | Abierta |
| DT-003 | Las reglas POL-02 y POL-03 se verifican hoy solo sobre la documentación; las pruebas ArchUnit y de catálogo se activan con el primer módulo de código. | Fase de propuesta (sin código). | QAS-02, QAS-07 | Alta | Líder técnico | Primer sprint de construcción | Abierta |
