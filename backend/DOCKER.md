# Backend en Docker

Pasos rápidos para ejecutar la API de FastAPI con Docker y publicarla en GitHub Container Registry (GHCR).

## Requisitos
- Docker instalado.
- Archivo `backend/.env` con al menos `DATABASE_URL`, `SECRET_KEY`, `SESSION_SECRET_KEY`, `GOOGLE_API_KEY` (y cualquier otra variable que ya uses).  
- Si usas Google Cloud Speech/TTS, coloca tu JSON en `backend/Keys/` y añade `GOOGLE_APPLICATION_CREDENTIALS=/app/Keys/<archivo>.json` al `.env`.

## Build local
```bash
docker build -t polo52-api:local -f backend/Dockerfile backend
```

## Ejecutar local
```bash
docker run --rm -p 8000:8000 \
  --env-file backend/.env \
  -v "$(pwd)/backend/Keys:/app/Keys:ro" \
  polo52-api:local
```
La API queda en http://localhost:8000 y docs en http://localhost:8000/docs.

> Nota: en el contenedor `localhost` apunta al propio contenedor. Si tu Postgres corre en tu host, usa `host.docker.internal` en `DATABASE_URL` (ya configurado en `.env`). Para otros hosts, ajusta el hostname.

> Producción: con `ROOT_PATH=/api` y `CORS_ALLOW_ORIGINS=https://polo52.com,https://www.polo52.com`, expón el backend detrás de un proxy que enrute `https://polo52.com/api/*` al contenedor.

## Publicar en GHCR
1) Inicia sesión (usa un token con scope `write:packages`):
```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u <tu_usuario_github> --password-stdin
```
2) Construye con el tag de GHCR:
```bash
IMAGE=ghcr.io/<org_o_usuario>/polo52-api:0.1.0
docker build -t "$IMAGE" -f backend/Dockerfile backend
```
3) Envía la imagen:
```bash
docker push "$IMAGE"
```
4) (Opcional) Probar la imagen publicada:
```bash
docker run --rm -p 8000:8000 --env-file backend/.env "$IMAGE"
```

Listo, con eso puedes consumir la imagen desde GHCR en servidores o pipelines.

## CI con GitHub Actions
Se agregó `.github/workflows/docker-ghcr.yml` para construir y publicar la imagen automáticamente a GHCR en cada push a `main/master`. Usa `GITHUB_TOKEN` con permisos de `packages: write` (habilitados por defecto). Tags generados: rama, SHA y `latest` para la rama principal.
