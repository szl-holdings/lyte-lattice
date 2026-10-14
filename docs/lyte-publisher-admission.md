# Canonical Lyte publisher source admission

The presentation package's read-only ownership verifier admits exact Git blobs
from `szl-holdings/a11oy`. The complete closure below was reviewed at commit
`e6cf9d06c92827225054550533e1a091b59f1031`. Every Python blob is byte-identical
at the earlier review commit `a2a9292346fa02d4c239564b6773f704204ea541`. Only
`.github/workflows/hf-sync.yml` changed between them, and that diff is limited
to third-party action pin bumps (`upload-artifact` v7.0.2, `harden-runner`
v2.22.1, `setup-node` v7.1.0).

## Admitted scope: the default estate route, not Lyte alone

The `publish-vertical-flagships` job in `hf-sync.yml` runs
`scripts/hf_publish_vertical_flagships_v4.py` without `SZL_FLAGSHIP_SCOPE`.
The entrypoint therefore takes its default `estate` route. That route runs
three publishers in one Python process, loading each with `exec_module`:

1. the generated-flagship publisher (Terra, Sentra, Counsel and Finance shells);
2. the source-owned Lyte publisher;
3. the combined vertical-services intelligence publisher.

Earlier admissions covered only the Lyte files. They did not cover the sibling
publishers that run before and after Lyte in the same process. This admission
binds the whole route, plus the job's own gates: the exact-main ownership
check, the vertical plan gate and the completion helper. An explicit
`SZL_FLAGSHIP_SCOPE=lyte` runs a subset of this closure and is also admitted.
Every other scope (`finance`, `sentra`, `terra`, `counsel`) does not publish
Lyte and fails closed. So does any non-literal scope value.

| Path | Git blob | Role |
| --- | --- | --- |
| `.github/workflows/hf-sync.yml` | `516f8334617cf4967465372db2ab61a50b49349b` | Workflow; job invokes the entrypoint with the default scope |
| `scripts/hf_publish_vertical_flagships_v4.py` | `508293e2631f0f7b952cfe06eb4836fdd81cffa4` | Entrypoint and scope dispatch |
| `scripts/hf_publish_lyte_enterprise.py` | `7c533d753a2b913a77bb71074f04aa5b753b0392` | Lyte publisher (`SZLHOLDINGS/lyte`) |
| `scripts/szl_release_guard.py` | `f6c7bc02df02076388be5fa0b6949d8929cc2ba2` | Lyte release primitive |
| `scripts/lyte_enterprise_live_contract.py` | `494116f65b24ea5b8a516abde31668be2248cbf4` | Lyte live contract |
| `scripts/hf_existing_space_guard.py` | `364e0bba7dc4e0abb7730f210263b3fd4387d144` | Existing-Space guard on `HfApi.create_repo` |
| `scripts/hf_exact_main_ownership.py` | `6e95133ac74f0d05d5372ed68022a691ceaa15c2` | Job gate: exact protected main |
| `scripts/estate_repair_dispatch.py` | `81f0e83729390ee66b633a8d45e5f1139374ba41` | Job gate: approved vertical plan |
| `scripts/estate_child_completion.py` | `5e59e91824d58da9bcc650c623c3bdfaf6f0040b` | Job gate: completion receipt |
| `scripts/hf_publish_vertical_flagships_v4_impl.py` | `6337abaa2151b2a71998fd19aaf39fa2ef88bf2b` | Generated-flagship overlay (runs before Lyte) |
| `scripts/_hf_publish_vertical_flagships_v4_impl_base.py` | `419931621a3d7de4da233840762761c4207007f5` | Generated-flagship writer |
| `scripts/hf_finance_read_proxy.py` | `841fee9442d6955925f3214b5ff8fd27eeede903` | Finance projection emitted into the Space app |
| `scripts/hf_flagship_runtime_contract.py` | `1b3571a8b49c31f12307bf44e77c303d2b86fb32` | Generated Space Dockerfile and requirements |
| `scripts/hf_finance_workspace.py` | `b3ec64fec7e60f5a98bf61550f72dbf441c3d635` | Finance presentation |
| `scripts/hf_finance_research_workspace.py` | `18ba3c0a1feb776e7f12f46c5b69b6069b597180` | Finance presentation |
| `scripts/hf_finance_signed_workspace.py` | `febc20a7dc1391d35397bb81e38222135eb3d100` | Finance presentation |
| `scripts/hf_finance_functional_gate.py` | `9c5b7cf066f612b0b7a6687fe3bdafc2414d07c0` | Read-only Finance public witness |
| `scripts/hf_finance_projection_manifest.py` | `4d00c2d0b1005c4f23f37c810754bdeb7eff4453` | Finance manifest and immutable Hub readback |
| `scripts/hf_publish_vertical_services_intelligence_v4.py` | `c4191e7f6139ad934fe9c8809174476934b2eb59` | Combined publisher, intelligence layer (runs after Lyte) |
| `scripts/hf_publish_vertical_services_frontier_v3.py` | `69b19505d307f22faeee49a98d11c97a58abd603` | Combined publisher, frontier layer |
| `scripts/hf_publish_vertical_services.py` | `3f51f74299235e99d3a1fce3b1eae3163014beba` | Combined writer (`SZLHOLDINGS/vertical-services`) |

