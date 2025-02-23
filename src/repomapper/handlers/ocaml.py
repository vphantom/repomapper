"""OCamlHandler class"""

from pathlib import Path
from typing import List, Optional
from .base import CtagEntry, LanguageHandler, ProcessDecision


class OCamlHandler(LanguageHandler):
    """Handler for OCaml files."""

    def should_process_file(self, file_path: Path) -> ProcessDecision:
        # First check if we handle this file type
        if file_path.suffix not in {".mli", ".ml"}:
            return ProcessDecision.UNHANDLED

        # Skip .ml files that have .mli counterparts
        if file_path.suffix == ".ml":
            mli_path = file_path.parent / (file_path.stem + ".mli")
            exists = mli_path.exists()
            return ProcessDecision.SKIP if exists else ProcessDecision.PROCESS

        return ProcessDecision.PROCESS  # Always process .mli files

    def _get_module_path(self, entry: CtagEntry) -> List[str]:
        """Get the module path as a list of module names."""
        path = []
        scope = entry.get("scope", "")
        scope_kind = entry.get("scopeKind", "")

        # Handle different scope formats
        if scope:
            if scope.startswith("module:"):
                # Handle explicit module: prefix
                path = scope[7:].split(".")
            elif scope_kind == "module":
                # Handle module scopes without prefix
                path = scope.split(".")  # Split on dots for nested modules
            elif "/" in scope:
                # Handle type-scoped items (they use / as separator)
                module_parts = scope.split("/")[0:-1]  # Exclude the type name
                for part in module_parts:
                    if "." in part:  # Handle module.type format
                        path.extend(part.split("."))
                    else:
                        path.append(part)
            else:
                # Try to handle other scope formats
                parts = scope.split(".")
                if len(parts) > 1:
                    path = parts[:-1]  # Take all but the last part as module path

        # If this is a module definition itself, add it to the path
        if entry.get("kind") == "module":
            path.append(entry.get("name", ""))

        return path

    def _get_full_name(self, entry: CtagEntry) -> str:
        """Get the fully qualified name including module path."""
        name = entry.get("name", "")
        path = self._get_module_path(entry)

        if path:
            return f"{'.'.join(path)}.{name}"
        return name

    def categorize_symbol(self, entry: CtagEntry) -> Optional[str]:
        kind = entry.get("kind", "")
        name = self._get_full_name(entry)

        if kind in {"function", "val"}:
            # Separate operators from regular functions
            if all(c in "!@#$%^&*+-=<>/?|~" for c in name.split(".")[-1]):
                return "Operators"
            return "Functions"
        elif kind == "type":
            return "Types"
        elif kind == "exception":
            return "Exceptions"
        elif kind == "module":
            # All module declarations (including aliases) are modules
            return "Modules"
        return None

    def filter_symbol(self, entry: CtagEntry) -> bool:
        # Get pattern safely, some entries might not have it
        pattern = entry.get("pattern", "")
        if not isinstance(pattern, str):
            return True
        pattern = pattern.strip("/^$/")
        # Skip OCaml implementation details and docstrings
        return not (
            pattern.startswith("(**")
            or pattern.endswith("{")
            or pattern.endswith("= {")
        )

    def get_symbol_description(self, entry: CtagEntry) -> str:
        """Get formatted description, preferring signature over pattern."""
        signature = entry.get("signature", "")
        if signature:
            # Remove 'let' from the start of signatures
            return signature.replace("let ", "")
        pattern = entry.get("pattern", "")
        if isinstance(pattern, str):
            return pattern.strip("/^$/")
        return str(pattern)

    def get_module_path(self, entry: CtagEntry) -> str:
        """Get the module path as a dot-separated string."""
        path = self._get_module_path(entry)
        return ".".join(path) if path else ""

    def get_symbol_name(self, entry: CtagEntry) -> str:
        """Get the symbol name."""
        return entry["name"]
