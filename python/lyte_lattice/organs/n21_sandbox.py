"""N21 Sandbox — cite Daytona / E2B. Take the job. Do not rehost.

Not Daytona. Not E2B. Not a cloud VM. Arithmetic/boolean expressions only.
"""
from __future__ import annotations

import ast
from typing import Any, Mapping

from lyte_lattice.organ import seal, text

NOTE = "Not Daytona. Not E2B. No shell, no network, no import."
DEFAULT_CODE = "1 + 2 * 3"
MAX_CHARS = 200
PYTHON_LANGS = frozenset({"py", "python", "python3"})

# Expression-only whitelist. Name/Call/Attribute/collections/imports stay out.
ALLOWED_NODES = frozenset(
    {
        "Expression",
        "BinOp",
        "UnaryOp",
        "BoolOp",
        "Compare",
        "Constant",
        "Num",
        "NameConstant",
        "Add",
        "Sub",
        "Mult",
        "Div",
        "FloorDiv",
        "Mod",
        "Pow",
        "UAdd",
        "USub",
        "And",
        "Or",
        "Not",
        "Eq",
        "NotEq",
        "Lt",
        "LtE",
        "Gt",
        "GtE",
        "Load",
    }
)
ARITH_CONST = (int, float, complex, bool)


def _receipt(
    payload: Mapping[str, Any],
    *,
    status: str,
    code: str,
    lang: str,
    allowed: bool,
    result: Any,
    error: str | None,
) -> dict[str, Any]:
    return seal(
        cell="N21",
        status=status,
        payload=payload,
        output={
            "code": code,
            "lang": lang,
            "allowed": allowed,
            "result": result,
            "error": error,
            "note": NOTE,
        },
    )


def _illegal_node(tree: ast.AST) -> str | None:
    for node in ast.walk(tree):
        name = type(node).__name__
        if name not in ALLOWED_NODES:
            return name
        if name == "Constant":
            val = getattr(node, "value", None)
            if val is None or isinstance(val, ARITH_CONST):
                continue
            return name
        if name == "Num":
            val = getattr(node, "n", None)
            if isinstance(val, (int, float, complex)):
                continue
            return name
        if name == "NameConstant":
            val = getattr(node, "value", None)
            if val is None or isinstance(val, bool):
                continue
            return name
    return None


def act(payload: Mapping[str, Any]) -> dict[str, Any]:
    lang = text(payload, "lang", default="py").lower()
    code = text(payload, "code", "expr", "expression", default=DEFAULT_CODE)
    if not code:
        code = DEFAULT_CODE

    if lang not in PYTHON_LANGS:
        return _receipt(
            payload,
            status="blocked",
            code=code,
            lang=lang,
            allowed=False,
            result=None,
            error=f"illegal node type: lang={lang}",
        )

    if len(code) > MAX_CHARS:
        return _receipt(
            payload,
            status="blocked",
            code=code,
            lang=lang,
            allowed=False,
            result=None,
            error="illegal node type: too-long",
        )

    try:
        tree = ast.parse(code, filename="<n21-sandbox>", mode="eval")
    except SyntaxError as exc:
        return _receipt(
            payload,
            status="blocked",
            code=code,
            lang=lang,
            allowed=False,
            result=None,
            error=f"illegal node type: SyntaxError ({exc.msg})",
        )

    illegal = _illegal_node(tree)
    if illegal is not None:
        return _receipt(
            payload,
            status="blocked",
            code=code,
            lang=lang,
            allowed=False,
            result=None,
            error=f"illegal node type: {illegal}",
        )

    try:
        compiled = compile(tree, "<n21-sandbox>", "eval")
        result = eval(compiled, {"__builtins__": {}}, {})  # noqa: S307 — whitelist + empty builtins
    except Exception as exc:
        return _receipt(
            payload,
            status="error",
            code=code,
            lang=lang,
            allowed=True,
            result=None,
            error=f"{type(exc).__name__}: {exc}",
        )

    if isinstance(result, bool) or result is None or isinstance(result, (int, float, complex)):
        out = result
    else:
        return _receipt(
            payload,
            status="blocked",
            code=code,
            lang=lang,
            allowed=False,
            result=None,
            error=f"illegal node type: {type(result).__name__}",
        )

    return _receipt(
        payload,
        status="ok",
        code=code,
        lang=lang,
        allowed=True,
        result=out,
        error=None,
    )
