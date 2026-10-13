"""Single-operator access protection; deploy behind HTTPS for hosted use."""
import base64
import binascii
import secrets
from starlette.responses import JSONResponse
from app.core.config import settings


async def protect_request(request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    if settings.AUTH_USERNAME:
        authenticated = False
        try:
            scheme, encoded = request.headers.get("authorization", "").split(" ", 1)
            username, password = base64.b64decode(encoded, validate=True).decode().split(":", 1)
            authenticated = (scheme.lower() == "basic" and
                secrets.compare_digest(username.encode(), settings.AUTH_USERNAME.encode()) and
                secrets.compare_digest(password.encode(), settings.AUTH_PASSWORD.encode()))
        except (ValueError, UnicodeError, binascii.Error):
            pass
        if not authenticated:
            return JSONResponse({"detail": "Sign in to SalesBattle."}, status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="SalesBattle", charset="UTF-8"'})
    elif not request.client or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
        return JSONResponse({"detail": "Remote access requires configured authentication."}, status_code=403)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        same_origin = str(request.base_url).rstrip("/")
        if origin and origin not in [same_origin, *settings.cors_origins]:
            return JSONResponse({"detail": "Request origin is not allowed."}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site" and not origin:
            return JSONResponse({"detail": "Cross-site writes are not allowed."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response
