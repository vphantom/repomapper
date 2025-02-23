"""Command line interface for the code map generator."""

import argparse
import os
import sys
from pathlib import Path
from .core import CodeMapper
from .ignore import IgnorePatternManager

PRODUCT_NAME = "Repo Mapper"
__version__ = "0.1.0"


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a map of code symbols from a directory using universal-ctags."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="directory to analyze (default: current directory)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="MAP.txt",
        help="output file path (default: MAP.txt, use - for stdout)",
    )
    parser.add_argument(
        "--version", action="version", version=f"{PRODUCT_NAME} v{__version__}"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="enable debug output"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list files that would be included in the map (one per line)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="when used with --list, also show excluded files",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.debug:
        print("DEBUG: Debug mode enabled", file=sys.stderr)
    directory = Path(args.directory)

    if not directory.is_dir():
        print(f"Error: {directory} is not a directory", file=sys.stderr)
        sys.exit(1)

    mapper = CodeMapper(debug=args.debug)

    if args.list:
        # Initialize exactly as generate_map() does
        mapper.output_file = None
        mapper.ignore_manager = IgnorePatternManager(directory)

        if args.debug:
            print("DEBUG: IgnoreManager initialized", file=sys.stderr)
            if mapper.ignore_manager.git_root:
                print(
                    f"DEBUG: Git root found at: {mapper.ignore_manager.git_root}",
                    file=sys.stderr,
                )
            else:
                print("DEBUG: No git root found", file=sys.stderr)
            print("DEBUG: Running ctags...", file=sys.stderr)

        mapper._run_ctags(directory)
        processable = mapper._get_processable_files(directory)

        if args.all:
            # Walk through all files
            for root, _, files in os.walk(directory):
                if args.debug:
                    print(f"DEBUG: Walking directory: {root}", file=sys.stderr)
                    print(f"DEBUG: Found files: {files}", file=sys.stderr)
                for file in files:
                    path = (Path(root) / file).resolve()
                    try:
                        # Use git root if available, otherwise use directory
                        base = (
                            mapper.ignore_manager.git_root
                            if mapper.ignore_manager.git_root
                            else directory
                        )
                        rel_path = path.relative_to(base)
                        status = "I" if path in processable else "."
                        print(f"{status} {rel_path}")
                    except ValueError:
                        print(f"E {path}")
                        continue
        else:
            # Just show included files
            for path in sorted(processable):
                try:
                    # Use git root if available, otherwise use directory
                    base = (
                        mapper.ignore_manager.git_root
                        if mapper.ignore_manager.git_root
                        else directory
                    )
                    rel_path = path.relative_to(base)
                    print(rel_path)
                except ValueError:
                    continue
        return

    if args.output == "-":
        mapper.generate_map(directory, sys.stdout)
    else:
        # Convert relative output path to absolute from git root or cwd
        output_file = Path(args.output)
        if not output_file.is_absolute():
            # If relative path, make it relative to git root or cwd
            mapper.generate_map(
                directory, output_path=args.output
            )  # This sets up ignore_manager
            base_dir = (
                mapper.ignore_manager.git_root
                if mapper.ignore_manager and mapper.ignore_manager.git_root
                else Path.cwd()
            )
            output_file = base_dir / output_file

        with output_file.open("w") as f:
            mapper.generate_map(directory, f, args.output)

        print(f"Created/updated: {output_file}")


if __name__ == "__main__":
    main()
