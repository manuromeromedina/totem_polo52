# app/rate_limit.py
"""
Rate limiting simple en memoria, por IP de cliente.

Pensado para un único proceso (ver Dockerfile: uvicorn corre sin
--workers). Si en el futuro se escala a múltiples workers o instancias,
esto hay que migrarlo a un backend compartido (Redis) para que el límite
sea efectivo entre procesos; en memoria, cada proceso llevaría su propio
conteo y el límite real terminaría siendo N veces el configurado.
"""
import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

from fastapi import HTTPException, Request


_buckets: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)

# De qué header sale la IP del cliente (RATE_LIMIT_CLIENT_IP_HEADER):
#   "cloudflare" (default): CF-Connecting-IP, que pone Cloudflare y el cliente
#                no puede cambiar si el tráfico pasa por Cloudflare.
#   "x-forwarded-for": la ÚLTIMA IP de X-Forwarded-For (la que agregó el proxy
#                de confianza; las anteriores las puede inventar el cliente).
#   "none": solo la IP de la conexión.
# Antes se usaba la PRIMERA IP de X-Forwarded-For, que la elige el cliente:
# rotándola se esquivaba el límite (p. ej. fuerza bruta contra /login).
CLIENT_IP_HEADER = os.getenv("RATE_LIMIT_CLIENT_IP_HEADER", "cloudflare").strip().lower()


def _client_key(request: Request) -> str:
    """Identifica al cliente por IP, sin creerle a headers que el cliente puede falsificar."""
    if CLIENT_IP_HEADER == "cloudflare":
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()
    elif CLIENT_IP_HEADER == "x-forwarded-for":
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[-1].strip()

    return request.client.host if request.client else "unknown"


def rate_limit(name: str, max_requests: int, window_seconds: int):
    """
    Dependencia de FastAPI: como máximo `max_requests` solicitudes cada
    `window_seconds` segundos, por IP y por `name` (para que endpoints
    distintos no compartan el mismo balde).
    """

    def dependency(request: Request) -> None:
        key = (name, _client_key(request))
        now = time.monotonic()
        bucket = _buckets[key]

        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()

        if len(bucket) >= max_requests:
            retry_after = max(1, int(window_seconds - (now - bucket[0])))
            raise HTTPException(
                status_code=429,
                detail="Demasiadas solicitudes. Intentá de nuevo en unos momentos.",
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)

    return dependency


def reset_rate_limits() -> None:
    """Limpia todos los contadores. Pensado para uso en tests."""
    _buckets.clear()
