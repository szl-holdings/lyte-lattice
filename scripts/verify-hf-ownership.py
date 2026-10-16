#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify Lyte's read-only delegation; never publish or certify runtime uptime."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import posixpath
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

SHA40 = re.compile(r'^[0-9a-f]{40}$')
SOURCE_REQUIRED_CHECKS = (
    'python-compile', 'lint', 'unit', 'api-contract', 'release-gates',
    'database-migrations', 'connector-contract', 'truth-and-governance',
    'security-scan', 'secret-scan', 'frontend-static-contract', 'accessibility',
    'responsive-overflow', 'bundle-budget', 'container-build', 'container-smoke',
    'source-binding',
)
# Reviewed immutable szl-holdings/a11oy blobs. The complete closure was reviewed
# at REVIEWED_PUBLISHER_COMMIT, including the native presentation and Sentra
# observation-budget helpers loaded by the generated-flagship route. The Lyte
# publisher, its 17 source gates and both pinned controllers are unchanged.
# Admission scope and reviewed identities: docs/lyte-publisher-admission.md.
# A new publisher, entrypoint, route or closure file requires a separate review.
REVIEWED_PUBLISHER_COMMIT = '58a0e102e8ebc0b35af86be3ec2de3b6c4e41d66'
PUBLISHER_PATH = 'scripts/hf_publish_lyte_enterprise.py'
ENTRYPOINT_PATH = 'scripts/hf_publish_vertical_flagships_v4.py'
WORKFLOW_PATH = '.github/workflows/hf-sync.yml'
DYNAMIC_PUBLISHER_BLOB = '7c533d753a2b913a77bb71074f04aa5b753b0392'
DYNAMIC_ENTRYPOINT_BLOB = '199cd4d30e86c6b0e01aeb7818803bb7d68d6a70'
# The workflow runs the entrypoint without SZL_FLAGSHIP_SCOPE, so its default
# estate route executes in ONE process: the generated-flagship publisher, then
# the Lyte publisher, then the combined vertical-services publisher. Bind that
# whole route, plus the workflow job's own source, plan and completion gates.
DYNAMIC_DEPENDENCY_BLOBS = {
    WORKFLOW_PATH: 'a955e43f7878b050a849d597b245581c396fac9f',
    'scripts/szl_release_guard.py': 'f6c7bc02df02076388be5fa0b6949d8929cc2ba2',
    'scripts/lyte_enterprise_live_contract.py': '494116f65b24ea5b8a516abde31668be2248cbf4',
    'scripts/hf_existing_space_guard.py': 'ebab5d507ba589bb64d01a45bf32a03c2b52cb45',
    'scripts/hf_exact_main_ownership.py': '6e95133ac74f0d05d5372ed68022a691ceaa15c2',
    'scripts/estate_repair_dispatch.py': '81f0e83729390ee66b633a8d45e5f1139374ba41',
    'scripts/estate_child_completion.py': '5e59e91824d58da9bcc650c623c3bdfaf6f0040b',
    # Generated-flagship route (Terra, Sentra, Counsel, Finance shells).
    'scripts/hf_publish_vertical_flagships_v4_impl.py': '421188ba9e1dcce78bf2503e4b10ead3e126bded',
    'scripts/_hf_publish_vertical_flagships_v4_impl_base.py': '419931621a3d7de4da233840762761c4207007f5',
    'scripts/hf_finance_read_proxy.py': '56ec9cd7df6eef37e59395ce35e010637487211c',
    'scripts/hf_flagship_runtime_contract.py': '1b3571a8b49c31f12307bf44e77c303d2b86fb32',
    'scripts/hf_finance_workspace.py': '6bf54deb552bdf94578cef45f84ead8a2318c3aa',
    'scripts/hf_finance_research_workspace.py': '18ba3c0a1feb776e7f12f46c5b69b6069b597180',
    'scripts/hf_finance_signed_workspace.py': 'febc20a7dc1391d35397bb81e38222135eb3d100',
    'scripts/hf_finance_functional_gate.py': '7d1d1bb9a7d44add13e7f06d8ed5904d8fddb21b',
    'scripts/hf_finance_projection_manifest.py': '4d00c2d0b1005c4f23f37c810754bdeb7eff4453',
    # Source-owned presentation and bounded Sentra observation code.
    'scripts/hf_vertical_native_presentation.py': 'a4a1b1dc0598b08438770e8771709521b28cddbb',
    'scripts/hf_sentra_upstream.py': '11e799ca6c8feb270888209188088a7f86c44fe3',
    # Combined vertical-services route, run after Lyte in the same process.
    'scripts/hf_publish_vertical_services_intelligence_v4.py': 'c4191e7f6139ad934fe9c8809174476934b2eb59',
    'scripts/hf_publish_vertical_services_frontier_v3.py': '69b19505d307f22faeee49a98d11c97a58abd603',
    'scripts/hf_publish_vertical_services.py': '3f51f74299235e99d3a1fce3b1eae3163014beba',
}
# Scope selection reviewed in the entrypoint. Explicit `lyte` runs a subset of
# the default estate closure; every other route does not publish Lyte.
ENTRYPOINT_SCOPE_VARIABLE = 'SZL_FLAGSHIP_SCOPE'
ADMITTED_DEFAULT_SCOPE = 'estate'
ADMITTED_SCOPES = ('estate', 'lyte')
# Non-standard-library imports reviewed in the closure. Any other import name
# is treated as a repository sibling module and must itself be admitted.
ADMITTED_EXTERNAL_IMPORTS = ('huggingface_hub',)
# One executable-suffix set for closure references and workflow job programs.
# JSX/TSX and the ESM/CJS TypeScript suffixes run under Node and its loaders.
CODE_SUFFIXES = ('.py', '.pyw', '.pyc', '.pyz', '.pyd', '.pth', '.so', '.sh', '.bash',
                 '.mjs', '.cjs', '.js', '.ts', '.jsx', '.tsx', '.mts', '.cts')
WORKFLOW_MODULES = ('pip',)

class ContractError(ValueError):
    """A publication authority or exact-source invariant is missing."""

def git_blob(source: str) -> str:
    payload = source.encode('utf-8')
    return hashlib.sha1(f'blob {len(payload)}\0'.encode('ascii') + payload).hexdigest()