## What the sibling publishers do

- **Generated flagships.** This route writes the existing `SZLHOLDINGS/terra`,
  `sentra`, `counsel` and `finance` Spaces. Each file is a separate
  `upload_file` commit with no parent compare-and-swap, followed by
  `restart_space`. The route then polls public endpoints for up to 30 minutes.
  The entrypoint strips Lyte and Vessels from this writer.
- **Space creation on this route.** On the estate route the existing-Space guard
  reuses an existing Space. It delegates to `create_repo` only after an exact
  404, so both sibling writers can still create a missing public Space. Only
  the selected single-target scopes block creation.
- **Combined vertical-services.** This route writes `SZLHOLDINGS/vertical-services`.
  It creates the `SENTRA_SIGNING_KEY` Space secret only when absent (a random
  value, never printed) and sets the `SZL_SOURCE_REVISION` Space variable. It
  checks out `szl-holdings/vertical-services` at the tip resolved by the
  entrypoint, which must pass that repository's Python contract suite. It then
  runs a separately pinned controller,
  `szl-holdings/.github@c889276e51e7d954c4bba8b216f86fc7577721fa`
  (blob `9d5b90b8bbf04e6d46ef0f971fc65604e1323b1b`), in a subprocess.
  Publishing (`--require-default-branch-tip`), restart and attestation all
  happen in that subprocess.
- **Finance helpers.** Most of these files are presentation strings or code
  emitted into the Space. The functional gate and the projection manifest only
  read: they make fixed public HTTP requests and immutable Hub readbacks, with
  no credentials.

The Lyte publisher still targets only backend `szl-holdings/lyte-services` and
the existing Space `SZLHOLDINGS/lyte`. It requires a verified current backend
commit, all 17 source check names, the GitHub Actions app identity, and its
separately pinned controller,
`szl-holdings/.github@163a61fd9759e5ecc3c2daf13e528f7b281ff81d`
(`.github/scripts/hf_deploy_from_dockerfile.py`, blob
`3fa968416a3623d66b5b5b64abf8b830cc854e1c`). Both controllers are checked
against their blobs before execution.

## How the verifier binds the route

Before it looks up evidence, reads checkout revisions or writes a receipt, the
verifier makes four checks:

1. Every admitted path must have its exact reviewed blob; CRLF and LF bytes are
   distinct identities. The supplied workflow must equal the admitted copy.
2. The entrypoint must read `SZL_FLAGSHIP_SCOPE` exactly once, through
   `os.environ.get` or `os.getenv` with the literal default `estate`. `os` must
   be the genuine module: imported, never rebound, shadowed by a parameter,
   patched (`os.environ = ...`) or passed on. That read must be the only binding
   of its name inside a module-level function, and that function must be what
   `if __name__ == "__main__":` runs, with no exit before the selector. The
   verifier then evaluates the dispatch for each admitted value. `estate` must
   fall through every scope test to the estate route, and `lyte` must leave
   through the return of `if scope == "lyte":`. Scope tests may compare with a
   literal (`==`, `!=`) or test membership (`in`, `not in`) in a literal set or
   a single literal module constant. Anything else fails closed: an
   unevaluable test, a scope use inside a loop, `try` or nested function, or a
   branch that captures either value first. The invoking job and the
   workflow-level env may select only `estate` or `lyte`.
