#!/usr/bin/env python3
"""
Unit tests for the code map generator.
"""

import os
import sys
import pytest
from pathlib import Path
from repomapper.handlers import (
    GenericHandler,
    OCamlHandler,
    ShellHandler,
    MarkdownHandler,
)
from repomapper.ignore import IgnorePatternManager
from repomapper.types import CtagEntry, ProcessDecision
from repomapper.core import CodeMapper
from repomapper.symbols import Symbol, SymbolTree
from repomapper.cli import main, PRODUCT_NAME, __version__


# Fixtures for creating temporary git repositories with ignore files
@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository with a basic structure."""
    # Initialize git repo
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    os.chdir(repo_dir)
    os.system("git init")

    return repo_dir


@pytest.fixture
def ignore_manager(git_repo):
    """Create an IgnorePatternManager instance for testing."""
    # Create standard ignore files first
    (git_repo / ".gitignore").write_text(
        """
*.pyc
/dist/
!important.pyc
""".strip()
    )

    # Create nested ignore files
    (git_repo / "src").mkdir(exist_ok=True)
    (git_repo / "src/lib").mkdir(exist_ok=True)
    (git_repo / "src/lib/.gitignore").write_text(
        """
temp/
*.log
""".strip()
    )

    return IgnorePatternManager(git_repo)


# Test git root detection
def test_find_git_root(git_repo, ignore_manager):
    """Test that git root is correctly identified."""
    assert ignore_manager.git_root == git_repo


# Test ignore pattern parsing
def test_parse_ignore_file(git_repo, ignore_manager):
    """Test parsing of ignore patterns from files."""
    # Create a test .gitignore file
    gitignore = git_repo / ".gitignore"
    gitignore.write_text(
        """
