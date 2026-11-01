"""Operator entrypoint. Tool arguments cannot select the actuator origin."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import stat
import sys

from . import __version__
from .adapters.source_catalog import load_source_catalog
from .models.common import AnalysisBudget, NormalizationError
from .models.source_catalog import SourceCatalog
from .policy.configuration import ConfigReadPolicy
from .server import build_services, run_stdio
from .services import Services
from .transport.bounded_json import loads_bounded

SOURCE_CATALOG_MAX_BYTES = 262144

_CONFIG_HINTS = {
    "INVALID_BASE_URL": (
        "--base-url must be a plain http(s) origin without a path, query, "
        "credentials or fragment"
    ),
    "INVALID_TIMEOUT": "--timeout must be greater than 0 and at most 60 seconds",
    "INVALID_TARGET_REGISTRATION": "--target-id must match [A-Za-z0-9_-]{1,64}",
    "INVALID_CREDENTIAL_REGISTRATION": (
        "--token-env names an environment variable whose value is not a "
        "supported Bearer token"
    ),
    "ADDRESS_DENIED": (
        "--base-url must resolve only to loopback addresses (127.0.0.0/8 or ::1)"
    ),
    "SOURCE_TARGET_MISMATCH": "--source-catalog targetId must equal --target-id",
}


class ConfigurationError(Exception):
    """Operator-facing startup failure; text never contains a value."""


def _timeout(value: str) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        raise ConfigurationError(_CONFIG_HINTS["INVALID_TIMEOUT"]) from None
    if not 0 < timeout <= 60:
        raise ConfigurationError(_CONFIG_HINTS["INVALID_TIMEOUT"])
    return timeout


def _bearer(name: str | None) -> str | None:
    if name is None:
        return None
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", name) is None:
        raise ConfigurationError(
            "--token-env must be a valid environment variable name"
        )
    token = os.environ.get(name)
    if not token:
        raise ConfigurationError(
            "environment variable named by --token-env is missing or empty; "
            "supply it in the parent client environment and forward its name "
            "to the MCP subprocess (Codex: env_vars). Do not put the token "
            "value in arguments or client configuration"
        )
    return token


def _read_source_catalog(path: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ConfigurationError("--source-catalog must name a regular file")
        chunks: list[bytes] = []
        remaining = SOURCE_CATALOG_MAX_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
    finally:
        os.close(descriptor)
    if sum(map(len, chunks)) > SOURCE_CATALOG_MAX_BYTES:
        raise ConfigurationError(
            f"--source-catalog exceeds {SOURCE_CATALOG_MAX_BYTES} bytes"
        )
    return b"".join(chunks)


def _catalog(path: str, target_id: str) -> SourceCatalog:
    try:
        payload = loads_bounded(
            _read_source_catalog(path), max_bytes=SOURCE_CATALOG_MAX_BYTES
        )
        return load_source_catalog(
            payload, target_id=target_id, budget=AnalysisBudget()
        )
    except ConfigurationError:
        raise
    except OSError:
        raise ConfigurationError(
            "--source-catalog could not be opened or read"
        ) from None
    except (NormalizationError, UnicodeError) as exc:
        code = (
            exc.code
            if isinstance(exc, NormalizationError)
            else "INVALID_SOURCE_CATALOG"
        )
        raise ConfigurationError(f"--source-catalog is invalid ({code})") from None


def _config_policy(args: argparse.Namespace) -> ConfigReadPolicy | None:
    enabled = (
        args.config_prefix
        or args.config_property
        or args.config_profiles
        or args.config_allow_values
    )
    if not enabled:
        return None
    if not (args.config_prefix or args.config_property or args.config_profiles):
        raise ConfigurationError(
            "--config-allow-values requires --config-prefix, --config-property "
            "or --config-profiles"
        )
    try:
        return ConfigReadPolicy(
            properties=frozenset(args.config_property),
            prefixes=frozenset(args.config_prefix),
            allow_values=args.config_allow_values,
            profiles=args.config_profiles,
        )
    except ValueError:
        raise ConfigurationError(
            "--config-prefix, --config-property and --config-profiles must use "
            "valid registration names"
        ) from None


def _services(
    args: argparse.Namespace,
    *,
    timeout: float,
    catalog: SourceCatalog | None,
    config_policy: ConfigReadPolicy | None,
    bearer_token: str | None,
) -> Services:
    try:
        return build_services(
            args.base_url,
            args.target_id,
            timeout,
            source_catalog=catalog,
            config_policy=config_policy,
            bearer_token=bearer_token,
        )
    except NormalizationError as exc:
        raise ConfigurationError(
            _CONFIG_HINTS.get(exc.code, "target registration is invalid")
        ) from None
    except ValueError as exc:
        raise ConfigurationError(
            _CONFIG_HINTS.get(str(exc), "server configuration is invalid")
        ) from None


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="spring-runtime-mcp")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SPRING_RUNTIME_BASE_URL", "http://127.0.0.1:18081"),
    )
    parser.add_argument(
        "--target-id",
        default=os.environ.get("SPRING_RUNTIME_TARGET_ID", "local"),
    )
    parser.add_argument(
        "--timeout",
        default=os.environ.get("SPRING_RUNTIME_TIMEOUT", "5"),
    )
    parser.add_argument(
        "--source-catalog",
        default=os.environ.get("SPRING_RUNTIME_SOURCE_CATALOG"),
        help="Operator-registered JSON workspace facts for this target.",
    )
    parser.add_argument(
        "--token-env",
        help="Name of the environment variable holding this target's Bearer token.",
    )
    parser.add_argument(
        "--config-prefix",
        action="append",
        default=[],
        metavar="PREFIX",
        help="Register one property prefix for opt-in config diagnostics.",
    )
    parser.add_argument(
        "--config-property",
        action="append",
        default=[],
        metavar="KEY",
        help="Register one property key for opt-in config diagnostics.",
    )
    parser.add_argument(
        "--config-profiles",
        action="store_true",
        help="Allow reading active profiles for drift comparison.",
    )
    parser.add_argument(
        "--config-allow-values",
        action="store_true",
        help="Allow registered config values after sanitization (off by default).",
    )
    args = parser.parse_args(argv)
    try:
        timeout = _timeout(args.timeout)
        bearer_token = _bearer(args.token_env)
        catalog = (
            _catalog(args.source_catalog, args.target_id)
            if args.source_catalog
            else None
        )
        config_policy = _config_policy(args)
        services = _services(
            args,
            timeout=timeout,
            catalog=catalog,
            config_policy=config_policy,
            bearer_token=bearer_token,
        )
    except ConfigurationError as exc:
        sys.stderr.write(f"spring-runtime-mcp: {exc}\n")
        raise SystemExit(2) from None
    try:
        asyncio.run(run_stdio(services))
    except KeyboardInterrupt:
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
