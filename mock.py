"""Compatibility shim for legacy ``mock`` imports.

The historical test suite imports ``mock`` as an external dependency, but on
modern Python versions the implementation lives in ``unittest.mock``.
Keeping this tiny shim in-repo avoids an unnecessary runtime dependency while
preserving backward-compatible imports.
"""

from unittest.mock import *  # noqa: F401,F403
