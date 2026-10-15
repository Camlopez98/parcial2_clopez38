"""Pruebas de las reglas arquitectónicas (POL-01 y POL-04)."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import verificar_reglas as vr  # noqa: E402

MODELO_VALIDO = '''
Container(api, "API PIA", "Java", "Atiende usuarios")
Container(sync, "Sincronizador", "Java", "Integra con el legado")
System_Ext(legado, "Sistema académico legado", "Fuente oficial")
Rel(api, db, "Lee y escribe", "SQL")
Rel(sync, legado, "Registra inscripciones", "Adaptador")
'''


def test_el_repositorio_cumple_todas_las_reglas():
    assert vr.verificar_repositorio(RAIZ) == []


def test_r1_acepta_que_el_sincronizador_use_el_legado():
    assert vr.verificar_aislamiento_legado(MODELO_VALIDO, "valido") == []


def test_r1_rechaza_que_la_api_llame_al_legado():
    modelo = MODELO_VALIDO + 'Rel(api, legado, "Consulta prerrequisitos", "HTTP")\n'
    errores = vr.verificar_aislamiento_legado(modelo, "invalido")
    assert len(errores) == 1 and "'api'" in errores[0]


def test_r1_rechaza_que_el_legado_llame_a_otro_contenedor():
    modelo = MODELO_VALIDO + 'Rel(legado, api, "Notifica", "HTTP")\n'
    assert len(vr.verificar_aislamiento_legado(modelo, "invalido")) == 1


def test_r1_acepta_al_sistema_pia_en_el_diagrama_de_contexto():
    modelo = '''
System(pia, "Plataforma de Inscripción Académica", "Sistema")
System_Ext(legado, "Sistema académico legado", "Fuente oficial")
Rel(pia, legado, "Sincroniza", "Asíncrono")
'''
    assert vr.verificar_aislamiento_legado(modelo, "contexto") == []


def test_r2_detecta_adr_incompleto():
    adr = "# ADR-099\n| Identificador | ADR-099 |\n| Estado | Aceptado |\n## 5. Decisión\n"
    errores = vr.verificar_adr(adr, "ADR-099.md")
    assert any("alternativas" in e for e in errores)
    assert any("justificación" in e for e in errores)


def test_r2_detecta_estado_invalido():
    adr = (RAIZ / "docs/actividad3/ADR-001-estilo-arquitectonico.md").read_text(encoding="utf-8")
    alterado = adr.replace("| Estado | Aceptado |", "| Estado | Quizás |")
    assert any("no válido" in e for e in vr.verificar_adr(alterado, "ADR-001"))


def test_r3_detecta_documento_sin_nombre_y_documento():
    assert vr.verificar_encabezado("# Actividad sin autor\n", "x.md")
    assert vr.verificar_encabezado(
        "**Estudiante:** Nombre Apellido — **Documento:** 123\n", "x.md") == []


def test_r4_detecta_diagrama_sin_exportar(tmp_path):
    (tmp_path / "nuevo.puml").write_text("@startuml\n@enduml\n", encoding="utf-8")
    (tmp_path / "nuevo.svg").write_text("<svg/>", encoding="utf-8")
    errores = vr.verificar_diagramas(tmp_path)
    assert errores == ["R4 [nuevo.puml] falta la exportación nuevo.png."]


ADR_002 = (RAIZ / "docs/actividad3/ADR-002-consistencia-cupos-inscripciones.md").read_text(encoding="utf-8")
NIVEL3 = (RAIZ / "docs/diagramas/c4-nivel3-componentes-inscripciones.puml").read_text(encoding="utf-8")


def test_r5_acepta_la_decision_vigente_de_cupos():
    assert vr.verificar_integridad_cupos(ADR_002, NIVEL3) == []


def test_r5_detecta_que_se_debilita_la_restriccion_de_cupo():
    alterado = ADR_002.replace("CHECK (inscritos <= capacidad)", "CHECK (inscritos >= 0)")
    assert any("CHECK" in e for e in vr.verificar_integridad_cupos(alterado, NIVEL3))


def test_r5_detecta_adr_de_cupos_rechazado():
    alterado = ADR_002.replace("| Estado | Aceptado |", "| Estado | Rechazado |")
    assert any("Aceptada" in e for e in vr.verificar_integridad_cupos(alterado, NIVEL3))


def test_r5_detecta_que_desaparece_el_control_de_cupos():
    alterado = NIVEL3.replace('"Control de cupos"', '"Gestor genérico"')
    assert any("Control de cupos" in e for e in vr.verificar_integridad_cupos(ADR_002, alterado))
