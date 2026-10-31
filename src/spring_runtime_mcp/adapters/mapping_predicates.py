"""Bounded projection of known positive WebFlux predicate conjunctions."""

from __future__ import annotations

import re
from typing import Any

from ..models.common import AnalysisBudget

HTTP_METHODS = frozenset(
    {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"}
)
_MAX_LENGTH = 4096
_MAX_DEPTH = 16
_MAX_CLAUSES = 32
_MAX_CONDITIONS = 16
_LEGACY_CONDITION = re.compile(
    r"(?P<kind>consumes|produces|headers|params)\s*\[(?P<value>.*)\]\Z"
)
_LEGACY_KIND = {
    "consumes": "consumes",
    "produces": "produces",
    "headers": "header",
    "params": "param",
}
# Quoted parameters and custom header predicates remain unsupported. Keeping
# alternatives in one header row preserves their set rather than inventing ANDs.
_TOKEN = r"[A-Za-z0-9!#$%&'*+.^_`|~-]+"
_MEDIA = re.compile(rf"{_TOKEN}/{_TOKEN}(?:;{_TOKEN}={_TOKEN})*\Z")


class _UnsupportedPredicate(Exception):
    pass


class _Conjunction:
    def __init__(self, text: str) -> None:
        self.text = text
        self.position = 0
        self.nodes = 0
        self.leaves: list[str] = []
        self.budget = AnalysisBudget()

    def _space(self) -> None:
        while self.position < len(self.text) and self.text[self.position] == " ":
            self.position += 1

    def expression(self, depth: int = 0) -> None:
        self.atom(depth)
        while True:
            self._space()
            if self.text.startswith("&&", self.position):
                self.position += 2
            elif self.text.startswith(",", self.position):
                # Retain the existing flat request-mapping spelling as well.
                self.position += 1
            else:
                return
            self.atom(depth)

    def atom(self, depth: int) -> None:
        self.budget.consume()
        self.nodes += 1
        if depth > _MAX_DEPTH or self.nodes > 2 * _MAX_CLAUSES:
            raise _UnsupportedPredicate
        self._space()
        if self.position >= len(self.text):
            raise _UnsupportedPredicate
        if self.text[self.position] == "(":
            if depth >= _MAX_DEPTH:
                raise _UnsupportedPredicate
            self.position += 1
            self.expression(depth + 1)
            self._space()
            if not self.text.startswith(")", self.position):
                raise _UnsupportedPredicate
            self.position += 1
            return
        start = self.position
        delimiters: list[str] = []
        while self.position < len(self.text):
            char = self.text[self.position]
            if not delimiters and (
                char in "()," or self.text.startswith(("&&", "||"), self.position)
            ):
                break
            if char in "[{" or (char == "(" and delimiters):
                delimiters.append({"[": "]", "{": "}", "(": ")"}[char])
                if depth + len(delimiters) > _MAX_DEPTH:
                    raise _UnsupportedPredicate
            elif char in "]})":
                if not delimiters or delimiters.pop() != char:
                    raise _UnsupportedPredicate
            self.position += 1
        leaf = self.text[start : self.position].strip()
        if not leaf or delimiters or len(self.leaves) >= _MAX_CLAUSES:
            raise _UnsupportedPredicate
        self.leaves.append(leaf)

    def parse(self) -> list[str]:
        self.expression()
        self._space()
        if self.position != len(self.text):
            raise _UnsupportedPredicate
        return self.leaves


def _media_condition(leaf: str) -> dict[str, Any] | None:
    name, separator, value = leaf.partition(":")
    if name not in {"Accept", "Content-Type"} or not separator:
        return None
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    media = [part.strip() for part in value.split(",")]
    value = ",".join(media)
    if (
        not media
        or len(value) > 256
        or any(not _MEDIA.fullmatch(part) for part in media)
    ):
        raise _UnsupportedPredicate
    return {"kind": "header", "name": name, "value": value, "negated": False}


def parse_predicate(
    raw: Any,
) -> tuple[list[str], list[str], list[dict[str, Any]], bool]:
    """Return no asserted facts unless every positive AND clause is understood.

    Different path predicates in an AND may describe intersections and cannot be
    emitted as a list of alternative paths. OR/NOT/custom clauses likewise stay
    unknown instead of turning branches into nonexistent method/path pairs.
    """
    if (
        not isinstance(raw, str)
        or not raw
        or len(raw) > _MAX_LENGTH
        or any(ord(char) < 32 or ord(char) == 127 for char in raw)
    ):
        return [], [], [], False
    text = raw.strip()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
    paths: list[str] = []
    methods: set[str] | None = None
    conditions: list[dict[str, Any]] = []
    try:
        for leaf in _Conjunction(text).parse():
            token, _, rest = leaf.partition(" ")
            method_set: set[str] | None = None
            if leaf.startswith("[") and leaf.endswith("]"):
                values = [part.strip() for part in leaf[1:-1].split(",")]
                if values and all(value in HTTP_METHODS for value in values):
                    method_set = set(values)
                    rest = ""
            elif token.upper() in HTTP_METHODS:
                method_set = {token.upper()}
                rest = rest.strip()
            if method_set is not None:
                methods = method_set if methods is None else methods & method_set
                if not methods:
                    raise _UnsupportedPredicate
                if not rest:
                    continue
                leaf = (
                    rest[1:-1].strip()
                    if rest.startswith("[") and rest.endswith("]")
                    else rest
                )
                if not leaf.startswith("/"):
                    raise _UnsupportedPredicate
            if leaf.startswith("/"):
                if len(leaf) > 1024 or any(char.isspace() for char in leaf):
                    raise _UnsupportedPredicate
                if paths and leaf not in paths:
                    raise _UnsupportedPredicate
                if not paths:
                    paths.append(leaf)
                continue
            condition = _media_condition(leaf)
            if condition is None:
                matched = _LEGACY_CONDITION.fullmatch(leaf)
                if matched is None or len(matched.group("value")) > 256:
                    raise _UnsupportedPredicate
                condition = {
                    "kind": _LEGACY_KIND[matched.group("kind")],
                    "name": None,
                    "value": matched.group("value").strip() or None,
                    "negated": False,
                }
            if len(conditions) >= _MAX_CONDITIONS:
                raise _UnsupportedPredicate
            conditions.append(condition)
    except _UnsupportedPredicate:
        return [], [], [], False
    if not paths:
        # A method/header-only predicate leaves the path unrestricted. The
        # current route projection cannot express that for exact path queries.
        return [], [], [], False
    return paths, sorted(methods or ()), conditions, True
