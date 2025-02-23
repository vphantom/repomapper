"""MarkdownHandler class"""

import re
from pathlib import Path
from typing import List, Optional, Tuple
from .base import CtagEntry, LanguageHandler, ProcessDecision


class MarkdownHandler(LanguageHandler):
    """Handler for Markdown files with direct header parsing."""

    def should_process_file(self, file_path: Path) -> ProcessDecision:
        return (
            ProcessDecision.PROCESS
            if file_path.suffix == ".md"
            else ProcessDecision.UNHANDLED
        )

    def categorize_symbol(self, entry: CtagEntry) -> Optional[str]:
        # Not used - we override the normal ctags processing
        return None

    def extract_headers(self, file_path: Path) -> List[Tuple[int, int, str]]:
        """Extract headers from Markdown file.
        Returns list of (line_number, level, header_text) tuples,
        sorted by line number.
        """
        headers = []
        with file_path.open() as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if line.startswith("#"):
                    # Match headers of level 1-3, allowing for leading whitespace
                    match = re.match(r"^(#{1,3})\s+(.+)$", line)
                    if match:
                        level = len(match.group(1))
                        if level <= 3:
                            headers.append((i, level, match.group(2)))
        return sorted(headers)  # Sort by line number
