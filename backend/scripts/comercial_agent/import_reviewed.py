"""
Importa a la base el CSV de revisión generado (y corregido a mano) por run.py.

Por defecto corre en modo "dry-run": solo imprime qué haría, sin tocar la
base. Hay que pasar --confirm explícitamente para que escriba de verdad.

Uso:
    python import_reviewed.py --csv output/revision_empresas.csv           # dry-run
    python import_reviewed.py --csv output/revision_empresas.csv --confirm  # escribe

Reglas de import (pensadas para no pisar datos que alguien ya haya cargado
a mano en la app):
- Empresa: se crea solo si el CUIL no existe todavía. Si ya existe, se
  saltea por completo (no se sobreescribe).
- Contacto "empresarial" / "comercial": se crea solo si no hay ya un
  contacto con ese mismo nombre para esa empresa.
- ServicioPolo + Lote: se crea solo si la tipología matcheó el catálogo del
  Polo y la ubicación se pudo interpretar como manzana/lote (columnas
  tipologia_catalogo / manzana / lote del CSV). Si falta cualquiera de las
  dos, se saltea (queda para carga manual).
- InfoComercial: se crea/actualiza solo los campos que vienen no vacíos en
  el CSV; completado=True solo si hay como minimo productos_servicios
  cargado (si no, la empresa puede terminar de completarlo ella misma vía
  el wizard cuando inicie sesión).
"""
import argparse
import csv
import os
import sys
from datetime import date, datetime

# Permite `from app...` corriendo este script desde scripts/comercial_agent/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dotenv import load_dotenv

DEFAULT_CSV = os.path.join(os.path.dirname(__file__), "output", "revision_empresas.csv")
DEFAULT_HORARIO = "No especificado (importar/confirmar con la empresa)"


def _parse_bool(value: str):
    if value in (None, ""):
        return None
    return str(value).strip().lower() in ("true", "1", "si", "sí")


def _clean(value: str):
    if value is None:
        return None
    value = value.strip()
    return value or None


def _parse_fecha(value: str) -> date:
    value = _clean(value)
    if not value:
        return date.today()
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return date.today()