def _repo_path(value: str) -> str:
    """Normalize a publisher-repository-relative POSIX path; the root is ''."""
    if '\\' in value or value.startswith('/'):
        raise ContractError('Publisher closure path is not repository-relative')
    path = posixpath.normpath(value)
    if path == '.':
        return ''
    if path == '..' or path.startswith('../'):
        raise ContractError('Publisher closure path escapes the publisher repository')
    return path

def _join(base: str, part: str) -> str:
    return _repo_path(posixpath.join(base, part) if base else part)

def _parent(path: str) -> str:
    if path == '':
        raise ContractError('Publisher closure path escapes the publisher repository')
    return posixpath.dirname(path)

def _literal_part(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value:
        return node.value
    raise ContractError('Publisher closure path is not statically reviewable')

def _call_name(node: ast.Call) -> str | None:
    func = node.func
    return func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else None

def _is_os_path(node: ast.AST) -> bool:
    return (isinstance(node, ast.Attribute) and node.attr == 'path'
            and isinstance(node.value, ast.Name) and node.value.id == 'os')

_PATH_TYPES = ('Path', 'PurePath', 'PurePosixPath', 'PosixPath')
_ENUMERATORS = ('listdir', 'scandir', 'walk', 'fwalk', 'glob', 'iglob', 'rglob', 'iterdir')
_ENUMERATOR_MODULES = ('os', 'glob', 'posix', 'nt')

class _Bindings:
    """Every name binding in one module, by function scope; static, never executed.

    A binding is an `assign` (`name = value` or `name: T = value`), an `import`
    (recording the bound module or `module.member`), a `param`, or `other` (any
    other form: loop, `with`, `except`, walrus, augmented, `del`, `def`, `class`,
    comprehension or `match` target). Class bodies and comprehensions count
    toward their enclosing function, which can only make a name less exact.
    """
    def __init__(self, tree: ast.Module):
        self.sites: dict[str, list[tuple[ast.AST | None, str, Any]]] = {}
        self.scope: dict[ast.AST, ast.AST | None] = {}
        self.parent: dict[ast.AST, ast.AST | None] = {}
        self.declared: set[str] = set()
        self.mutated: set[str] = set()
        self.star = False
        self._simple: set[int] = set()
        self._visit(tree, None)
        receivers = {id(node.value) for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        probes = {id(node.args[0]) for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                  and node.func.id == 'getattr' and len(node.args) in (2, 3) and not node.keywords
                  and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str)
                  and node.args[1].value not in _ENUMERATORS}
        # Loads other than an attribute receiver or a literal `getattr` probe.
        self.escapes = {id(node) for node in ast.walk(tree) if isinstance(node, ast.Name)
                        and isinstance(node.ctx, ast.Load)
                        and id(node) not in receivers and id(node) not in probes}
        self.escaped = {node.id for node in ast.walk(tree) if id(node) in self.escapes}

    def _bind(self, name: str, scope: ast.AST | None, kind: str, value: Any) -> None:
        self.sites.setdefault(name, []).append((scope, kind, value))

    def _visit(self, node: ast.AST, scope: ast.AST | None) -> None:
        self.scope[node] = scope
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            self.parent[node] = scope
            args = node.args
            outer = [*args.defaults, *(item for item in args.kw_defaults if item is not None)]
            inner: list[ast.AST] = [args]
            if isinstance(node, ast.Lambda):
                inner.append(node.body)
            else:
                self._bind(node.name, scope, 'other', node)
                outer += [*node.decorator_list, *([node.returns] if node.returns else [])]
                inner += [*node.body, *getattr(node, 'type_params', ())]
            for item in (*args.posonlyargs, *args.args, args.vararg, *args.kwonlyargs, args.kwarg):
                if item is not None:
                    self._bind(item.arg, node, 'param', item)
            for child in outer:
                self._visit(child, scope)
            self.scope[args] = node
            for child in inner:
                if child is args:
                    for item in ast.iter_child_nodes(args):
                        if item not in outer:
                            self._visit(item, node)
                else:
                    self._visit(child, node)
            return
        if isinstance(node, ast.ClassDef):
            self._bind(node.name, scope, 'other', node)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == '*':
                    self.star = True
                elif isinstance(node, ast.Import):
                    top = alias.name.split('.', 1)[0]
                    self._bind(alias.asname or top, scope, 'import', alias.name if alias.asname else top)
                else:
                    module = None if node.level else f'{node.module}.{alias.name}'
                    self._bind(alias.asname or alias.name, scope, 'import', module)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            self.declared.update(node.names)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                if isinstance(target, ast.Name):
                    self._simple.add(id(target))
                    self._bind(target.id, scope, 'assign', node)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            self._bind(node.name, scope, 'other', node)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            self._bind(node.name, scope, 'other', node)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            self._bind(node.rest, scope, 'other', node)
        elif (isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Load)
              and id(node) not in self._simple):
            self._bind(node.id, scope, 'other', node)
        elif isinstance(node, ast.Attribute) and not isinstance(node.ctx, ast.Load):
            root = node.value
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                self.mutated.add(root.id)
        for child in ast.iter_child_nodes(node):
            self._visit(child, scope)

    def resolve(self, name: str, scope: ast.AST | None) -> list[tuple[ast.AST | None, str, Any]] | None:
        """The bindings a load of `name` in `scope` observes; None when not exact."""
        if self.star or name in self.declared:
            return None
        while True:
            found = [site for site in self.sites.get(name, ()) if site[0] is scope]
            if found:
                return found
            if scope is None:
                return None
            scope = self.parent[scope]

    def module(self, name: str) -> str | None:
        """The one module every binding of `name` imports, if nothing else binds or patches it."""
        sites = self.sites.get(name, [])
        modules = {value for _, kind, value in sites}
        if (not sites or self.star or name in self.declared or name in self.mutated
                or any(kind != 'import' for _, kind, _ in sites) or len(modules) != 1):
            return None
        return modules.pop()

    def genuine(self, node: ast.AST, module: str) -> bool:
        """`node` is the standard-library module itself: imported, never rebound, patched or passed on."""
        return (isinstance(node, ast.Name) and self.module(node.id) == module
                and node.id not in self.escaped)

    def path_type(self, func: ast.AST) -> bool:
        if isinstance(func, ast.Name):
            return func.id in _PATH_TYPES and self.module(func.id) == f'pathlib.{func.id}'
        return (isinstance(func, ast.Attribute) and func.attr in _PATH_TYPES
                and self.genuine(func.value, 'pathlib'))

