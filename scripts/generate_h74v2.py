#!/usr/bin/env python3
"""Fail-closed replacement for the legacy synthetic H74-1v2 generator.

The former script could fall back to synthetic fields/footprints/targets and write an
internal READY receipt. That is not a valid competition prediction or organizer
receipt. This command is disabled until official features and authorized template /
labels can be consumed by a compliant, real-data model and holdout.
"""
import sys


def main() -> int:
    print("BLOCKED: H74-1v2 generation is not scientifically validated.", file=sys.stderr)
    print(
        "The legacy implementation used synthetic geological fields and synthetic hidden truth; "
        "the mirror footprint/catalogue provenance is not organizer-authenticated.",
        file=sys.stderr,
    )
    print(
        "No competition TIFF or READY receipt was generated. Use authorized official data and "
        "implement the required buffered segment holdout first.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
