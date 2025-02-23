"""Type definitions used across the codebase."""

from enum import Enum
from pathlib import Path
from typing import NamedTuple, TypedDict
import re


class ProcessDecision(Enum):
    """Decision on whether to process a file."""

    PROCESS = 1  # Yes, process this file
    SKIP = 2  # No, skip this file (handler is responsible but declines)
    UNHANDLED = 3  # Handler doesn't handle this type of file


class CtagEntry(TypedDict, total=False):
    """Type definition for a ctag entry from JSON output."""

    name: str
    path: str
    pattern: str
    kind: str
    line: int
    scope: str
    language: str
    access: str
    signature: str
    typeref: str


class CompiledPattern(NamedTuple):
    """Represents a compiled ignore pattern with its properties."""

    pattern: str  # Original pattern string
    regex: re.Pattern  # Compiled regex for matching
    is_negation: bool  # True if pattern starts with !
    is_dir_only: bool  # True if pattern ends with /
    source_dir: Path  # Directory containing this pattern (relative to git root)
    source_type: str  # 'git' or 'map'
