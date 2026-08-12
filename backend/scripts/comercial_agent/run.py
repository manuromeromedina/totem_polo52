"""
Agente de carga: excel -> (busca web) -> (scrapea) -> (extrae con IA) -> CSV de revisión.

No escribe nada en la base. Genera un CSV para que se revise/corrija a mano
antes de importarlo con import_reviewed.py.

Uso:
    python run.py [--excel PATH] [--out PATH] [--limit N] [--start N] [--delay SEG]

Ejemplo para probar con pocas empresas antes de correr las 171:
    python run.py --limit 5
"""
import argparse
import csv
import os
import time
from datetime import date

from dotenv import load_dotenv

from excel_import import load_empresas
from web_finder import find_company_url
from scraper import scrape_text
from extractor import extract_comercial_info
from ubicacion_parser import parse_tipologia, parse_ubicacion

FIELDNAMES = [
    "nombre", "cuil", "cuil_placeholder", "rubro",
    "contacto_nombre", "contacto_telefono", "cant_empleados", "fecha_ingreso",
    "propietario", "tipologia_excel", "tipologia_catalogo",
    "ubicacion_excel", "manzana", "lote",
    "pagina_web_excel", "pagina_web_encontrada", "fuente_web", "scrape_ok",
    "descripcion_empresa",
    "productos_servicios", "publico_objetivo", "atiende_publico",
    "horario_atencion_comercial", "rango_precios", "modalidad_venta",
    "marcas_representadas", "certificaciones", "observaciones_comerciales",
    "contacto_comercial_telefono", "contacto_comercial_correo",
    "contacto_comercial_redes", "contacto_comercial_direccion",
    "revisar", "notas",
]

DEFAULT_EXCEL = "/Users/maxiquelas/Downloads/POLO 52 - EMPRESAS INSTALADAS 2026.xlsx"
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), "output", "revision_empresas.csv")


def _load_ya_procesadas(out_path: str) -> set:
    """Nombres ya presentes en el CSV de salida, para poder resumir una corrida cortada."""
    if not os.path.exists(out_path):
        return set()
    with open(out_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["nombre"] for row in reader}


def run(excel_path: str, out_path: str, limit: int, start: int, delay: float, resume: bool) -> None:
    empresas = load_empresas(excel_path)
    empresas = empresas[start:]
    if limit:
        empresas = empresas[:limit]

    ya_procesadas = _load_ya_procesadas(out_path) if resume else set()
    if ya_procesadas:
        print(f"Reanudando: {len(ya_procesadas)} empresas ya en {out_path}, se van a saltear.")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    write_header = not (resume and os.path.exists(out_path))
    mode = "a" if resume else "w"

    with open(out_path, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()

        total = len(empresas)
        for i, empresa in enumerate(empresas, start=1):
            if empresa.nombre in ya_procesadas:
                continue

            print(f"[{i}/{total}] {empresa.nombre}")

            web_result = None
            try:
                web_result = find_company_url(empresa.nombre, empresa.rubro, empresa.pagina_web)
            except Exception as exc:  # noqa: BLE001
                print(f"    fallo buscando web: {exc}")

            texto = None
            scrape_ok = False
            if web_result:
                print(f"    web encontrada ({web_result.source}): {web_result.url}")
                texto = scrape_text(web_result.url)
                scrape_ok = texto is not None
                if not scrape_ok:
                    print("    no se pudo scrapear esa url")
            else:
                print("    no se encontro web/redes")

            extraccion = extract_comercial_info(empresa.nombre, empresa.rubro, texto)

            tipologia_catalogo = parse_tipologia(empresa.tipologia)
            ubicacion_parseada = parse_ubicacion(empresa.ubicacion_raw)

            notas = list(empresa.notas_excel)
            revisar = empresa.cuil_placeholder or not scrape_ok
            if not scrape_ok:
                notas.append("No se pudo encontrar o scrapear una web/red social para esta empresa.")
            if empresa.tipologia and not tipologia_catalogo:
                notas.append(f"Tipologia '{empresa.tipologia}' no coincide con el catalogo del Polo, revisar a mano.")
                revisar = True
            if empresa.ubicacion_raw and not ubicacion_parseada:
                notas.append(f"No se pudo interpretar la ubicacion '{empresa.ubicacion_raw}' como manzana/lote.")
                revisar = True

            writer.writerow({
                "nombre": empresa.nombre,
                "cuil": empresa.cuil,
                "cuil_placeholder": empresa.cuil_placeholder,
                "rubro": empresa.rubro or "",
                "contacto_nombre": empresa.contacto_nombre or "",
                "contacto_telefono": empresa.contacto_telefono or "",
                "cant_empleados": empresa.cant_empleados if empresa.cant_empleados is not None else "",
                "fecha_ingreso": empresa.fecha_ingreso or "",
                "propietario": empresa.propietario or "",
                "tipologia_excel": empresa.tipologia or "",
                "tipologia_catalogo": tipologia_catalogo or "",
                "ubicacion_excel": empresa.ubicacion_raw or "",
                "manzana": ubicacion_parseada[0] if ubicacion_parseada else "",
                "lote": ubicacion_parseada[1] if ubicacion_parseada else "",
                "pagina_web_excel": empresa.pagina_web or "",
                "pagina_web_encontrada": web_result.url if web_result else "",
                "fuente_web": web_result.source if web_result else "",
                "scrape_ok": scrape_ok,
                "descripcion_empresa": extraccion["descripcion_empresa"] or "",
                "productos_servicios": extraccion["productos_servicios"] or "",
                "publico_objetivo": extraccion["publico_objetivo"] or "",
                "atiende_publico": extraccion["atiende_publico"] if extraccion["atiende_publico"] is not None else "",
                "horario_atencion_comercial": extraccion["horario_atencion_comercial"] or "",
                "rango_precios": extraccion["rango_precios"] or "",
                "modalidad_venta": extraccion["modalidad_venta"] or "",
                "marcas_representadas": extraccion["marcas_representadas"] or "",
                "certificaciones": extraccion["certificaciones"] or "",
                "observaciones_comerciales": extraccion["observaciones_comerciales"] or "",
                "contacto_comercial_telefono": extraccion["contacto_telefono"] or "",
                "contacto_comercial_correo": extraccion["contacto_correo"] or "",
                "contacto_comercial_redes": extraccion["contacto_redes_sociales"] or "",
                "contacto_comercial_direccion": extraccion["contacto_direccion"] or "",
                "revisar": revisar,
                "notas": " | ".join(notas),
            })
            f.flush()

            time.sleep(delay)

    print(f"\nListo. Resultados en: {out_path}")


if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--excel", default=DEFAULT_EXCEL, help="Ruta al excel de empresas")
    parser.add_argument("--out", default=DEFAULT_OUT, help="CSV de salida para revision")
    parser.add_argument("--limit", type=int, default=0, help="Maximo de empresas a procesar (0 = todas)")
    parser.add_argument("--start", type=int, default=0, help="Indice desde donde arrancar en la lista")
    parser.add_argument("--delay", type=float, default=1.5, help="Segundos de espera entre empresas")
    parser.add_argument(
        "--no-resume", action="store_true",
        help="No saltear empresas ya presentes en --out (sobreescribe el CSV desde cero)",
    )
    args = parser.parse_args()

    run(
        excel_path=args.excel,
        out_path=args.out,
        limit=args.limit,
        start=args.start,
        delay=args.delay,
        resume=not args.no_resume,
    )
