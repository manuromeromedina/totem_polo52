# app/rate_limit.py
"""
Rate limiting simple en memoria, por IP de cliente.

Pensado para un único proceso (ver Dockerfile: uvicorn corre sin
--workers). Si en el futuro se escala a múltiples workers o instancias,
esto hay que migrarlo a un backend compartido (Redis) para que el límite
sea efectivo entre procesos; en memoria, cada proceso llevaría su propio
conteo y el límite real terminaría siendo N veces el configurado.
"""
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

from fastapi import HTTPException, Request


_buckets: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    """
    Identifica al cliente por IP. Prioriza los headers que pone un proxy
    delante (Cloudflare / nginx) sobre request.client.host, que detrás de
    un proxy sería la IP del proxy y no la del usuario real.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip

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
