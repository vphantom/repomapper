"""Core CodeMapper class"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set
from .symbols import Symbol, SymbolTree
from .ignore import IgnorePatternManager
from .types import CtagEntry, ProcessDecision
from .handlers import (
    GenericHandler,
    LanguageHandler,
    MarkdownHandler,
    OCamlHandler,
    ShellHandler,
)


class CodeMapper:
    """Main class for generating code maps."""

    def __init__(self, debug=False):
        self.debug = debug
        self.generic_handler = GenericHandler(debug=debug)
        self.handlers: Dict[str, LanguageHandler] = {
            "OCaml": OCamlHandler(),
            "Sh": ShellHandler(),
            "Markdown": MarkdownHandler(),
        }
        self.processed_files: Set[Path] = set()
        self.ignore_manager: Optional[IgnorePatternManager] = None
        # Symbol tree for each file
        self.file_trees: Dict[Path, SymbolTree] = {}

    def _run_ctags(self, directory: Path) -> List[CtagEntry]:
        """Run ctags and get JSON output."""
        cmd = [
            "ctags",
            "--output-format=json",
            "--fields=*",
            "--fields=+S",  # Ensure scope field is included for Python
            "--extras=*",
            "--kinds-Python=+vm",  # Include variables and class members
            "-R",
            str(directory),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Parse JSON lines (one JSON object per line)
            entries = []
            for line in result.stdout.splitlines():
                if line.strip():
                    entries.append(json.loads(line))
            return entries
        except subprocess.CalledProcessError as e:
            print(f"Error running ctags: {e}", file=sys.stderr)
            sys.exit(1)

    def _get_file_info(self, file_path: Path) -> str:
        """Get file metadata."""
        try:
            line_count = sum(1 for _ in file_path.open())
            return f"  Size: {line_count} lines"
        except Exception as e:
            return f"  Error reading file: {e}"

    def _get_processable_files(self, directory: Path) -> Set[Path]:
        """Get all files that can be processed by our handlers.

        Files are filtered based on:
        1. Hidden files/directories (starting with .)
        2. Patterns from .gitignore and .mapignore files
        3. Whether any handler can process them
        """
        if self.ignore_manager is None or self.ignore_manager.git_root is None:
            # If we're not in a git repo, fall back to basic filtering
            use_ignore_patterns = False
        else:
            use_ignore_patterns = True
            git_root = self.ignore_manager.git_root

        files = set()
        for root, _, filenames in os.walk(directory):
            root_path = Path(root)
            # Skip hidden directories
            if any(part.startswith(".") for part in root_path.parts):
                continue

            for filename in filenames:
                # Skip hidden files
                if filename.startswith("."):
                    continue

                file_path = (root_path / filename).resolve()

                # Skip the output file itself if it's a path (not stdout or -)
                if (
                    (output_file := getattr(self, "output_file", None))
                    and isinstance(output_file, (str, Path))
                    and output_file != "-"
                ):
                    if Path(filename) == Path(output_file).name:
                        continue
                    if file_path == Path(output_file).resolve():
                        continue

                if use_ignore_patterns:
                    try:
                        rel_path = file_path.relative_to(git_root)
                        if self.ignore_manager.should_ignore(rel_path):
                            continue
                    except ValueError:
                        # If file is not under git_root, skip ignore pattern check
                        pass
                handled = False
                for handler in self.handlers.values():
                    decision = handler.should_process_file(file_path)
                    if decision == ProcessDecision.PROCESS:
                        files.add(file_path)
                        handled = True
                        break
                    elif decision == ProcessDecision.SKIP:
                        handled = True
                        break

                if not handled:
                    decision = self.generic_handler.should_process_file(file_path)
                    if decision == ProcessDecision.PROCESS:
                        files.add(file_path)
        return files

    def _setup_output_file(self, output_path: str) -> Path:
        """Prepare the output file location and handle backup if needed.

        Args:
            output_path: Path to the desired output file

        Returns:
            Path to the output file to use
        """
        # Use git root if available, otherwise current directory
        base_dir = (
            self.ignore_manager.git_root
            if self.ignore_manager and self.ignore_manager.git_root
            else Path.cwd()
        )
        map_file = base_dir / output_path
        backup_file = Path(str(map_file) + "~")

        if map_file.exists():
            if backup_file.exists():
                backup_file.unlink()
            map_file.rename(backup_file)

        return map_file

    def generate_map(self, directory: Path, output_file=None, output_path="MAP.txt"):
        """Generate the code map and write to file.

        Args:
            directory: Directory to analyze
            output_file: File object to write to, or None to create a new file
            output_path: Path to output file if output_file is None
        """
        self.output_file = output_file
        self.ignore_manager = IgnorePatternManager(directory)
        entries = self._run_ctags(directory)
        all_files = self._get_processable_files(directory)

        # Group entries by file and module path
        files_dict: Dict[Path, Dict[str, Dict[str, List[Symbol]]]] = {}

        for file_path in all_files:
            files_dict[file_path] = {}

        for entry in entries:
            file_path = Path(entry["path"]).resolve()
            if not file_path.exists() or file_path not in all_files:
                continue

            language = entry.get("language")
            handler = self.handlers.get(language, self.generic_handler)

            if not handler.should_process_file(file_path):
                continue

            if not handler.filter_symbol(entry):
                continue

            category = handler.categorize_symbol(entry)
            if not category:
                continue

            # Get description, module path and name using handler methods
            desc = handler.get_symbol_description(entry)
            module_path = handler.get_module_path(entry)
            name = handler.get_symbol_name(entry)

            # Extract inheritance info from typeref
            inherits_from = []
            if typeref := entry.get("typeref"):
                # Format is typically "typename:BaseClass"
                if ":" in typeref:
                    inherits_from = [typeref.split(":")[-1]]

            symbol = Symbol(
                name=name,
                kind=entry["kind"],
                pattern=desc,
                line=entry.get("line", 0),  # Default to 0 if line number is missing
                scope=entry.get("scope"),
                signature=entry.get("signature"),
                type_ref=entry.get("typeref"),
                inherits_from=inherits_from,
            )

            # Initialize symbol tree for this file if needed
            if file_path not in self.file_trees:
                self.file_trees[file_path] = SymbolTree()

            # Add symbol to tree with proper scope
            scope = entry.get("scope")
            self.file_trees[file_path].add_symbol(symbol, scope)

            # Also maintain the old structure for now
            if module_path not in files_dict[file_path]:
                files_dict[file_path][module_path] = {}
            if category not in files_dict[file_path][module_path]:
                files_dict[file_path][module_path][category] = []
            # Don't add module declarations as symbols when they're already section headers
            if not (category == "Modules" and symbol.name == module_path):
                files_dict[file_path][module_path][category].append(symbol)

        if output_file:
            self._write_map(output_file, files_dict)
        else:
            output_file = self._setup_output_file(output_path)
            with output_file.open("w") as f:
                self._write_map(f, files_dict)

    def _get_symbol_category(self, symbol: Symbol) -> str:
        """Determine the category for a symbol based on its kind and properties."""
        kind = symbol.kind

        if kind in {"class", "struct", "interface", "c"}:
            return "Classes"
        elif kind in {"function", "f"}:
            if symbol.parent:  # Method of a class
                return "Methods"
            return "Functions"
        elif kind in {"variable", "field", "v"}:
            if symbol.parent:  # Class member
                return "Class Variables"
            elif symbol.name.isupper():  # Constants
                return "Constants"
            return "Variables"
        elif kind in {"namespace", "package", "module", "i"}:
            return "Modules"

        return kind.title()

    def _write_map(self, output, files_dict):
        """Write the map to the given output file object."""
        print(
            """# This file was automatically generated. Do not edit manually.
