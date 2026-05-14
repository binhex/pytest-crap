"""Tests for the CRAP calculator."""

import math
import tempfile
from pathlib import Path
from unittest.mock import patch

from pytest_crap.calculator import FunctionScore, calculate_crap


def expected_crap(cc: int, coverage_percent: float) -> float:
    cov_factor = (1.0 - coverage_percent / 100.0) ** 3
    return (cc**2) * cov_factor + cc


def run_with_source(code: str, executed: set[int]) -> list[FunctionScore]:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        path = f.name
    try:
        scores = calculate_crap(path, executed)
        return scores
    finally:
        Path(path).unlink()


def test_simple_function_with_coverage() -> None:
    code = """
def add(a, b):
    return a + b
"""
    # function is lines 2-3, fully covered
    executed: set[int] = {2, 3}
    scores = run_with_source(code, executed)
    assert len(scores) == 1
    s = scores[0]
    assert math.isclose(s.coverage_percent, 100.0)
    assert math.isclose(s.crap, expected_crap(s.cc, s.coverage_percent))


def test_complex_function_no_coverage() -> None:
    code = """
def complex_func(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                x += 1
    return x
"""
    executed: set[int] = set()
    scores = run_with_source(code, executed)
    assert len(scores) == 1
    s = scores[0]
    assert math.isclose(s.coverage_percent, 0.0)
    assert math.isclose(s.crap, expected_crap(s.cc, 0.0))


def test_partial_coverage() -> None:
    code = """
def func(a):
    x = 1
    y = 2
    if a:
        x += y
    return x
"""
    # lines 2-6; say only lines 2 and 6 executed -> 2/5 = 40%
    executed: set[int] = {2, 6}
    scores = run_with_source(code, executed)
    assert len(scores) == 1
    s = scores[0]
    total_lines = s.end_line - s.start_line + 1
    covered = sum(1 for ln in range(s.start_line, s.end_line + 1) if ln in executed)
    expected_percent = (covered / total_lines) * 100.0
    assert math.isclose(s.coverage_percent, expected_percent)
    assert math.isclose(s.crap, expected_crap(s.cc, s.coverage_percent))


def test_multiple_functions() -> None:
    code = """
def a():
    return 1

def b():
    return 2
"""
    # cover only the first function
    executed: set[int] = {2}
    scores = run_with_source(code, executed)
    assert len(scores) == 2
    a_score = next(s for s in scores if s.name == "a")
    b_score = next(s for s in scores if s.name == "b")
    assert math.isclose(a_score.coverage_percent, 50.0) or math.isclose(
        a_score.coverage_percent, 100.0
    )
    assert math.isclose(b_score.coverage_percent, 0.0)


def test_class_methods() -> None:
    code = """
class C:
    def m1(self):
        return 1

    def m2(self):
        return 2
"""
    executed: set[int] = {3}
    scores = run_with_source(code, executed)
    # two methods
    assert len(scores) == 2
    m1 = next(s for s in scores if s.name == "m1")
    m2 = next(s for s in scores if s.name == "m2")
    # compute expected coverage dynamically
    total_m1 = m1.end_line - m1.start_line + 1
    covered_m1 = sum(1 for ln in range(m1.start_line, m1.end_line + 1) if ln in executed)
    expected_m1 = (covered_m1 / total_m1) * 100.0
    assert math.isclose(m1.coverage_percent, expected_m1)
    total_m2 = m2.end_line - m2.start_line + 1
    covered_m2 = sum(1 for ln in range(m2.start_line, m2.end_line + 1) if ln in executed)
    expected_m2 = (covered_m2 / total_m2) * 100.0
    assert math.isclose(m2.coverage_percent, expected_m2)


def test_docstring_not_counted_towards_coverage() -> None:
    """Docstring lines should not reduce coverage percentage."""
    code = '''
def foo():
    """A docstring that should be ignored."""
    return 1
'''
    # Only the return line is covered
    executed: set[int] = {4}
    scores = run_with_source(code, executed)
    assert len(scores) == 1
    s = scores[0]
    # Without fix: total lines = 4-2+1 = 3, 1 covered -> 33.3%
    # With fix: total lines = 4-4+1 = 1, 1 covered -> 100%
    assert math.isclose(s.coverage_percent, 100.0)
    assert math.isclose(s.crap, expected_crap(s.cc, 100.0))


