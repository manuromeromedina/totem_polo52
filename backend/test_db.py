# test_db.py
from sqlalchemy import create_engine, text
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)

with engine.connect() as conn:
    # 1) Listar tablas
    result = conn.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public';"
    ))
    tables = [row[0] for row in result]
    print("✅ Tablas en public:", tables)

    # 2) Para cada tabla, contar filas
    for t in tables:
        try:
            cnt = conn.execute(text(f"SELECT count(*) FROM {t}")).scalar()
            print(f"   · {t}: {cnt} filas")
        except Exception as e:
            print(f"   · ERROR contando {t}: {e}")