class _ExactAnchors:
    """Names for `_anchored` in one scope: anchored only if every binding the load can
    observe there is an anchored assignment. Unlike the discovery union, an anchor in
    an unrelated scope, or one overwritten by any other binding, does not count."""
    def __init__(self, bindings: _Bindings, origin: str, scope: ast.AST | None,
                 seen: frozenset[tuple[str, int]] = frozenset()):
        self.bindings, self.origin, self.scope, self.seen = bindings, origin, scope, seen

    def get(self, name: str) -> frozenset[str] | None:
        sites = self.bindings.resolve(name, self.scope)
        if not sites or any(kind != 'assign' for _, kind, _ in sites):
            return None
        result: set[str] = set()
        for scope, _, node in sites:
            key = (name, id(node))
            if key in self.seen:
                return None
            names = _ExactAnchors(self.bindings, self.origin, scope, self.seen | {key})
            value = _anchored(node.value, self.origin, names, self.bindings)
            if value is None:
                return None
            result |= value
        return frozenset(result)

def _anchored(node: ast.AST, origin: str, names: dict[str, frozenset[str]] | _ExactAnchors,
              trust: _Bindings | None = None) -> frozenset[str] | None:
    """Repository paths of an expression anchored at this file's own location.

    With `trust`, every anchor must be genuine: `__file__` never rebound, the real
    `os` module and real `pathlib` constructors, and exactly scoped names.
    """
    if isinstance(node, ast.Name):
        if node.id == '__file__':
            return frozenset({origin}) if trust is None or '__file__' not in trust.sites else None
        return names.get(node.id)
    if isinstance(node, ast.Attribute) and node.attr == 'parent':
        base = _anchored(node.value, origin, names, trust)
        return None if base is None else frozenset(_parent(path) for path in base)
    if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
            and node.value.attr == 'parents'):
        base = _anchored(node.value.value, origin, names, trust)
        if base is None:
            return None
        if not (isinstance(node.slice, ast.Constant) and type(node.slice.value) is int
                and node.slice.value >= 0):
            raise ContractError('Publisher closure path is not statically reviewable')
        result = set()
        for path in base:
            for _ in range(node.slice.value + 1):
                path = _parent(path)
            result.add(path)
        return frozenset(result)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        base = _anchored(node.left, origin, names, trust)
        if base is None:
            return None
        part = _literal_part(node.right)
        return frozenset(_join(path, part) for path in base)
    if not isinstance(node, ast.Call):
        return None
    func, name = node.func, _call_name(node)
    if isinstance(func, ast.Attribute) and _is_os_path(func.value) and node.args:
        if trust is not None and not trust.genuine(func.value.value, 'os'):
            return None
        base = _anchored(node.args[0], origin, names, trust)
        if base is None:
            return None
        if name in ('abspath', 'realpath', 'normpath'):
            return base
        if name == 'dirname':
            return frozenset(_parent(path) for path in base)
        if name == 'join':
            parts = [_literal_part(arg) for arg in node.args[1:]]
            return frozenset(_join(path, '/'.join(parts)) for path in base)
        return None
    if name in _PATH_TYPES and node.args:
        if trust is not None and not trust.path_type(func):
            return None
        base = _anchored(node.args[0], origin, names, trust)
        if base is None:
            return None
        parts = [_literal_part(arg) for arg in node.args[1:]]
        return frozenset(_join(path, '/'.join(parts)) if parts else path for path in base)
    if isinstance(func, ast.Attribute):
        base = _anchored(func.value, origin, names, trust)
        if base is None:
            return None
        if func.attr in ('resolve', 'absolute'):
            return base
        if func.attr == 'with_name':
            if len(node.args) != 1 or node.keywords:
                raise ContractError('Publisher closure path is not statically reviewable')
            part = _literal_part(node.args[0])
            return frozenset(_join(_parent(path), part) for path in base)
        if func.attr == 'joinpath':
            parts = [_literal_part(arg) for arg in node.args]
            return frozenset(_join(path, '/'.join(parts)) for path in base)
    return None

def _check_enumerations(tree: ast.Module, origin: str, names: dict[str, frozenset[str]],
                        bindings: _Bindings) -> None:
    """Directory listing can select unreviewed code; the job CWD is the repository root.

    A listing is recognised by its name on any receiver, through import and
    assignment aliases, and by string (`getattr`, `methodcaller`, subscripts).
    A listing module (`os`, `glob`, `posix`, `nt`) may be used only as an
    attribute receiver or in a literal `getattr` probe. The one admitted shape
    is a glob on a receiver not anchored at this file whose literal pattern ends
    in a concrete, wildcard-free, non-code suffix: it cannot select code.
    Anchored enumeration stays rejected. Only the genuine `ast` module's
    `walk` is exempt, because it walks syntax trees, not directories.
    """
    admitted = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ('glob', 'rglob', 'iglob') and len(node.args) == 1
                and not node.keywords and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            suffix = posixpath.splitext(node.args[0].value)[1]
            if (re.fullmatch(r'\.[A-Za-z0-9]+', suffix) is not None and suffix not in CODE_SUFFIXES
                    and _anchored(node.func.value, origin, names) is None):
                admitted.add(id(node.func))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            listing = (node.module or '').split('.', 1)[0] in _ENUMERATOR_MODULES and any(
                alias.name == '*' or alias.name in _ENUMERATORS for alias in node.names)
        elif isinstance(node, ast.Call):
            listing = ((isinstance(node.func, ast.Name) and node.func.id in _ENUMERATORS)
                       or (_call_name(node) in ('getattr', 'attrgetter', 'methodcaller') and any(
                           isinstance(arg, ast.Constant) and arg.value in _ENUMERATORS for arg in node.args)))
        elif isinstance(node, ast.Subscript):
            listing = isinstance(node.slice, ast.Constant) and node.slice.value in _ENUMERATORS
        elif isinstance(node, ast.Attribute):
            listing = (node.attr in _ENUMERATORS and id(node) not in admitted
                       and not (node.attr == 'walk' and bindings.genuine(node.value, 'ast')))
        elif isinstance(node, ast.Name):
            listing = id(node) in bindings.escapes and any(
                kind == 'import' and module in _ENUMERATOR_MODULES
                for _, kind, module in bindings.sites.get(node.id, ()))
        else:
            listing = False
        if listing:
            raise ContractError('Publisher closure enumerates a repository directory')

