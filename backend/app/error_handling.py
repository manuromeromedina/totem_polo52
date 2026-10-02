# app/error_handling.py
"""
Convierte cualquier excepción no manejada en un 500 JSON *dentro* del stack
de middlewares.

Sin esto, la excepción sube hasta el ServerErrorMiddleware de Starlette (la
capa más externa) y su 500 sale sin los headers de CORS: el navegador bloquea
la respuesta y el frontend la interpreta como "Error de conexión" en vez de un
error del servidor. Registrado como el middleware más interno, su respuesta
pasa por CORSMiddleware y SecurityHeadersMiddleware como cualquier otra.
"""
import logging

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("uvicorn.error")

GENERIC_500_DETAIL = "Error interno del servidor. Intentá de nuevo en unos minutos."


class CatchUnhandledErrorsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception("Error no manejado en %s %s", scope.get("method"), scope.get("path"))
            if response_started:
                # ya se mandaron headers: no se puede reemplazar la respuesta
                raise
            response = JSONResponse({"detail": GENERIC_500_DETAIL}, status_code=500)
            await response(scope, receive, send)
