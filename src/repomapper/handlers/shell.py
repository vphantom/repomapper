"""Handlers for Shell scripts."""

from pathlib import Path
from typing import Optional
from .base import CtagEntry, LanguageHandler, ProcessDecision


class ShellHandler(LanguageHandler):
    """Handler for Shell scripts."""

    def should_process_file(self, file_path: Path) -> ProcessDecision:
        if file_path.suffix in {".sh", ".bash"} or (
            file_path.suffix == "" and file_path.name.endswith(("sh", "bash"))
        ):
            return ProcessDecision.PROCESS
        return ProcessDecision.UNHANDLED

    def categorize_symbol(self, entry: CtagEntry) -> Optional[str]:
        kind = entry.get("kind", "")
        pattern = entry.get("pattern", "")

        if kind == "function":
            # Only show actual function definitions, not variable assignments
            if isinstance(pattern, str) and (
                "function " in pattern or pattern.endswith("() {")
            ):
                return "Functions"
        return None
