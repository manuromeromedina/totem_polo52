"""Datos temporales para la suite E2E de Playwright (repo del frontend, e2e-sistema/).

Uso (desde backend/):
    python scripts/e2e_data.py setup            crea empresas y usuarios E2E (idempotente)
    python scripts/e2e_data.py cleanup          borra TODO lo E2E y muestra el conteo final
    python scripts/e2e_data.py report           cuenta lo E2E que hay en la base
    python scripts/e2e_data.py reset-token EMAIL [MINUTOS]
                                                imprime un token de recuperación (MINUTOS<0 = vencido)

Todo lo que crea lleva prefijo E2E_/e2e_ y CUILs del rango 20999000000-20999999999,
para que la limpieza nunca toque datos reales.
"""
import json
import os
import sys
from datetime import date

from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import models, services  # noqa: E402
from app.config import SessionLocal, engine  # noqa: E402

engine.echo = False

PWD = "E2e#Prueba2026!"
CUIL_POLO_E2E = 20999000001
CUIL_EMP = 20999000002
CUIL_EMP2 = 20999000003
CUIL_PENDIENTE = 20999000010
CUIL_RECHAZADA = 20999000011

EMPRESAS = [
    # cuil, nombre, estado, estado_solicitud
    (CUIL_POLO_E2E, "E2E_Polo_Admin", True, "aprobada"),
    (CUIL_EMP, "E2E_Empresa_Prueba", True, "aprobada"),
    (CUIL_EMP2, "E2E_Empresa_Dos", True, "aprobada"),  # para probar aislamiento entre empresas
    (CUIL_PENDIENTE, "E2E_Pendiente", False, "pendiente"),
    (CUIL_RECHAZADA, "E2E_Rechazada", False, "rechazada"),
]
USERS = [
    # nombre, rol, cuil, estado
    ("e2e_admin_polo", "admin_polo", CUIL_POLO_E2E, True),
    ("e2e_admin_empresa", "admin_empresa", CUIL_EMP, True),
    ("e2e_admin_empresa2", "admin_empresa", CUIL_EMP2, True),
    ("e2e_publico", "publico", CUIL_EMP, True),
    ("e2e_deshabilitado", "admin_empresa", CUIL_EMP, False),
    ("e2e_pendiente", "admin_empresa", CUIL_PENDIENTE, True),
    ("e2e_rechazado", "admin_empresa", CUIL_RECHAZADA, True),
    ("e2e_reset", "admin_empresa", CUIL_EMP, True),
    ("e2e_polo_pwd", "admin_polo", CUIL_POLO_E2E, True),  # para probar el cambio de contraseña
    ("e2e_emp_pwd", "admin_empresa", CUIL_EMP2, True),  # cambio de contraseña de admin_empresa
    ("e2e_bienvenida", "admin_empresa", CUIL_EMP2, True),  # todavía no vio el aviso de bienvenida
]
CON_BIENVENIDA = {"e2e_bienvenida"}

E2E_CUILS = "SELECT cuil FROM empresa WHERE nombre ILIKE 'E2E%' OR cuil BETWEEN 20999000000 AND 20999999999"
E2E_LOTES = "dueno ILIKE 'E2E%' OR dueno ILIKE 'Prueba Automatica%'"


def setup():
    db = SessionLocal()
    try:
        for cuil, nombre, estado, solicitud in EMPRESAS:
            if not db.get(models.Empresa, cuil):
                db.add(models.Empresa(
                    cuil=cuil, nombre=nombre, rubro="Testing E2E", cant_empleados=3,
                    observaciones="Empresa temporal de prueba E2E", fecha_ingreso=date.today(),
                    horario_trabajo="9 a 18", estado=estado, estado_solicitud=solicitud,
                ))
        db.commit()
        roles = {r.tipo_rol: r for r in db.query(models.Rol).all()}
        for nombre, rol, cuil, estado in USERS:
            if db.query(models.Usuario).filter_by(nombre=nombre).first():
                continue
            u = models.Usuario(
                nombre=nombre, email=f"{nombre}@example.com", contrasena=services.hash_password(PWD),
                estado=estado, fecha_registro=date.today(), cuil=cuil, mostrar_bienvenida=nombre in CON_BIENVENIDA,
            )
            db.add(u)
            db.commit()
            db.refresh(u)
            db.add(models.RolUsuario(id_usuario=u.id_usuario, id_rol=roles[rol].id_rol))
            db.commit()
    finally:
        db.close()
    print(json.dumps({"password": PWD, "users": [u[0] for u in USERS]}))


def report():
    queries = {
        "empresas": f"SELECT count(*) FROM empresa WHERE cuil IN ({E2E_CUILS})",
        "usuarios": "SELECT count(*) FROM usuario WHERE nombre ILIKE 'e2e%' OR email ILIKE 'e2e%'",
        "vehiculos": f"SELECT count(*) FROM empresa_vehiculos WHERE cuil IN ({E2E_CUILS})",
        "servicios": f"SELECT count(*) FROM empresa_servicio WHERE cuil IN ({E2E_CUILS})",
        "servicio_polo": f"SELECT count(*) FROM servicio_polo WHERE cuil IN ({E2E_CUILS}) OR nombre ILIKE 'E2E%'",
        "lotes": f"SELECT count(*) FROM lotes WHERE {E2E_LOTES}",
    }
    with engine.connect() as c:
        counts = {k: c.execute(text(q)).scalar() for k, q in queries.items()}
    print(json.dumps(counts))
    return counts


def cleanup():
    with engine.begin() as c:
        # vehiculos y servicios cuelgan de tablas intermedias: se borran antes que la empresa
        c.execute(text(f"DELETE FROM vehiculos WHERE id_vehiculo IN (SELECT id_vehiculo FROM empresa_vehiculos WHERE cuil IN ({E2E_CUILS}))"))
        c.execute(text(f"DELETE FROM servicio WHERE id_servicio IN (SELECT id_servicio FROM empresa_servicio WHERE cuil IN ({E2E_CUILS}))"))
        c.execute(text(f"DELETE FROM lotes WHERE {E2E_LOTES}"))
        c.execute(text("DELETE FROM servicio_polo WHERE nombre ILIKE 'E2E%'"))
        c.execute(text("DELETE FROM usuario WHERE nombre ILIKE 'e2e%' OR email ILIKE 'e2e%'"))
        c.execute(text(f"DELETE FROM empresa WHERE cuil IN ({E2E_CUILS})"))
    report()


def reset_token(email: str, minutes: str = "60"):
    print(services.create_password_reset_token(email, expires_minutes=int(minutes)))


def tts_wav(texto: str, salida: str):
    """Genera `texto` hablado en un WAV PCM 48 kHz (Google TTS, mismas credenciales
    que el backend). Se usa como micrófono simulado de Chromium en la suite E2E
    (--use-file-for-fake-audio-capture), para probar el circuito de voz real."""
    from google.cloud import texttospeech  # import tardío: solo hace falta acá

    client = texttospeech.TextToSpeechClient()
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=texto),
        voice=texttospeech.VoiceSelectionParams(language_code="es-US", name="es-US-Studio-B"),
        audio_config=texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16, sample_rate_hertz=48000),
    )
    with open(salida, "wb") as f:
        f.write(response.audio_content)  # LINEAR16 ya viene con cabecera WAV
    print(salida)


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["report"]
    {"setup": setup, "cleanup": cleanup, "report": report, "reset-token": reset_token, "tts-wav": tts_wav}[cmd](*args)
