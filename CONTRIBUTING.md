# Contributing Guide

## Development Setup

1. Install development dependencies:

```bash
pip install black flake8 pytest
```

## Before Submitting Changes

1. Run the preparation rule (formats code, runs linter and tests):

```bash
make prep
```

2. Fix any issues reported by the linter or tests

## Code Style

- We use [black](https://black.readthedocs.io/) for Python code formatting
- Line length is limited to 88 characters (black default)
- We follow PEP 8 style guidelines, enforced by Flake8

## Commit Messages

- Use clear, descriptive commit messages
- Start with a short summary line (50 chars or less)
- Follow with a detailed description if needed

## Pull Request Process

1. Create a new branch for your changes
2. Make your changes and commit them
3. Run `make format` and `make lint` before committing
4. Push your branch and create a pull request
5. Wait for review and address any feedback
