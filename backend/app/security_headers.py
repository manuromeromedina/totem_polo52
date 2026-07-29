# app/security_headers.py
"""
Middleware que agrega headers de seguridad estándar a toda respuesta.

No incluye Content-Security-Policy: esta es una API (no sirve HTML de la
app), y una CSP genérica podría no ajustarse a lo que necesite el frontend
si algún día se sirve algo desde acá. Cloudflare (delante del backend en
producción) también agrega headers propios; esto asegura que estén
presentes igual si cambia la configuración del proxy.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response
