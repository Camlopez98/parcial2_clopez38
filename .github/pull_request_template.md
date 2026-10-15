## Descripción del cambio

<!-- Qué cambia y por qué. Enlazar el issue o el ADR relacionado. -->

## Tipo de cambio

- [ ] Funcionalidad dentro de un módulo
- [ ] Regla académica nueva o modificada
- [ ] Corrección
- [ ] Cambio significativo de arquitectura (requiere ADR aprobado por el comité, sección 3.2 de la Actividad 5)
- [ ] Documentación

## Lista de verificación (criterios de aceptación, sección 7 de la Actividad 5)

- [ ] Las verificaciones automáticas (`Verificación de reglas arquitectónicas` y `Pruebas automatizadas`) están en verde.
- [ ] No se introduce ninguna dependencia del sistema legado fuera del Sincronizador (POL-01).
- [ ] Se respetan las fronteras de módulo y no se crean ciclos (POL-02).
- [ ] Si toca cupos o inscripciones: la prueba de concurrencia V-03.1 pasa y no se alteran `ck_cupo` ni el índice único (POL-03).
- [ ] Si cambia contenedores, componentes, comunicación o transacciones: se actualizaron los `.puml` y sus SVG y PNG, y el ADR correspondiente (POL-04).
- [ ] Se agregaron o actualizaron las pruebas del comportamiento nuevo.
- [ ] Toda excepción a una política está registrada con su identificador `EXC-NNN`.
- [ ] No se agregan dependencias con licencia comercial (RES-01).
