"""
Middleware for PortBroker application
Handles request logging, error processing, and sensitive data filtering
"""

import time
import uuid
import logging
import traceback
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .errors import PortBrokerException, get_http_status
from .logging_utils import get_logger


logger = get_logger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle exceptions and return structured error responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate trace ID for request tracking
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        
        try:
            response = await call_next(request)
            return response
        except PortBrokerException as e:
            # Set trace ID if not already set
            if not e.trace_id:
                e.trace_id = trace_id
            
            logger.error(
                "PortBroker exception occurred",
                extra={
                    "trace_id": trace_id,
                    "error_category": e.category.value,
                    "error_message": e.message,
                    "retriable": e.retriable,
                    "details": e.details,
                    "path": request.url.path,
                    "method": request.method
                }
            )
            
            return JSONResponse(
                status_code=get_http_status(e),
                content=e.to_dict()
            )
        except Exception as e:
            # Log unexpected errors with trace ID
            logger.error(
                "Unexpected error occurred",
                extra={
                    "trace_id": trace_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "path": request.url.path,
                    "method": request.method,
                    "traceback": traceback.format_exc()
                }
            )
            
            # Return generic error response (no sensitive information)
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "internal_server_error",
                        "message": "An internal server error occurred",
                        "retriable": False,
                        "trace_id": trace_id
                    }
                }
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests and responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        trace_id = getattr(request.state, 'trace_id', str(uuid.uuid4()))
        
        # Log request start
        logger.info(
            "Request started",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "url": str(request.url),
                "user_agent": request.headers.get("user-agent"),
                "content_type": request.headers.get("content-type"),
                "client_ip": request.client.host if request.client else None
            }
        )
        
        response = await call_next(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        # Log request completion
        logger.info(
            "Request completed",
            extra={
                "trace_id": trace_id,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "response_size": response.headers.get("content-length")
            }
        )
        
        # Add trace ID to response headers
        response.headers["X-Trace-ID"] = trace_id
        
        return response


class StatisticsTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request statistics"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only track API requests (not static files or portal UI)
        should_track = (
            request.url.path.startswith("/api/anthropic") or
            request.url.path.startswith("/api/v1/chat") or
            request.url.path.startswith("/api/portal")
        )
        
        if not should_track:
            return await call_next(request)

        start_time = time.time()
        trace_id = getattr(request.state, 'trace_id', str(uuid.uuid4()))
        
        # Store request info for tracking
        request.state.start_time = start_time
        request.state.tracking_data = {
            "trace_id": trace_id,
            "endpoint": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
        
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        # Track in background (don't block response)
        try:
            await self._track_request_async(
                request,
                response,
                duration_ms,
                trace_id
            )
        except Exception as e:
            # Log error but don't fail the request
            logger.error(
                "Failed to track request statistics",
                extra={
                    "trace_id": trace_id,
                    "error": str(e)
                }
            )
        
        return response

    async def _track_request_async(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
        trace_id: str
    ):
        """Track request statistics asynchronously"""
        from app.core.database import AsyncSessionLocal
        from app.services.statistics_service import StatisticsService
        
        # Extract tracking data from request state
        tracking_data = getattr(request.state, "tracking_data", {})
        
        # Get provider and strategy info from request state if available
        provider_info = getattr(request.state, "provider_info", {})
        strategy_info = getattr(request.state, "strategy_info", {})
        model_info = getattr(request.state, "model_info", {})
        api_key_info = getattr(request.state, "api_key_info", {})
        
        # Determine request/response sizes
        request_size = None
        if hasattr(request, "_body"):
            request_size = len(request._body) if request._body else 0
        
        response_size = None
        if response.headers.get("content-length"):
            try:
                response_size = int(response.headers["content-length"])
            except (ValueError, TypeError):
                pass
        
        async with AsyncSessionLocal() as db:
            try:
                await StatisticsService.track_request(
                    db=db,
                    trace_id=trace_id,
                    endpoint=tracking_data.get("endpoint", ""),
                    method=tracking_data.get("method", ""),
                    status_code=response.status_code,
                    duration_ms=int(duration_ms),
                    provider_id=provider_info.get("id"),
                    provider_name=provider_info.get("name"),
                    strategy_id=strategy_info.get("id"),
                    strategy_name=strategy_info.get("name"),
                    strategy_type=strategy_info.get("type"),
                    requested_model=model_info.get("requested"),
                    actual_model=model_info.get("actual"),
                    model_tier=model_info.get("tier"),
                    request_size=request_size,
                    response_size=response_size,
                    input_tokens=model_info.get("input_tokens"),
                    output_tokens=model_info.get("output_tokens"),
                    total_tokens=model_info.get("total_tokens"),
                    client_ip=tracking_data.get("client_ip"),
                    user_agent=tracking_data.get("user_agent"),
                    api_key_id=api_key_info.get("id"),
                )
            except Exception as e:
                logger.error(
                    "Statistics tracking failed in database operation",
                    extra={
                        "trace_id": trace_id,
                        "error": str(e)
                    }
                )