def _module_reference(module: str, origin: str) -> str | None:
    top = module.split('.', 1)[0]
    if not top:
        raise ContractError('Publisher closure import is not statically reviewable')
    if top == '__future__' or top in sys.stdlib_module_names or top in ADMITTED_EXTERNAL_IMPORTS:
        return None
    return _join(posixpath.dirname(origin), top + '.py')

_MODULE_LOADERS = ('import_module', '__import__', 'run_module')
_FILE_LOADERS = {'spec_from_file_location': 1, 'SourceFileLoader': 1, 'run_path': 0}
_REPOSITORY_LITERAL = re.compile(r'(?:\./)?scripts/[A-Za-z0-9_./-]+')

def file_references(path: str, source: str) -> tuple[set[str], set[str]]:
    """Statically derive (code, data) repository references; never execute source."""
    try:
        tree = ast.parse(source, filename=path)
    except (SyntaxError, ValueError):
        raise ContractError(f'Publisher closure source is not parseable Python: {path}') from None
    assignments = [node for node in ast.walk(tree)
                   if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None]
    names: dict[str, frozenset[str]] = {}
    for _ in range(len(assignments) + 1):
        changed = False
        for node in assignments:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = _anchored(node.value, path, names)
            for target in targets:
                if isinstance(target, ast.Name) and value:
                    merged = names.get(target.id, frozenset()) | value
                    if merged != names.get(target.id):
                        names[target.id], changed = merged, True
        if not changed:
            break
    anchors, cursor = {path}, path
    while cursor:
        cursor = posixpath.dirname(cursor)
        anchors.add(cursor)
    bindings = _Bindings(tree)
    _check_enumerations(tree, path, names, bindings)
    definitions: dict[str, list[ast.FunctionDef]] = {}
    calls: dict[str, list[ast.Call]] = {}
    callee_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            definitions.setdefault(node.name, []).append(node)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            calls.setdefault(node.func.id, []).append(node)
            callee_ids.add(id(node.func))
    value_uses = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
                  and isinstance(node.ctx, ast.Load) and id(node) not in callee_ids}

    def resolved(target: ast.AST, seen: frozenset[tuple[str, str]]) -> bool:
        """Exactly anchored where it is evaluated, or a parameter whose every
        same-module call site resolves. A discovery-union anchor from another
        scope, or one any other binding overwrites, does not resolve a loader."""
        scope = bindings.scope.get(target)
        function = scope if isinstance(scope, ast.FunctionDef) else None
        positional = [arg.arg for arg in (function.args.posonlyargs + function.args.args)] if function else []
        keyword = [arg.arg for arg in function.args.kwonlyargs] if function else []
        if not (isinstance(target, ast.Name) and target.id in positional + keyword):
            exact = _ExactAnchors(bindings, path, scope)
            return _anchored(target, path, exact, bindings) is not None
        if (function.name, target.id) in seen:
            return True
        stores = [node for node in ast.walk(function) if isinstance(node, ast.Name)
                  and node.id == target.id and not isinstance(node.ctx, ast.Load)]
        own = bindings.resolve(target.id, function)
        helper = bindings.resolve(function.name, bindings.parent[function])
        sites = calls.get(function.name, [])
        if (stores or not own or len(own) != 1 or own[0][1] != 'param'
                or not helper or [node for _, _, node in helper] != [function]
                or len(definitions[function.name]) != 1 or function.name in value_uses
                or not sites):
            return False
        for call in sites:
            if (any(isinstance(arg, ast.Starred) for arg in call.args)
                    or any(kw.arg is None for kw in call.keywords)):
                return False
            argument = next((kw.value for kw in call.keywords if kw.arg == target.id), None)
            if argument is None and target.id in positional and positional.index(target.id) < len(call.args):
                argument = call.args[positional.index(target.id)]
            if argument is None or not resolved(argument, seen | {(function.name, target.id)}):
                return False
        return True

    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(ref for alias in node.names
                         if (ref := _module_reference(alias.name, path)) is not None)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise ContractError(f'Publisher closure uses a relative import: {path}')
            ref = _module_reference(node.module or '', path)
            if ref is not None:
                found.add(ref)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _REPOSITORY_LITERAL.fullmatch(node.value):
                found.add(_repo_path(node.value))
        elif isinstance(node, (ast.List, ast.Tuple)):
            items = node.elts
            for index, item in enumerate(items[:-1]):
                if isinstance(item, ast.Constant) and item.value == '-m':
                    module = _literal_part(items[index + 1])
                    if module.split('.', 1)[0] in WORKFLOW_MODULES:
                        continue
                    if (ref := _module_reference(module, path)) is not None:
                        found.add(ref)
        if isinstance(node, ast.Call):
            name = _call_name(node)
            if name in _MODULE_LOADERS:
                target = node.args[0] if node.args else None
                if (ref := _module_reference(_literal_part(target), path)) is not None:
                    found.add(ref)
            elif name in _FILE_LOADERS:
                index = _FILE_LOADERS[name]
                target = node.args[index] if len(node.args) > index else next(
                    (kw.value for kw in node.keywords if kw.arg == 'location'), None)
                literal = isinstance(target, ast.Constant) and isinstance(target.value, str)
                if target is None or not (literal or resolved(target, frozenset())):
                    raise ContractError(f'Publisher closure loads a computed module path: {path}')
                if isinstance(target, ast.Constant):
                    found.add(_repo_path(target.value))
        if isinstance(node, (ast.BinOp, ast.Call, ast.Attribute, ast.Subscript)):
            found.update(ref for ref in (_anchored(node, path, names) or ()) if ref not in anchors)
    code = {ref for ref in found if posixpath.splitext(ref)[1] in CODE_SUFFIXES}
    return code, found - code

def derive_execution_closure(roots: list[str] | tuple[str, ...],
                             sources: dict[str, str]) -> tuple[list[str], list[str]]:
    """Transitive repository code closure from the workflow roots, or ContractError."""
    closure: set[str] = set()
    data: set[str] = set()
    queue = list(roots)
    while queue:
        path = queue.pop()
        if path in closure:
            continue
        source = sources.get(path)
        if not isinstance(source, str):
            raise ContractError(f'Publisher execution closure reaches an unreviewed repository path: {path}')
        closure.add(path)
        code, found = file_references(path, source)
        queue.extend(sorted(code))
        data |= found
    data = {ref for ref in data if not any(other.startswith(ref + '/') for other in data | closure)}
    return sorted(closure), sorted(data)