3. The workflow roots are every repository program the invoking job runs, and
   the closure is derived from them statically, with AST only and no
   execution. The derivation follows `__file__`-anchored paths (`HERE / "x.py"`,
   `with_name`, `parents[n]`), `scripts/...` literals, sibling imports,
   `importlib`/`runpy` targets and `-m` module arguments, transitively.
   Python, shell and JavaScript/TypeScript suffixes are all code, including
   `.jsx`, `.tsx`, `.mts` and `.cts`. The following fail closed:
   - a relative import, or a path escaping the repository;
   - any import outside the standard library and `huggingface_hub`;
   - a loader target unless it is a literal, a `__file__`-anchored path, or a
     parameter whose every same-module call site resolves the same way (the
     entrypoint's `load_module` chain). The anchor must be exact where the
     loader runs. Every binding the load can observe in its own scope must be
     an anchored assignment. An anchor in an unrelated function, or one
     overwritten by any other binding (assignment, loop, `with`, `except`,
     walrus, augmented assignment, import, `global`, parameter), does not
     count. Neither does a rebound `__file__`, a non-genuine `os.path` or a
     shadowed `pathlib` constructor;
   - any directory enumeration (`os.listdir`, `os.scandir`, `os.walk`,
     `glob.glob`/`iglob`, `Path.glob`/`rglob`/`iterdir`/`walk`), anchored or
     not, because the job runs at the repository root. Listing is recognised
     by name on any receiver, and through aliases: `import os as o`,
     `from os import listdir as ls`, `from os import *`, `L = os.listdir`, and
     by string through `getattr`, `methodcaller` or subscripts. A listing
     module may appear only as an attribute receiver or in a literal
     `getattr` probe, such as the release guard's `getattr(os, "O_NOFOLLOW", 0)`.
     Only the genuine `ast` module's `walk` is exempt. The one exception is a
     glob on an unanchored path whose literal pattern ends in a concrete,
     wildcard-free, non-code suffix. That covers the Lyte publisher's
     run-local `*.json` replay-journal check, which cannot select code.
4. The derived closure must equal the admitted registry exactly. An
   unreferenced registered file is rejected, and so is an unregistered helper.

The receipt records the closure under `publisher_execution_closure`: the
reviewed commit, workflow roots, scopes, every admitted path and blob,
`lyte_only: false`, and the repository data files the route reads without a
blob binding. Unrelated publisher-repository commits remain admissible only
while this entire closure is byte-identical; the exact checkout revision is
recorded.

## Remaining limits

- Exact blob binding means any change to any of these 21 files, including
  unrelated Terra, Finance or vertical-services edits, turns this verifier red
  until it is reviewed again.
- Data inputs are disclosed, not bound. These are the Terra forge bundle under
  `deployments/vertical-forge/terra/`, the Finance component manifests under
  `verticals/puriq-markets/runtime/components/`, and the run's own flagship
  receipt. The publishers parse them as data and check the Terra bundle's
  hash chain themselves.
- Out of scope: the external controller bytes (pinned by blob inside admitted
  code), the `vertical-services` and `lyte-services` sources, third-party
  actions and the `huggingface_hub` package.
- The derivation is static. It cannot see paths passed indirectly through
  helper parameters from non-literal sources, so exact-blob review remains the
  authority for that. The same applies to dynamic namespace writes
  (`globals()[...]`, `exec`), attribute names computed on objects other than
  a listing module, in-process environment mutation before the scope read,
  and what each dispatch branch's call does once reached.
- The generated-flagship publisher runs before Lyte in the same process and can
  poll for up to 30 minutes inside a 50-minute job. That is an availability
  risk for the Lyte publication, not an authority change.
- This admission records what the route does. It does not approve the sibling
  writers' create-on-absence or non-atomic per-file uploads for the other
  Spaces.

No provider code is executed by this presentation verifier. Its source checks,
current-tip recheck, canonical-target policy, read-only permissions, and
prohibition on local publisher credentials remain required. The retired
`SZLHOLDINGS/lyte-lattice` Space remains retired. A successful delegation receipt
establishes source ownership only, not runtime readiness or live deployment.
