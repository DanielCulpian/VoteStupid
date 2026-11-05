import logging
import math
import os
from collections import OrderedDict, deque
from threading import Lock
from time import monotonic
from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse


MAX_BODY_BYTES = 64 * 1024
RATE_POLICIES = {"all": 300, "create": 10, "vote": 30, "admin": 30, "ws": 30, "login": 5, "login_total": 20}


def allowed_origins() -> list[str]:
    """Read exact CORS origins and reject wildcards, paths, and credentials."""
    origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    result = []
    for value in origins:
        origin = value.strip()
        if not origin:
            continue
        parsed = urlsplit(origin)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.path
                or parsed.query or parsed.fragment or "*" in origin):
            raise ValueError("CORS_ALLOWED_ORIGINS debe contener orígenes HTTP exactos.")
        result.append(origin)
    return result


class RateLimiter:
    def __init__(self, clock=monotonic, max_keys: int = 10000):
        """Initialize one-minute windows with bounded memory and a replaceable clock."""
        self.clock = clock
        self.max_keys = max_keys
        self.buckets = OrderedDict()
        self.lock = Lock()

    def clear(self):
        """Reset the counters to isolate test scenarios."""
        with self.lock:
            self.buckets.clear()

    def check(self, client: str, category: str) -> int:
        """Consume the global and operation quotas, or return the required wait in seconds."""
        now = self.clock()
        with self.lock:
            while self.buckets:
                oldest = next(iter(self.buckets.values()))
                if oldest[-1] > now - 60:
                    break
                self.buckets.popitem(last=False)
            keys = [(client, "all")]
            if category != "all":
                keys.append((client, category))
            if len(self.buckets) + sum(key not in self.buckets for key in keys) > self.max_keys:
                return 60
            for key in keys:
                bucket = self.buckets.get(key, ())
                while bucket and bucket[0] <= now - 60:
                    bucket.popleft()
                if len(bucket) >= RATE_POLICIES[key[1]]:
                    return max(1, math.ceil(60 - (now - bucket[0])))
            for key in keys:
                self.buckets.setdefault(key, deque()).append(now)
                self.buckets.move_to_end(key)
        return 0


class SafeAccessLog(logging.Filter):
    def filter(self, record):
        """Remove query strings from Uvicorn HTTP and WebSocket log arguments."""
        if isinstance(record.args, tuple):
            record.args = tuple(value.split("?", 1)[0] if isinstance(value, str) else value
                                for value in record.args)
        return True


class ApiProtection:
    def __init__(self, app, limiter: RateLimiter, origins: list[str]):
        """Receive the shared rate limiter and allowed HTTP and WebSocket origins."""
        self.app = app
        self.limiter = limiter
        self.origins = origins
        self.active_sockets = {}
        self.total_sockets = 0

    async def __call__(self, scope, receive, send):
        """Limit traffic and body size without leaking error details or caching private responses."""
        kind = scope["type"]
        if kind not in {"http", "websocket"}:
            return await self.app(scope, receive, send)
        headers = Headers(scope=scope)
        path = scope.get("path", "")
        client = (scope.get("client") or ("unknown",))[0]
        category = "all"
        if kind == "websocket":
            category = "ws"
        elif path == "/api/admin/auth/login":
            category = "login"
        elif path.startswith("/api/admin/"):
            category = "admin"
        elif path.rstrip("/") == "/api/polls" and scope["method"] == "POST":
            category = "create"
        elif path.rstrip("/").endswith("/votes") and scope["method"] in {"POST", "PUT"}:
            category = "vote"

        # CORS handles preflight requests before they reach this middleware.
        wait = self.limiter.check(client, category)
        if kind == "websocket":
            origin = headers.get("origin")
            if origin and origin not in self.origins:
                return await send({"type": "websocket.close", "code": 1008})
            if wait or self.active_sockets.get(client, 0) >= 20 or self.total_sockets >= 1000:
                if "websocket.http.response" in scope.get("extensions", {}):
                    response = JSONResponse({"detail": "Demasiadas conexiones. Inténtalo más tarde."}, 429,
                                            headers={"Retry-After": str(wait or 60)})
                    return await response(scope, receive, send)
                return await send({"type": "websocket.close", "code": 1008})
            self.active_sockets[client] = self.active_sockets.get(client, 0) + 1
            self.total_sockets += 1
            try:
                await self.app(scope, receive, send)
            except Exception:
                logging.getLogger("votestupid.security").error("Error interno procesando una conexión WebSocket.")
                try:
                    await send({"type": "websocket.close", "code": 1011})
                except RuntimeError:
                    pass
            finally:
                self.total_sockets -= 1
                self.active_sockets[client] -= 1
                if not self.active_sockets[client]:
                    del self.active_sockets[client]
            return

        # Prevent browsers and proxies from storing any API response.
        async def safe_send(message):
            """Add privacy headers without logging request bodies or tokens."""
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers["Cache-Control"] = "no-store"
                response_headers["X-Content-Type-Options"] = "nosniff"
                response_headers["Referrer-Policy"] = "no-referrer"
            await send(message)

        if wait:
            return await JSONResponse({"detail": "Demasiadas peticiones. Inténtalo más tarde."}, 429,
                                      headers={"Retry-After": str(wait)})(scope, receive, safe_send)
        body = bytearray()
        try:
            size = int(headers.get("content-length", "0"))
            if size < 0:
                raise ValueError
        except ValueError:
            return await JSONResponse({"detail": "Tamaño de petición inválido."}, 400)(scope, receive, safe_send)
        if size > MAX_BODY_BYTES:
            return await JSONResponse({"detail": "La petición es demasiado grande."}, 413)(scope, receive, safe_send)
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > MAX_BODY_BYTES:
                return await JSONResponse({"detail": "La petición es demasiado grande."}, 413)(scope, receive, safe_send)
            if not message.get("more_body", False):
                break
        delivered = False
        started = False

        async def bounded_receive():
            """Deliver the validated body once while preserving the disconnect signal."""
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        async def track_send(message):
            """Track whether the response has started to avoid sending a second HTTP response."""
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await safe_send(message)

        try:
            await self.app(scope, bounded_receive, track_send)
        except Exception:
            logging.getLogger("votestupid.security").error("Error interno procesando una petición HTTP.")
            if not started:
                await JSONResponse({"detail": "No se ha podido completar la operación. Inténtalo más tarde."}, 500)(scope, receive, safe_send)
