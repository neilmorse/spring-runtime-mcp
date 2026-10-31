"""Offline deterministic probe for opaque cursor rejection found during real soak.

Default success means the original defect reproduced; --expect-repaired instead
requires bounded rejection before cache registration.
No cursor, decoded bytes, credentials, or target response is printed or saved.
"""

from __future__ import annotations

import argparse
import base64
import json
import secrets
from pathlib import Path
from unittest.mock import patch

from spring_runtime_mcp.models.common import NormalizationError
from spring_runtime_mcp.models.queries import InspectBeansQuery
from spring_runtime_mcp.policy.sanitization import SanitizerPipeline
from spring_runtime_mcp.snapshots import SnapshotStore
from spring_runtime_mcp.transport.responses import serialize_response


def investigate(samples: int) -> dict[str, object]:
    pipeline = SanitizerPipeline()
    # Synthetic opaque bytes happen to resemble userinfo after base64 decoding.
    # Actual random cursors can have the same shape. Preserve the sink's rejection.
    candidate = (
        base64.urlsafe_b64encode(
            bytes([65]) * 14 + bytes([58, 66, 64]) + bytes([67]) * 15
        )
        .decode()
        .rstrip("=")
    )
    store = SnapshotStore()
    cursor: str | None = None
    registration_rejection: str | None = None
    with patch(
        "spring_runtime_mcp.snapshots.secrets.token_urlsafe", return_value=candidate
    ) as mint:
        try:
            cursor = store.put({"data": {"items": []}}, InspectBeansQuery())
        except NormalizationError as failure:
            registration_rejection = failure.code
        mint_attempts = mint.call_count
    rejection: str | None = None
    try:
        serialize_response({"nextCursor": cursor}, 1, sanitizer=pipeline)
    except NormalizationError as failure:
        rejection = failure.code
    rejected = sum(
        pipeline.high_risk(secrets.token_urlsafe(32)) for _ in range(samples)
    )
    return {
        "probe": "opaque-cursor-output-guard-conflict",
        "deterministicReproduced": rejection == "UNSAFE_OUTPUT",
        "candidateAcceptedByStore": cursor == candidate,
        "candidateRejectedAtWireSink": rejection,
        "randomSampleSize": samples,
        "randomCandidatesRejectedByGuard": rejected,
        "randomSampleIsNotAnErrorRateEstimateForAllTools": True,
        "candidateRejectedAtRegistration": registration_rejection,
        "registrationAttempts": mint_attempts,
        "unsafeHandleRegistrationPrevented": registration_rejection == "UNSAFE_OUTPUT"
        and cursor is None
        and store._size == 0
        and 1 <= mint_attempts <= 16,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--expect-repaired", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.samples <= 100_000:
        parser.error("--samples must be between 1 and 100000")
    result = investigate(args.samples)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    if args.expect_repaired:
        return 0 if result["unsafeHandleRegistrationPrevented"] else 1
    return 0 if result["deterministicReproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