def _workflow_entry_job(workflow: str) -> tuple[str, str]:
    marker = re.search(r'(?m)^jobs:[ \t]*$', workflow)
    if marker is None:
        raise ContractError('Publisher workflow has no jobs section')
    jobs = [block for block in re.split(r'(?m)^(?=  [A-Za-z0-9_-]+:[ \t]*$)', workflow[marker.end():])
            if re.match(r'  [A-Za-z0-9_-]+:', block)]
    invoking = [block for block in jobs if ENTRYPOINT_PATH in block]
    if len(invoking) != 1:
        raise ContractError('Publisher workflow must invoke the entrypoint from exactly one job')
    return workflow[:marker.start()], invoking[0]

_SELECTOR_ERROR = 'Publisher entrypoint must keep the reviewed default estate scope selector'
_EXIT_CALLS = ('exit', '_exit', 'quit', 'abort')

def _is_scope_read(node: ast.AST, bindings: _Bindings) -> bool:
    """`os.environ.get(VAR, default)` or `os.getenv(VAR, default)` on the genuine `os` module."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and len(node.args) == 2 and not node.keywords
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == ENTRYPOINT_SCOPE_VARIABLE):
        return False
    func = node.func
    return ((func.attr == 'getenv' and bindings.genuine(func.value, 'os'))
            or (func.attr == 'get' and isinstance(func.value, ast.Attribute)
                and func.value.attr == 'environ' and bindings.genuine(func.value.value, 'os')))

def _uses(node: ast.AST, name: str) -> bool:
    return any(isinstance(item, ast.Name) and item.id == name for item in ast.walk(node))

def _may_exit(node: ast.AST) -> bool:
    """A return, raise, assert or process exit that runs without entering a nested function body."""
    stack = [node]
    while stack:
        item = stack.pop()
        if isinstance(item, (ast.Return, ast.Raise, ast.Assert)) or (
                isinstance(item, ast.Call) and _call_name(item) in _EXIT_CALLS):
            return True
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            stack.extend((*item.decorator_list, item.args))
        elif isinstance(item, ast.Lambda):
            stack.append(item.args)
        else:
            stack.extend(ast.iter_child_nodes(item))
    return False

def _scope_members(node: ast.AST, bindings: _Bindings, scope: ast.AST | None,
                   seen: frozenset[str] = frozenset()) -> frozenset[str]:
    """Strings of a literal scope set; a named set must be one literal module constant."""
    if isinstance(node, ast.Name):
        sites = bindings.resolve(node.id, scope)
        if (node.id in seen or not sites or len(sites) != 1
                or sites[0][0] is not None or sites[0][1] != 'assign'):
            raise ContractError(_SELECTOR_ERROR)
        node, scope, seen = sites[0][2].value, None, seen | {node.id}
    if not isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        raise ContractError(_SELECTOR_ERROR)
    members: set[str] = set()
    for item in node.elts:
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            members.add(item.value)
        elif isinstance(item, ast.Starred):
            members |= _scope_members(item.value, bindings, scope, seen)
        else:
            raise ContractError(_SELECTOR_ERROR)
    return frozenset(members)

def _takes(test: ast.AST, name: str, value: str, bindings: _Bindings, scope: ast.AST) -> bool:
    """Whether `if <test>` is taken for this scope value; anything unevaluable fails closed."""
    if not (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name)
            and test.left.id == name and len(test.ops) == 1):
        raise ContractError(_SELECTOR_ERROR)
    op, right = test.ops[0], test.comparators[0]
    if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(right, ast.Constant) and isinstance(right.value, str):
        return (value == right.value) == isinstance(op, ast.Eq)
    if isinstance(op, (ast.In, ast.NotIn)):
        return (value in _scope_members(right, bindings, scope)) == isinstance(op, ast.In)
    raise ContractError(_SELECTOR_ERROR)

def _route(statements: list[ast.stmt], name: str, value: str, bindings: _Bindings,
           scope: ast.AST) -> tuple[ast.stmt, ast.If | None] | None:
    """Partially evaluate the dispatch for one scope value.

    Returns the statement through which the value leaves, with the innermost
    taken `if` whose body holds it, or None when it falls through. A scope use
    other than an evaluable `if` test (a loop, `try`, nested function or call
    argument) fails closed.
    """
    for statement in statements:
        if isinstance(statement, ast.If) and _uses(statement.test, name):
            taken = _takes(statement.test, name, value, bindings, scope)
            result = _route(statement.body if taken else statement.orelse, name, value, bindings, scope)
            if result is not None:
                leaving, branch = result
                return leaving, branch if branch is not None else statement if taken else None
        elif _uses(statement, name):
            raise ContractError(_SELECTOR_ERROR)
        elif _may_exit(statement):
            return statement, None
    return None

def _runs_as_entrypoint(tree: ast.Module, function: ast.FunctionDef, bindings: _Bindings) -> bool:
    """`if __name__ == "__main__":` runs the selector's function, and nothing exits first."""
    guards = [node for node in tree.body if isinstance(node, ast.If)
              and isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name)
              and node.test.left.id == '__name__' and len(node.test.ops) == 1
              and isinstance(node.test.ops[0], ast.Eq)
              and isinstance(node.test.comparators[0], ast.Constant)
              and node.test.comparators[0].value == '__main__']
    own = bindings.resolve(function.name, None)
    if (len(guards) != 1 or guards[0].orelse or len(guards[0].body) != 1 or '__name__' in bindings.sites
            or function not in tree.body or not own or [node for _, _, node in own] != [function]
            or any(_may_exit(node) for node in tree.body[:tree.body.index(guards[0])])):
        return False
    statement = guards[0].body[0]
    call = (statement.value if isinstance(statement, ast.Expr)
            else statement.exc if isinstance(statement, ast.Raise) else None)
    if (isinstance(call, ast.Call) and _call_name(call) in ('SystemExit', 'exit')
            and len(call.args) == 1 and not call.keywords):
        call = call.args[0]
    return (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
            and call.func.id == function.name and not call.args and not call.keywords)

