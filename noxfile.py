"""Nox sessions for testing and linting."""

import nox

PYTHON_VERSIONS = ["3.11", "3.12", "3.13", "3.14"]


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    """Run the test suite."""
    session.install("-e", ".[dev]")
    session.run("pytest")


@nox.session(python="3.13")
def lint(session):
    """Run ruff linter on the source code and tests."""
    session.install("ruff")
    session.run("ruff", "check", "src/", "tests/")


@nox.session(python="3.13")
def format_check(session):
    """Check code formatting with ruff."""
    session.install("ruff")
    session.run("ruff", "format", "--check", "src/", "tests/")


@nox.session(python="3.13")
def format(session):
    """Format code with ruff."""
    session.install("ruff")
    session.run("ruff", "format", "src/", "tests/")
