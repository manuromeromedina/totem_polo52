"""
Reescribe `empresa.observaciones` para las empresas importadas desde
revision_empresas.csv con un párrafo más largo y natural, generado con
Gemini a partir EXCLUSIVAMENTE de los datos ya cargados (rubro, tipología,
ubicación, cantidad de empleados, contacto y, si existe, la ficha de
info_comercial). No se scrapea nada nuevo ni se inventa información: es una
redacción, no una extracción.

El texto actual de `observaciones` para muchas empresas es un mensaje de
log de importación ("Importado automaticamente desde planilla...") en vez
de una descripción útil; esto lo reemplaza por un párrafo pensado para que
el chatbot público lo pueda usar directo en sus respuestas.

Uso:
    python enrich_descriptions.py --csv output/revision_empresas.csv           # dry-run
    python enrich_descriptions.py --csv output/revision_empresas.csv --confirm  # escribe

Es re-corrible: salta las empresas cuya `observaciones` ya no empiece con
"Importado automaticamente" (es decir, ya enriquecidas).
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import google.generativeai as genai
from dotenv import load_dotenv
from google.generativeai.types import GenerationConfig

DEFAULT_CSV = os.path.join(os.path.dirname(__file__), "output", "revision_empresas.csv")
IMPORT_MARKER = "Importado automaticamente"

_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

_GENERATION_CONFIG = GenerationConfig(
    temperature=0.3,
    top_p=0.9,
    max_output_tokens=350,
    candidate_count=1,
)

_PROMPT_TEMPLATE = """
Sos un asistente que redacta la descripción de una empresa instalada en el
Parque Industrial Polo 52, para el directorio del parque.

Usá EXCLUSIVAMENTE los datos que te paso abajo. No inventes ni agregues
ningún dato, cifra, cliente, año, certificación, historia o característica
que no esté explícitamente en esta lista. Si un dato no aparece, simplemente
no lo menciones (no digas "no especificado" ni nada parecido).

Datos conocidos de la empresa:
{datos}

Redactá un párrafo de 3 a 5 frases, natural y fluido (no una lista, no
repitas los nombres de los campos), que combine estos datos para que un
visitante del parque entienda a qué se dedica la empresa. Empezá directo
con la descripción, sin saludos ni introducciones.
"""


def _clean(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _build_datos(row: dict) -> str:
    lineas = [f"- Nombre: {row['nombre']}"]

    rubro = _clean(row.get("rubro"))
    if rubro:
        lineas.append(f"- Rubro: {rubro}")

    cant = _clean(row.get("cant_empleados"))
    if cant and cant != "0":
        lineas.append(f"- Cantidad de empleados: {cant}")

    tipologia = _clean(row.get("tipologia_catalogo")) or _clean(row.get("tipologia_excel"))
    if tipologia:
        lineas.append(f"- Tipo de espacio que ocupa en el parque: {tipologia}")

    manzana, lote = _clean(row.get("manzana")), _clean(row.get("lote"))
    if manzana and lote:
        lineas.append(f"- Ubicación dentro del parque: Manzana {manzana}, Lote {lote}")

    descripcion_scrapeada = _clean(row.get("descripcion_empresa"))
    if descripcion_scrapeada:
        lineas.append(f"- Descripción encontrada en su sitio web: {descripcion_scrapeada}")

    productos = _clean(row.get("productos_servicios"))
    if productos:
        lineas.append(f"- Productos/servicios: {productos}")

    publico = _clean(row.get("publico_objetivo"))
    if publico:
        lineas.append(f"- Público objetivo: {publico}")

    atiende = _clean(row.get("atiende_publico"))
    if atiende and atiende.lower() == "true":
        lineas.append("- Atiende al público directamente en el local/planta")

    horario = _clean(row.get("horario_atencion_comercial"))
    if horario:
        lineas.append(f"- Horario de atención comercial: {horario}")

    modalidad = _clean(row.get("modalidad_venta"))
    if modalidad:
        lineas.append(f"- Modalidad de venta: {modalidad}")

    rango = _clean(row.get("rango_precios"))
    if rango:
        lineas.append(f"- Rango de precios: {rango}")

    marcas = _clean(row.get("marcas_representadas"))
    if marcas:
        lineas.append(f"- Marcas que representa/distribuye: {marcas}")

    certif = _clean(row.get("certificaciones"))
    if certif:
        lineas.append(f"- Certificaciones: {certif}")

    obs_comerciales = _clean(row.get("observaciones_comerciales"))
    if obs_comerciales:
        lineas.append(f"- Otros datos comerciales: {obs_comerciales}")

    return "\n".join(lineas)


def generate_description(model, row: dict) -> str:
    datos = _build_datos(row)
    prompt = _PROMPT_TEMPLATE.format(datos=datos)
    response = model.generate_content(prompt, generation_config=_GENERATION_CONFIG)
    text = (response.text or "").strip()
    return text


def run(csv_path: str, confirm: bool) -> None:
    load_dotenv()
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(model_name=_MODEL_NAME)

    from app.config import SessionLocal
    from app import models

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    db = SessionLocal()
    generadas = 0
    salteadas = 0
    errores = 0

    try:
        for i, row in enumerate(rows, start=1):
            cuil = int(row["cuil"])
            nombre = row["nombre"]

            empresa = db.query(models.Empresa).filter_by(cuil=cuil).first()
            if not empresa:
                print(f"[{i}/{len(rows)}] {nombre} (CUIL {cuil}): no existe en la base, se saltea.")
                salteadas += 1
                continue

            if empresa.observaciones and not empresa.observaciones.startswith(IMPORT_MARKER):
                print(f"[{i}/{len(rows)}] {nombre}: ya tiene descripcion enriquecida, se saltea.")
                salteadas += 1
                continue

            try:
                nueva_descripcion = generate_description(model, row)
            except Exception as exc:  # noqa: BLE001
                print(f"[{i}/{len(rows)}] {nombre}: fallo generando descripcion: {exc}")
                errores += 1
                continue

            if not nueva_descripcion:
                print(f"[{i}/{len(rows)}] {nombre}: Gemini no devolvio texto, se saltea.")
                errores += 1
                continue

            print(f"[{i}/{len(rows)}] {nombre}: {nueva_descripcion[:100]}...")
            generadas += 1

            if confirm:
                empresa.observaciones = nueva_descripcion
                db.commit()

        print("\n=== Resumen ===")
        print(f"Descripciones generadas: {generadas}")
        print(f"Salteadas (ya enriquecidas o sin empresa): {salteadas}")
        print(f"Errores: {errores}")
        if not confirm:
            print("\n(dry-run: no se escribio nada en la base. Correr con --confirm para aplicar.)")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=DEFAULT_CSV, help="CSV de revision (salida de run.py)")
    parser.add_argument("--confirm", action="store_true", help="Escribir de verdad en la base (si no, dry-run)")
    args = parser.parse_args()

    run(args.csv, confirm=args.confirm)
