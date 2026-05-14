"""Tests for the function mapper."""

import tempfile
from pathlib import Path

import pytest

from pytest_crap.mapper import map_functions


def test_single_function() -> None:
    """Test mapping a single function."""
    code = """
def hello():
    return "world"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name

    try:
        functions = map_functions(path)
        assert len(functions) == 1
        assert functions[0].name == "hello"
        assert functions[0].start_line == 2
        assert not functions[0].is_method
        assert not functions[0].is_async
    finally:
        Path(path).unlink()


def test_multiple_functions() -> None:
    """Test mapping multiple functions."""
    code = """
def func1():
    pass

def func2():
    pass

def func3():
    pass
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name

    try:
        functions = map_functions(path)
        assert len(functions) == 3
        names = [f.name for f in functions]
        assert names == ["func1", "func2", "func3"]
    finally:
        Path(path).unlink()


def test_nested_functions() -> None:
    """Test that nested functions are discovered."""
    code = """
def outer():
    def inner():
        pass
    return inner
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name

    try:
        functions = map_functions(path)
        # Both outer and inner should be found
        assert len(functions) == 2
        names = [f.name for f in functions]
        assert "outer" in names
        assert "inner" in names
    finally:
        Path(path).unlink()


def test_class_methods() -> None:
    """Test that class methods are correctly identified."""
    code = """
class MyClass:
    def method1(self):
        pass

    def method2(self):
        pass
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name

    try:
        functions = map_functions(path)
        assert len(functions) == 2
        for func in functions:
            assert func.is_method
            assert func.name in ["method1", "method2"]
    finally:
        Path(path).unlink()


def test_async_functions() -> None:
    """Test that async functions are detected."""
    code = """
async def async_func():
    await something()

def sync_func():
    pass
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name

    try:
        functions = map_functions(path)
        assert len(functions) == 2
        async_func = next(f for f in functions if f.name == "async_func")
        sync_func = next(f for f in functions if f.name == "sync_func")
        assert async_func.is_async
        assert not sync_func.is_async
    finally:
        Path(path).unlink()


def test_decorators() -> None:
    """Test that decorated functions are correctly mapped."""
    code = """
@decorator
def decorated():
    pass

@decorator1
@decorator2
def multi_decorated():
    pass
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name

    try:
        functions = map_functions(path)
        assert len(functions) == 2
        names = [f.name for f in functions]
        assert "decorated" in names
        assert "multi_decorated" in names
    finally:
        Path(path).unlink()


def test_empty_file() -> None:
    """Test mapping an empty file."""
    code = ""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name

    try:
        functions = map_functions(path)
        assert len(functions) == 0
    finally:
        Path(path).unlink()


def test_file_not_found() -> None:
    """Test that FileNotFoundError is raised for missing files."""
    with pytest.raises(FileNotFoundError):
        map_functions("/nonexistent/file.py")


def test_syntax_error() -> None:
    """Test that SyntaxError is raised for invalid Python."""
    code = "def bad syntax here"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name

    try:
        with pytest.raises(SyntaxError):
            map_functions(path)
    finally:
        Path(path).unlink()


def test_docstring_skipped_for_coverage_start() -> None:
    """Test that docstrings are skipped for coverage_start_line."""
    code = '''
def foo():
    """A docstring."""
    return 1
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name

    try:
        functions = map_functions(path)
        assert len(functions) == 1
        func = functions[0]
        # start_line is the def line (line 2)
        assert func.start_line == 2
        # docstring is on line 3, so executable code starts at line 4
        assert func.coverage_start_line == 4
        assert func.end_line == 4
    finally:
        Path(path).unlink()


def test_multiline_docstring_skipped() -> None:
    """Test that multiline docstrings are fully skipped."""
    code = '''
def foo():
    """Line 1
    Line 2
    Line 3"""
    return 1
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name

    try:
        functions = map_functions(path)
        assert len(functions) == 1
        func = functions[0]
        assert func.start_line == 2
        # The multiline docstring spans lines 3-5, so executable code starts at line 6
        assert func.coverage_start_line == 6
        assert func.end_line == 6
    finally:
        Path(path).unlink()


def test_no_docstring_coverage_start_equals_start() -> None:
    """Test that coverage_start_line equals start_line when no docstring exists."""
    code = """
def foo():
    return 1
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name

    try:
        functions = map_functions(path)
        assert len(functions) == 1
        func = functions[0]
        assert func.start_line == 2
        assert func.coverage_start_line == 2
    finally:
        Path(path).unlink()


def test_docstring_only_body() -> None:
    """Test function with only a docstring (abstract stub) — no executable lines."""
    code = '''
def foo():
    """Just a stub."""
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name

    try:
        functions = map_functions(path)
        assert len(functions) == 1
        func = functions[0]
        assert func.start_line == 2
        assert func.end_line == 3
        # Docstring-only body: coverage_start_line after end_line (no executable lines)
        assert func.coverage_start_line == 4
    finally:
        Path(path).unlink()


def test_line_ranges() -> None:
    """Test that line ranges are correct."""
    code = """
def func1():
    x = 1
    y = 2
    return x + y

def func2():
    pass
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name

    try:
        functions = map_functions(path)
        assert len(functions) == 2
        func1 = next(f for f in functions if f.name == "func1")
        func2 = next(f for f in functions if f.name == "func2")

        assert func1.start_line == 2
        assert func2.start_line == 7
    finally:
        Path(path).unlink()
