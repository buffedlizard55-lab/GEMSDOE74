"""gems74: submission format validator and writer for the DOE GEMS Prize (DrivenData #306).

The metric lives in ``src/gems74/metric.py`` (single implementation, shared by all sessions).
"""

from .submission import (  # noqa: F401
    EXPECTED_CRS,
    EXPECTED_SHAPE,
    EXPECTED_TRANSFORM,
    validate_submission,
    write_submission,
)
