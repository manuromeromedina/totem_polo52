# app/bootstrap.py
import os
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import SessionLocal, engine, Base
from app import models, services

ROLES_BASE = ["admin_polo", "admin_empresa", "publico"]

# Catálogos de referencia (tablas tipo_*) que la app da por cargados: los
# formularios de alta de vehículos/contactos/servicios los consultan y
# esperan encontrarlos. No son datos de negocio que cambien por sí solos,
# así que se recrean automáticamente si la base queda vacía.
CATALOGS = [
    (
        models.TipoVehiculo,
        "id_tipo_vehiculo",
        {1: "corporativos", 2: "terceros", 3: "personales"},
    ),
    (
        models.TipoContacto,
        "id_tipo_contacto",
        {1: "comercial", 2: "empresarial"},
    ),
    (
        models.TipoServicioPolo,
        "id_tipo_servicio_polo",
        {
            1: "coworking",
            2: "nave",
            3: "oficina",
            4: "local comercial",
            5: "container",
            6: "lavadero",
        },
    ),
    (
        models.TipoServicio,
        "id_tipo_servicio",
        {1: "agua", 2: "espacios verdes", 3: "internet", 4: "residuos"},
    ),
]

# Por defecto coincide con POLO_CUIL (app/routes/admin_users.py) para que el
# admin inicial quede vinculado a la empresa que representa al propio Polo 52.
ADMIN_CUIL = int(os.getenv("BOOTSTRAP_ADMIN_CUIL", os.getenv("POLO_CUIL", "44123456789")))
ADMIN_USERNAME = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin")
ADMIN_EMAIL = os.getenv("BOOTSTRAP_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")


def _ensure_roles(db: Session) -> dict:
    roles = {r.tipo_rol: r for r in db.query(models.Rol).all()}
    for tipo in ROLES_BASE:
        if tipo not in roles:
            rol = models.Rol(tipo_rol=tipo)
            db.add(rol)
            db.flush()
            roles[tipo] = rol
    return roles


def _ensure_catalogs(db: Session) -> None:
    """Inserta los valores de CATALOGS que falten, sin tocar los que ya existan."""
    for model, id_field, values in CATALOGS:
        existing_ids = {getattr(row, id_field) for row in db.query(model).all()}
        for id_value, tipo_value in values.items():
            if id_value not in existing_ids:
                db.add(model(**{id_field: id_value, "tipo": tipo_value}))


def _ensure_admin_empresa(db: Session) -> models.Empresa:
    empresa = db.query(models.Empresa).filter(models.Empresa.cuil == ADMIN_CUIL).first()
    if empresa:
        return empresa
    empresa = models.Empresa(
        cuil=ADMIN_CUIL,
        nombre="Administración Polo 52",
        rubro="Administración",
        cant_empleados=1,
        observaciones="Empresa interna generada automáticamente para alojar al usuario admin_polo inicial.",
        fecha_ingreso=date.today(),
        horario_trabajo="24hs",
        estado=True,
    )
    db.add(empresa)
    db.flush()
    return empresa


def _ensure_schema_upgrades() -> None:
    """
    Agrega columnas nuevas a tablas ya existentes: `Base.metadata.create_all()`
    solo crea tablas faltantes, no columnas faltantes en tablas que ya
    existen. Sin Alembic, esta es la forma más simple de mantener el schema
    al día en cada arranque (idempotente gracias a IF NOT EXISTS).
    """
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE empresa ADD COLUMN IF NOT EXISTS estado_solicitud "
            "VARCHAR(20) NOT NULL DEFAULT 'aprobada'"
        ))
        conn.execute(text(
            "ALTER TABLE usuario ADD COLUMN IF NOT EXISTS mostrar_bienvenida "
            "BOOLEAN NOT NULL DEFAULT TRUE"
        ))
        conn.execute(text(
            "ALTER TABLE lotes ADD COLUMN IF NOT EXISTS latitud DOUBLE PRECISION"
        ))
        conn.execute(text(
            "ALTER TABLE lotes ADD COLUMN IF NOT EXISTS longitud DOUBLE PRECISION"
        ))


def run_startup_bootstrap() -> None:
    """
    Crea las tablas si no existen (idempotente), asegura los catálogos de
    referencia (tipo_vehiculo, tipo_contacto, tipo_servicio_polo,
    tipo_servicio) y garantiza que exista al menos un usuario con rol
    admin_polo, tomando las credenciales de BOOTSTRAP_ADMIN_EMAIL /
    BOOTSTRAP_ADMIN_PASSWORD. Los catálogos y roles se revisan en cada
    arranque; la creación del admin solo pasa si todavía no hay ninguno.
    """
    Base.metadata.create_all(bind=engine)
    _ensure_schema_upgrades()

    db = SessionLocal()
    try:
        roles = _ensure_roles(db)
        _ensure_catalogs(db)
        db.commit()

        ya_hay_admin = (
            db.query(models.Usuario)
            .join(models.RolUsuario, models.RolUsuario.id_usuario == models.Usuario.id_usuario)
            .join(models.Rol, models.Rol.id_rol == models.RolUsuario.id_rol)
            .filter(models.Rol.tipo_rol == "admin_polo")
            .first()
        )
        if ya_hay_admin:
            return

        if not ADMIN_EMAIL or not ADMIN_PASSWORD:
            print(
                "\n  No hay ningún usuario admin_polo y faltan las variables de entorno "
                "BOOTSTRAP_ADMIN_EMAIL / BOOTSTRAP_ADMIN_PASSWORD: no se creó un admin automáticamente.\n"
            )
            return

        empresa = _ensure_admin_empresa(db)

        admin = models.Usuario(
            nombre=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            contrasena=services.hash_password(ADMIN_PASSWORD),
            estado=True,
            fecha_registro=date.today(),
            cuil=empresa.cuil,
        )
        db.add(admin)
        db.flush()

        db.add(models.RolUsuario(id_usuario=admin.id_usuario, id_rol=roles["admin_polo"].id_rol))
        db.commit()

        print(f"\n Usuario admin_polo inicial creado: nombre='{ADMIN_USERNAME}', email='{ADMIN_EMAIL}'\n")
    finally:
        db.close()
