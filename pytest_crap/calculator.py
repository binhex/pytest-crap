"""CRAP score calculator combining radon CC and line coverage data."""

from dataclasses import dataclass

from radon.complexity import cc_visit

from .mapper import map_functions


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

    out: list[FunctionScore] = []
    for fdef in funcs:
        # Use coverage_start_line to exclude non-executable lines (e.g. docstrings)
        # from the coverage percentage calculation.
        total_lines = max(1, fdef.end_line - fdef.coverage_start_line + 1)
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
