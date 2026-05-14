"""CRAP score calculator combining radon CC and line coverage data."""

from dataclasses import dataclass

from radon.complexity import cc_visit

from .mapper import map_functions


def _count_executable_lines(source_lines: list[str], start: int, end: int) -> int:
    """Count lines in [start, end] that are neither blank nor comment-only.

    Blank lines and comments are never tracked by coverage tools; including
    them in the CRAP denominator produces an artificially inflated score.
    """
    count = 0
    # source_lines is 0-indexed; start/end are 1-based line numbers.
    for ln in range(start, end + 1):
        if ln < 1 or ln > len(source_lines):
            continue
        stripped = source_lines[ln - 1].strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


@dataclass
class FunctionScore:
    name: str
    file_path: str
    start_line: int
    end_line: int
    cc: int
    coverage_percent: float
    crap: float


def calculate_crap(file_path: str, covered_lines: set[int]) -> list[FunctionScore]:
    """Calculate CRAP scores for all functions in a file.

    Args:
        file_path: path to Python source file
        covered_lines: set of 1-based line numbers that were executed

    Returns:
        List of FunctionScore objects
    """
    with open(file_path) as f:
        source = f.read()

    funcs = map_functions(file_path)

    # Use radon to get CC per function
    cc_nodes = cc_visit(source)
    # Map by start line to complexity
    cc_by_start: dict[int, int] = {}
    for node in cc_nodes:
        start = getattr(node, "lineno", None)
        complexity = getattr(node, "complexity", None)
        if start is None or complexity is None:
            continue
        cc_by_start[start] = complexity

    source_lines: list[str] = source.split("\n")

    out: list[FunctionScore] = []
    for fdef in funcs:
        # Count only executable lines: exclude docstrings, blank lines, and
        # comment-only lines.  These lines are never reported by coverage tools
        # yet would be included in the physical line range, artificially
        # inflating the CRAP score.
        total_lines = max(
            1,
            _count_executable_lines(source_lines, fdef.coverage_start_line, fdef.end_line),
        )
        covered = sum(
            1 for ln in range(fdef.coverage_start_line, fdef.end_line + 1) if ln in covered_lines
        )
        coverage_percent = (covered / total_lines) * 100.0
        cc = cc_by_start.get(fdef.start_line, 0)
        # CRAP = CC^2 * (1 - cov/100)^3 + CC
        cov_factor = (1.0 - coverage_percent / 100.0) ** 3
        crap = (cc**2) * cov_factor + cc
        out.append(
            FunctionScore(
                name=fdef.name,
                file_path=file_path,
                start_line=fdef.start_line,
                end_line=fdef.end_line,
                cc=cc,
                coverage_percent=coverage_percent,
                crap=crap,
            )
        )

    return out
