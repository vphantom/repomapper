"""IgnorePatternManager class"""

import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional
from .types import CompiledPattern


class IgnorePatternManager:
    """Manages .gitignore and .mapignore pattern handling.

    This class is responsible for:
    1. Finding the git root directory
    2. Loading and parsing .gitignore files from all directory levels
    3. Loading and parsing .mapignore from git root
    4. Determining if files should be ignored based on combined patterns
    """

    def __init__(self, start_path: Path):
        """Initialize with a starting path to locate git root from."""
        self.start_path = start_path.resolve()
        self.git_root = self.find_git_root()
        self.patterns_by_dir = self.collect_ignore_patterns() if self.git_root else {}

    def find_git_root(self) -> Optional[Path]:
        """Find the git root directory (containing .git/) by walking up from start_path.

        Returns:
            Path to git root directory if found, None otherwise

        Note:
            The .git directory might be a file in case of git worktrees or submodules.
            We consider the parent of .git as the root in all cases.
        """
        current = self.start_path

        while current != current.parent:
            git_dir = current / ".git"
            if git_dir.exists():
                return current
            current = current.parent

        root_git = current / ".git"
        return current if root_git.exists() else None

    def _parse_ignore_file(self, ignore_path: Path) -> List[str]:
        """Parse an ignore file (either .gitignore or .mapignore) into a list of patterns.

        Handles:
        - Empty lines and comments (ignored)
        - Basic glob patterns
        - Negation patterns (starting with !)
        - Directory-specific patterns (ending with /)

        Returns:
            List of valid ignore patterns found in the file
        """
        if not ignore_path.is_file():
            return []

        patterns = []
        with ignore_path.open() as f:
            for line in f:
                # Remove comments and whitespace
                line = line.split("#")[0].strip()
                if not line:
                    continue

                patterns.append(line)
        return patterns

    def collect_ignore_patterns(
        self, start_from: Optional[Path] = None
    ) -> Dict[Path, Dict[str, List[str]]]:
        """Collect all .gitignore and .mapignore patterns from the entire repository tree.

        This method performs a complete collection of ignore patterns by:
        1. Walking up from start_from to git root to collect ancestor patterns
        2. Walking down through all subdirectories to collect descendant patterns

        Args:
            start_from: Path to start collecting from (defaults to self.start_path)

        Returns:
            Dictionary mapping directory paths to their ignore patterns, where each
            directory contains a dict with 'git' and 'map' keys for the respective
            ignore patterns. All paths are relative to git root.

        Note:
            - Paths are processed from root to leaf, so more specific patterns
              (closer to target) will override more general ones when applied.
            - Both .gitignore and .mapignore use the same pattern syntax.
            - Patterns from deeper directories are automatically scoped to their location
        """
        if self.git_root is None:
            return {}

        start_from = start_from or self.start_path
        patterns_by_dir = defaultdict(lambda: {"git": [], "map": []})

        def check_directory(path: Path) -> None:
            """Check a directory for ignore files and add any patterns found."""
            rel_path = path.relative_to(self.git_root)
            # Use '.' for root directory instead of empty string
            key = Path(".") if path == self.git_root else rel_path

            for ignore_type, filename in [("git", ".gitignore"), ("map", ".mapignore")]:
                ignore_file = path / filename
                if ignore_file.is_file():
                    patterns = self._parse_ignore_file(ignore_file)
                    if patterns:
                        patterns_by_dir[key][ignore_type] = patterns

        # First, walk up to collect ancestor patterns
        current = start_from.resolve()
        while current >= self.git_root:
            check_directory(current)
            if current == self.git_root:
                break
            current = current.parent

        # Then, walk down to collect descendant patterns
        for root, dirs, _ in os.walk(start_from):
            root_path = Path(root)
            if ".git" in dirs:
                dirs.remove(".git")
            check_directory(root_path)

        return dict(patterns_by_dir)

    def _compile_pattern(
        self, pattern: str, source_dir: Path, source_type: str
    ) -> CompiledPattern:
        """Compile a single ignore pattern into a regex pattern.

        Args:
            pattern: The raw pattern string from the ignore file
            source_dir: Directory containing this pattern (relative to git root)
            source_type: Either 'git' or 'map'

        Returns:
            CompiledPattern with regex and pattern properties
        """
        is_negation = pattern.startswith("!")
        if is_negation:
            pattern = pattern[1:]

        is_dir_only = pattern.endswith("/")
        if is_dir_only:
            pattern = pattern[:-1]

        # Convert glob pattern to regex
        # 1. Escape special regex chars except * and ?
        regex = re.escape(pattern)
        # 2. Convert glob patterns to regex patterns
        # Handle glob patterns (order matters: ** must be handled before *)
        regex = regex.replace(r"\*\*", ".*")
        regex = regex.replace(r"\*", "[^/]*")
        regex = regex.replace(r"\?", "[^/]")
        # 3. Handle directory-specific patterns
        if is_dir_only:
            regex += "/.*"
        # 4. Anchor pattern appropriately
        if pattern.startswith("/"):
            regex = "^" + regex[1:] + "$"
        elif "/" in pattern:
            # Can match anywhere under source_dir
            regex = ".*/" + regex + "$"
        else:
            # Pattern without / can match any component
            regex = "(^|.*/?)" + regex + "($|/.*)"

        return CompiledPattern(
            pattern=pattern,
            regex=re.compile(regex),
            is_negation=is_negation,
            is_dir_only=is_dir_only,
            source_dir=source_dir,
            source_type=source_type,
        )

    def _compile_all_patterns(self) -> List[CompiledPattern]:
        """Compile all patterns from all ignore files.

        Returns patterns in order of precedence (more specific paths first).
        """
        all_patterns: List[CompiledPattern] = []

        # Get all directories with patterns, sorted by path depth (deepest first)
        dirs = sorted(
            self.patterns_by_dir.keys(), key=lambda p: len(p.parts), reverse=True
        )

        for dir_path in dirs:
            dir_patterns = self.patterns_by_dir[dir_path]
            for source_type in ["git", "map"]:
                for pattern in dir_patterns[source_type]:
                    compiled = self._compile_pattern(pattern, dir_path, source_type)
                    all_patterns.append(compiled)

        return all_patterns

    def should_ignore(self, path: Path) -> bool:
        """Determine if a path should be ignored based on all patterns.

        Args:
            path: Path to check, must be relative to git root

        Returns:
            True if path matches any non-negated pattern and no later
            negation pattern, False otherwise.
        """
        if not hasattr(self, "_compiled_patterns"):
            self._compiled_patterns = self._compile_all_patterns()

        path_str = str(path)
        is_ignored = False

        # Check each pattern in order (most specific first)
        for pattern in self._compiled_patterns:
            # Get the part of the path relative to the pattern's directory
            if pattern.source_dir == Path("."):
                rel_path = path_str
            else:
                # Only check patterns from directories that are ancestors of this path
                pattern_dir_str = str(pattern.source_dir)
                if not path_str.startswith(pattern_dir_str + "/"):
                    continue
                rel_path = path_str[len(pattern_dir_str) :]

            if pattern.regex.search(rel_path):
                is_ignored = not pattern.is_negation

        return is_ignored