def entrypoint_default_scope(entrypoint: str) -> str:
    """The literal default of the entrypoint's one scope selector that drives dispatch.

    Reviewed shape: a module-level function that `if __name__ == "__main__":`
    runs reads `scope = os.environ.get(VAR, "estate")` (genuine `os`) as the
    only binding of that name. Evaluating its dispatch for each admitted value,
    `estate` falls through every scope test to the estate route and `lyte`
    leaves through the return of `if scope == "lyte":`. No exit precedes the
    selector, and an unreachable or captured branch fails closed.
    """
    try:
        tree = ast.parse(entrypoint)
    except (SyntaxError, ValueError):
        raise ContractError('Publisher entrypoint is not parseable Python') from None
    bindings = _Bindings(tree)
    mentions = [node for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and node.value == ENTRYPOINT_SCOPE_VARIABLE]
    selectors = [(function, node) for function in ast.walk(tree) if isinstance(function, ast.FunctionDef)
                 for node in function.body if isinstance(node, ast.Assign)
                 and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                 and _is_scope_read(node.value, bindings)]
    if len(mentions) != 1 or len(selectors) != 1:
        raise ContractError(_SELECTOR_ERROR)
    function, assignment = selectors[0]
    name, default = assignment.targets[0].id, assignment.value.args[1]
    stores = [node for node in ast.walk(function) if isinstance(node, ast.Name)
              and node.id == name and not isinstance(node.ctx, ast.Load)]
    own = bindings.resolve(name, function)
    dispatch = [node for node in ast.walk(function) if isinstance(node, ast.If)
                and isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name)
                and node.test.left.id == name and len(node.test.ops) == 1
                and isinstance(node.test.ops[0], ast.Eq)
                and isinstance(node.test.comparators[0], ast.Constant)
                and node.test.comparators[0].value == 'lyte'
                and node.body and isinstance(node.body[0], ast.Return)]
    if (len(stores) != 1 or not own or [node for _, _, node in own] != [assignment]
            or len(dispatch) != 1 or not isinstance(default, ast.Constant)
            or default.value != ADMITTED_DEFAULT_SCOPE
            or not _runs_as_entrypoint(tree, function, bindings)):
        raise ContractError(_SELECTOR_ERROR)
    index = function.body.index(assignment)
    last = max(position for position, node in enumerate(function.body) if _uses(node, name))
    prefix, region = function.body[:index], function.body[index + 1:last + 1]
    if any(_may_exit(node) or _uses(node, name) for node in prefix):
        raise ContractError(_SELECTOR_ERROR)
    if _route(region, name, ADMITTED_DEFAULT_SCOPE, bindings, function) is not None:
        raise ContractError(_SELECTOR_ERROR)
    lyte = _route(region, name, 'lyte', bindings, function)
    if lyte is None or not isinstance(lyte[0], ast.Return) or lyte[1] is not dispatch[0]:
        raise ContractError(_SELECTOR_ERROR)
    return default.value

def workflow_entrypoint_scopes(workflow: str, default: str) -> list[str]:
    """Every scope the invoking job can select; unresolved values fail closed."""
    head, job = _workflow_entry_job(workflow)
    scopes = {default}
    for line in (head + job).splitlines():
        if ENTRYPOINT_SCOPE_VARIABLE not in line:
            continue
        values = re.findall(ENTRYPOINT_SCOPE_VARIABLE + r'["\']?\s*[:=]\s*(\S+)', line)
        literals = [value.strip('"\'') for value in values]
        if not literals or any(re.fullmatch(r'[a-z]+', value) is None for value in literals):
            raise ContractError('Publisher workflow scope is not a reviewed literal')
        scopes.update(literals)
    return sorted(scopes)

def workflow_job_roots(workflow: str) -> list[str]:
    """Repository programs the entrypoint's job runs, including its gates."""
    _, job = _workflow_entry_job(workflow)
    if re.search(r'(?m)^\s*(?:-\s*)?uses:\s*["\']?\./', job):
        raise ContractError('Publisher workflow job uses an unreviewed local action')
    suffixes = '|'.join(re.escape(suffix[1:]) for suffix in CODE_SUFFIXES)
    roots = {_repo_path(match) for match in re.findall(
        r'(?<![\w./:@$-])(?:\./)?((?:[\w-][\w.-]*/)*[\w-][\w.-]*\.(?:' + suffixes + r'))(?![\w.-])', job)}
    for module in re.findall(r'(?:^|\s)-m\s+([\w.]+)', job):
        top = module.split('.', 1)[0]
        if top not in WORKFLOW_MODULES and top not in sys.stdlib_module_names:
            raise ContractError('Publisher workflow job runs an unreviewed module')
    if ENTRYPOINT_PATH not in roots:
        raise ContractError('Canonical workflow no longer invokes the owned publisher')
    return sorted(roots)

def validate_publisher_closure(publisher: str, entrypoint: str, workflow: str,
                               dependencies: dict[str, str] | None) -> dict[str, Any]:
    if (git_blob(publisher) != DYNAMIC_PUBLISHER_BLOB
            or git_blob(entrypoint) != DYNAMIC_ENTRYPOINT_BLOB):
        raise ContractError('Dynamic publisher and entrypoint require reviewed exact Git blobs')
    if not isinstance(dependencies, dict) or set(dependencies) != set(DYNAMIC_DEPENDENCY_BLOBS):
        raise ContractError('Complete reviewed publisher dependency closure is required')
    for path, expected in DYNAMIC_DEPENDENCY_BLOBS.items():
        source = dependencies[path]
        if not isinstance(source, str) or git_blob(source) != expected:
            raise ContractError(f'Publisher dependency requires a reviewed exact Git blob: {path}')
    if dependencies[WORKFLOW_PATH] != workflow:
        raise ContractError('Reviewed publisher workflow and supplied workflow disagree')
    # Exact bytes alone do not prove the admitted set is the route that runs.
    # Derive it statically from the workflow job and entrypoint; never execute.
    default = entrypoint_default_scope(entrypoint)
    scopes = workflow_entrypoint_scopes(workflow, default)
    if not set(scopes) <= set(ADMITTED_SCOPES):
        raise ContractError('Publisher workflow selects an entrypoint scope outside the admitted closure')
    sources = {path: source for path, source in dependencies.items() if path != WORKFLOW_PATH}
    sources.update({PUBLISHER_PATH: publisher, ENTRYPOINT_PATH: entrypoint})
    roots = workflow_job_roots(workflow)
    closure, data = derive_execution_closure(roots, sources)
    if set(closure) != set(sources):
        raise ContractError('Admitted publisher registry differs from the derived execution closure')
    admitted = {PUBLISHER_PATH: DYNAMIC_PUBLISHER_BLOB, ENTRYPOINT_PATH: DYNAMIC_ENTRYPOINT_BLOB,
                **DYNAMIC_DEPENDENCY_BLOBS}
    return {'schema': 'szl.lyte.publisher-execution-closure/v1',
            'reviewed_publisher_commit': REVIEWED_PUBLISHER_COMMIT,
            'derivation': 'STATIC_AST_NO_EXECUTION',
            'workflow': WORKFLOW_PATH, 'workflow_roots': roots,
            'entrypoint': ENTRYPOINT_PATH,
            'entrypoint_scope_variable': ENTRYPOINT_SCOPE_VARIABLE,
            'entrypoint_default_scope': default, 'workflow_scopes': scopes,
            'admitted_scopes': list(ADMITTED_SCOPES),
            'route': 'estate-default: generated flagships, Lyte, combined vertical-services; one process',
            'lyte_only': False,
            'admitted_blobs': dict(sorted(admitted.items())),
            'unbound_data_references': data}

