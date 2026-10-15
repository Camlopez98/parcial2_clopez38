#!/usr/bin/env python3
"""Verificación automática de reglas arquitectónicas de PIA (Actividad 5).

Reglas:
  R1 (POL-01): en los modelos C4, solo el Sincronizador (o el sistema PIA completo en
      el diagrama de contexto) se relaciona con el sistema legado.
  R2 (POL-04): cada ADR contiene las secciones obligatorias y un estado válido.
  R3 (POL-04): cada documento de actividad y cada ADR empieza con nombre y documento.
  R4 (POL-04): cada diagrama .puml tiene sus versiones .svg y .png.

Uso: python scripts/verificar_reglas.py [raiz_del_repositorio]
Termina con código 1 si encuentra incumplimientos.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DECLARACION = re.compile(r'^\s*(\w+)\(\s*(\w+)\s*,\s*"([^"]*)"', re.MULTILINE)
RELACION = re.compile(r'^\s*Rel\w*\(\s*(\w+)\s*,\s*(\w+)\s*,', re.MULTILINE)

SECCIONES_ADR = {
    "identificador": r"Identificador",
    "fecha": r"\|\s*Fecha\s*\|",
    "estado": r"\|\s*Estado\s*\|",
    "contexto y problema": r"#+\s*\d*\.?\s*Contexto",
    "drivers relacionados": r"#+\s*\d*\.?\s*Drivers",
    "alternativas": r"#+\s*\d*\.?\s*Alternativas",
    "criterios de comparación": r"#+\s*\d*\.?\s*Criterios",
    "decisión": r"#+\s*\d*\.?\s*Decisi[oó]n",
    "justificación": r"#+\s*\d*\.?\s*Justificaci[oó]n",
    "consecuencias": r"#+\s*\d*\.?\s*Consecuencias",
    "riesgos": r"Riesgos",
    "condiciones de revisión": r"#+\s*\d*\.?\s*Condiciones para revisar",
}
ESTADOS_VALIDOS = ("Propuesto", "En revisión", "Aceptado", "Rechazado", "Reemplazado", "Obsoleto")
ENCABEZADO = re.compile(r"^\*\*Estudiante:\*\*\s+\S.+—\s+\*\*Documento:\*\*\s+\d+")


def verificar_aislamiento_legado(contenido: str, nombre: str) -> list[str]:
    """R1: solo el Sincronizador (o el sistema PIA en el contexto) toca al legado."""
    elementos = {alias: (macro, etiqueta) for macro, alias, etiqueta in DECLARACION.findall(contenido)}
    legado = {a for a, (m, e) in elementos.items()
              if "legado" in e.lower() and m.endswith("_Ext")}
    permitidos = {a for a, (m, e) in elementos.items()
                  if m == "System" or "sincronizador" in e.lower()}
    errores = []
    for origen, destino in RELACION.findall(contenido):
        if destino in legado and origen not in permitidos:
            errores.append(f"R1 [{nombre}] '{origen}' se relaciona con el legado '{destino}'; "
                           "solo el Sincronizador puede hacerlo (POL-01).")
        if origen in legado and destino not in permitidos:
            errores.append(f"R1 [{nombre}] el legado '{origen}' se relaciona con '{destino}'; "
                           "solo el Sincronizador puede hacerlo (POL-01).")
    return errores


def verificar_adr(contenido: str, nombre: str) -> list[str]:
    """R2: estructura mínima y estado válido de un ADR."""
    errores = [f"R2 [{nombre}] falta la sección '{seccion}'."
               for seccion, patron in SECCIONES_ADR.items()
               if not re.search(patron, contenido, re.IGNORECASE)]
    estado = re.search(r"\|\s*Estado\s*\|\s*([^|\n]+)\|", contenido)
    if estado and not estado.group(1).strip().startswith(ESTADOS_VALIDOS):
        errores.append(f"R2 [{nombre}] estado '{estado.group(1).strip()}' no válido; "
                       f"use uno de {', '.join(ESTADOS_VALIDOS)}.")
    alternativas = re.findall(r"^###\s+A\d+", contenido, re.MULTILINE)
    if len(alternativas) < 2:
        errores.append(f"R2 [{nombre}] debe documentar al menos dos alternativas (### A1, ### A2).")
    return errores


def verificar_encabezado(contenido: str, nombre: str) -> list[str]:
    """R3: el documento empieza con nombre y documento del autor."""
    primera = contenido.lstrip().splitlines()[0] if contenido.strip() else ""
    if not ENCABEZADO.match(primera):
        return [f"R3 [{nombre}] la primera línea debe ser '**Estudiante:** <nombre> — **Documento:** <número>'."]
    return []


def verificar_diagramas(directorio: Path) -> list[str]:
    """R4: cada fuente .puml tiene sus exportaciones .svg y .png."""
    errores = []
    for fuente in sorted(directorio.glob("*.puml")):
        for ext in (".svg", ".png"):
            if not fuente.with_suffix(ext).exists():
                errores.append(f"R4 [{fuente.name}] falta la exportación {fuente.with_suffix(ext).name}.")
    return errores


def verificar_repositorio(raiz: Path) -> list[str]:
    docs = raiz / "docs"
    errores: list[str] = []
    for modelo in sorted((docs / "diagramas").glob("c4-*.puml")):
        errores += verificar_aislamiento_legado(modelo.read_text(encoding="utf-8"), modelo.name)
    adrs = sorted((docs / "actividad3").glob("ADR-*.md"))
    if len(adrs) < 3:
        errores.append(f"R2 [docs/actividad3] se esperan al menos 3 ADR y hay {len(adrs)}.")
    for adr in adrs:
        texto = adr.read_text(encoding="utf-8")
        errores += verificar_adr(texto, adr.name) + verificar_encabezado(texto, adr.name)
    for actividad in sorted(docs.glob("actividad*.md")):
        errores += verificar_encabezado(actividad.read_text(encoding="utf-8"), actividad.name)
    errores += verificar_diagramas(docs / "diagramas")
    return errores


def main() -> int:
    raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    errores = verificar_repositorio(raiz)
    if errores:
        print(f"Se encontraron {len(errores)} incumplimientos de reglas arquitectónicas:")
        for error in errores:
            print(f"  - {error}")
        return 1
    print("Reglas arquitectónicas R1-R4 verificadas: 0 incumplimientos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