def test_docstring_partial_coverage() -> None:
    """Docstring lines excluded but remaining lines counted correctly."""
    code = '''
def foo():
    """A docstring."""
    x = 1
    if x:
        return x
    return 0
'''
    # Cover only the first executable line (x = 1)
    executed: set[int] = {4}
    scores = run_with_source(code, executed)
    assert len(scores) == 1
    s = scores[0]
    # Executable range starts after the docstring (line 4) and ends at line 7.
    # 4 executable lines (4-7), 1 covered -> 25%
    executable_start = 4  # line after docstring
    executable_end = s.end_line
    total_lines = executable_end - executable_start + 1
    covered = sum(1 for ln in range(executable_start, executable_end + 1) if ln in executed)
    expected_percent = (covered / total_lines) * 100.0
    assert math.isclose(s.coverage_percent, expected_percent)
    assert math.isclose(s.crap, expected_crap(s.cc, s.coverage_percent))


def test_multiline_docstring_coverage() -> None:
    """Multiline docstrings should also be excluded from coverage range."""
    code = '''
def foo():
    """Line 1
    Line 2
    Line 3"""
    return 1
'''
    executed: set[int] = {6}
    scores = run_with_source(code, executed)
    assert len(scores) == 1
    s = scores[0]
    # Executable range: only line 6. 1 covered -> 100%
    assert math.isclose(s.coverage_percent, 100.0)


def test_blank_lines_not_counted_towards_coverage() -> None:
    """Blank lines between statements should not reduce coverage percentage."""
    code = """
def foo():
    a = 1

    b = 2

    return a + b
"""
    # Executable: def line, a=1, b=2, return.  Blank lines are excluded.
    executed: set[int] = {2, 3, 5, 7}
    scores = run_with_source(code, executed)
    assert len(scores) == 1
    s = scores[0]
    assert math.isclose(s.coverage_percent, 100.0)
    assert math.isclose(s.crap, expected_crap(s.cc, 100.0))


def test_comment_lines_not_counted_towards_coverage() -> None:
    """Comment-only lines should not reduce coverage percentage."""
    code = """
def foo():
    # Step 1: initialise
    a = 1
    # Step 2: increment
    a += 1
    # Step 3: return
    return a
"""
    # Executable: def line, a=1, a+=1, return.
    executed: set[int] = {2, 4, 6, 8}
    scores = run_with_source(code, executed)
    assert len(scores) == 1
    s = scores[0]
    assert math.isclose(s.coverage_percent, 100.0)
    assert math.isclose(s.crap, expected_crap(s.cc, 100.0))


def test_blank_and_comment_lines_partial_coverage() -> None:
    """Blank/comment lines excluded but coverage computed over remaining lines."""
    code = """
def foo():
    # setup
    a = 1

    # compute
    b = a * 2

    return b
"""
    # Executable lines: def(2), a=1(4), b=a*2(7), return(9) = 4 total.
    # Cover def + a=1 + return b = 3 of 4 = 75%.
    executed: set[int] = {2, 4, 9}
    scores = run_with_source(code, executed)
    assert len(scores) == 1
    s = scores[0]
    assert math.isclose(s.coverage_percent, 75.0)
    assert math.isclose(s.crap, expected_crap(s.cc, 75.0))


def test_docstring_blank_and_comment_all_filtered() -> None:
    """Docstring, blank, and comment lines are all excluded."""
    code = (
        "\n"
        "def foo():\n"
        '    """Docstring."""\n'
        "    # setup\n"
        "    a = 1\n"
        "\n"
        "    # compute\n"
        "    b = a * 2\n"
        "\n"
        "    return b\n"
    )
    # Executable: def(2), a=1(5), b=a*2(8), return(10).  4 lines.
    # Cover all 4 -> 100%.
    executed: set[int] = {2, 5, 8, 10}
    scores = run_with_source(code, executed)
    assert len(scores) == 1
    s = scores[0]
    assert math.isclose(s.coverage_percent, 100.0)
    assert math.isclose(s.crap, expected_crap(s.cc, 100.0))


def test_cc_visit_node_without_lineno() -> None:
    """Test handling of CC nodes without lineno."""
    code = """
def func():
    return 1
"""
    executed: set[int] = {2}

    # Mock cc_visit to return a node without lineno
    mock_node = type("MockNode", (), {"lineno": None, "complexity": 1})()

    with patch("pytest_crap.calculator.cc_visit", return_value=[mock_node]):
        scores = run_with_source(code, executed)
    # The function should still be scored with CC=0
    assert len(scores) == 1
    s = scores[0]
    assert s.cc == 0


def test_cc_visit_node_without_complexity() -> None:
    """Test handling of CC nodes without complexity."""
    code = """
def func():
    return 1
"""
    executed: set[int] = {2}

    # Mock cc_visit to return a node without complexity
    mock_node = type("MockNode", (), {"lineno": 2, "complexity": None})()

    with patch("pytest_crap.calculator.cc_visit", return_value=[mock_node]):
        scores = run_with_source(code, executed)
    # The function should still be scored with CC=0
    assert len(scores) == 1
    s = scores[0]
    assert s.cc == 0
