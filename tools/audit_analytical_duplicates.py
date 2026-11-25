#!/usr/bin/env python3
"""Find structurally identical top-level Python function bodies in analytical code.

This is a conservative static audit: it flags exact AST-body matches, not merely
similar names. Human review is required before removing scientifically distinct
implementations or UI orchestration.
"""
from __future__ import annotations
import ast, hashlib, json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN = [ROOT / "analysis_engine", ROOT / "pages"]

def norm(node: ast.AST) -> str:
    body = ast.Module(body=node.body, type_ignores=[])
    return ast.dump(body, annotate_fields=True, include_attributes=False)

def main():
    found = defaultdict(list)
    for base in SCAN:
        if not base.exists(): continue
        for path in base.rglob("*.py"):
            try: tree = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError): continue
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    digest = hashlib.sha256(norm(node).encode()).hexdigest()
                    found[digest].append({"file":str(path.relative_to(ROOT)),"function":node.name,"line":node.lineno})
    duplicates = [v for v in found.values() if len(v) > 1]
    report = {"scope":[str(x.relative_to(ROOT)) for x in SCAN],"exact_duplicate_groups":duplicates,
              "unique_function_bodies":len(found),"duplicate_groups":len(duplicates),
              "interpretation":"Exact AST-body matches only. Similar calculations with different assumptions require manual scientific review."}
    out=ROOT/"reports"; out.mkdir(exist_ok=True)
    (out/"exact_duplicate_function_audit.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__ == "__main__": main()
