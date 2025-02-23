"""
Language-specific handlers for code mapping.
"""

from .base import LanguageHandler
from .generic import GenericHandler
from .ocaml import OCamlHandler
from .shell import ShellHandler
from .markdown import MarkdownHandler

__all__ = [
    "GenericHandler",
    "LanguageHandler",
    "OCamlHandler",
    "ShellHandler",
    "MarkdownHandler",
]
