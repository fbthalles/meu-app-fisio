"""Execute original AST nodes without importing UI or Firebase entrypoints.

No formula is copied. Only functions, literal constants and selected questionnaire
UI blocks are executed. This is unit coverage, not full Streamlit integration.
"""
import ast
from datetime import datetime
from pathlib import Path
import re
import types
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def tree(filename):
    return ast.parse((ROOT / filename).read_text(encoding='utf-8'))


def execute(nodes, namespace, filename):
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(ROOT / filename), 'exec'), namespace)


def load(filename):
    namespace = dict(pd=pd, np=np, re=re, datetime=datetime)
    nodes = []
    for node in tree(filename).body:
        if isinstance(node, ast.FunctionDef):
            node.decorator_list = []
            nodes.append(node)
        elif isinstance(node, ast.Assign):
            try:
                ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            nodes.append(node)
    execute(nodes, namespace, filename)
    return types.SimpleNamespace(**namespace)


class Widgets:
    def __init__(self, responses):
        self.responses = responses
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def columns(self, n):
        return [self] * (n if isinstance(n, int) else len(n))
    def expander(self, *args, **kwargs):
        return self
    def selectbox(self, label, options, index=0, key=None, **kwargs):
        return self.responses.get(key, options[index])
    def slider(self, label, low, high, value, key=None, **kwargs):
        return self.responses.get(key, value)
    def info(self, *args, **kwargs):
        pass
    def markdown(self, *args, **kwargs):
        pass


def questionnaire(label, responses):
    filename = 'modulo_avaliacao.py'
    matches = [node for node in ast.walk(tree(filename))
               if isinstance(node, ast.With) and any(
                   isinstance(item.context_expr, ast.Call)
                   and isinstance(item.context_expr.func, ast.Attribute)
                   and item.context_expr.func.attr == 'expander'
                   and item.context_expr.args
                   and isinstance(item.context_expr.args[0], ast.Constant)
                   and label in str(item.context_expr.args[0].value)
                   for item in node.items)]
    assert len(matches) == 1, f'Expected exactly one questionnaire block: {label}'
    ns = dict(st=Widgets(responses), proms_aplicados=[], novas_respostas_proms={},
              _idx_prom=lambda options, key, default: default,
              _val_prom=lambda key, default: default)
    execute(matches, ns, filename)
    return ns


def evaluation_assignment(name, **inputs):
    """Run one original inline assignment; fail if source becomes ambiguous."""
    filename = 'modulo_avaliacao.py'
    nodes = [n for n in ast.walk(tree(filename)) if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    assert len(nodes) == 1, name
    execute(nodes, inputs, filename)
    return inputs[name]
