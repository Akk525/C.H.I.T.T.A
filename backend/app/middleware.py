from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_413_BODY = json.dumps({"detail": "Request body too large"}).encode()


async def _send_413(send: Send) -> None:
    await send({
        "type": "http.response.start",
        "status": 413,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(_413_BODY)).encode()),
        ],
    })
    await send({"type": "http.response.body", "body": _413_BODY, "more_body": False})


class BodySizeLimitMiddleware:
    """Pure ASGI middleware that rejects HTTP requests whose body exceeds max_bytes.

    Fast path: Content-Length header present → reject before reading any body.
    Slow path (chunked transfers): stream and count bytes, buffer for replay to
    the inner app if within limit.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Fast path: reject by Content-Length before touching the body stream
        headers: dict[bytes, bytes] = dict(scope.get("headers", []))
        cl_raw = headers.get(b"content-length")
        if cl_raw is not None:
            try:
                if int(cl_raw) > self.max_bytes:
                    await _send_413(send)
                    return
            except ValueError:
                pass  # malformed Content-Length — let the inner app handle it

        # Slow path: stream the body, counting bytes
        chunks: list[bytes] = []
        total = 0

        while True:
            message: Message = await receive()
            msg_type = message.get("type")

            if msg_type == "http.disconnect":
                captured = message

                async def _replay_disconnect() -> Message:
                    return captured

                await self.app(scope, _replay_disconnect, send)
                return

            if msg_type != "http.request":
                break  # unexpected message type — pass through unchanged

            chunk: bytes = message.get("body", b"")
            total += len(chunk)

            if total > self.max_bytes:
                # Drain the remaining body so the client doesn't get a broken pipe
                while message.get("more_body", False):
                    message = await receive()
                await _send_413(send)
                return

            chunks.append(chunk)
            if not message.get("more_body", False):
                break

        # Replay the buffered body to the inner app as a single message
        full_body = b"".join(chunks)
        replayed = False

        async def _replay_body() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": full_body, "more_body": False}
            return {"type": "http.disconnect"}

        await self.app(scope, _replay_body, send)
