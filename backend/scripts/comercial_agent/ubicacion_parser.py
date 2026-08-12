"""Parseo best-effort de la columna "Ubicación" del excel a (manzana, lote)."""
import re
from typing import Optional, Tuple

# Catálogo real de app/bootstrap.py (TipoServicioPolo). "parking" no tiene
# equivalente en el catálogo actual, así que queda sin mapear a propósito.
TIPOLOGIA_A_CATALOGO = {
    "coworking": "coworking",
    "nave": "nave",
    "oficina": "oficina",
    "local comercial": "local comercial",
    "container": "container",
    "lavadero": "lavadero",
}

_MZA = r"(?:mza|mz|manzana)\.?\s*0*(\d+)"
_LOTE = r"(?:lote|lot)\.?\s*0*(\d+)"

_PATRON_MZA_LOTE = re.compile(_MZA + r".*?" + _LOTE, re.IGNORECASE)
_PATRON_LOTE_MZA = re.compile(_LOTE + r".*?" + _MZA, re.IGNORECASE)


def parse_tipologia(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    return TIPOLOGIA_A_CATALOGO.get(str(raw).strip().lower())


def parse_ubicacion(raw: Optional[str]) -> Optional[Tuple[int, int]]:
    """Devuelve (manzana, lote) si se puede interpretar, o None si el formato es demasiado libre."""
    if not raw:
        return None
    text = str(raw)

    match = _PATRON_MZA_LOTE.search(text)
    if match:
        return int(match.group(1)), int(match.group(2))

    match = _PATRON_LOTE_MZA.search(text)
    if match:
        return int(match.group(2)), int(match.group(1))

    return None
