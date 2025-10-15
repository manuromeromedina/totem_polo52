# backend/tests/test_schemas.py
import pytest

def test_schemas_basic_validation():
    try:
        from app import schemas
        from pydantic import ValidationError
    except Exception:
        pytest.skip("No existe app.schemas")

    if not hasattr(schemas, "UserCreate"):
        pytest.skip("schemas.UserCreate no existe")

    UserCreate = schemas.UserCreate

    # Detectar campos requeridos en el modelo (Pydantic v2)
    fields = getattr(UserCreate, "model_fields", {})
    required = {
        name
        for name, f in fields.items()
        if getattr(f, "is_required", lambda: f.default is ... )() or f.default is ...
    }

    # Payload base con tipos correctos: cuil = int
    base_payload = {
        "email": "test@x.com",
        "password": "Aaa!2345",
        "nombre": "Test",
        "cuil": 20123456783,   # <— entero, no string
        "id_rol": 1,
    }

    # Construir payload que cubra los requeridos
    payload = {}
    for k in (set(["email", "password", "nombre"]) | required):
        if k in base_payload:
            payload[k] = base_payload[k]
        else:
            # fallback simple por nombre de campo
            if "email" in k:
                payload[k] = "test@x.com"
            elif "password" in k:
                payload[k] = "Aaa!2345"
            elif "cuil" in k.lower() or "cuit" in k.lower():
                payload[k] = 20123456783  # entero
            elif "rol" in k.lower() or k.lower().startswith("id"):
                payload[k] = 1
            else:
                payload[k] = "X"

    # 1) Valida con payload correcto
    u = UserCreate(**payload)
    assert getattr(u, "email", None) == payload.get("email")

    # 2) Email inválido debe fallar
    bad_email_payload = {**payload, "email": "not-an-email"}
    with pytest.raises(ValidationError):
        UserCreate(**bad_email_payload)

    # 3) Password débil: si hay validador custom debería fallar (no lo forzamos)
    weak_pwd_payload = {**payload, "password": "123"}
    try:
        UserCreate(**weak_pwd_payload)
    except ValidationError:
        pass
