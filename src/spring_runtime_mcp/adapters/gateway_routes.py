"""Project the verbose Spring Cloud Gateway route inventory into safe facts."""

from __future__ import annotations

import re
from typing import Any

from ..contracts.definitions import glob_matches
from ..models.common import AnalysisBudget, NormalizationError
from ..policy.sanitization import MARKER, SanitizerPipeline

_MAX_ROUTES = 2_000
_NAME = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}"
_ROUTE = re.compile(_NAME)
_DESTINATION = re.compile(rf"lb://({_NAME})")
_PREDICATE = re.compile(r"Paths: \[([^\]\r\n]*)\], match trailing slash: (true|false)")
_PATH = re.compile(r"/(?!/)[A-Za-z0-9_.$/:*?{}~\-]{0,255}")


def _paths(
    predicate: object, sanitizer: SanitizerPipeline
) -> tuple[list[str] | None, bool | None]:
    if not isinstance(predicate, str) or len(predicate) > 4096:
        return None, None
    match = _PREDICATE.fullmatch(predicate)
    if match is None:
        return None, None
    paths = match[1].split(", ")
    if len(paths) > 16 or any(
        _PATH.fullmatch(path) is None or sanitizer.high_risk(path) for path in paths
    ):
        return None, None
    return paths, match[2] == "true"


def _service(uri: object, sanitizer: SanitizerPipeline) -> str | None:
    match = _DESTINATION.fullmatch(uri) if isinstance(uri, str) else None
    if match is None or sanitizer.identifier(match[1]) == MARKER:
        return None
    return match[1]


def normalize_gateway_routes(
    body: object, *, path_pattern: str | None, sanitizer: SanitizerPipeline
) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(body, dict) or not isinstance(body.get("routes"), list):
        raise NormalizationError("UNSUPPORTED_SHAPE")
    routes = body["routes"]
    gaps = {"GATEWAY_ROUTE_LIMIT"} if len(routes) > _MAX_ROUTES else set()
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    budget = AnalysisBudget()
    for index, route in enumerate(routes[:_MAX_ROUTES], start=1):
        budget.consume()
        route_id = route.get("route_id") if isinstance(route, dict) else None
        if (
            not isinstance(route_id, str)
            or _ROUTE.fullmatch(route_id) is None
            or sanitizer.identifier(route_id) == MARKER
            or route_id in seen
        ):
            gaps.add("GATEWAY_ROUTE_UNREADABLE")
            continue
        seen.add(route_id)
        paths, trailing_slash = _paths(route.get("predicate"), sanitizer)
        if paths is None:
            gaps.add("GATEWAY_PREDICATE_UNSUPPORTED")
        if path_pattern is not None and not any(
            glob_matches(path_pattern, path) for path in paths or ()
        ):
            continue
        order = route.get("order")
        if type(order) is not int or not -(2**31) <= order < 2**31:
            order = None
            gaps.add("GATEWAY_ORDER_UNREADABLE")
        target_service = _service(route.get("uri"), sanitizer)
        if target_service is None:
            gaps.add("GATEWAY_DESTINATION_UNRESOLVED")
        items.append(
            {
                "id": f"gateway_route_{index:06d}",
                "routeId": route_id,
                "paths": paths,
                "matchTrailingSlash": trailing_slash,
                "order": order,
                "targetService": target_service,
            }
        )
    return items, sorted(gaps)
