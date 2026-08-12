# app/services/comercial_chatbot_service.py
"""
Wizard de carga de información comercial, exclusivo para el rol admin_empresa.

A diferencia de chatbot_service.py (texto libre -> SQL de solo lectura vía
Gemini, para el público general), este flujo ESCRIBE en la base de datos:
por eso avanza con una secuencia fija de preguntas (QUESTIONS) y valida/
normaliza cada respuesta con reglas determinísticas en vez de delegarle a un
modelo la generación de la escritura. El objetivo es completar, de a un campo
por mensaje, la ficha comercial que Polo 52 nunca nos entregó, para que
después el chatbot público (chatbot_service.py) pueda responder consultas
comerciales sobre las empresas.
"""
import unicodedata
from datetime import date
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app import models


def _normalize(value: str) -> str:
    normalized = "".join(
        c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn"
    )
    return normalized.lower().strip()


QUESTIONS: List[Dict] = [
    {
        "field": "productos_servicios",
        "question": "Para empezar: ¿qué productos o servicios ofrece tu empresa exactamente?",
        "type": "text",
    },
    {
        "field": "publico_objetivo",
        "question": "¿A quién le vendés principalmente: a otras empresas (mayorista/B2B), al público en general (B2C), o a ambos?",
        "type": "enum",
        "options": ["B2B", "B2C", "Ambos"],
    },
    {
        "field": "atiende_publico",
        "question": "¿Atendés al público directamente en el local o planta? (sí/no)",
        "type": "bool",
    },
    {
        "field": "horario_atencion_comercial",
        "question": "¿Cuál es el horario de atención comercial para clientes (puede ser distinto al horario laboral interno)?",
        "type": "text",
    },
    {
        "field": "rango_precios",
        "question": "¿Cómo describirías tus precios: económicos, medios o premium?",
        "type": "enum",
        "options": ["Económico", "Medio", "Premium"],
    },
    {
        "field": "modalidad_venta",
        "question": "¿Vendés de forma presencial, online, o ambas?",
        "type": "enum",
        "options": ["Presencial", "Online", "Ambas"],
    },
    {
        "field": "marcas_representadas",
        "question": "¿Representás o distribuís marcas específicas? Nombralas, o decime que no aplica.",
        "type": "text",
    },
    {
        "field": "certificaciones",
        "question": "¿Contás con certificaciones (ISO, normas de calidad, etc.)? Mencionalas, o decime que no tenés.",
        "type": "text",
    },
    {
        "field": "observaciones_comerciales",
        "question": "Por último, ¿hay algo más que quieras agregar sobre el perfil comercial de tu empresa?",
        "type": "text",
    },
]

_AFFIRMATIVE = {"si", "sí", "s", "claro", "correcto", "afirmativo", "siempre", "obvio", "exacto"}
_NEGATIVE = {"no", "nunca", "negativo", "para nada"}


def _get_or_create_row(db: Session, cuil: int) -> models.InfoComercial:
    row = db.query(models.InfoComercial).filter_by(cuil=cuil).first()
    if not row:
        row = models.InfoComercial(cuil=cuil, completado=False)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _pending_fields(row: models.InfoComercial) -> List[Dict]:
    return [q for q in QUESTIONS if getattr(row, q["field"]) is None]


def _parse_bool(raw: str) -> Optional[bool]:
    words = set(_normalize(raw).split())
    has_affirmative = bool(words & _AFFIRMATIVE)
    has_negative = bool(words & _NEGATIVE)
    if has_affirmative and not has_negative:
        return True
    if has_negative and not has_affirmative:
        return False
    return None


def _parse_enum(raw: str, options: List[str]) -> Optional[str]:
    normalized = _normalize(raw)
    for option in options:
        if _normalize(option) in normalized:
            return option
    return None


def _apply_answer(row: models.InfoComercial, question: Dict, raw_answer: str) -> Optional[str]:
    """Valida y guarda la respuesta en `row`. Devuelve un mensaje de error si no es válida, o None si se guardó."""
    raw_answer = raw_answer.strip()
    if not raw_answer:
        return "No entendí tu respuesta, ¿podrías escribirla de nuevo?"

    field = question["field"]
    qtype = question["type"]

    if qtype == "bool":
        parsed = _parse_bool(raw_answer)
        if parsed is None:
            return "Respondeme con sí o no, por favor."
        setattr(row, field, parsed)

    elif qtype == "enum":
        parsed = _parse_enum(raw_answer, question["options"])
        if parsed is None:
            opciones = ", ".join(question["options"])
            return f"No reconocí esa opción. Elegí una de estas: {opciones}."
        setattr(row, field, parsed)

    else:  # text
        setattr(row, field, raw_answer)

    return None


def get_comercial_chat_response(
    db: Session, cuil: int, message: Optional[str]
) -> Tuple[str, bool, Optional[str], int, int]:
    """
    Avanza el wizard de carga comercial un paso.

    Devuelve (reply, done, campo_actual, progreso_actual, progreso_total).
    Llamar con message vacío/None devuelve la pregunta pendiente sin
    consumir ninguna respuesta (útil para arrancar o refrescar la conversación).
    """
    row = _get_or_create_row(db, cuil)
    total = len(QUESTIONS)

    if row.completado:
        return (
            "Ya completaste el registro de información comercial. Si necesitás modificar algún dato, "
            "contactá al administrador del Polo.",
            True,
            None,
            total,
            total,
        )

    pending = _pending_fields(row)

    if not message or not message.strip():
        if not pending:
            row.completado = True
            row.fecha_actualizacion = date.today()
            db.commit()
            return ("¡Listo! Ya tenés cargada toda la información comercial.", True, None, total, total)
        next_q = pending[0]
        answered = total - len(pending)
        return (next_q["question"], False, next_q["field"], answered, total)

    current_q = pending[0]
    error = _apply_answer(row, current_q, message)
    if error:
        answered = total - len(pending)
        return (error, False, current_q["field"], answered, total)

    db.commit()
    db.refresh(row)

    remaining = _pending_fields(row)
    answered = total - len(remaining)

    if not remaining:
        row.completado = True
        row.fecha_actualizacion = date.today()
        db.commit()
        return (
            "¡Gracias! Con esto ya tenemos completo el perfil comercial de tu empresa.",
            True,
            None,
            total,
            total,
        )

    next_q = remaining[0]
    return (next_q["question"], False, next_q["field"], answered, total)