# Comment
*.pyc
/dist/
node_modules/
!important.pyc
""".strip()
    )

    patterns = ignore_manager._parse_ignore_file(gitignore)
    assert len(patterns) == 4
    assert "*.pyc" in patterns
    assert "/dist/" in patterns
    assert "node_modules/" in patterns
    assert "!important.pyc" in patterns


# Test pattern collection
def test_collect_ignore_patterns(git_repo, ignore_manager):
    """Test collection of patterns from multiple ignore files."""
    # Create nested structure with ignore files
    (git_repo / "src").mkdir(exist_ok=True)
    (git_repo / "src/lib").mkdir(exist_ok=True)

    # Root .gitignore
    (git_repo / ".gitignore").write_text("*.pyc\n/dist/")
    # Root .mapignore
    (git_repo / ".mapignore").write_text("dune\n*.install")
    # Nested .gitignore
    (git_repo / "src/.gitignore").write_text("*.o\n*.a")
    # Deep nested .gitignore
    (git_repo / "src/lib/.gitignore").write_text("temp/\n*.log")

    patterns = ignore_manager.collect_ignore_patterns()

    # Check that we found all the ignore files
    assert Path(".") in patterns
    assert Path("src") in patterns
    assert Path("src/lib") in patterns

    # Check that both git and map patterns were collected
    assert patterns[Path(".")]["git"] == ["*.pyc", "/dist/"]
    assert patterns[Path(".")]["map"] == ["dune", "*.install"]


# Add new fixtures
@pytest.fixture
def ocaml_handler():
    """Create an OCamlHandler instance for testing."""
    return OCamlHandler()


# Test OCaml functionality
def test_ocaml_file_processing(ocaml_handler):
    """Test OCaml file processing rules."""
    # Should process .mli files
    assert (
        ocaml_handler.should_process_file(Path("test.mli")) == ProcessDecision.PROCESS
    )

    # Should process .ml files without corresponding .mli
    assert ocaml_handler.should_process_file(Path("only.ml")) == ProcessDecision.PROCESS

    # Should not process .ml files that have .mli counterpart
    ml_with_mli = Path("test.ml")
    mli_path = ml_with_mli.with_suffix(".mli")
    mli_path.touch()  # Create the .mli file
    assert ocaml_handler.should_process_file(ml_with_mli) == ProcessDecision.SKIP
    mli_path.unlink()  # Clean up


def test_ocaml_module_path(ocaml_handler):
    """Test module path extraction from OCaml symbols."""
    # Test nested module path
    entry = CtagEntry(
        name="my_function",
        scope="Module1.SubModule",
        scopeKind="module",
        kind="function",
    )
    assert ocaml_handler._get_module_path(entry) == ["Module1", "SubModule"]

    # Test single module
    entry = CtagEntry(name="my_type", scope="module:MyModule", kind="type")
    assert ocaml_handler._get_module_path(entry) == ["MyModule"]

    # Test no module
    entry = CtagEntry(name="top_level", kind="function")
    assert ocaml_handler._get_module_path(entry) == []


def test_ocaml_symbol_categorization(ocaml_handler):
    """Test OCaml symbol categorization."""
    # Test function categorization
    func_entry = CtagEntry(
        name="my_function", kind="function", signature="val my_function : int -> string"
    )
    assert ocaml_handler.categorize_symbol(func_entry) == "Functions"

    # Test operator categorization
    op_entry = CtagEntry(
        name="(+)", kind="function", signature="val (+) : int -> int -> int"
    )
    assert ocaml_handler.categorize_symbol(op_entry) == "Functions"

    # Test type categorization
    type_entry = CtagEntry(name="my_type", kind="type", signature="type my_type = int")
    assert ocaml_handler.categorize_symbol(type_entry) == "Types"

    # Test module categorization
    module_entry = CtagEntry(
        name="MyModule", kind="module", signature="sig\n  val x : int\nend"
    )
    assert ocaml_handler.categorize_symbol(module_entry) == "Modules"

    # Test module alias categorization
    module_alias_entry = CtagEntry(
        name="MyAlias", kind="module", signature="= MyModule"
    )
    assert ocaml_handler.categorize_symbol(module_alias_entry) == "Modules"


def test_ocaml_symbol_filtering(ocaml_handler):
    """Test OCaml symbol filtering."""
    # Should filter out implementation details
    impl_entry = CtagEntry(
        name="internal", kind="function", pattern="/^let internal = {$/"
    )
    assert not ocaml_handler.filter_symbol(impl_entry)

    # Should filter out docstrings
    doc_entry = CtagEntry(
        name="doc", kind="function", pattern="/^(** Documentation *)$/"
    )
    assert not ocaml_handler.filter_symbol(doc_entry)

    # Should keep normal functions
    normal_entry = CtagEntry(
        name="valid_function",
        kind="function",
        pattern="/^let valid_function x = x + 1$/",
    )
    assert ocaml_handler.filter_symbol(normal_entry)


def test_handler_interface_defaults(generic_handler):
    """Test default implementations of handler interface methods."""
    entry = CtagEntry(
        name="test_func",
        kind="function",
        pattern="/^def test_func():$/",
        signature="test_func()",
    )

    # Test get_symbol_description with signature
    assert generic_handler.get_symbol_description(entry) == "test_func()"

    # Test get_symbol_description with pattern only
    entry_no_sig = CtagEntry(
        name="test_func",
        kind="function",
        pattern="/^def test_func():$/",
    )
    assert generic_handler.get_symbol_description(entry_no_sig) == "def test_func():"

    # Test get_module_path default
    assert generic_handler.get_module_path(entry) == ""

    # Test get_symbol_name default
    assert generic_handler.get_symbol_name(entry) == "test_func"


def test_ocaml_handler_interface(ocaml_handler):
    """Test OCaml-specific implementations of handler interface methods."""
    # Test signature cleaning
    entry = CtagEntry(
        name="test_func",
        kind="function",
        signature="let test_func x = x + 1",
    )
    assert ocaml_handler.get_symbol_description(entry) == "test_func x = x + 1"

    # Test module path handling
    module_entry = CtagEntry(
        name="func",
        kind="function",
        scope="Module1.SubModule",
        scopeKind="module",
    )
    assert ocaml_handler.get_module_path(module_entry) == "Module1.SubModule"

    # Test symbol name handling
    assert ocaml_handler.get_symbol_name(module_entry) == "func"


# Add new fixture
@pytest.fixture
def shell_handler():
    """Create a ShellHandler instance for testing."""
    return ShellHandler()


def test_shell_file_processing(shell_handler):
    """Test shell script file processing rules."""
    # Should process .sh files
    assert shell_handler.should_process_file(Path("test.sh"))

    # Should process .bash files
    assert shell_handler.should_process_file(Path("test.bash"))

    # Should process files without extension (common for shell scripts)
    assert shell_handler.should_process_file(Path("script"))


def test_shell_symbol_categorization(shell_handler):
    """Test shell script symbol categorization."""
    # Test function with 'function' keyword
    func_entry = CtagEntry(
        name="my_function", kind="function", pattern="/^function my_function() {$/"
    )
    assert shell_handler.categorize_symbol(func_entry) == "Functions"

    # Test function without 'function' keyword should return None
    func_entry2 = CtagEntry(
        name="other_function", kind="function", pattern="/^other_function() {$/"
    )
    assert shell_handler.categorize_symbol(func_entry2) is None

    # Test non-function should return None
    var_entry = CtagEntry(name="MY_VAR", kind="variable", pattern="/^MY_VAR=42$/")
    assert shell_handler.categorize_symbol(var_entry) is None


@pytest.fixture
def markdown_handler():
    """Create a MarkdownHandler instance for testing."""
    return MarkdownHandler()


@pytest.fixture
def generic_handler():
    """Create a GenericHandler instance for testing."""
    return GenericHandler(debug=False)


@pytest.fixture
def code_mapper():
    """Create a CodeMapper instance for testing."""
    return CodeMapper()


def test_markdown_file_processing(markdown_handler):
    """Test Markdown file processing rules."""
    # Should process .md files
    assert (
        markdown_handler.should_process_file(Path("test.md")) == ProcessDecision.PROCESS
    )

    # Should not process other text files
    assert (
        markdown_handler.should_process_file(Path("test.txt"))
        == ProcessDecision.UNHANDLED
    )
    assert (
        markdown_handler.should_process_file(Path("test.markdown"))
        == ProcessDecision.UNHANDLED
    )


def test_markdown_header_extraction(tmp_path, markdown_handler):
    """Test Markdown header extraction."""
    # Create a test markdown file
    md_file = tmp_path / "test.md"
    md_file.write_text(
        """
