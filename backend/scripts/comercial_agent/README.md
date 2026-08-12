# Agente de carga de empresas

Herramienta offline (no forma parte de la API desplegada) para poblar toda
la ficha de las ~171 empresas de la planilla "POLO 52 - EMPRESAS INSTALADAS
2026": los datos base que ya están en la planilla (contacto, cantidad de
empleados, nave/lote que ocupan en el parque) y, vía scraping + Gemini, los
datos comerciales que Polo 52 nunca nos entregó (productos, precios,
modalidad de venta, contacto comercial público, descripción de la empresa).

No se ejecuta como parte del backend ni se incluye en la imagen Docker
(`Dockerfile` solo copia `app/`). Es un script que se corre a mano, una vez
(o cuando se actualice la planilla).

## Pipeline

1. **`excel_import.py`** — lee la hoja "2026" de la planilla (nombre,
   rubro, contacto, cantidad de empleados, tipología, ubicación,
   propietario, página web, fecha de instalación) y cruza con la hoja
   "Empresas 2025" para completar CUIL por nombre cuando existe. Las
   empresas sin CUIL real reciben un CUIL placeholder (prefijo `99...`, que
   ningún CUIL argentino real usa) marcado con `cuil_placeholder=True`.
2. **`ubicacion_parser.py`** — interpreta la columna "Tipología" contra el
   catálogo real del Polo (nave/oficina/local comercial/coworking/etc.) y la
   columna "Ubicación" (texto libre tipo "Mza 48 lote 13") a
   `(manzana, lote)`. Best-effort: lo que no puede interpretar queda sin
   parsear y se marca para revisión, no se fuerza.
3. **`web_finder.py`** — para cada empresa, busca su sitio/red social:
   primero la URL del excel si existe, después dominios heurísticos
   (`nombre.com.ar`), y como último recurso una búsqueda gratuita en
   DuckDuckGo (sin API key). Es best-effort: puede no encontrar nada para
   empresas chicas sin presencia web.
4. **`scraper.py`** — descarga y limpia el texto visible de la home (+ una
   subpágina de contacto si la detecta).
5. **`extractor.py`** — le pasa ese texto a Gemini para completar una
   descripción de la empresa, los campos de `info_comercial` (productos,
   público objetivo, precios, etc.) y datos de contacto comercial.
   Instrucción explícita de no inventar nada que el texto no respalde.
6. **`run.py`** — orquesta todo lo anterior y escribe **un CSV de revisión**
   (`output/revision_empresas.csv`), fila por empresa. No toca la base.
7. **`import_reviewed.py`** — lee ese CSV (ya revisado/corregido a mano) y
   recién ahí escribe en la base: `Empresa`, `Contacto` (tipo empresarial y
   comercial), `ServicioPolo`+`Lote` (solo si la tipología y la ubicación se
   pudieron interpretar) e `InfoComercial`. Corre en modo dry-run por
   defecto; hace falta `--confirm` para que escriba de verdad. Nunca pisa
   una `Empresa` que ya exista por CUIL.

## Instalación

```bash
cd backend
./venv/bin/python -m pip install -r scripts/comercial_agent/requirements.txt
```

Usa el mismo `.env` del backend (`GOOGLE_API_KEY`, `DATABASE_URL`).

## Uso

```bash
cd backend/scripts/comercial_agent

# 1) Probar con pocas empresas primero
../../venv/bin/python run.py --limit 5

# 2) Revisar/corregir output/revision_empresas.csv a mano (planillas de
#    Excel/Google Sheets van bien). Prestar atención a:
#    - cuil_placeholder=True -> reemplazar por el CUIL real si se consigue
#    - revisar=True -> algo no se pudo resolver solo (web, tipologia o
#      ubicacion): ver la columna "notas" para el motivo puntual
#    - tipologia_catalogo / manzana / lote vacios -> no se va a crear
#      ServicioPolo/Lote para esa empresa hasta completarlos a mano
#    - cualquier campo con info incorrecta o mal inferida por la IA

# 3) Correr el resto de las empresas (podés cortar y retomar; por defecto
#    resume el CSV existente y no reprocesa lo ya hecho)
../../venv/bin/python run.py

# 4) Ver que haria el import sin escribir nada (dry-run)
../../venv/bin/python import_reviewed.py

# 5) Importar de verdad
../../venv/bin/python import_reviewed.py --confirm
```

## Notas

- `output/` no se commitea (contiene datos scrapeados, no código).
- La búsqueda en DuckDuckGo es gratuita pero informal (no es una API
  oficial): puede fallar o cambiar de formato. Si eso pasa, revisar
  `web_finder._duckduckgo_search`.
- El scraping respeta un delay de ~1.5s entre empresas para no golpear
  DuckDuckGo ni los sitios de las empresas.
