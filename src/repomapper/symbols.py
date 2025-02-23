"""Symbol and SymbolTree classes for code mapping."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Symbol:
    """Represents a code symbol with its metadata."""

    name: str
    kind: str
    pattern: str
    line: int
    scope: Optional[str] = None
    signature: Optional[str] = None
    type_ref: Optional[str] = None

    # Relationship tracking
    parent: Optional["Symbol"] = None
    children: List["Symbol"] = None
    inherits_from: List[str] = None

    def __post_init__(self):
        """Initialize collections after basic initialization."""
        if self.children is None:
            self.children = []
        if self.inherits_from is None:
            self.inherits_from = []

    def add_child(self, child: "Symbol") -> None:
        """Add a child symbol and set its parent."""
        child_base = child.name.split(".")[-1]

        for existing in self.children:
            existing_base = existing.name.split(".")[-1]
            if (
                existing_base == child_base
                and existing.kind == child.kind
                and (
                    existing.pattern == child.pattern
                    or existing.signature == child.signature
                )
            ):
                return

        self.children.append(child)
        child.parent = self


class SymbolTree:
    """Manages hierarchical relationships between symbols."""

    def __init__(self):
        self.root_symbols: Dict[str, Symbol] = {}  # Keyed by fully qualified name
        self.scope_map: Dict[str, Symbol] = {}

    def add_symbol(self, symbol: Symbol, scope: Optional[str] = None) -> None:
        """Add a symbol to the tree, maintaining proper relationships."""
        if scope:
            scope_parts = scope.split(".")
            current_scope = ""
            current_parent = None

            for part in scope_parts:
                current_scope = f"{current_scope}.{part}" if current_scope else part
                parent = self.scope_map.get(current_scope)
                if parent:
                    current_parent = parent

            if current_parent:
                current_parent.add_child(symbol)
            else:
                self.root_symbols[symbol.name] = symbol
        else:
            self.root_symbols[symbol.name] = symbol

        full_name = f"{scope}.{symbol.name}" if scope else symbol.name

        if symbol.kind in {"class", "struct", "interface", "namespace", "module", "c"}:
            self.scope_map[full_name] = symbol
            if symbol.name not in self.scope_map:
                self.scope_map[symbol.name] = symbol

    def get_symbol(self, name: str) -> Optional[Symbol]:
        """Get a symbol by its fully qualified name."""
        return self.root_symbols.get(name) or self.scope_map.get(name)
