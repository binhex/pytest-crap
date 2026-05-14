"""Function-to-line mapper using AST."""

import ast
from dataclasses import dataclass


@dataclass
class FunctionDef:
    """Represents a function definition with its line range."""

    name: str
    start_line: int
    end_line: int
    coverage_start_line: int
    is_method: bool = False
    is_async: bool = False


class FunctionMapper(ast.NodeVisitor):
    """Maps functions in a Python file to their line ranges."""

    def __init__(self) -> None:
        self.functions: list[FunctionDef] = []
        self.current_class: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit a class definition."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a function definition."""
        self._add_function(node, is_async=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit an async function definition."""
        self._add_function(node, is_async=True)
        self.generic_visit(node)

    @staticmethod
    def _is_docstring(stmt: ast.stmt) -> bool:
        """Check if an AST statement node is a docstring expression."""
        return (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        )

    def _add_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_async: bool,
    ) -> None:
        """Add a function to the list."""
        # Calculate end line: use the end of the last statement or decorator
        end_line = node.end_lineno or node.lineno

        # Calculate the line where executable code starts, skipping docstring if present.
        # Docstrings are non-executable and are never reported as covered by coverage
        # tools, yet the AST node's end_lineno includes them. Excluding them from the
        # coverage range prevents artificially-inflated CRAP scores.
        coverage_start_line: int = node.lineno
        first_stmt = node.body[0]
        if self._is_docstring(first_stmt):
            docstring_end = first_stmt.end_lineno or first_stmt.lineno
            coverage_start_line = docstring_end + 1

        # If the docstring was the entire body (e.g. an abstract stub), there are no
        # executable lines to cover.
        if coverage_start_line > end_line:
            coverage_start_line = end_line + 1

        self.functions.append(
            FunctionDef(
                name=node.name,
                start_line=node.lineno,
                end_line=end_line,
                coverage_start_line=coverage_start_line,
                is_method=self.current_class is not None,
                is_async=is_async,
            )
        )


def map_functions(file_path: str) -> list[FunctionDef]:
    """Extract all function definitions from a Python file.

    Args:
        file_path: Path to a Python source file.

    Returns:
        List of FunctionDef objects with line ranges.

    Raises:
        SyntaxError: If the file cannot be parsed.
        FileNotFoundError: If the file does not exist.
    """
    with open(file_path) as f:
        source = f.read()

    tree = ast.parse(source)
    mapper = FunctionMapper()
    mapper.visit(tree)

    return mapper.functions
