"""
Extracción estructurada de datos comerciales a partir del texto scrapeado de
la web de una empresa, usando Gemini.

Misma postura anti-alucinación que el resto del proyecto (ver
app/services/chatbot_service.py): el modelo debe dejar un campo vacío si el
texto no lo respalda con evidencia clara, en vez de inventarlo. Estos
resultados van a un CSV de revisión humana antes de tocar la base — no se
insertan directo.
"""
import json
import os
import re
from typing import Dict, Optional

import google.generativeai as genai
from dotenv import load_dotenv
from google.generativeai.types import GenerationConfig
from typing_extensions import TypedDict

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
_model = genai.GenerativeModel(model_name=_MODEL_NAME)


class _ExtraccionComercial(TypedDict):
    descripcion_empresa: str
    productos_servicios: str
    publico_objetivo: str
    atiende_publico: str
    horario_atencion_comercial: str
    rango_precios: str
    modalidad_venta: str
    marcas_representadas: str
    certificaciones: str
    observaciones_comerciales: str
    contacto_telefono: str
    contacto_correo: str
    contacto_redes_sociales: str
    contacto_direccion: str


_GENERATION_CONFIG = GenerationConfig(
    temperature=0.1,
    top_p=0.9,
    max_output_tokens=800,
    candidate_count=1,
    response_mime_type="application/json",
    response_schema=_ExtraccionComercial,
)

_EMPTY_RESULT: Dict[str, Optional[str]] = {
    "descripcion_empresa": None,
    "productos_servicios": None,
    "publico_objetivo": None,
    "atiende_publico": None,
    "horario_atencion_comercial": None,
    "rango_precios": None,
    "modalidad_venta": None,
    "marcas_representadas": None,
    "certificaciones": None,
    "observaciones_comerciales": None,
    "contacto_telefono": None,
    "contacto_correo": None,
    "contacto_redes_sociales": None,
    "contacto_direccion": None,
}

_PROMPT_TEMPLATE = """
Sos un asistente que completa una ficha comercial para el directorio del
Parque Industrial Polo 52, a partir del texto de la web pública de una
empresa instalada ahí.

Empresa: {nombre}
Rubro declarado (puede ser impreciso): {rubro}

Texto extraído de su sitio web / red social:
\"\"\"
{texto}
\"\"\"

Completá estos campos SOLO si el texto los respalda con evidencia razonable.
Si el texto no menciona algo, dejá ese campo como cadena vacía (""). NUNCA
inventes datos que no estén en el texto.

- descripcion_empresa: descripción completa de la empresa para mostrar en su perfil (3 a 5 frases). Cubrí todo lo que el texto respalde de: quiénes son y a qué se dedican, trayectoria/historia/año de fundación, especialización o diferencial, a qué tipo de clientes atienden, alcance geográfico, y cualquier logro o dato distintivo mencionado. Es un párrafo más desarrollado que productos_servicios, sin repetir las mismas frases. Si el texto solo da para una o dos frases reales, no rellenes con relleno genérico: mejor corto y verídico que largo e inventado.
- productos_servicios: resumen breve (1-2 frases) de qué vende/ofrece específicamente (productos, líneas, servicios concretos).
- publico_objetivo: "B2B", "B2C" o "Ambos", solo si se infiere con claridad.
- atiende_publico: "true" o "false" (string), solo si el texto lo aclara.
- horario_atencion_comercial: horario de atención si figura.
- rango_precios: "Económico", "Medio" o "Premium", solo si hay indicios reales (ej. se autodefinen como premium/artesanal/mayorista low-cost). Si no hay pistas, dejar vacío.
- modalidad_venta: "Presencial", "Online" o "Ambas", solo si se puede inferir.
- marcas_representadas: marcas que distribuye/representa, si las nombra.
- certificaciones: normas o certificaciones que mencione (ISO, etc.).
- observaciones_comerciales: cualquier otro dato comercial relevante no cubierto arriba.
- contacto_telefono: teléfono de contacto comercial si figura en el texto.
- contacto_correo: email de contacto si figura.
- contacto_redes_sociales: usuario/link de redes sociales si figura.
- contacto_direccion: dirección física si figura.
"""


def _clean(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if not value or value.lower() in ("no", "n/a", "no aplica", "no disponible", "null", "none"):
        return None
    return value


def _parse_bool(value: Optional[str]) -> Optional[bool]:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in ("true", "si", "sí", "1"):
        return True
    if normalized in ("false", "no", "0"):
        return False
    return None


_ENUM_OPTIONS = {
    "publico_objetivo": ["B2B", "B2C", "Ambos"],
    "rango_precios": ["Económico", "Medio", "Premium"],
    "modalidad_venta": ["Presencial", "Online", "Ambas"],
}


def _normalize_enum(field: str, value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    for option in _ENUM_OPTIONS[field]:
        if option.lower() in normalized or normalized in option.lower():
            return option
    return None


def extract_comercial_info(nombre: str, rubro: Optional[str], texto: Optional[str]) -> Dict:
    """Devuelve un dict con los campos de info_comercial + contacto comercial inferidos (o None)."""
    if not texto:
        return dict(_EMPTY_RESULT)

    prompt = _PROMPT_TEMPLATE.format(nombre=nombre, rubro=rubro or "no especificado", texto=texto)

    try:
        response = _model.generate_content(prompt, generation_config=_GENERATION_CONFIG)
        raw = response.text
    except Exception as exc:  # noqa: BLE001 - errores de API no deben tumbar el batch
        print(f"    [extractor] Gemini fallo para {nombre!r}: {exc}")
        return dict(_EMPTY_RESULT)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            return dict(_EMPTY_RESULT)
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return dict(_EMPTY_RESULT)

    result = dict(_EMPTY_RESULT)
    for field in result:
        if field == "atiende_publico":
            result[field] = _parse_bool(data.get(field))
        elif field in _ENUM_OPTIONS:
            result[field] = _normalize_enum(field, _clean(data.get(field)))
        else:
            result[field] = _clean(data.get(field))
    return result
