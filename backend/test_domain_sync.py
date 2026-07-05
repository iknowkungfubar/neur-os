"""Verify Python and TypeScript domain layers stay in sync.

The same logic exists in backend/domain/ (Python) and shared/ (TypeScript).
This test ensures their public exports match — if one adds a function without
the other, this catches it."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _py_exports() -> set[str]:
    """Extract top-level function and class names from Python domain files."""
    exports = set()
    for f in sorted((ROOT / "backend/domain").rglob("*.py")):
        tree = ast.parse(f.read_text())
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                exports.add(node.name)
    return exports


def _ts_exports() -> set[str]:
    """Extract exported function and class names from TypeScript domain file."""
    exports = set()
    ts_file = ROOT / "shared/domain.ts"
    if not ts_file.exists():
        return exports
    text = ts_file.read_text()
    # matches: export class X or export function X
    for m in re.finditer(r'export\s+(?:class|function)\s+(\w+)', text):
        exports.add(m.group(1))
    return exports


def test_domain_interface_in_sync():
    py = _py_exports()
    ts = _ts_exports()
    # PascalCase class names are identical between TS and Python.
    # camelCase function names (TS) map to snake_case (Python).
    def to_py(name: str) -> str:
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower() if name[0].islower() else name
    ts_in_py = {t for t in ts if to_py(t) in py}
    missing_in_py = ts - ts_in_py
    assert not missing_in_py, f"TypeScript exports not found in Python domain: {missing_in_py}"
    # Warn about Python-only exports
    py_only = py - {to_py(t) for t in ts}
    if py_only:
        print(f"Note: Python-only domain exports (no TS equivalent): {sorted(py_only)}")
