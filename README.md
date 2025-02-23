# Repo Mapper

[![license](https://img.shields.io/github/license/vphantom/repomapper.svg?style=plastic)]() [![GitHub release](https://img.shields.io/github/release/vphantom/repomapper.svg?style=plastic)]()

RepoMapper is a command-line tool that generates a comprehensive `MAP.txt` file for your codebase, providing a structured overview of your project's files and their contents. It analyzes both code and documentation files, extracting key information like:

- Headers and structure from Markdown files
- Functions, classes, and other symbols from code files
- Special handling for languages with separate interface/implementation files

This file is mostly intended for use with LLM coding assistants as a concise map of all function, method and property signatures available throughout a project.

## Installation

Requirements:
- Python 3.7 or later
- Universal Ctags (`ctags`) must be installed on your system

### Using pip from source

```bash
git clone https://github.com/vphantom/repomapper.git
cd repomapper
pip install -e .
```

### Standalone script from source

```bash
git clone https://github.com/vphantom/repomapper.git
cd repomapper
python3 scripts/build_single.py
```

### Standalone script download

You may also wish to download our stand-alone `repomapper` script instead from the releases page: <https://github.com/vphantom/repomapper/releases>

## Usage

Basic usage to generate a map of your current directory:

```bash
repomapper
```

This will create a `MAP.txt` file in your current directory.  Run `repomapper --help` for a list of available options.

RepoMapper looks for its own `.mapignore` files as well as standard `.gitignore` files throughout your directory structure, so that you may omit files which are otherwise included in your Git repository.

Speaking of files to ignore, you probably want to add `MAP.txt` to your `.gitignore` file.

## ACKNOWLEDGEMENTS

This project was created as an experiment with LLM-based code generation using <https://github.com/Aider-AI/aider> with the Anthropic Claude Sonnet 3.5 model.  ~90% of the implementation was done by the model.

## LICENSE AND COPYRIGHT

Copyright (c) 2025 Stephane Lavergne <https://github.com/vphantom>

Distributed under the MIT (X11) License:
http://www.opensource.org/licenses/mit-license.php

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