# Top Level Header
Some content
## Second Level
### Third Level
## Another Second
Not a #header
####Too Many Hashes
""".strip()
    )

    headers = markdown_handler.extract_headers(md_file)

    # Check that headers were extracted correctly
    assert len(headers) == 4
    assert headers == [
        (1, 1, "Top Level Header"),
        (3, 2, "Second Level"),
        (4, 3, "Third Level"),
        (5, 2, "Another Second"),
    ]


def test_markdown_header_edge_cases(tmp_path, markdown_handler):
    """Test edge cases in Markdown header extraction."""
    md_file = tmp_path / "edge_cases.md"
    md_file.write_text(
        """
#Not a header
# Header with #hash# in it
##No space
# Header with trailing space 
 # Header with leading space
""".strip()
    )

    headers = markdown_handler.extract_headers(md_file)

    # Should only match proper headers (space after #)
    assert len(headers) == 3
    assert headers == [
        (2, 1, "Header with #hash# in it"),
        (4, 1, "Header with trailing space"),
        (5, 1, "Header with leading space"),
    ]


def test_cli_help(capsys):
    """Test that --help produces expected output."""
    with pytest.raises(SystemExit) as exc_info:
        sys.argv = ["repomapper.py", "--help"]
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "--version" in captured.out


def test_cli_version(capsys):
    """Test that --version produces expected output."""
    with pytest.raises(SystemExit) as exc_info:
        sys.argv = ["repomapper.py", "--version"]
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert f"{PRODUCT_NAME} v{__version__}" in captured.out


def test_cli_output_file(tmp_path):
    """Test writing to a custom output file."""
    output_file = tmp_path / "custom.md"
    sys.argv = ["repomapper.py", "-o", str(output_file), str(tmp_path)]

    # Create a test file to map
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test Header\n## Section")

    main()

    assert output_file.exists()
    content = output_file.read_text()
    assert "# This file was automatically generated." in content
    assert "Test Header" in content
    assert "Section" in content


def test_cli_stdout(capsys, tmp_path):
    """Test writing to stdout."""
    sys.argv = ["repomapper.py", "-o", "-", str(tmp_path)]

    # Create a test file to map
    test_file = tmp_path / "test.md"
    test_file.write_text("# Test Header\n## Section")

    main()

    captured = capsys.readouterr()
    assert "# This file was automatically generated." in captured.out
    assert "Test Header" in captured.out
    assert "Section" in captured.out


def test_cli_list_mode(capsys, tmp_path):
    """Test --list mode output."""
    # Create test files
    (tmp_path / "src").mkdir()
    (tmp_path / "src/test.ml").touch()
    (tmp_path / "src/test.mli").touch()
    (tmp_path / "src/script.sh").touch()
    (tmp_path / "src/ignored.pyc").touch()

    # Initialize git repo
    os.chdir(tmp_path)
    os.system("git init")
    (tmp_path / ".gitignore").write_text("*.pyc\n")

    # Run with --list
    sys.argv = ["repomapper.py", "--list", str(tmp_path)]
    main()

    captured = capsys.readouterr()
    output_lines = captured.out.strip().split("\n")
    # Should show included files (relative paths)
    assert "src/test.mli" in output_lines
    assert "src/script.sh" in output_lines
    # Should not show excluded files
    assert "src/ignored.pyc" not in output_lines
    assert "src/test.ml" not in output_lines  # Excluded due to .mli


def test_cli_list_all_mode(capsys, tmp_path):
    """Test --list --all mode output."""
    # Create test files
    (tmp_path / "src").mkdir()
    (tmp_path / "src/test.ml").touch()
    (tmp_path / "src/test.mli").touch()
    (tmp_path / "src/script.sh").touch()
    (tmp_path / "src/ignored.pyc").touch()

    # Initialize git repo
    os.chdir(tmp_path)
    os.system("git init")
    (tmp_path / ".gitignore").write_text("*.pyc\n")

    # Run with --list --all
    sys.argv = ["repomapper.py", "--list", "--all", str(tmp_path)]
    main()

    captured = capsys.readouterr()
    # Should show all files with status indicators
    assert "I src/test.mli" in captured.out  # Included
    assert "I src/script.sh" in captured.out  # Included
    assert ". src/ignored.pyc" in captured.out  # Excluded by gitignore
    assert ". src/test.ml" in captured.out  # Excluded due to .mli


def test_cli_list_debug_mode(capsys, tmp_path):
    """Test --list with --debug flag."""
    # Create test file
    (tmp_path / "test.ml").touch()

    # Initialize git repo
    os.chdir(tmp_path)
    os.system("git init")

    # Run with --list --debug
    sys.argv = ["repomapper.py", "--list", "--debug", str(tmp_path)]
    main()

    captured = capsys.readouterr()
    # Should show debug messages
    assert "DEBUG: Debug mode enabled" in captured.err
    assert "DEBUG: Git root found at:" in captured.err
    assert "DEBUG: Running ctags..." in captured.err
    # Should still show normal output
    assert "test.ml" in captured.out


def test_cli_list_empty_dir(capsys, tmp_path):
    """Test --list with an empty directory."""
    # Initialize empty git repo
    os.chdir(tmp_path)
    os.system("git init")

    # Run with --list
    sys.argv = ["repomapper.py", "--list", str(tmp_path)]
    main()

    captured = capsys.readouterr()
    # Should have no output for empty dir
    assert not captured.out.strip()


def test_cli_list_absolute_path(capsys, tmp_path):
    """Test --list with absolute vs relative paths."""
    # Create test file in a subdirectory
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    test_file = subdir / "test.sh"
    test_file.touch()

    # Initialize git repo
    os.chdir(tmp_path)
    os.system("git init")

    # Test with relative path
    os.chdir(subdir)
    sys.argv = ["repomapper.py", "--list", "."]
    main()
    captured = capsys.readouterr()
    assert "test.sh" in captured.out  # Should show relative path

    # Test with absolute path
    sys.argv = ["repomapper.py", "--list", str(subdir)]
    main()
    captured = capsys.readouterr()
    assert "test.sh" in captured.out  # Should still show relative path


def test_build_single(tmp_path):
    """Test the build_single.py script functionality."""
    from scripts.build_single import combine_files

    # Create a test file structure
    pkg_dir = tmp_path / "repomapper"
    src_dir = pkg_dir / "src"
    src_dir.mkdir(parents=True)

    # Create a simple test file
    test_file = src_dir / "test.py"
    test_file.write_text(
        """
