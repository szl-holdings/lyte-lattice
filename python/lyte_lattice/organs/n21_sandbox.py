"""N21 Sandbox — cite Daytona / E2B. Take the job. Do not rehost.

Not Daytona. Not E2B. Not a cloud VM. Arithmetic/boolean expressions only.

The whitelisted tree is evaluated by a small interpreter, never ``eval()``.
It applies Python's own operator functions, so results match Python. Every
integer value it produces, intermediate results included, must fit in
MAX_INT_BITS. A power whose size lower bound already exceeds that is refused
before it is computed. Any other result is checked right after its operation;
the operands are already bounded, so one operation builds at most
2 * MAX_INT_BITS bits before the refusal. ``9**9**9`` cannot pin a CPU.
"""
from __future__ import annotations

import ast
import operator
from typing import Any, Callable, Mapping

from lyte_lattice.organ import seal, text

NOTE = "Not Daytona. Not E2B. No shell, no network, no import."
DEFAULT_CODE = "1 + 2 * 3"
MAX_CHARS = 200
# Bound on every integer the expression builds, intermediate values included.
# 4096 bits is about 1,233 decimal digits, inside CPython's 4,300-digit
# int-to-str limit, so an admitted result always fits the JSON receipt.
MAX_INT_BITS = 4096
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

_BINARY: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_UNARY: dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Not: operator.not_,
}
_COMPARE: dict[type[ast.cmpop], Callable[[Any, Any], Any]] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}


class BoundExceeded(ArithmeticError):
    """An integer the expression builds would exceed MAX_INT_BITS."""

    def __init__(self) -> None:
        super().__init__(f"integer above {MAX_INT_BITS} bits")


def _bounded(value: Any) -> Any:
    if isinstance(value, int) and value.bit_length() > MAX_INT_BITS:
        raise BoundExceeded()
    return value


def _power(base: Any, exponent: Any) -> Any:
    # |base| ** n has at least (bit_length(|base|) - 1) * n + 1 bits. Refuse
    # before computing when that lower bound already exceeds MAX_INT_BITS;
    # _bounded() checks the exact size of anything that is computed.
    if isinstance(base, int) and isinstance(exponent, int) and exponent > 0 and abs(base) > 1:
        if (abs(base).bit_length() - 1) * exponent + 1 > MAX_INT_BITS:
            raise BoundExceeded()
    return _bounded(operator.pow(base, exponent))


def _evaluate(node: ast.AST) -> Any:
    """Evaluate a whitelisted node with Python's operator semantics, bounded."""
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant):
        return _bounded(node.value)
    if isinstance(node, ast.UnaryOp):
        return _bounded(_UNARY[type(node.op)](_evaluate(node.operand)))
    if isinstance(node, ast.BinOp):
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        if isinstance(node.op, ast.Pow):
            return _power(left, right)
        return _bounded(_BINARY[type(node.op)](left, right))
    if isinstance(node, ast.BoolOp):
        # `and` returns the first falsy operand, `or` the first truthy one,
        # otherwise the last operand; later operands are never evaluated.
        decisive = isinstance(node.op, ast.Or)
        value: Any = None
        for operand in node.values:
            value = _evaluate(operand)
            if bool(value) is decisive:
                return value
        return value
    if isinstance(node, ast.Compare):
        # a < b < c is (a < b) and (b < c), with b evaluated once.
        left = _evaluate(node.left)
        result: Any = True
        for op, comparator in zip(node.ops, node.comparators):
            right = _evaluate(comparator)
            result = _COMPARE[type(op)](left, right)
            if not result:
                return result
            left = right
        return result
    # _illegal_node() admits nothing else; refuse rather than guess.
    raise TypeError(f"illegal node type: {type(node).__name__}")


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
        result = _evaluate(tree)
    except BoundExceeded as exc:
        return _receipt(
            payload,
            status="blocked",
            code=code,
            lang=lang,
            allowed=False,
            result=None,
            error=f"bound exceeded: {exc}",
        )
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
