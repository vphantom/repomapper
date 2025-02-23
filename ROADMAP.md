# Development Status

## Future Enhancements

- [ ] Harden against edge cases:

  System & Resources:
  - [ ] (!) Check ctags availability and version
  - [ ] (!) Add subprocess timeout handling for ctags
  - [ ] (!) Handle output file/directory permission issues
  - [ ] Handle directory traversal (symlinks, permissions)
  - [ ] Add memory management for large codebases
  - [ ] Handle race conditions with file changes

  File Handling:
  - [ ] (!) Handle file encoding issues (UTF-8, binary files)
  - [ ] Handle path normalization edge cases
  - [ ] Handle malformed file extensions
  - [ ] Handle line number overflow in large files

  Git & Ignore Patterns:
  - [ ] (!) Improve git repo detection error handling
  - [ ] Handle circular symlinks in git root detection
  - [ ] Handle invalid pattern syntax in ignore files
  - [ ] Handle race conditions with ignore file changes
  - [ ] Add memory management for large ignore files

  Symbol Processing:
  - [ ] (!) Handle circular references in symbol relationships
  - [ ] (!) Handle name collisions in symbol scopes
  - [ ] (!) Handle invalid/malformed symbol data
  - [ ] (!) Handle malformed CtagEntry dictionaries
  - [ ] Handle memory issues with deep symbol trees
  - [ ] Add validation for regex patterns
  - [ ] Improve type safety in TypedDict fields

  Handler Framework:
  - [ ] (!) Add return type validation for handler methods
  - [ ] (!) Add exception handling in abstract methods
  - [ ] Add debug output safety checks
  - [ ] Add pattern string type validation
  - [ ] Add access level validation

  Language-Specific:
  - [ ] Handle malformed markdown headers
  - [ ] Handle malformed OCaml module paths
  - [ ] Handle invalid OCaml signatures
  - [ ] Handle OCaml file pair edge cases
  - [ ] Handle shell script variations (shebang, function styles)

## Other Ideas

1. Performance Optimizations:
   - Cache ctags output
   - Consider parallel processing for large codebases
   - Optimize pattern matching for large ignore files

2. Language Support:
   - Perl: packages, subs, POD documentation
   - JavaScript: class/function structure, module exports
   - Python (decorators, etc.)

3. User Experience:
   - Better error messages and diagnostics