def hello():
    return "Hello, World!"
""".strip()
    )

    # Create output file path
    output = tmp_path / "combined.py"

    # Run the build
    combine_files(output)

    # Verify the output exists and is executable
    assert output.exists()
    assert output.stat().st_mode & 0o111  # Check executable bits

    # Basic content checks
    content = output.read_text()
    # Check for essential elements
    assert "#!/usr/bin/env python3" in content  # Shebang line
    assert "Single-file distribution" in content  # Header comment
    assert "import " in content  # Has some imports
    assert content.strip().endswith("main()")  # Ends with main() call


def test_build_imports(tmp_path):
    """Test that the build script handles imports correctly."""
    from scripts.build_single import combine_files, get_imports

    # Test import extraction
    code = """
import sys
from os import path
from typing import List, Optional
""".strip()

    imports, names = get_imports(code)
    assert "import sys" in imports
    assert "from os import path" in imports
    assert "sys" in names
    assert "path" in names

    # Test relative import conversion
    pkg_dir = tmp_path / "repomapper"
    src_dir = pkg_dir / "src"
    src_dir.mkdir(parents=True)

    # Create files with relative imports
    (src_dir / "module1.py").write_text(
        """
from .module2 import func2
def func1(): return func2()
""".strip()
    )

    (src_dir / "module2.py").write_text(
        """
