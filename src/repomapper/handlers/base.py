"""Base LanguageHelper class"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from ..types import CtagEntry, ProcessDecision


class LanguageHandler(ABC):
    """Base class for language-specific symbol handling."""

    @abstractmethod
    def should_process_file(self, file_path: Path) -> ProcessDecision:
        """Determine if this handler should process the given file.

        Returns:
            ProcessDecision.PROCESS: Handler will process this file
            ProcessDecision.SKIP: Handler is responsible for this file type but declines to process
            ProcessDecision.UNHANDLED: Handler doesn't handle this type of file
        """
        pass

    @abstractmethod
    def categorize_symbol(self, entry: CtagEntry) -> Optional[str]:
        """Categorize a symbol entry into a section (e.g., 'Functions', 'Types')."""
        pass

    def filter_symbol(self, entry: CtagEntry) -> bool:
        """Filter out unwanted symbols. Can be overridden by specific handlers."""
        return True

    def get_symbol_description(self, entry: CtagEntry) -> str:
        """Get the formatted description of a symbol.
        Default implementation uses pattern or signature as-is."""
        signature = entry.get("signature", "")
        pattern = entry.get("pattern", "")
        if isinstance(pattern, str):
            pattern = pattern.strip("/^$/")
        return signature if signature else pattern

    def get_module_path(self, entry: CtagEntry) -> str:
        """Get the module path for a symbol.
        Default implementation returns empty string."""
        return ""

    def get_symbol_name(self, entry: CtagEntry) -> str:
        """Get the symbol name, potentially qualified.
        Default implementation returns raw name."""
        return entry["name"]