def verified_source_revision(head: dict) -> str:
    value = head.get('sha')
    commit = head.get('commit')
    verification = commit.get('verification') if isinstance(commit, dict) else None
    if (not isinstance(value, str) or not SHA40.fullmatch(value)
            or value == '0' * 40 or not isinstance(verification, dict)
            or verification.get('verified') is not True):
        raise ContractError('Backend tip must be an exact verified nonzero Git commit')
    return value

def admit_source_checks(head: dict, evidence: dict) -> str:
    revision = verified_source_revision(head)
    checks = evidence.get('check_runs')
    count = evidence.get('total_count')
    if (not isinstance(checks, list) or type(count) is not int
            or count != len(checks)):
        raise ContractError('Complete backend check-run evidence is required')
    trusted = [row for row in checks if isinstance(row, dict)
               and row.get('head_sha') == revision and isinstance(row.get('app'), dict)
               and row['app'].get('slug') == 'github-actions']
    for name in SOURCE_REQUIRED_CHECKS:
        rows = [row for row in trusted if row.get('name') == name]
        if not rows or any(row.get('status') != 'completed'
                           or row.get('conclusion') != 'success' for row in rows):
            raise ContractError(f'Backend source gate did not pass: {name}')
    return revision

def github_json(path: str) -> dict:
    """Read only the public backend's fixed GitHub origin, without credentials."""
    allowed = r'/repos/szl-holdings/lyte-services/commits/(?:main|[0-9a-f]{40}/check-runs\?filter=latest&per_page=100&page=[1-9][0-9]?)'
    if re.fullmatch(allowed, path) is None:
        raise ContractError('Unadmitted GitHub source-evidence route')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ContractError('GitHub source-evidence redirect refused')
    request = urllib.request.Request('https://api.github.com' + path, headers={
        'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
        'Cache-Control': 'no-cache', 'User-Agent': 'SZL-Lyte-ReadOnly-Authority/3',
    })
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=30) as response:
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ContractError('GitHub source-evidence response exceeds its bound')
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ContractError('Duplicate GitHub evidence JSON key')
            result[key] = value
        return result
    result = json.loads(payload, object_pairs_hook=unique_object)
    if not isinstance(result, dict):
        raise ContractError('GitHub source-evidence response must be an object')
    return result

def read_source_evidence() -> tuple[dict, dict]:
    head = github_json('/repos/szl-holdings/lyte-services/commits/main')
    revision = verified_source_revision(head)
    checks = []
    count = None
    for page in range(1, 11):
        item = github_json(f'/repos/szl-holdings/lyte-services/commits/{revision}/check-runs?filter=latest&per_page=100&page={page}')
        rows, total = item.get('check_runs'), item.get('total_count')
        if (not isinstance(rows, list) or type(total) is not int or total < 0
                or total > 1000 or len(rows) > 100 or (count is not None and total != count)):
            raise ContractError('Backend check-run pagination is incomplete or changed')
        count = total
        checks.extend(rows)
        if len(checks) == count:
            return head, {'check_runs': checks, 'total_count': count}
        if not rows or len(checks) > count:
            break
    raise ContractError('Complete backend check-run pagination is required')

def require_current_source(revision: str) -> None:
    if verified_source_revision(github_json('/repos/szl-holdings/lyte-services/commits/main')) != revision:
        raise ContractError('Backend tip changed after read-only source admission')

