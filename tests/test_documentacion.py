"""Pruebas de integridad de la documentación (enlaces e imágenes)."""
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ENLACE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")
DOCUMENTOS = sorted([RAIZ / "README.md", *RAIZ.glob("docs/**/*.md")])


def enlaces_locales(documento: Path):
    texto = re.sub(r"```.*?```", "", documento.read_text(encoding="utf-8"), flags=re.DOTALL)
    for destino in ENLACE.findall(texto):
        if destino.startswith(("http://", "https://", "mailto:", "#")):
            continue
        yield unquote(destino.split("#")[0])


@pytest.mark.parametrize("documento", DOCUMENTOS, ids=lambda p: str(p.relative_to(RAIZ)))
def test_enlaces_e_imagenes_locales_existen(documento):
    rotos = [d for d in enlaces_locales(documento) if d and not (documento.parent / d).exists()]
    assert rotos == [], f"Enlaces rotos en {documento.relative_to(RAIZ)}: {rotos}"


def test_existen_los_entregables_minimos():
    for ruta in ["README.md", "docs/actividad1.md", "docs/actividad2.md",
                 "docs/actividad4.md", "docs/actividad5.md", "docs/diagramas"]:
        assert (RAIZ / ruta).exists(), f"Falta el entregable {ruta}"
    assert len(list((RAIZ / "docs/actividad3").glob("ADR-*.md"))) >= 3


def test_existen_los_tres_niveles_c4():
    for nivel in ["c4-nivel1-contexto", "c4-nivel2-contenedores", "c4-nivel3-componentes-inscripciones"]:
        assert (RAIZ / f"docs/diagramas/{nivel}.puml").exists()
