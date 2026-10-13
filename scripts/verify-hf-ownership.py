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
# at REVIEWED_PUBLISHER_COMMIT. Every Python blob below is byte-identical at the
# earlier a2a9292346fa02d4c239564b6773f704204ea541 review; only the workflow
# changed (third-party action pin bumps). The Lyte publisher pins controller
# .github@163a61fd9759e5ecc3c2daf13e528f7b281ff81d; the combined vertical-services
# writer separately pins .github@c889276e51e7d954c4bba8b216f86fc7577721fa.
# Admission scope and reviewed identities: docs/lyte-publisher-admission.md.
# A new publisher, entrypoint, route or closure file requires a separate review.
REVIEWED_PUBLISHER_COMMIT = 'e6cf9d06c92827225054550533e1a091b59f1031'
PUBLISHER_PATH = 'scripts/hf_publish_lyte_enterprise.py'
ENTRYPOINT_PATH = 'scripts/hf_publish_vertical_flagships_v4.py'
WORKFLOW_PATH = '.github/workflows/hf-sync.yml'
DYNAMIC_PUBLISHER_BLOB = '7c533d753a2b913a77bb71074f04aa5b753b0392'
DYNAMIC_ENTRYPOINT_BLOB = '508293e2631f0f7b952cfe06eb4836fdd81cffa4'
# The workflow runs the entrypoint without SZL_FLAGSHIP_SCOPE, so its default
# estate route executes in ONE process: the generated-flagship publisher, then
# the Lyte publisher, then the combined vertical-services publisher. Bind that
# whole route, plus the workflow job's own source, plan and completion gates.
DYNAMIC_DEPENDENCY_BLOBS = {
    WORKFLOW_PATH: '516f8334617cf4967465372db2ab61a50b49349b',
    'scripts/szl_release_guard.py': 'f6c7bc02df02076388be5fa0b6949d8929cc2ba2',
    'scripts/lyte_enterprise_live_contract.py': '494116f65b24ea5b8a516abde31668be2248cbf4',
    'scripts/hf_existing_space_guard.py': '364e0bba7dc4e0abb7730f210263b3fd4387d144',
    'scripts/hf_exact_main_ownership.py': '6e95133ac74f0d05d5372ed68022a691ceaa15c2',
    'scripts/estate_repair_dispatch.py': '81f0e83729390ee66b633a8d45e5f1139374ba41',
    'scripts/estate_child_completion.py': '5e59e91824d58da9bcc650c623c3bdfaf6f0040b',
    # Generated-flagship route (Terra, Sentra, Counsel, Finance shells).
    'scripts/hf_publish_vertical_flagships_v4_impl.py': '6337abaa2151b2a71998fd19aaf39fa2ef88bf2b',
    'scripts/_hf_publish_vertical_flagships_v4_impl_base.py': '419931621a3d7de4da233840762761c4207007f5',
    'scripts/hf_finance_read_proxy.py': '841fee9442d6955925f3214b5ff8fd27eeede903',
    'scripts/hf_flagship_runtime_contract.py': '1b3571a8b49c31f12307bf44e77c303d2b86fb32',
    'scripts/hf_finance_workspace.py': 'b3ec64fec7e60f5a98bf61550f72dbf441c3d635',
    'scripts/hf_finance_research_workspace.py': '18ba3c0a1feb776e7f12f46c5b69b6069b597180',
    'scripts/hf_finance_signed_workspace.py': 'febc20a7dc1391d35397bb81e38222135eb3d100',
    'scripts/hf_finance_functional_gate.py': '9c5b7cf066f612b0b7a6687fe3bdafc2414d07c0',
    'scripts/hf_finance_projection_manifest.py': '4d00c2d0b1005c4f23f37c810754bdeb7eff4453',
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
CODE_SUFFIXES = ('.py', '.pyw', '.pyc', '.pyz', '.pyd', '.pth', '.so', '.sh', '.bash')
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

def _anchored(node: ast.AST, origin: str, names: dict[str, frozenset[str]]) -> frozenset[str] | None:
    """Repository paths of an expression anchored at this file's own location."""
    if isinstance(node, ast.Name):
        return frozenset({origin}) if node.id == '__file__' else names.get(node.id)
    if isinstance(node, ast.Attribute) and node.attr == 'parent':
        base = _anchored(node.value, origin, names)
        return None if base is None else frozenset(_parent(path) for path in base)
    if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
            and node.value.attr == 'parents'):
        base = _anchored(node.value.value, origin, names)
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
        base = _anchored(node.left, origin, names)
        if base is None:
            return None
        part = _literal_part(node.right)
        return frozenset(_join(path, part) for path in base)
    if not isinstance(node, ast.Call):
        return None
    func, name = node.func, _call_name(node)
    if (name in ('listdir', 'scandir', 'walk', 'glob', 'iglob') and node.args
            and _anchored(node.args[0], origin, names) is not None):
        raise ContractError('Publisher closure enumerates a repository directory')
    if isinstance(func, ast.Attribute) and _is_os_path(func.value) and node.args:
        base = _anchored(node.args[0], origin, names)
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
    if name in ('Path', 'PurePath', 'PurePosixPath', 'PosixPath') and node.args:
        base = _anchored(node.args[0], origin, names)
        if base is None:
            return None
        parts = [_literal_part(arg) for arg in node.args[1:]]
        return frozenset(_join(path, '/'.join(parts)) if parts else path for path in base)
    if isinstance(func, ast.Attribute):
        base = _anchored(func.value, origin, names)
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
        if func.attr in ('glob', 'rglob', 'iterdir', 'walk'):
            raise ContractError('Publisher closure enumerates a repository directory')
    return None

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
                if target is None or not (
                        isinstance(target, (ast.Name, ast.Attribute))
                        or (isinstance(target, ast.Constant) and isinstance(target.value, str))
                        or _anchored(target, path, names) is not None):
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

def entrypoint_default_scope(entrypoint: str) -> str:
    """The literal default of the entrypoint's single scope selector."""
    try:
        tree = ast.parse(entrypoint)
    except (SyntaxError, ValueError):
        raise ContractError('Publisher entrypoint is not parseable Python') from None
    mentions = [node for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and node.value == ENTRYPOINT_SCOPE_VARIABLE]
    defaults = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and _call_name(node) in ('get', 'getenv') and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == ENTRYPOINT_SCOPE_VARIABLE):
            value = node.args[1] if len(node.args) == 2 and not node.keywords else None
            defaults.append(value.value if isinstance(value, ast.Constant) else None)
    if len(mentions) != 1 or len(defaults) != 1 or defaults[0] != ADMITTED_DEFAULT_SCOPE:
        raise ContractError('Publisher entrypoint must keep the reviewed default estate scope selector')
    return defaults[0]

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
    roots = {_repo_path(match) for match in re.findall(
        r'(?<![\w./:@$-])(?:\./)?((?:[\w-][\w.-]*/)*[\w-][\w.-]*\.(?:py|pyw|sh|bash|mjs|cjs|js|ts))(?![\w.-])', job)}
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