def constants(source: str) -> dict[str, Any]:
    result = {}
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        raise ContractError('Publisher source is not parseable Python') from None
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                result[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return result

def validate_card(text: str) -> None:
    if not text.startswith('---\n'):
        raise ContractError('README must start with Hub YAML metadata')
    end = text.find('\n---\n', 4)
    if end < 0:
        raise ContractError('README metadata closing delimiter missing')
    rows = [line.split(':', 1)[1].strip() for line in text[4:end].splitlines() if line.startswith('short_description:')]
    if len(rows) != 1:
        raise ContractError('Exactly one short_description is required')
    raw = rows[0]
    quoted = len(raw) >= 2 and raw[0] in {'"', "'"} and raw[-1] == raw[0]
    if ':' in raw and not quoted:
        raise ContractError('Colon-bearing description must be quoted')
    value = raw[1:-1] if quoted else raw
    if not value or len(value) > 60:
        raise ContractError('Description must contain 1..60 characters')

def validate_caller(text: str) -> None:
    if not re.search(r'(?m)^permissions:\s*\n  contents: read\s*$', text):
        raise ContractError('Caller must explicitly have read-only contents permission')
    forbidden = (
        r'\$\{\{\s*secrets\.',
        r'(?m)^\s+[\w-]+:\s*write\s*$',
        r'(?m)^\s+HF_[A-Z_]+:',
        r'reusable-hf-deploy\.yml@',
        r'\b(?:upload_folder|upload_file|create_repo|restart_space|pause_space)\s*\(',
    )
    if any(re.search(pattern, text) for pattern in forbidden):
        raise ContractError('Presentation caller must not own a provider credential or write lane')

def validate(alignment: dict, publisher: str, entrypoint: str, workflow: str,
             caller: str, readme: str, *, source_head: dict | None = None,
             source_checks: dict | None = None,
             publisher_dependencies: dict[str, str] | None = None) -> dict:
    validate_card(readme)
    validate_caller(caller)
    if alignment.get('schema') != 'szl.estate.alignment/v1':
        raise ContractError('Unrecognized estate authority schema')
    rows = [row for row in alignment.get('public_bodies', []) if row.get('id') == 'lyte']
    if len(rows) != 1:
        raise ContractError('Lyte must have exactly one public body')
    expected = {'backend_source': 'szl-holdings/lyte-services', 'presentation_source': 'szl-holdings/lyte-lattice', 'hub_surface': 'SZLHOLDINGS/lyte'}
    if any(rows[0].get(key) != value for key, value in expected.items()):
        raise ContractError('Lyte runtime, presentation, or Hub authority changed')
    policy = alignment.get('hub_alias_policy', {})
    if policy.get('duplicate_authority_spaces_forbidden') is not True or 'lyte' not in policy.get('canonical_public_space_slugs', []):
        raise ContractError('Canonical Space / duplicate-authority policy missing')
    owner = constants(publisher)
    entry = constants(entrypoint)
    if owner.get('SOURCE_REPOSITORY') != expected['backend_source'] or owner.get('HF_REPOSITORY') != expected['hub_surface']:
        raise ContractError('Publisher does not target the admitted backend and Space')
    revision = owner.get('SOURCE_REVISION')
    dynamic = 'SOURCE_REVISION' not in owner
    closure = None
    if dynamic:
        closure = validate_publisher_closure(publisher, entrypoint, workflow, publisher_dependencies)
        if (owner.get('SOURCE_VARIABLE') != 'LYTE_SOURCE_REVISION'
                or owner.get('SOURCE_REQUIRED_CHECKS') != SOURCE_REQUIRED_CHECKS):
            raise ContractError('Dynamic publisher and entrypoint require reviewed exact Git blobs')
        if source_head is None or source_checks is None:
            raise ContractError('Dynamic publisher requires actual immutable source evidence')
        revision = admit_source_checks(source_head, source_checks)
    else:
        if not isinstance(revision, str) or not SHA40.fullmatch(revision) or revision == '0' * 40:
            raise ContractError('Backend revision must be an immutable Git commit')
        if entry.get('LYTE_SOURCE_REVISION') != revision:
            raise ContractError('Vertical entrypoint and Lyte source pins disagree')
    if entry.get('SOURCE_OWNED_FLAGSHIP_SLUGS') != ('lyte',):
        raise ContractError('Lyte must remain source-owned, not a generic generated shell')
    if 'hf_publish_lyte_enterprise.py' not in entrypoint or 'hf_publish_vertical_flagships_v4.py' not in workflow:
        raise ContractError('Canonical workflow no longer invokes the owned publisher')
    if owner.get('ORIGIN') != 'https://szlholdings-lyte.hf.space':
        raise ContractError('Unexpected runtime origin')
    result = {'schema': 'szl.lyte.canonical-delegation/v2', 'state': 'DELEGATED',
            **expected, 'backend_source_revision': revision,
            'source_revision_policy': 'reviewed-verified-current-tip' if dynamic else 'matching-immutable-static-pins',
            'backend_signature_verified': dynamic,
            'required_source_checks': list(SOURCE_REQUIRED_CHECKS) if dynamic else [],
            'backend_tip_reverified': False,
            'publisher_repository': 'szl-holdings/a11oy',
            'publisher_workflow': '.github/workflows/hf-sync.yml',
            'publisher_entrypoint': 'scripts/hf_publish_vertical_flagships_v4.py',
            'source_owned_publisher': 'scripts/hf_publish_lyte_enterprise.py',
            'retired_space': 'SZLHOLDINGS/lyte-lattice',
            'retired_space_recreated': False, 'provider_writes': False,
            'provider_credentials_local': False, 'runtime_observed': False,
            'scope': 'SOURCE_AUTHORITY_ONLY_NOT_RUNTIME_ACCEPTANCE'}
    if closure is not None:
        result['publisher_execution_closure'] = closure
    return result

def revision(root: Path) -> str:
    value = subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--verify', 'HEAD'], text=True).strip()
    if not SHA40.fullmatch(value):
        raise ContractError('Checkout is not bound to a full commit identity')
    return value

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--governance', type=Path, required=True)
    parser.add_argument('--publisher', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    paths = {'alignment': args.governance / 'estate/alignment.v1.json',
             'publisher': args.publisher / PUBLISHER_PATH,
             'entrypoint': args.publisher / ENTRYPOINT_PATH,
             'workflow': args.publisher / WORKFLOW_PATH,
             'caller': args.source / '.github/workflows/hf-deploy.yml',
             'readme': args.source / 'README.md'}
    content = {key: path.read_bytes().decode('utf-8') for key, path in paths.items()}
    # Every production CLI invocation admits the entire reviewed closure first,
    # reading every registered file from the publisher checkout and deriving the
    # workflow-selected route. A legacy static SOURCE_REVISION cannot bypass it.
    dependencies = {path: (args.publisher / path).read_bytes().decode('utf-8')
                    for path in DYNAMIC_DEPENDENCY_BLOBS}
    closure = validate_publisher_closure(content['publisher'], content['entrypoint'],
                                         content['workflow'], dependencies)
    source = {'publisher_dependencies': dependencies}
    if 'SOURCE_REVISION' not in constants(content['publisher']):
        source['source_head'], source['source_checks'] = read_source_evidence()
    result = validate(json.loads(content['alignment']), content['publisher'], content['entrypoint'], content['workflow'], content['caller'], content['readme'], **source)
    result['checkout_revisions'] = {'presentation': revision(args.source), 'governance': revision(args.governance), 'publisher': revision(args.publisher)}
    result['input_sha256'] = {key: hashlib.sha256(value.encode()).hexdigest() for key, value in content.items()}
    result['publisher_dependency_blobs'] = dict(DYNAMIC_DEPENDENCY_BLOBS)
    result['publisher_execution_closure'] = closure
    if 'source_head' in source:
        require_current_source(result['backend_source_revision'])
        result['backend_tip_reverified'] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
