"""gRPC authentication interceptor for Bindu."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import grpc
from grpc import aio

from bindu.settings import AuthSettings
from bindu.utils.auth_utils import JWTValidator, extract_bearer_token
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.grpc.auth")


def _metadata_value(
    metadata: Iterable[tuple[str, Any]] | None, key: str
) -> str | None:
    if not metadata:
        return None
    target = key.lower()
    for meta_key, meta_value in metadata:
        if meta_key.lower() != target:
            continue
        if isinstance(meta_value, bytes):
            return meta_value.decode("utf-8", errors="replace")
        return str(meta_value)
    return None


def _abort_handler(
    handler: grpc.RpcMethodHandler,
    status: grpc.StatusCode,
    details: str,
) -> grpc.RpcMethodHandler:
    request_deserializer = getattr(handler, "request_deserializer", None)
    response_serializer = getattr(handler, "response_serializer", None)

    async def abort_unary_unary(_request, context):
        await context.abort(status, details)

    async def abort_stream_unary(_request_iterator, context):
        await context.abort(status, details)

    async def abort_unary_stream(_request, context):
        await context.abort(status, details)
        if False:
            yield None

    async def abort_stream_stream(_request_iterator, context):
        await context.abort(status, details)
        if False:
            yield None

    if handler.request_streaming and handler.response_streaming:
        return grpc.stream_stream_rpc_method_handler(
            abort_stream_stream,
            request_deserializer=request_deserializer,
            response_serializer=response_serializer,
        )
    if handler.request_streaming:
        return grpc.stream_unary_rpc_method_handler(
            abort_stream_unary,
            request_deserializer=request_deserializer,
            response_serializer=response_serializer,
        )
    if handler.response_streaming:
        return grpc.unary_stream_rpc_method_handler(
            abort_unary_stream,
            request_deserializer=request_deserializer,
            response_serializer=response_serializer,
        )
    return grpc.unary_unary_rpc_method_handler(
        abort_unary_unary,
        request_deserializer=request_deserializer,
        response_serializer=response_serializer,
    )


class GrpcAuthInterceptor(aio.ServerInterceptor):
    """Server interceptor that enforces JWT auth via metadata."""

    def __init__(
        self,
        auth_config: AuthSettings,
        validator: JWTValidator | None = None,
    ) -> None:
        self._auth_config = auth_config
        self._validator = validator or JWTValidator(auth_config)

    async def intercept_service(self, continuation, handler_call_details):
        handler = await continuation(handler_call_details)
        if handler is None:
            return None

        method = handler_call_details.method or "<unknown>"
        authorization = _metadata_value(
            handler_call_details.invocation_metadata, "authorization"
        )
        token = extract_bearer_token(authorization)
        if not token:
            logger.warning("Missing authorization metadata for gRPC call %s", method)
            return _abort_handler(
                handler,
                grpc.StatusCode.UNAUTHENTICATED,
                "Missing authorization token",
            )

        try:
            self._validator.validate_token(token)
        except Exception as exc:
            logger.warning(
                "Invalid authorization token for gRPC call %s: %s",
                method,
                exc,
            )
            return _abort_handler(
                handler,
                grpc.StatusCode.UNAUTHENTICATED,
                "Invalid authorization token",
            )

        return handler
