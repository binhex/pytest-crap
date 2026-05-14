# pytest-crap

[![Test](https://github.com/ChristianMurphy/pytest-crap/actions/workflows/test.yml/badge.svg)](https://github.com/ChristianMurphy/pytest-crap/actions/workflows/test.yml)
[![PyPI - Version](https://img.shields.io/pypi/v/pytest-crap)](https://pypi.org/project/pytest-crap/)

## Forked to filter out docstrings, blank lines and comments from calculated CRAP score

A pytest plugin that calculates CRAP scores and displays prioritized lists of high-risk functions to guide test writing.

## What is CRAP?

**CRAP** stands for **Change Risk Anti-Patterns** (or, more colloquially, "Change Risk Analysis and Predictions"). The metric was introduced by Alberto Savoia and Bob Evans to help developers identify code that is both complex and poorly tested—a risky combination.

The CRAP score combines two factors:

- **Cyclomatic Complexity (CC)**: A measure of how many independent paths exist through your code. More branches (`if`, `for`, `while`, `try`, etc.) means higher complexity.
- **Code Coverage**: The percentage of lines executed by your tests.

The formula is:

```
CRAP(m) = CC(m)² × (1 - cov(m))³ + CC(m)
```

Where `CC(m)` is the cyclomatic complexity and `cov(m)` is the code coverage (0.0 to 1.0) for method `m`.

### Why Use CRAP Scores?

- **Prioritize testing efforts**: Focus on functions that are both complex AND under-tested
- **Identify risky code**: High CRAP scores indicate code that's likely to harbor bugs and is difficult to change safely
- **Track improvement**: Monitor CRAP scores over time to ensure code quality improves

### Interpreting CRAP Scores

| Score | Interpretation |
|-------|----------------|
| < 5 | Excellent — low complexity, well tested |
| 5–15 | Acceptable — reasonable balance |
| 15–30 | Warning — consider adding tests or simplifying |
| > 30 | Critical — high risk, prioritize for refactoring/testing |

A function with **CC=1 and 100% coverage** has a CRAP score of **1** (perfect).
A function with **CC=10 and 0% coverage** has a CRAP score of **110** (very high risk).

## Installation

```bash
pip install pytest-crap
```

Or with Poetry:

```bash
poetry add pytest-crap
```

## Requirements

- Python 3.10+
- pytest 7.0+
- pytest-cov (for coverage data)

## Usage

Run pytest with the `--crap` flag:

```bash
pytest --crap
```

This will run your tests with coverage enabled and display CRAP score tables at the end.

### Example Output

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                            CRAP by Function                              ┃
┡━━━━━━━━┯━━━━━┯━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━┩
│   CRAP │  CC │ Coverage │ Function             │ File                    │
├────────┼─────┼──────────┼──────────────────────┼─────────────────────────┤
│  42.50 │   8 │    12.5% │ complex_parser       │ src/parser.py           │
│  31.00 │   5 │     0.0% │ validate_input       │ src/validator.py        │
│  12.25 │   3 │    50.0% │ process_data         │ src/processor.py        │
│   1.00 │   1 │   100.0% │ simple_helper        │ src/utils.py            │
└────────┴─────┴──────────┴──────────────────────┴─────────────────────────┘
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--crap` | `false` | Enable CRAP score reporting |
| `--crap-threshold` | `30` | CRAP score threshold for highlighting. Functions at or above this value are flagged as high-risk. |
| `--crap-top-n` | `20` | Number of functions to display in each table. Set to `0` to show all. |

### Examples

Show top 10 functions with a stricter threshold:

```bash
pytest --crap --crap-threshold=15 --crap-top-n=10
```

Show all functions regardless of score:

```bash
pytest --crap --crap-top-n=0
```

Combine with other pytest options:

```bash
pytest --crap --cov-branch -v tests/
```

## Output Tables

pytest-crap displays three summary tables:

1. **CRAP by Function**: Individual functions ranked by CRAP score
2. **CRAP by File**: Files ranked by their highest CRAP score, with count of functions above threshold
3. **CRAP by Folder**: Directories ranked by highest CRAP score

## Integration with CI

Add to your CI pipeline to track CRAP scores. Example GitHub Actions step:

```yaml
- name: Run tests with CRAP reporting
  run: pytest --crap --crap-threshold=30
```

## Contributing

See [contributing.md](./contributing.md) for development setup and guidelines.

## License

MIT

## References

- [Original CRAP metric paper](http://www.artima.com/weblogs/viewpost.jsp?thread=210575) by Alberto Savoia
- [Cyclomatic Complexity](https://en.wikipedia.org/wiki/Cyclomatic_complexity) on Wikipedia
- [radon](https://radon.readthedocs.io/) - Python library for code metrics
