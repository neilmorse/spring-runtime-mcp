"""Read-only application mappings and Spring Cloud Gateway routes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from ..adapters.gateway_routes import normalize_gateway_routes
from ..adapters.mappings import normalize_mappings
from ..contracts.definitions import validate_arguments
from ..models.common import NormalizationError
from ..models.queries import MappingQuery
from ..transport.response_gate import EndpointReadError
from ..services import Services
from ..diagnostics import failed, partial
from .support import tool_handler, finalize, read_checked, resume, shell, stamp


@tool_handler
async def verify_mappings(
    arguments: Mapping[str, Any], services: Services
) -> dict[str, Any]:
    request_target = "local"
    try:
        query = validate_arguments(arguments, "springboot_verify_mappings")
        request_target = query.target_id
        assert isinstance(query, MappingQuery)
        if query.cursor:
            return resume(services, query)
        snapshot = uuid4().hex
        gateway = query.route_source == "gateway"
        endpoint = "gateway-routes" if gateway else "mappings"
        observation = await read_checked(services, query.target_id, endpoint, snapshot)
        if gateway:
            items, gaps = await services.analyze(
                normalize_gateway_routes,
                observation.body,
                path_pattern=query.path_pattern,
                sanitizer=services.sanitizer,
            )
        else:
            items, gaps = await services.analyze(
                normalize_mappings,
                observation.body,
                path_pattern=query.path_pattern,
                http_method=query.http_method,
                controller_pattern=query.controller_class_pattern,
                context_id=query.context_id,
            )
        result = shell(
            query.target_id,
            "registered target mappings",
            "gateway-routes-1" if gateway else "mappings-1",
        )
        stamp(result, observation, endpoint, snapshot)
        for item in items:
            item["endpointId"] = endpoint
            item["observationId"] = observation.observation_id
        result["data"] = {"items": items}
        result["totalMatched"] = None if gaps else len(items)
        if "GATEWAY_ROUTE_LIMIT" in gaps:
            result["truncated"] = True
            result["truncationReasons"] = ["GATEWAY_ROUTE_LIMIT"]
        partial(result, gaps)
        return finalize(result, services, query)
    except NormalizationError as exc:
        return failed(
            exc.code,
            request_target,
            endpoint=exc.endpoint_id if isinstance(exc, EndpointReadError) else None,
            http_status=exc.http_status if isinstance(exc, EndpointReadError) else None,
        )
    except TimeoutError:
        return failed("TARGET_TIMEOUT", request_target)
    except (ValueError, TypeError, KeyError, RecursionError, UnicodeError):
        return failed("MALFORMED_EVIDENCE", request_target)
    except Exception:
        return failed("INTERNAL_ERROR", request_target)