def import_csv(csv_path: str, confirm: bool) -> None:
    from app.config import SessionLocal
    from app import models

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    db = SessionLocal()
    creadas_empresa = 0
    saltadas_empresa = 0
    creados_contacto = 0
    creadas_info_comercial = 0

    try:
        tipo_comercial = db.query(models.TipoContacto).filter_by(tipo="comercial").first()
        tipo_empresarial = db.query(models.TipoContacto).filter_by(tipo="empresarial").first()
        if not tipo_comercial or not tipo_empresarial:
            print("ERROR: faltan los catalogos tipo_contacto 'comercial'/'empresarial'. Corre el backend una vez para que el bootstrap los cree.")
            return

        tipos_servicio_polo = {
            t.tipo: t.id_tipo_servicio_polo for t in db.query(models.TipoServicioPolo).all()
        }

        creados_servicio_polo = 0
        creados_lote = 0

        for row in rows:
            cuil = int(row["cuil"])
            nombre = row["nombre"]

            empresa = db.query(models.Empresa).filter_by(cuil=cuil).first()
            if empresa:
                saltadas_empresa += 1
                print(f"- {nombre} (CUIL {cuil}): ya existe, se saltea Empresa.")
            else:
                creadas_empresa += 1
                notas = row.get("notas") or ""
                descripcion = _clean(row.get("descripcion_empresa"))
                horario_comercial = _clean(row.get("horario_atencion_comercial"))
                observaciones = "Importado automaticamente desde planilla de empresas del Polo."
                if descripcion:
                    observaciones += f" {descripcion}"
                if notas:
                    observaciones += f" [Notas: {notas}]"
                print(f"+ {nombre} (CUIL {cuil}{' [PLACEHOLDER]' if _parse_bool(row['cuil_placeholder']) else ''}): crear Empresa")
                if confirm:
                    empresa = models.Empresa(
                        cuil=cuil,
                        nombre=nombre,
                        rubro=row.get("rubro") or "Sin especificar",
                        cant_empleados=int(row["cant_empleados"]) if row.get("cant_empleados") else 0,
                        observaciones=observaciones.strip(),
                        fecha_ingreso=_parse_fecha(row.get("fecha_ingreso")),
                        horario_trabajo=horario_comercial or DEFAULT_HORARIO,
                        estado=True,
                    )
                    db.add(empresa)
                    db.flush()

            if not empresa and not confirm:
                # en dry-run no existe el objeto todavia; simulamos igual el resto con un placeholder
                empresa = models.Empresa(cuil=cuil, nombre=nombre)

            # ServicioPolo + Lote (nave/oficina/local/etc. que ocupa dentro del parque)
            tipologia_catalogo = _clean(row.get("tipologia_catalogo"))
            manzana = _clean(row.get("manzana"))
            lote = _clean(row.get("lote"))
            if tipologia_catalogo and manzana and lote and tipologia_catalogo in tipos_servicio_polo:
                existe_sp = confirm and db.query(models.ServicioPolo).filter_by(
                    cuil=cuil, nombre=f"{tipologia_catalogo.capitalize()} - {nombre}"
                ).first()
                if not existe_sp:
                    creados_servicio_polo += 1
                    creados_lote += 1
                    print(f"    + ServicioPolo ({tipologia_catalogo}) + Lote (Mza {manzana}, Lote {lote})")
                    if confirm:
                        servicio_polo = models.ServicioPolo(
                            nombre=f"{tipologia_catalogo.capitalize()} - {nombre}",
                            propietario=_clean(row.get("propietario")),
                            id_tipo_servicio_polo=tipos_servicio_polo[tipologia_catalogo],
                            cuil=cuil,
                        )
                        db.add(servicio_polo)
                        db.flush()
                        db.add(models.Lote(
                            id_servicio_polo=servicio_polo.id_servicio_polo,
                            dueno=_clean(row.get("propietario")) or nombre,
                            lote=int(lote),
                            manzana=int(manzana),
                        ))

            # Contacto empresarial (interno, viene del excel)
            contacto_nombre = _clean(row.get("contacto_nombre"))
            if contacto_nombre:
                existe = confirm and db.query(models.Contacto).filter_by(
                    cuil_empresa=cuil, nombre=contacto_nombre
                ).first()
                if not existe:
                    creados_contacto += 1
                    print(f"    + Contacto empresarial: {contacto_nombre}")
                    if confirm:
                        db.add(models.Contacto(
                            cuil_empresa=cuil,
                            id_tipo_contacto=tipo_empresarial.id_tipo_contacto,
                            nombre=contacto_nombre,
                            telefono=_clean(row.get("contacto_telefono")),
                        ))

            # Contacto comercial (encontrado via scraping)
            com_tel = _clean(row.get("contacto_comercial_telefono"))
            com_correo = _clean(row.get("contacto_comercial_correo"))
            com_redes = _clean(row.get("contacto_comercial_redes"))
            com_dir = _clean(row.get("contacto_comercial_direccion"))
            if any([com_tel, com_correo, com_redes, com_dir]):
                nombre_contacto_comercial = f"{nombre} (comercial)"
                existe = confirm and db.query(models.Contacto).filter_by(
                    cuil_empresa=cuil, nombre=nombre_contacto_comercial
                ).first()
                if not existe:
                    creados_contacto += 1
                    print(f"    + Contacto comercial encontrado por scraping")
                    if confirm:
                        db.add(models.Contacto(
                            cuil_empresa=cuil,
                            id_tipo_contacto=tipo_comercial.id_tipo_contacto,
                            nombre=nombre_contacto_comercial,
                            telefono=com_tel,
                            direccion=com_dir,
                            datos={
                                "pagina_web": row.get("pagina_web_encontrada") or None,
                                "correo": com_correo,
                                "redes_sociales": com_redes,
                            },
                        ))

            # InfoComercial
            campos_comerciales = {
                "productos_servicios": _clean(row.get("productos_servicios")),
                "publico_objetivo": _clean(row.get("publico_objetivo")),
                "atiende_publico": _parse_bool(row.get("atiende_publico")),
                "horario_atencion_comercial": _clean(row.get("horario_atencion_comercial")),
                "rango_precios": _clean(row.get("rango_precios")),
                "modalidad_venta": _clean(row.get("modalidad_venta")),
                "marcas_representadas": _clean(row.get("marcas_representadas")),
                "certificaciones": _clean(row.get("certificaciones")),
                "observaciones_comerciales": _clean(row.get("observaciones_comerciales")),
            }
            if any(campos_comerciales.values()):
                creadas_info_comercial += 1
                completado = campos_comerciales["productos_servicios"] is not None
                print(f"    + InfoComercial (completado={completado})")
                if confirm:
                    existente = db.query(models.InfoComercial).filter_by(cuil=cuil).first()
                    if not existente:
                        db.add(models.InfoComercial(
                            cuil=cuil,
                            completado=completado,
                            fecha_actualizacion=date.today(),
                            **campos_comerciales,
                        ))

            if confirm:
                db.commit()

        print("\n=== Resumen ===")
        print(f"Empresas creadas: {creadas_empresa}")
        print(f"Empresas salteadas (ya existian): {saltadas_empresa}")
        print(f"Contactos creados: {creados_contacto}")
        print(f"ServicioPolo + Lote creados: {creados_servicio_polo}")
        print(f"Fichas InfoComercial creadas: {creadas_info_comercial}")
        if not confirm:
            print("\n(dry-run: no se escribio nada en la base. Correr con --confirm para aplicar.)")
    finally:
        db.close()


if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=DEFAULT_CSV, help="CSV de revision (salida de run.py)")
    parser.add_argument("--confirm", action="store_true", help="Escribir de verdad en la base (si no, dry-run)")
    args = parser.parse_args()

    import_csv(args.csv, confirm=args.confirm)
