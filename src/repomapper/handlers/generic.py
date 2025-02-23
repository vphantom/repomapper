"""GenericHandler class"""

import sys
from pathlib import Path
from typing import Optional
from .base import CtagEntry, LanguageHandler, ProcessDecision


class GenericHandler(LanguageHandler):
    """Generic handler for any language supported by ctags."""

    def __init__(self, debug=False):
        """Initialize generic handler."""
        self.debug = debug

    def should_process_file(self, file_path: Path) -> ProcessDecision:
        """Accept any file that ctags might process."""
        # Accept files with extensions (skip extensionless files except shell scripts)
        if bool(file_path.suffix) or file_path.name.endswith(("sh", "bash")):
            return ProcessDecision.PROCESS
        return ProcessDecision.UNHANDLED

    def categorize_symbol(self, entry: CtagEntry) -> Optional[str]:
        """Categorize symbols based on their ctags kind.

        Categories are based on analysis of ctags kinds across languages:
        - Python: c(class) f(function) m(member) v(variable) i(module) ...
        """
        kind = entry.get("kind", "")

        # Handle imports and unknown symbols
        if kind in {"I", "x", "unknown", "module"} or entry.get("roles") == "imported":
            return "Unknown" if self.debug else None

        # Structural elements
        if kind in {"class", "struct", "interface", "c"}:
            return "Types"
        elif kind in {"namespace", "package", "i"}:
            return "Modules"

        # Callable elements
        elif kind in {"function", "method", "member", "f", "m"}:
            return "Functions"

        # Data elements
        elif kind in {"variable", "field", "v"}:
            return "Variables"

        # For unknown kinds, only show in debug mode
        if not kind:
            if self.debug:
                print(f"DEBUG: No kind found for {entry.get('name')}", file=sys.stderr)
            return None
        return kind.title() if self.debug else None

    def filter_symbol(self, entry: CtagEntry) -> bool:
        """Filter out unwanted symbols based on generic criteria."""
        # Check access level if available
        if access := entry.get("access"):
            if access in {"private", "protected"}:
                return False

        # Basic filtering of common implementation details
        pattern = entry.get("pattern", "")
        if not isinstance(pattern, str):
            return True
        # Filter out common noise like closing braces
        return not pattern.strip("/^$/").endswith("{")


"""Generic handler class"""