# See: https://github.com/vphantom/repomapper
#
# Each section describes a file and each line begins with (line_number).""",
            file=output,
        )

        def write_symbol_tree(symbol: Symbol, indent_level: int = 0) -> None:
            """Recursively write a symbol and its children."""
            # Check for duplicates before doing anything else
            if symbol.parent is not None:
                # Skip duplicate detection for enum members
                is_enum_member = (
                    symbol.parent.kind == "class"
                    and "enum" in symbol.parent.pattern.lower()
                    and symbol.kind == "variable"
                )

                if not is_enum_member:
                    base_name = symbol.name.split(".")[-1]

                    for sibling in symbol.parent.children:
                        if sibling == symbol:  # Skip self-comparison
                            continue

                        sibling_base = sibling.name.split(".")[-1]
                        is_duplicate = (
                            sibling_base == base_name
                            and sibling.kind == symbol.kind
                            and (
                                sibling.pattern == symbol.pattern
                                or sibling.signature == symbol.signature
                            )
                        )

                        if is_duplicate:
                            return

            indent = "  " * indent_level
            desc = symbol.pattern.strip()
            if symbol.signature:
                desc = symbol.signature

            # Clean up trailing comments
            desc = re.sub(r"\s*[#//].*$", "", desc.rstrip())

            # Clean up type hints
            desc = re.sub(r"\(inherits from: .*?\)", "", desc)
            desc = re.sub(r": Optional\[(.*?)\]", r"?: \1", desc)  # Optional[T] -> T?
            desc = re.sub(r": List\[(.*?)\]", r": \1[]", desc)  # List[T] -> T[]
            desc = re.sub(
                r": Dict\[(.*?),(.*?)\]", r": {\1: \2}", desc
            )  # Dict[K,V] -> {K: V}

            # Show inheritance if present
            if symbol.inherits_from:
                desc = f"{desc} inherits from {', '.join(symbol.inherits_from)}"

            # Don't show duplicated name in description if it matches the symbol name
            if desc.startswith(f"{symbol.name}:"):
                desc = desc[len(symbol.name) + 1 :].strip()

            # Handle fully qualified names (e.g. Symbol.scope vs scope)
            simple_name = (
                symbol.name.split(".")[-1] if "." in symbol.name else symbol.name
            )

            print(f"{indent}({symbol.line}) {simple_name}: {desc}", file=output)

            # Sort children by kind, then line number
            sorted_children = sorted(
                symbol.children, key=lambda s: (self._get_symbol_category(s), s.line)
            )

            # Group children by kind, filtering duplicates
            children_by_kind = {}
            seen_symbols = set()
            for child in sorted_children:
                symbol_id = (child.name, child.kind, child.signature)
                if symbol_id in seen_symbols:
                    continue
                seen_symbols.add(symbol_id)
                kind = self._get_symbol_category(child)
                if kind not in children_by_kind:
                    children_by_kind[kind] = []
                children_by_kind[kind].append(child)

            for kind in sorted(children_by_kind.keys()):
                if children_by_kind[kind]:  # Only print categories with children
                    print(f"{indent}  {kind}:", file=output)
                    for child in sorted(children_by_kind[kind], key=lambda s: s.line):
                        write_symbol_tree(child, indent_level + 2)

        for file_path in sorted(files_dict.keys()):
            # Skip the output file itself if it's a regular file
            if hasattr(output, "name") and file_path != Path(output.name).resolve():
                try:
                    rel_path = file_path.relative_to(self.ignore_manager.start_path)
                    display_path = rel_path
                except ValueError:
                    display_path = file_path
                print(f"\n{display_path}:", file=output)
                print(self._get_file_info(file_path), file=output)

            # Special handling for Markdown files
            if file_path.suffix == ".md":
                md_handler = MarkdownHandler()
                headers = md_handler.extract_headers(file_path)
                for line_num, level, header_text in headers:
                    indent = "  " * level
                    print(f"{indent}({line_num}) {header_text}", file=output)
                continue

            # Check if any language-specific handler wants to process this file
            handler = None
            for lang_handler in self.handlers.values():
                if (
                    lang_handler.should_process_file(file_path)
                    == ProcessDecision.PROCESS
                ):
                    handler = lang_handler
                    break

            if handler:
                # Use old structure for language-specific handlers
                for module_path in sorted(files_dict[file_path].keys()):
                    if module_path:
                        print(f"  Module {module_path}:", file=output)
                        indent = "    "
                    else:
                        indent = "  "

                    categories = files_dict[file_path][module_path]
                    for category in sorted(categories.keys()):
                        symbols = sorted(categories[category], key=lambda s: s.line)
                        if symbols:
                            print(f"{indent}{category}:", file=output)
                            for symbol in symbols:
                                desc = symbol.pattern.strip()
                                if symbol.signature:
                                    desc = symbol.signature
                                print(
                                    f"{indent}  ({symbol.line}) {symbol.name}: {desc}",
                                    file=output,
                                )
            # Use symbol tree for files handled by generic handler
            elif file_path in self.file_trees:
                tree = self.file_trees[file_path]
                # Sort root symbols by category then line number
                root_symbols = sorted(
                    tree.root_symbols.values(),
                    key=lambda s: (self._get_symbol_category(s), s.line),
                )

                by_category = {}
                for symbol in root_symbols:
                    category = self._get_symbol_category(symbol)
                    if category not in by_category:
                        by_category[category] = []
                    by_category[category].append(symbol)

                for category in sorted(by_category.keys()):
                    if category in {"Unknown", "File"} and not self.debug:
                        continue
                    print(f"  {category}:", file=output)
                    for symbol in by_category[category]:
                        write_symbol_tree(symbol, indent_level=2)
