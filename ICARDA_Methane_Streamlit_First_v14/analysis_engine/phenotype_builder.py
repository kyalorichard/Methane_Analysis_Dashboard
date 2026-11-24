
"""Safe, auditable formula evaluation for user-defined phenotype variables."""
import ast
import numpy as np
import pandas as pd

_ALLOWED_FUNCTIONS = {
    "abs": abs, "sqrt": np.sqrt, "log": np.log, "log1p": np.log1p,
    "exp": np.exp, "minimum": np.minimum, "maximum": np.maximum,
    "clip": np.clip, "where": np.where,
}

class FormulaError(ValueError):
    pass

def _eval_node(node, columns):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, columns)
    if isinstance(node, ast.Name):
        if node.id in columns:
            return columns[node.id]
        if node.id in _ALLOWED_FUNCTIONS:
            return _ALLOWED_FUNCTIONS[node.id]
        raise FormulaError(f"Unknown variable or function: {node.id}")
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        left, right = _eval_node(node.left, columns), _eval_node(node.right, columns)
        ops = {ast.Add: lambda a,b:a+b, ast.Sub:lambda a,b:a-b,
               ast.Mult:lambda a,b:a*b, ast.Div:lambda a,b:a/b,
               ast.Pow:lambda a,b:a**b, ast.Mod:lambda a,b:a%b}
        fn = ops.get(type(node.op))
        if fn is None: raise FormulaError("Unsupported arithmetic operator.")
        with np.errstate(all="ignore"):
            return fn(left, right)
    if isinstance(node, ast.UnaryOp):
        value = _eval_node(node.operand, columns)
        if isinstance(node.op, ast.USub): return -value
        if isinstance(node.op, ast.UAdd): return value
        if isinstance(node.op, ast.Not): return np.logical_not(value)
        raise FormulaError("Unsupported unary operator.")
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, columns)
        result = True
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, columns)
            ops = {ast.Gt: np.greater, ast.GtE: np.greater_equal,
                   ast.Lt: np.less, ast.LtE: np.less_equal,
                   ast.Eq: np.equal, ast.NotEq: np.not_equal}
            fn = ops.get(type(op))
            if fn is None: raise FormulaError("Unsupported comparison operator.")
            result = np.logical_and(result, fn(left, right))
            left = right
        return result
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, columns) for v in node.values]
        if isinstance(node.op, ast.And): return np.logical_and.reduce(values)
        if isinstance(node.op, ast.Or): return np.logical_or.reduce(values)
        raise FormulaError("Unsupported logical operator.")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCTIONS:
            raise FormulaError("Only supported functions may be called.")
        if node.keywords: raise FormulaError("Keyword arguments are not supported.")
        fn = _ALLOWED_FUNCTIONS[node.func.id]
        args = [_eval_node(arg, columns) for arg in node.args]
        return fn(*args)
    raise FormulaError(f"Unsupported formula syntax: {type(node).__name__}")

def evaluate_phenotype_formula(df, formula):
    """Evaluate formula against dataframe columns; no eval/exec or attribute access."""
    if not isinstance(formula, str) or not formula.strip():
        raise FormulaError("Enter a formula.")
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"Formula syntax error: {exc.msg}") from exc
    allowed_nodes = (ast.Expression, ast.Name, ast.Constant, ast.BinOp, ast.UnaryOp,
                     ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
                     ast.USub, ast.UAdd, ast.Not, ast.Call, ast.Load,
                     ast.Compare, ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq,
                     ast.NotEq, ast.BoolOp, ast.And, ast.Or)
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            raise FormulaError(f"Unsupported syntax: {type(node).__name__}")
    result = _eval_node(tree, {str(c): pd.to_numeric(df[c], errors="coerce") for c in df.columns})
    if np.isscalar(result):
        result = pd.Series(result, index=df.index)
    result = pd.Series(result, index=df.index, name="derived_phenotype")
    result = pd.to_numeric(result, errors="coerce").replace([np.inf, -np.inf], np.nan)
    return result

def create_derived_phenotype(df, name, formula):
    name = str(name).strip()
    if not name or not name.replace("_", "a").isalnum() or name[0].isdigit():
        raise FormulaError("Use a valid variable name: letters, numbers and underscores; do not start with a number.")
    if name in df.columns:
        raise FormulaError(f"'{name}' already exists. Choose a new name; source columns are not overwritten.")
    out = df.copy()
    out[name] = evaluate_phenotype_formula(df, formula)
    if out[name].notna().sum() == 0:
        raise FormulaError("The formula produced no valid values. Check variable names, units and denominator values.")
    return out