def func2(): return 42
""".strip()
    )

    # Build combined file
    output = tmp_path / "combined.py"
    combine_files(output)

    # Check that relative imports were converted
    content = output.read_text()
    assert "from .module2" not in content  # Relative import should be gone
    assert "def func2():" in content  # Function should be included
    assert "def func1():" in content  # Function should be included


def test_build_duplicate_prevention(tmp_path):
    """Test that the build script prevents duplicate code."""
    from scripts.build_single import combine_files

    # Create test files with shared code
    pkg_dir = tmp_path / "repomapper"
    src_dir = pkg_dir / "src"
    src_dir.mkdir(parents=True)

    shared_code = """
VERSION = "1.0.0"
PRODUCT_NAME = "Test"
"""

    (src_dir / "module1.py").write_text(shared_code)
    (src_dir / "module2.py").write_text(shared_code)

    # Build combined file
    output = tmp_path / "combined.py"
    combine_files(output)

    # Count occurrences in output
    content = output.read_text()
    assert content.count('VERSION = "1.0.0"') == 1  # Should only appear once
    assert content.count('PRODUCT_NAME = "Test"') == 1  # Should only appear once


def test_private_member_filtering(code_mapper):
    """Test filtering of private members."""
    # Create a test entry with private access
    private_entry = CtagEntry(
        name="_private_method",
        kind="method",
        access="private",
        pattern="/^    def _private_method(self):$/",
    )

    # Create a test entry with public access
    public_entry = CtagEntry(
        name="public_method",
        kind="method",
        access="public",
        pattern="/^    def public_method(self):$/",
    )

    # Test with generic handler
    assert not code_mapper.generic_handler.filter_symbol(private_entry)
    assert code_mapper.generic_handler.filter_symbol(public_entry)


def test_comment_cleanup(code_mapper):
    """Test cleanup of comments from symbol descriptions."""
    # Create a test file and symbol tree
    tree = code_mapper.file_trees[Path("test.py")] = SymbolTree()

    # Test various comment styles
    symbols = [
        Symbol(
            name="func1", kind="function", pattern="def func1(): # A comment", line=1
        ),
        Symbol(
            name="func2", kind="function", pattern="def func2():  // C++ style", line=2
        ),
        Symbol(
            name="func3",
            kind="function",
            pattern="def func3():    # Multiple spaces",
            line=3,
        ),
        Symbol(
            name="func4",
            kind="function",
            pattern="def func4(): pass # Trailing code",
            line=4,
        ),
        Symbol(name="no_comment", kind="function", pattern="def no_comment():", line=5),
    ]

    # Add symbols to tree
    for symbol in symbols:
        tree.add_symbol(symbol)

    # Use StringIO to capture output
    from io import StringIO

    output = StringIO()
    code_mapper._write_map(output, {Path("test.py"): {}})
    result = output.getvalue()

    # Verify comments are removed
    assert "def func1():" in result
    assert "# A comment" not in result
    assert "// C++ style" not in result
    assert "# Multiple spaces" not in result
    assert "def func4(): pass" in result
    assert "# Trailing code" not in result
    assert "def no_comment():" in result


def test_duplicate_symbol_handling(code_mapper):
    """Test handling of duplicate symbols."""
    # Create a symbol tree
    tree = code_mapper.file_trees[Path("test.py")] = SymbolTree()

    # Test regular method duplicates
    parent = Symbol(name="MyClass", kind="class", pattern="class MyClass:", line=1)
    tree.add_symbol(parent)

    method1 = Symbol(
        name="my_method", kind="method", pattern="def my_method(self):", line=2
    )
    method2 = Symbol(
        name="my_method", kind="method", pattern="def my_method(self):", line=3
    )

    parent.add_child(method1)
    parent.add_child(method2)
    assert len(parent.children) == 1  # Duplicates should be eliminated
    assert parent.children[0].line == 2  # First occurrence should be kept

    # Test enum member handling (should keep one form)
    enum_class = Symbol(
        name="MyEnum", kind="class", pattern="class MyEnum(Enum):", line=4
    )
    tree.add_symbol(enum_class)

    enum_val1 = Symbol(
        name="MyEnum.VALUE", kind="variable", pattern="    VALUE = 1", line=5
    )
    enum_val2 = Symbol(name="VALUE", kind="variable", pattern="    VALUE = 1", line=5)

    enum_class.add_child(enum_val1)
    enum_class.add_child(enum_val2)
    assert len(enum_class.children) == 1  # Should keep only one form
    # Either form is acceptable, but there should only be one
    assert enum_class.children[0].name in {"MyEnum.VALUE", "VALUE"}


def test_file_discovery(tmp_path, code_mapper):
    """Test file discovery and filtering."""
    # Create a test directory structure
    src = tmp_path / "src"
    src.mkdir()

    # Create various test files
    (src / "test.ml").touch()
    (src / "test.mli").touch()
    (src / "only.ml").touch()  # ML file without MLI
    (src / "script.sh").touch()
    (src / "script.bash").touch()
    (src / "ignored.pyc").touch()
    (src / ".hidden").touch()

    # Create a hidden directory with valid files (should be skipped)
    hidden_dir = src / ".git"
    hidden_dir.mkdir()
    (hidden_dir / "valid.ml").touch()

    # Create nested directories
    lib = src / "lib"
    lib.mkdir()
    (lib / "module.ml").touch()
    (lib / "module.mli").touch()  # This should cause module.ml to be skipped

    # Initialize git repo for ignore pattern testing
    os.chdir(tmp_path)
    os.system("git init")

    # Add ignore patterns
    (tmp_path / ".gitignore").write_text("*.pyc\n")

    # Get processable files
    code_mapper.ignore_manager = IgnorePatternManager(tmp_path)
    files = code_mapper._get_processable_files(tmp_path)

    # Convert to set of relative paths for easier comparison
    rel_files = {str(f.relative_to(tmp_path)) for f in files}

    # Verify expected files - test.ml should be skipped due to test.mli
    assert rel_files == {
        "src/only.ml",  # This ML file should be included (no MLI)
        "src/test.mli",  # MLI file should be included
        "src/script.sh",  # Shell scripts should be included
        "src/script.bash",
        "src/lib/module.mli",  # Only MLI should be included, ML is skipped
    }


# Test pattern matching
@pytest.mark.parametrize(
    "path,should_ignore",
    [
        ("file.pyc", True),  # Basic glob pattern
        ("src/file.pyc", True),  # Glob in subdirectory
        ("dist/file.txt", True),  # Directory pattern
        ("important.pyc", False),  # Negated pattern
        ("src/lib/temp/file", True),  # Nested directory pattern
        ("src/lib/file.log", True),  # Deep nested pattern
        ("normal.txt", False),  # Non-matching file
    ],
)
def test_should_ignore(git_repo, ignore_manager, path, should_ignore):
    """Test pattern matching for various file paths."""
    # Create standard ignore files first
    (git_repo / ".gitignore").write_text(
        """
*.pyc
/dist/
!important.pyc
""".strip()
    )

    # Create nested ignore files
    (git_repo / "src").mkdir(exist_ok=True)
    (git_repo / "src/lib").mkdir(exist_ok=True)
    (git_repo / "src/lib/.gitignore").write_text(
        """
temp/
*.log
""".strip()
    )

    assert ignore_manager.should_ignore(Path(path)) == should_ignore
